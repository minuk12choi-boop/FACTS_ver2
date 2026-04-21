from collections import defaultdict
from datetime import datetime

from ..models import FactsEditHistory, FactsStepPlan, FactsTipMissingCompatPath
from .common import _as_of_cutoff
from .common import _step_group_key, _uniq_join, _as_of_date
from .common import _natural_sort_key


def _history_item_recipeid(row, payload):
    return str((payload or {}).get("recipeid") or getattr(row, "recipeid", "") or "").strip().upper()


def _history_payload_object_id(payload):
    payload = payload or {}
    obj_id = payload.get("id")
    try:
        if obj_id in (None, ""):
            return None
        return int(obj_id)
    except (TypeError, ValueError):
        return None


def _history_item_key(row, payload):
    data = payload or {}
    obj_id = _history_payload_object_id(data)
    if obj_id is not None:
        return ("id", obj_id)
    body = str(data.get("eqp_body_name") or "").strip().upper()
    cham = str(data.get("eqp_cham_name") or "").strip().upper()
    recipeid = _history_item_recipeid(row, data)
    return ("value", body, cham, recipeid)


def _history_payload_matches_plan(payload):
    payload = payload or {}
    return any(k in payload for k in ["compatibility_due_date", "eval_lot_id", "required_eval_stage_id", "required_eval_stage_code", "required_eval_stage_name", "memo", "eqp_body_name", "eqp_cham_name"])


def _history_payload_matches_tip_missing(payload):
    payload = payload or {}
    return any(k in payload for k in ["always_emergency", "major_minor", "eqp_body_name", "eqp_cham_name"])


def _empty_plan_summary():
    return {
        "plan_flag": "N",
        "plan_body_names": "",
        "plan_cham_names": "",
        "plan_due_dates": "",
        "plan_eval_lot_ids": "",
        "plan_eval_stages": "",
        "plan_memos": "",
        "has_plan": False,
    }


def _empty_tip_missing_summary():
    return {
        "tip_missing_flag": "N",
        "tip_missing_always": "",
        "tip_missing_major": "",
        "tip_missing_body": "",
        "tip_missing_cham": "",
        "manual_body_list": [],
        "manual_cham_list": [],
        "manual_path_objects": [],
    }


def _build_plan_summary(processid, stepseq, lineid=""):
    plan_qs = list(
        FactsStepPlan.objects.filter(
            processid=processid,
            stepseq=stepseq,
            lineid=lineid,
            is_active=True,
        ).select_related("required_eval_stage").order_by("-updated_at", "-id")
    )

    if not plan_qs:
        return _empty_plan_summary()

    return {
        "plan_flag": "Y",
        "plan_body_names": _uniq_join([x.eqp_body_name for x in plan_qs]),
        "plan_cham_names": _uniq_join([x.eqp_cham_name for x in plan_qs]),
        "plan_due_dates": _uniq_join([
            x.compatibility_due_date.strftime("%Y-%m-%d") if x.compatibility_due_date else ""
            for x in plan_qs
        ]),
        "plan_eval_lot_ids": _uniq_join([x.eval_lot_id for x in plan_qs]),
        "plan_eval_stages": _uniq_join([
            x.required_eval_stage.stage_name if x.required_eval_stage else ""
            for x in plan_qs
        ]),
        "plan_memos": _uniq_join([x.memo for x in plan_qs]),
        "has_plan": True,
    }


def _build_tip_missing_summary(snap_date, processid, stepseq, lineid=""):
    qs = list(
        FactsTipMissingCompatPath.objects.filter(
            snap_date=snap_date,
            processid=processid,
            stepseq=stepseq,
            lineid=lineid,
            is_active=True,
        ).order_by("-updated_at", "-id")
    )
    if not qs:
        return _empty_tip_missing_summary()

    manual_body_list = []
    manual_cham_list = []
    manual_path_objects = []

    for obj in qs:
        body = str(obj.eqp_body_name or "").strip().upper()
        cham = str(obj.eqp_cham_name or "").strip().upper()

        if body and body not in manual_body_list:
            manual_body_list.append(body)

        cham_token = ""
        if body and cham:
            cham_token = f"{body}-{cham}"
            if cham_token not in manual_cham_list:
                manual_cham_list.append(cham_token)

        manual_path_objects.append({
            "always_emergency": str(obj.always_emergency or "").strip(),
            "major_minor": str(obj.major_minor or "").strip(),
            "body": body,
            "cham": cham,
            "cham_token": cham_token,
        })

    return {
        "tip_missing_flag": "Y",
        "tip_missing_always": _uniq_join([x.always_emergency for x in qs], upper=True),
        "tip_missing_major": _uniq_join([x.major_minor for x in qs], upper=True),
        "tip_missing_body": _uniq_join([x.eqp_body_name for x in qs], upper=True),
        "tip_missing_cham": _uniq_join([x.eqp_cham_name for x in qs], upper=True),
        "manual_body_list": manual_body_list,
        "manual_cham_list": manual_cham_list,
        "manual_path_objects": manual_path_objects,
    }


def _build_plan_summary_map(step_keys, as_of_date=None):
    valid_keys = {_step_group_key(l, p, s) for l, p, s in step_keys if (p or "") and (s or "")}
    if not valid_keys:
        return {}

    cutoff = _as_of_cutoff(as_of_date)
    processids = sorted({p for _, p, _ in valid_keys if p})
    stepseqs = sorted({s for _, _, s in valid_keys if s})
    lineids = sorted({l for l, _, _ in valid_keys})

    result = {}
    history_seen_keys = set()
    if cutoff is not None:
        history_qs = FactsEditHistory.objects.filter(
            action_type__in=["plan_add", "plan_update", "plan_delete"],
            created_at__lte=cutoff,
            processid__in=processids,
            stepseq__in=stepseqs,
            lineid__in=lineids,
        ).order_by("created_at", "id")

        state_by_step = defaultdict(dict)
        for row in history_qs:
            payload_after = row.after_json or {}
            payload_before = row.before_json or {}
            payload = payload_after if row.action_type != "plan_delete" else payload_before
            if not _history_payload_matches_plan(payload):
                continue
            step_key = _step_group_key(row.lineid, row.processid, row.stepseq)
            if step_key not in valid_keys:
                continue
            history_seen_keys.add(step_key)
            before_key = _history_item_key(row, payload_before)
            after_key = _history_item_key(row, payload_after)
            if row.action_type == "plan_delete":
                state_by_step[step_key].pop(before_key, None)
            else:
                if row.action_type == "plan_update" and before_key != after_key:
                    state_by_step[step_key].pop(before_key, None)
                state_by_step[step_key][after_key] = {
                    "eqp_body_name": str(payload_after.get("eqp_body_name") or "").strip().upper(),
                    "eqp_cham_name": str(payload_after.get("eqp_cham_name") or "").strip().upper(),
                    "compatibility_due_date": str(payload_after.get("compatibility_due_date") or "").strip(),
                    "eval_lot_id": str(payload_after.get("eval_lot_id") or "").strip(),
                    "required_eval_stage_name": str(payload_after.get("required_eval_stage_name") or "").strip(),
                    "memo": str(payload_after.get("memo") or "").strip(),
                }

        for key, items_dict in state_by_step.items():
            items = list(items_dict.values())
            if not items:
                continue
            result[key] = {
                "plan_flag": "Y",
                "plan_body_names": _uniq_join([x["eqp_body_name"] for x in items], upper=False),
                "plan_cham_names": _uniq_join([x["eqp_cham_name"] for x in items], upper=False),
                "plan_due_dates": _uniq_join([x["compatibility_due_date"] for x in items], upper=False),
                "plan_eval_lot_ids": _uniq_join([x["eval_lot_id"] for x in items], upper=False),
                "plan_eval_stages": _uniq_join([x["required_eval_stage_name"] for x in items], upper=False),
                "plan_memos": _uniq_join([x["memo"] for x in items], upper=False),
                "has_plan": True,
            }

    fallback_keys = valid_keys - history_seen_keys
    if fallback_keys:
        qs = list(
            FactsStepPlan.objects.filter(
                processid__in=[p for _, p, _ in fallback_keys],
                stepseq__in=[s for _, _, s in fallback_keys],
                lineid__in=[l for l, _, _ in fallback_keys],
                is_active=True,
                created_at__lte=cutoff if cutoff is not None else datetime.max,
                updated_at__lte=cutoff if cutoff is not None else datetime.max,
            ).select_related("required_eval_stage").order_by("-updated_at", "-id")
        )
        grouped = defaultdict(list)
        for obj in qs:
            key = _step_group_key(obj.lineid, obj.processid, obj.stepseq)
            if key in fallback_keys:
                grouped[key].append(obj)
        for key, plan_qs in grouped.items():
            result[key] = {
                "plan_flag": "Y",
                "plan_body_names": _uniq_join([x.eqp_body_name for x in plan_qs]),
                "plan_cham_names": _uniq_join([x.eqp_cham_name for x in plan_qs]),
                "plan_due_dates": _uniq_join([x.compatibility_due_date.strftime("%Y-%m-%d") if x.compatibility_due_date else "" for x in plan_qs]),
                "plan_eval_lot_ids": _uniq_join([x.eval_lot_id for x in plan_qs]),
                "plan_eval_stages": _uniq_join([x.required_eval_stage.stage_name if x.required_eval_stage else "" for x in plan_qs]),
                "plan_memos": _uniq_join([x.memo for x in plan_qs]),
                "has_plan": True,
            }
    return result


def _build_tip_missing_summary_map(snap_date, step_keys, as_of_date=None):
    valid_keys = {_step_group_key(l, p, s) for l, p, s in step_keys if (p or "") and (s or "")}
    if not valid_keys:
        return {}

    cutoff = _as_of_cutoff(as_of_date)
    processids = sorted({p for _, p, _ in valid_keys if p})
    stepseqs = sorted({s for _, _, s in valid_keys if s})
    lineids = sorted({l for l, _, _ in valid_keys})
    result = {}
    history_seen_keys = set()

    if cutoff is not None:
        history_qs = FactsEditHistory.objects.filter(
            action_type__in=["tip_missing_add", "tip_missing_update", "tip_missing_delete"],
            snap_date__lte=snap_date,
            created_at__lte=cutoff,
            processid__in=processids,
            stepseq__in=stepseqs,
            lineid__in=lineids,
        ).order_by("created_at", "id")
        state_by_step = defaultdict(dict)
        for row in history_qs:
            payload_after = row.after_json or {}
            payload_before = row.before_json or {}
            payload = payload_after if row.action_type != "tip_missing_delete" else payload_before
            if not _history_payload_matches_tip_missing(payload):
                continue
            step_key = _step_group_key(row.lineid, row.processid, row.stepseq)
            if step_key not in valid_keys:
                continue
            history_seen_keys.add(step_key)
            before_key = _history_item_key(row, payload_before)
            after_key = _history_item_key(row, payload_after)
            if row.action_type == "tip_missing_delete":
                state_by_step[step_key].pop(before_key, None)
            else:
                if row.action_type == "tip_missing_update" and before_key != after_key:
                    state_by_step[step_key].pop(before_key, None)
                state_by_step[step_key][after_key] = {
                    "always_emergency": str(payload_after.get("always_emergency") or "").strip(),
                    "major_minor": str(payload_after.get("major_minor") or "").strip(),
                    "eqp_body_name": str(payload_after.get("eqp_body_name") or "").strip().upper(),
                    "eqp_cham_name": str(payload_after.get("eqp_cham_name") or "").strip().upper(),
                }
        for key, items_dict in state_by_step.items():
            items = list(items_dict.values())
            if not items:
                continue
            manual_body_list = []
            manual_cham_list = []
            manual_path_objects = []
            for data in items:
                body = data["eqp_body_name"]
                cham = data["eqp_cham_name"]
                if body and body not in manual_body_list:
                    manual_body_list.append(body)
                cham_token = f"{body}-{cham}" if body and cham else ""
                if cham_token and cham_token not in manual_cham_list:
                    manual_cham_list.append(cham_token)
                manual_path_objects.append({
                    "always_emergency": data["always_emergency"],
                    "major_minor": data["major_minor"],
                    "body": body,
                    "cham": cham,
                    "cham_token": cham_token,
                })
            result[key] = {
                "tip_missing_flag": "Y",
                "tip_missing_always": _uniq_join([x["always_emergency"] for x in items]),
                "tip_missing_major": _uniq_join([x["major_minor"] for x in items]),
                "tip_missing_body": _uniq_join([x["eqp_body_name"] for x in items]),
                "tip_missing_cham": _uniq_join([x["eqp_cham_name"] for x in items]),
                "manual_body_list": manual_body_list,
                "manual_cham_list": manual_cham_list,
                "manual_path_objects": manual_path_objects,
            }

    fallback_keys = valid_keys - history_seen_keys
    if fallback_keys:
        qs = list(
            FactsTipMissingCompatPath.objects.filter(
                snap_date=snap_date,
                processid__in=[p for _, p, _ in fallback_keys],
                stepseq__in=[s for _, _, s in fallback_keys],
                lineid__in=[l for l, _, _ in fallback_keys],
                is_active=True,
                created_at__lte=cutoff if cutoff is not None else datetime.max,
                updated_at__lte=cutoff if cutoff is not None else datetime.max,
            ).order_by("-updated_at", "-id")
        )
        grouped = defaultdict(list)
        for obj in qs:
            key = _step_group_key(obj.lineid, obj.processid, obj.stepseq)
            if key in fallback_keys:
                grouped[key].append(obj)
        for key, items in grouped.items():
            manual_body_list = []
            manual_cham_list = []
            manual_path_objects = []
            for obj in items:
                body = str(obj.eqp_body_name or "").strip().upper()
                cham = str(obj.eqp_cham_name or "").strip().upper()
                if body and body not in manual_body_list:
                    manual_body_list.append(body)
                cham_token = f"{body}-{cham}" if body and cham else ""
                if cham_token and cham_token not in manual_cham_list:
                    manual_cham_list.append(cham_token)
                manual_path_objects.append({
                    "always_emergency": str(obj.always_emergency or "").strip(),
                    "major_minor": str(obj.major_minor or "").strip(),
                    "body": body,
                    "cham": cham,
                    "cham_token": cham_token,
                })
            result[key] = {
                "tip_missing_flag": "Y",
                "tip_missing_always": _uniq_join([x.always_emergency for x in items]),
                "tip_missing_major": _uniq_join([x.major_minor for x in items]),
                "tip_missing_body": _uniq_join([x.eqp_body_name for x in items]),
                "tip_missing_cham": _uniq_join([x.eqp_cham_name for x in items]),
                "manual_body_list": manual_body_list,
                "manual_cham_list": manual_cham_list,
                "manual_path_objects": manual_path_objects,
            }
    return result


def _make_override_target_list(source_path_items, manual_path_objects):
    target_map = {}

    for p in source_path_items:
        path_ref = {
            "lineid": p["lineid"],
            "recipeid": p["recipeid"],
            "path": p["path"],
            "eqpline": p["eqpline"],
            "childeqp": p["childeqp"],
        }

        for member in p["members"]:
            key = member["member_key"]
            item = target_map.setdefault(
                key,
                {
                    "member_key": key,
                    "eqp_body_name": member["eqp_body_name"],
                    "eqp_cham_name": member["eqp_cham_name"],
                    "display_name": member["display_name"],
                    "has_cham": member["has_cham"],
                    "source_types": set(),
                    "has_always": False,
                    "has_major": False,
                    "path_refs": [],
                    "manual_tip_missing": False,
                    "manual_tip_missing_always": False,
                    "manual_tip_missing_major": False,
                },
            )

            item["source_types"].add("SOURCE_PATH")
            item["has_always"] = True
            item["has_major"] = True
            item["path_refs"].append(path_ref)

    for mp in manual_path_objects:
        body = str(mp.get("body") or "").strip().upper()
        cham = str(mp.get("cham") or "").strip().upper()
        if not body:
            continue

        key = f"{body}-{cham}" if cham else body
        item = target_map.setdefault(
            key,
            {
                "member_key": key,
                "eqp_body_name": body,
                "eqp_cham_name": cham,
                "display_name": key,
                "has_cham": bool(cham),
                "source_types": set(),
                "has_always": False,
                "has_major": False,
                "path_refs": [],
                "manual_tip_missing": False,
                "manual_tip_missing_always": False,
                "manual_tip_missing_major": False,
            },
        )

        item["source_types"].add("TIP_MISSING")
        item["manual_tip_missing"] = True
        if mp.get("always_emergency") == "상시":
            item["has_always"] = True
            item["manual_tip_missing_always"] = True
        if mp.get("major_minor") == "주요":
            item["has_major"] = True
            item["manual_tip_missing_major"] = True

    result = []
    for key in sorted(target_map.keys()):
        item = target_map[key]
        result.append(
            {
                "member_key": item["member_key"],
                "eqp_body_name": item["eqp_body_name"],
                "eqp_cham_name": item["eqp_cham_name"],
                "display_name": item["display_name"],
                "has_cham": item["has_cham"],
                "has_always": item["has_always"],
                "has_major": item["has_major"],
                "manual_tip_missing": item["manual_tip_missing"],
                "manual_tip_missing_always": item["manual_tip_missing_always"],
                "manual_tip_missing_major": item["manual_tip_missing_major"],
                "source_types": sorted(item["source_types"]),
                "path_refs": item["path_refs"],
            }
        )

    return result


def get_plan_detail_rows_as_of(snap_date, lineid, processid, stepseq):
    cutoff = _as_of_cutoff(snap_date)
    rows = []

    history_qs = FactsEditHistory.objects.filter(
        action_type__in=["plan_add", "plan_update", "plan_delete"],
        created_at__lte=cutoff,
        lineid=lineid,
        processid=processid,
        stepseq=stepseq,
    ).order_by("created_at", "id")

    state = {}
    for row in history_qs:
        payload_after = row.after_json or {}
        payload_before = row.before_json or {}
        payload = payload_after if row.action_type != "plan_delete" else payload_before
        if not _history_payload_matches_plan(payload):
            continue
        before_key = _history_item_key(row, payload_before)
        after_key = _history_item_key(row, payload_after)
        if row.action_type == "plan_delete":
            state.pop(before_key, None)
            continue
        if row.action_type == "plan_update" and before_key != after_key:
            state.pop(before_key, None)
        state[after_key] = {
            "id": payload_after.get("id") or payload_before.get("id") or "",
            "lineid": str(payload_after.get("lineid") or row.lineid or "").strip(),
            "always_emergency": str(payload_after.get("always_emergency") or "").strip(),
            "major_minor": str(payload_after.get("major_minor") or "").strip(),
            "eqp_body_name": str(payload_after.get("eqp_body_name") or "").strip(),
            "eqp_cham_name": str(payload_after.get("eqp_cham_name") or "").strip(),
            "compatibility_due_date": str(payload_after.get("compatibility_due_date") or "").strip(),
            "eval_lot_id": str(payload_after.get("eval_lot_id") or "").strip(),
            "required_eval_stage_id": payload_after.get("required_eval_stage_id") or "",
            "required_eval_stage_code": str(payload_after.get("required_eval_stage_code") or "").strip(),
            "required_eval_stage_name": str(payload_after.get("required_eval_stage_name") or "").strip(),
            "memo": str(payload_after.get("memo") or "").strip(),
        }

    if state:
        rows = list(state.values())
    else:
        qs = FactsStepPlan.objects.filter(
            lineid=lineid,
            processid=processid,
            stepseq=stepseq,
            is_active=True,
        ).select_related("required_eval_stage")
        if cutoff is not None:
            qs = qs.filter(created_at__lte=cutoff, updated_at__lte=cutoff)
        rows = [{
            "id": obj.id,
            "lineid": obj.lineid or "",
            "always_emergency": obj.always_emergency or "",
            "major_minor": obj.major_minor or "",
            "eqp_body_name": obj.eqp_body_name or "",
            "eqp_cham_name": obj.eqp_cham_name or "",
            "compatibility_due_date": obj.compatibility_due_date.strftime("%Y-%m-%d") if obj.compatibility_due_date else "",
            "eval_lot_id": obj.eval_lot_id or "",
            "required_eval_stage_id": obj.required_eval_stage_id or "",
            "required_eval_stage_code": obj.required_eval_stage.stage_code if obj.required_eval_stage else "",
            "required_eval_stage_name": obj.required_eval_stage.stage_name if obj.required_eval_stage else "",
            "memo": obj.memo or "",
        } for obj in qs.order_by("-updated_at", "-id")]

    rows.sort(key=lambda x: (_natural_sort_key(x.get("eqp_body_name") or ""), _natural_sort_key(x.get("eqp_cham_name") or ""), str(x.get("id") or "")), reverse=False)
    return rows


def get_tip_missing_detail_rows_as_of(snap_date, lineid, processid, stepseq):
    cutoff = _as_of_cutoff(snap_date)
    rows = []

    history_qs = FactsEditHistory.objects.filter(
        action_type__in=["tip_missing_add", "tip_missing_update", "tip_missing_delete"],
        snap_date__lte=snap_date,
        created_at__lte=cutoff,
        lineid=lineid,
        processid=processid,
        stepseq=stepseq,
    ).order_by("created_at", "id")

    state = {}
    for row in history_qs:
        payload_after = row.after_json or {}
        payload_before = row.before_json or {}
        payload = payload_after if row.action_type != "tip_missing_delete" else payload_before
        if not _history_payload_matches_tip_missing(payload):
            continue
        effective_snap = _as_of_date(row.snap_date)
        if effective_snap and effective_snap > snap_date:
            continue
        before_key = _history_item_key(row, payload_before)
        after_key = _history_item_key(row, payload_after)
        if row.action_type == "tip_missing_delete":
            state.pop(before_key, None)
            continue
        if row.action_type == "tip_missing_update" and before_key != after_key:
            state.pop(before_key, None)
        state[after_key] = {
            "id": payload_after.get("id") or payload_before.get("id") or "",
            "lineid": str(payload_after.get("lineid") or row.lineid or "").strip(),
            "always_emergency": str(payload_after.get("always_emergency") or "").strip(),
            "major_minor": str(payload_after.get("major_minor") or "").strip(),
            "eqp_body_name": str(payload_after.get("eqp_body_name") or "").strip(),
            "eqp_cham_name": str(payload_after.get("eqp_cham_name") or "").strip(),
        }

    if state:
        rows = list(state.values())
    else:
        qs = FactsTipMissingCompatPath.objects.filter(
            snap_date__lte=snap_date,
            lineid=lineid,
            processid=processid,
            stepseq=stepseq,
            is_active=True,
        )
        if cutoff is not None:
            qs = qs.filter(created_at__lte=cutoff, updated_at__lte=cutoff)
        rows = [{
            "id": obj.id,
            "lineid": obj.lineid or "",
            "always_emergency": obj.always_emergency or "",
            "major_minor": obj.major_minor or "",
            "eqp_body_name": obj.eqp_body_name or "",
            "eqp_cham_name": obj.eqp_cham_name or "",
        } for obj in qs.order_by("-snap_date", "-updated_at", "-id")]

    rows.sort(key=lambda x: (_natural_sort_key(x.get("eqp_body_name") or ""), _natural_sort_key(x.get("eqp_cham_name") or ""), str(x.get("id") or "")), reverse=False)
    return rows
