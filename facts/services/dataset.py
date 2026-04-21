from collections import defaultdict
from datetime import date, datetime

from django.core.cache import cache

from ..models import FactsStepPathOverride
from .common import _as_of_cutoff, _as_of_date, _natural_sort_key, normalize_layer_value
from .history_state import (
    _build_plan_summary_map,
    _build_tip_missing_summary_map,
    _empty_plan_summary,
    _empty_tip_missing_summary,
    _make_override_target_list,
)
from .path_utils import (
    _compact_cham_tokens,
    _flatten_body_values,
    _merge_cham_html,
    _merge_eqpgroup_html,
    _parse_eqpgroup_tokens,
    _parse_path_members,
    _path_signature,
)
from .prevent import _get_tip_threshold_days, _row_is_tip_prevented
from .source import _base_source_queryset, _build_path_key, _build_step_key


def build_step_dataset(
    snap_date,
    processid=None,
    areaname=None,
    layerid=None,
    lineid=None,
    compat_filter="all",
    include_measure=True,
    include_emergency=True,
    exclude_skiprule_100=False,
    tip_mode=False,
    for_prp_table=False,
    as_of_date=None,
):
    resolved_as_of = _as_of_date(as_of_date) or _as_of_date(snap_date) or date.today()
    cache_key = f"facts:step-dataset:{snap_date}|{resolved_as_of}|{processid}|{areaname}|{layerid}|{lineid}|{compat_filter}|{int(bool(include_measure))}|{int(bool(include_emergency))}|{int(bool(exclude_skiprule_100))}|{int(bool(tip_mode))}|{int(bool(for_prp_table))}|{_get_tip_threshold_days()}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    threshold_days = _get_tip_threshold_days()
    source_rows = _base_source_queryset(
        snap_date=snap_date,
        processid=processid,
        areaname=areaname,
        layerid=layerid,
        lineid=lineid,
        include_measure=include_measure,
        exclude_skiprule_100=exclude_skiprule_100,
    )

    override_qs = FactsStepPathOverride.objects.filter(snap_date=snap_date, is_active=True)
    if processid:
        override_qs = override_qs.filter(processid=processid)
    if lineid:
        override_qs = override_qs.filter(lineid=lineid)
    override_qs = override_qs.filter(created_at__lte=_as_of_cutoff(resolved_as_of), updated_at__lte=_as_of_cutoff(resolved_as_of))

    overrides = {}
    for o in override_qs:
        key = _build_path_key(o.lineid, o.processid, o.stepseq, o.recipeid, o.path, o.eqpline, o.childeqp)
        overrides[key] = o

    step_map = defaultdict(lambda: {
        "snap_date": snap_date,
        "lineid": "",
        "processid": "",
        "stepseq": "",
        "recipeid_set": set(),
        "areaname": "",
        "layerid": "",
        "skiprule": "",
        "descript": "",
        "stepseq_type": "",
        "eqpgroup_values": set(),
        "cham_values": set(),
        "tip_eqpgroup_values": set(),
        "tip_cham_values": set(),
        "paths": [],
        "tip_values": set(),
        "tip_detail_rows": [],
        "tip_age_days": {},
        "childeqp_values": set(),
        "path_signatures": set(),
        "tip_path_signatures": set(),
    })

    cutoff_dt = _as_of_cutoff(resolved_as_of)
    for row in source_rows:
        row_key = _build_step_key(row)
        path_key = _build_path_key(row.lineid, row.processid, row.stepseq, row.recipeid, row.path, row.eqpline, row.childeqp)
        override = overrides.get(path_key)
        final_always_emergency = override.manual_always_emergency if override and override.manual_always_emergency else (row.always_emergency or "")
        final_major_minor = override.manual_major_minor if override and override.manual_major_minor else ""
        if not include_emergency and final_always_emergency == "비상시":
            continue
        is_tip_prevented = _row_is_tip_prevented(row, threshold_days, as_of_date=resolved_as_of)
        final_body_compat = row.body_compat or "N"
        final_cham_compat = row.cham_compat or "N"
        final_body_count = row.body_compat_count or 0
        final_cham_count = row.cham_compat_count or 0

        step_item = step_map[row_key]
        step_item["lineid"] = row.lineid or ""
        step_item["processid"] = row.processid or ""
        step_item["stepseq"] = row.stepseq or ""
        step_item["areaname"] = row.areaname or ""
        step_item["layerid"] = normalize_layer_value(row.layerid)
        step_item["skiprule"] = row.skiprule or ""
        step_item["descript"] = row.descript or ""
        step_item["stepseq_type"] = row.stepseq_type or ""

        if row.recipeid:
            step_item["recipeid_set"].add(str(row.recipeid).upper())
        if row.eqpgroup:
            for token in _parse_eqpgroup_tokens(row.eqpgroup):
                step_item["eqpgroup_values"].add(token)
        if row.tip:
            raw_tip = str(row.tip).strip()
            step_item["tip_values"].add(raw_tip)
            age_days = 0
            if row.eventtime and cutoff_dt is not None:
                try:
                    if getattr(row.eventtime, "tzinfo", None):
                        age_days = (cutoff_dt - row.eventtime.replace(tzinfo=None)).days
                    else:
                        age_days = (cutoff_dt - row.eventtime).days
                except Exception:
                    age_days = 0
            age_days = max(int(age_days), 0)
            tip_text = raw_tip.split(":", 1)[1].strip() if ":" in raw_tip else raw_tip
            member_tokens = [t.strip() for t in tip_text.split(",") if t.strip()]
            if not member_tokens and tip_text:
                member_tokens = [tip_text]
            for part in member_tokens:
                prev_age = step_item["tip_age_days"].get(part)
                if prev_age is None or age_days > prev_age:
                    step_item["tip_age_days"][part] = age_days
        if row.childeqp:
            step_item["childeqp_values"].add(str(row.childeqp))
        path_members = _parse_path_members(row.path, row.eqpgroup)
        path_sig = _path_signature(row)
        if path_sig:
            step_item["path_signatures"].add(path_sig)
            if not is_tip_prevented:
                step_item["tip_path_signatures"].add(path_sig)
        for m in path_members:
            body_name = str(m.get("eqp_body_name") or "").strip().upper()
            cham_name = str(m.get("display_name") or "").strip().upper()
            if body_name:
                step_item["eqpgroup_values"].add(body_name)
                if not is_tip_prevented:
                    step_item["tip_eqpgroup_values"].add(body_name)
            if m["has_cham"] and cham_name:
                step_item["cham_values"].add(cham_name)
                if not is_tip_prevented:
                    step_item["tip_cham_values"].add(cham_name)
        step_item["paths"].append({
            "lineid": row.lineid or "",
            "recipeid": row.recipeid or "",
            "path": row.path or "",
            "eqpline": row.eqpline or "",
            "childeqp": row.childeqp or "",
            "eqpgroup": row.eqpgroup or "",
            "members": path_members,
            "final_always_emergency": final_always_emergency,
            "final_major_minor": final_major_minor,
            "final_body_compat": final_body_compat,
            "final_cham_compat": final_cham_compat,
            "body_compat_count": final_body_count,
            "cham_compat_count": final_cham_count,
            "body_compat_tip": "N" if is_tip_prevented else (row.body_compat or "N"),
            "cham_compat_tip": "N" if is_tip_prevented else (row.cham_compat or "N"),
            "body_compat_count_tip": 0 if is_tip_prevented else (row.body_compat_count or 0),
            "cham_compat_count_tip": 0 if is_tip_prevented else (row.cham_compat_count or 0),
            "tip": row.tip or "",
        })

    result = []
    step_keys = set(step_map.keys())
    plan_summary_map = _build_plan_summary_map(step_keys, as_of_date=resolved_as_of)
    tip_missing_summary_map = _build_tip_missing_summary_map(snap_date, step_keys, as_of_date=resolved_as_of)

    for _, item in step_map.items():
        lineid_val = item["lineid"]
        processid_val = item["processid"]
        stepseq_val = item["stepseq"]
        step_key = (lineid_val, processid_val, stepseq_val)
        plan_summary = plan_summary_map.get(step_key, _empty_plan_summary())
        tip_missing_summary = tip_missing_summary_map.get(step_key, _empty_tip_missing_summary())
        source_eqps = sorted(_flatten_body_values(item["eqpgroup_values"]))
        source_chams = sorted(item["cham_values"])
        source_eqps_tip = sorted(_flatten_body_values(item["tip_eqpgroup_values"]))
        source_chams_tip = sorted(item["tip_cham_values"])
        manual_eqps = tip_missing_summary["manual_body_list"]
        manual_chams = tip_missing_summary["manual_cham_list"]
        merged_eqps = []
        for x in source_eqps + manual_eqps:
            if x not in merged_eqps:
                merged_eqps.append(x)
        merged_chams = []
        for x in source_chams + manual_chams:
            if x not in merged_chams:
                merged_chams.append(x)
        merged_eqps_tip = []
        for x in source_eqps_tip + manual_eqps:
            if x not in merged_eqps_tip:
                merged_eqps_tip.append(x)
        merged_chams_tip = []
        for x in source_chams_tip + manual_chams:
            if x not in merged_chams_tip:
                merged_chams_tip.append(x)
        recipe_str = ", ".join(sorted(item["recipeid_set"])) if item["recipeid_set"] else ""
        eqpgroup_str = ", ".join(merged_eqps) if merged_eqps else ""
        cham_display = _compact_cham_tokens(merged_chams)
        paths = item["paths"]
        manual_path_count = len(tip_missing_summary.get("manual_path_objects") or [])
        body_path_count = len(merged_eqps)
        source_path_count = len(item.get("path_signatures", set()))
        tip_source_path_count = len(item.get("tip_path_signatures", set()))
        cham_path_count = source_path_count + manual_path_count
        body_compat_count_tip = len(merged_eqps_tip)
        cham_compat_count_tip = tip_source_path_count + manual_path_count
        body_compat_flag = "Y" if body_path_count >= 2 else "N"
        cham_compat_flag = "Y" if cham_path_count >= 2 else "N"
        body_compat_tip = "Y" if body_compat_count_tip >= 2 else "N"
        cham_compat_tip = "Y" if cham_compat_count_tip >= 2 else "N"
        if not merged_eqps:
            compat_type_base = "미등록"
        elif body_compat_flag == "Y":
            compat_type_base = "body호환"
        elif cham_compat_flag == "Y":
            compat_type_base = "cham호환"
        else:
            compat_type_base = "단독"
        if not merged_eqps_tip:
            compat_type_tip = "미등록"
        elif body_compat_tip == "Y":
            compat_type_tip = "body호환"
        elif cham_compat_tip == "Y":
            compat_type_tip = "cham호환"
        else:
            compat_type_tip = "단독"
        compat_type = compat_type_tip if tip_mode else compat_type_base
        if compat_filter != "all" and compat_type != compat_filter:
            continue
        has_always = True if paths else False
        has_major = True if paths else False
        for mp in tip_missing_summary["manual_path_objects"]:
            if mp["always_emergency"] == "상시":
                has_always = True
            if mp["major_minor"] == "주요":
                has_major = True
        override_target_list = _make_override_target_list(paths, tip_missing_summary["manual_path_objects"])
        always_count = sum(1 for x in override_target_list if x.get("has_always"))
        emergency_count = max(len(override_target_list) - always_count, 0)
        major_count = sum(1 for x in override_target_list if x.get("has_major"))
        minor_count = max(len(override_target_list) - major_count, 0)
        tip_parts = []
        has_prevent_prefix = False
        for raw_tip in item["tip_values"]:
            if str(raw_tip or "").strip().upper().startswith("PREVENT:"):
                has_prevent_prefix = True
                break
        for part in sorted(item.get("tip_age_days", {}).keys()):
            tip_parts.append(f"{part}({int(item['tip_age_days'][part])}일↑)")
        row = {
            "snap_date": snap_date,
            "lineid": lineid_val,
            "processid": processid_val,
            "stepseq": stepseq_val,
            "areaname": item["areaname"],
            "layerid": item["layerid"],
            "skiprule": item["skiprule"],
            "descript": item["descript"],
            "recipeid": recipe_str,
            "stepseq_type": item["stepseq_type"],
            "eqpgroup": eqpgroup_str,
            "cham_display": cham_display,
            "eqpgroup_html": _merge_eqpgroup_html(source_eqps, manual_eqps),
            "cham_html": _merge_cham_html(source_chams, manual_chams),
            "body_compat_flag": body_compat_flag,
            "cham_compat_flag": cham_compat_flag,
            "body_path_count": body_path_count,
            "cham_path_count": cham_path_count,
            "body_compat_count": body_path_count,
            "cham_compat_count": cham_path_count,
            "compat_type": compat_type,
            "compat_type_base": compat_type_base,
            "compat_type_tip": compat_type_tip,
            "body_compat_tip": body_compat_tip,
            "cham_compat_tip": cham_compat_tip,
            "body_compat_count_tip": body_compat_count_tip,
            "cham_compat_count_tip": cham_compat_count_tip,
            "tip": (("PREVENT: " + ", ".join(tip_parts)) if tip_parts and has_prevent_prefix else ", ".join(tip_parts)) if tip_parts else "",
            "childeqp": ", ".join(sorted(item["childeqp_values"])) if item["childeqp_values"] else "",
            "has_always": has_always,
            "has_major": has_major,
            "always_count": always_count,
            "emergency_count": emergency_count,
            "major_count": major_count,
            "minor_count": minor_count,
            "always_summary_text": f"상시:{always_count}, 비상시:{emergency_count}",
            "major_summary_text": f"주요:{major_count}, 비주요:{minor_count}",
            "has_plan": plan_summary["has_plan"],
            "plan_flag": plan_summary["plan_flag"],
            "plan_body_names": plan_summary["plan_body_names"],
            "plan_cham_names": plan_summary["plan_cham_names"],
            "plan_due_dates": plan_summary["plan_due_dates"],
            "plan_eval_lot_ids": plan_summary["plan_eval_lot_ids"],
            "plan_eval_stages": plan_summary["plan_eval_stages"],
            "plan_memos": plan_summary["plan_memos"],
            "tip_missing_flag": tip_missing_summary["tip_missing_flag"],
            "tip_missing_always": tip_missing_summary["tip_missing_always"],
            "tip_missing_major": tip_missing_summary["tip_missing_major"],
            "tip_missing_body": tip_missing_summary["tip_missing_body"],
            "tip_missing_cham": tip_missing_summary["tip_missing_cham"],
            "override_target_list": override_target_list,
            "override_target_count": len(override_target_list),
            "is_compatible": (body_compat_flag == "Y" or cham_compat_flag == "Y"),
        }
        result.append(row)

    result.sort(key=lambda x: ((x["lineid"] or ""), (x["processid"] or ""), _natural_sort_key(x["stepseq"])))
    cache.set(cache_key, result, 60)
    return result


def summarize_steps(step_rows, use_tip=False):
    if use_tip:
        calc_rows = [r for r in step_rows if r.get("compat_type_tip") != "미등록"]
        body_key = "body_compat_tip"
        cham_key = "cham_compat_tip"
    else:
        calc_rows = [r for r in step_rows if r.get("compat_type_base") != "미등록"]
        body_key = "body_compat_flag"
        cham_key = "cham_compat_flag"

    total = len(calc_rows)

    single_cnt = sum(1 for r in calc_rows if r[body_key] == "N" and r[cham_key] == "N")
    body_cnt = sum(1 for r in calc_rows if r[body_key] == "Y")
    cham_exclusive_cnt = sum(1 for r in calc_rows if r[cham_key] == "Y" and r[body_key] != "Y")
    compatible = sum(1 for r in calc_rows if r[body_key] == "Y" or r[cham_key] == "Y")

    return {
        "total_steps": total,
        "compatible_steps": compatible,
        "compat_rate": round((compatible / total) * 100, 1) if total else 0.0,
        "body_rate": round((body_cnt / total) * 100, 1) if total else 0.0,
        "cham_rate_cum": round(((body_cnt + cham_exclusive_cnt) / total) * 100, 1) if total else 0.0,
        "single_cnt": single_cnt,
        "body_cnt": body_cnt,
        "cham_cnt": cham_exclusive_cnt,
    }
