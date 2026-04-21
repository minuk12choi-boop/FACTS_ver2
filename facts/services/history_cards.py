from django.core.cache import cache
from django.db.models import Count

from ..models import FactsEditHistory
from .common import get_action_type_label
from .dataset import build_step_dataset, summarize_steps
from .prevent import _get_tip_threshold_days, get_prevent_distribution


def get_history_daily_cards(
    week_dates,
    lineid="",
    processid="",
    include_measure=True,
    include_emergency=True,
    exclude_skiprule_100=True,
):
    cache_key = (
        f"facts:history-cards:{min(week_dates)}|{max(week_dates)}|{lineid}|{processid}|"
        f"{int(bool(include_measure))}|{int(bool(include_emergency))}|{int(bool(exclude_skiprule_100))}|{_get_tip_threshold_days()}"
    )
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    cards = []
    for d in sorted(week_dates):
        rows = build_step_dataset(
            snap_date=d,
            lineid=lineid or None,
            processid=processid or None,
            include_measure=include_measure,
            include_emergency=include_emergency,
            exclude_skiprule_100=exclude_skiprule_100,
            tip_mode=False,
            for_prp_table=True,
        )
        summary = summarize_steps(rows) if rows else {"total_steps": 0, "compat_rate": 0, "single_cnt": 0, "body_cnt": 0, "cham_cnt": 0}
        summary_tip = summarize_steps(rows, use_tip=True) if rows else {"single_cnt": 0, "body_cnt": 0, "cham_cnt": 0}
        dist = get_prevent_distribution(snap_date=d, lineid=lineid, processid=processid)
        prevent_counts = []
        for idx, label in enumerate(dist["labels"]):
            total = sum((ds["data"][idx] if idx < len(ds["data"]) else 0) for ds in dist["datasets"])
            prevent_counts.append({"label": label, "value": total})
        history_qs = FactsEditHistory.objects.filter(snap_date=d)
        if lineid:
            history_qs = history_qs.filter(lineid=lineid)
        if processid:
            history_qs = history_qs.filter(processid=processid)
        cards.append({
            "date": d,
            "summary": summary,
            "tip_single": summary_tip["single_cnt"],
            "tip_body": summary_tip["body_cnt"],
            "tip_cham": summary_tip["cham_cnt"],
            "prevent_counts": prevent_counts,
            "plan_count": sum(1 for r in rows if r.get("has_plan")),
            "tip_missing_count": sum(1 for r in rows if r.get("tip_missing_flag") == "Y"),
            "change_count": history_qs.count(),
            "change_by_action": [
                {
                    "action_type": item["action_type"],
                    "action_type_label": get_action_type_label(item["action_type"]),
                    "cnt": item["cnt"],
                }
                for item in history_qs.values("action_type").annotate(cnt=Count("id")).order_by("action_type")
            ],
        })
    cache.set(cache_key, cards, 60)
    return cards


def get_history_action_choices(snap_date=None, lineid="", processid=""):
    qs = FactsEditHistory.objects.all()
    if snap_date:
        qs = qs.filter(snap_date=snap_date)
    if lineid:
        qs = qs.filter(lineid=lineid)
    if processid:
        qs = qs.filter(processid=processid)
    values = list(qs.order_by().values_list("action_type", flat=True).distinct())
    values.sort()
    return [(v, get_action_type_label(v)) for v in values]
