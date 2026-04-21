from collections import Counter
from datetime import datetime

from ..models import FactsPreventRuleMaster, FactsWipSource
from .common import _as_of_cutoff


def get_prevent_rule_rows():
    rows = list(FactsPreventRuleMaster.objects.filter(is_active=True).order_by("sort_order", "prevent_days", "id"))
    if not rows:
        return [type("RuleObj", (), {"id": 0, "sort_order": 0, "prevent_days": 7, "color_code": "#5B8FF9", "is_active": True, "is_current": True})()]
    return rows


def get_current_prevent_rule():
    current = FactsPreventRuleMaster.objects.filter(is_active=True, is_current=True).order_by("sort_order", "prevent_days", "id").first()
    if current:
        return current
    return get_prevent_rule_rows()[0]


def _get_tip_threshold_days():
    rule = get_current_prevent_rule()
    try:
        return int(getattr(rule, "prevent_days", 7) or 7)
    except (TypeError, ValueError):
        return 7


def _row_is_tip_prevented(row, threshold_days, as_of_date=None):
    tip_value = str(getattr(row, "tip", "") or "").strip().upper()
    prevent_value = str(getattr(row, "prevent", "") or "").strip().upper()
    if not tip_value and prevent_value != "PREVENT":
        return False
    eventtime = getattr(row, "eventtime", None)
    if not eventtime:
        return False
    cutoff_dt = _as_of_cutoff(as_of_date) or datetime.now()
    try:
        if getattr(eventtime, "tzinfo", None):
            age_days = (cutoff_dt - eventtime.replace(tzinfo=None)).days
        else:
            age_days = (cutoff_dt - eventtime).days
    except Exception:
        return False
    is_prevent_marked = prevent_value == "PREVENT" or tip_value.startswith("PREVENT")
    return is_prevent_marked and age_days >= threshold_days


def get_prevent_distribution(snap_date, lineid="", processid="", areaname="", include_measure=True, exclude_skiprule_100=False, tip_mode=True):
    rules = get_prevent_rule_rows()
    qs = FactsWipSource.objects.filter(snap_date=snap_date).exclude(tip="").exclude(eventtime__isnull=True)
    if lineid:
        qs = qs.filter(lineid=lineid)
    if processid:
        qs = qs.filter(processid=processid)
    if areaname:
        qs = qs.filter(areaname=areaname)
    if not include_measure:
        qs = qs.exclude(stepseq_type="계측")
    if exclude_skiprule_100:
        qs = qs.exclude(skiprule="100")

    rows = list(qs.order_by("lineid", "processid", "areaname", "stepseq", "recipeid", "tip", "eventtime"))
    labels = [f"{rules[0].prevent_days}일 이하"] + [f"{r.prevent_days}일 이상" for r in rules]
    if not rows:
        return {"labels": labels, "datasets": [], "rows": [], "current_threshold": _get_tip_threshold_days(), "resolved_snap_date": snap_date.isoformat() if snap_date else ""}

    now_dt = datetime.now()
    buckets = Counter()
    detail_rows = []
    min_rule = min(int(r.prevent_days) for r in rules)
    seen = set()

    for row in rows:
        ev = row.eventtime
        age_days = (now_dt - ev.replace(tzinfo=None) if getattr(ev, "tzinfo", None) else now_dt - ev).days
        if age_days < min_rule:
            bucket = f"{min_rule}일 이하"
        else:
            bucket = f"{max([int(r.prevent_days) for r in rules if age_days >= int(r.prevent_days)])}일 이상"

        raw_tip = str(row.tip or "").strip()
        tip_text = raw_tip.split(":", 1)[1].strip() if ":" in raw_tip else raw_tip
        member_tokens = [t.strip() for t in tip_text.split(",") if t.strip()] or ([tip_text] if tip_text else [])
        event_str = row.eventtime.strftime("%Y-%m-%d %H:%M:%S") if row.eventtime else ""

        for member in member_tokens:
            key = (row.lineid or "", row.processid or "", row.areaname or "", row.stepseq or "", row.recipeid or "", member)
            if key in seen:
                continue
            seen.add(key)
            buckets[bucket] += 1
            detail_rows.append({
                "lineid": row.lineid or "",
                "processid": row.processid or "",
                "areaname": row.areaname or "",
                "stepseq": row.stepseq or "",
                "recipeid": row.recipeid or "",
                "tip": f"PREVENT: {member}",
                "eventtime": event_str,
                "age_days": age_days,
                "bucket": bucket,
            })

    datasets = []
    for rule in rules:
        label = f"{rule.prevent_days}일 이상"
        datasets.append({
            "label": label,
            "data": [0] + [buckets.get(label, 0) if l == label else 0 for l in [f"{r.prevent_days}일 이상" for r in rules]],
            "backgroundColor": rule.color_code,
        })
    datasets.insert(0, {
        "label": f"{min_rule}일 이하",
        "data": [buckets.get(f"{min_rule}일 이하", 0)] + [0 for _ in rules],
        "backgroundColor": "#FFFFFF",
        "borderColor": "#111111",
        "borderWidth": 1.5,
    })
    return {
        "labels": labels,
        "datasets": datasets,
        "rows": detail_rows,
        "current_threshold": _get_tip_threshold_days(),
        "rule_rows": [{"days": r.prevent_days, "color": r.color_code} for r in rules],
        "resolved_snap_date": snap_date.isoformat() if snap_date else "",
    }
