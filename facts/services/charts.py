from datetime import date, timedelta

from django.core.cache import cache

from .dataset import build_step_dataset, summarize_steps


def _month_start(d):
    return date(d.year, d.month, 1)


def _next_month_start(d):
    return date(d.year + (1 if d.month == 12 else 0), 1 if d.month == 12 else d.month + 1, 1)


def _prev_month_start(d):
    return date(d.year - 1, 12, 1) if d.month == 1 else date(d.year, d.month - 1, 1)


def _get_daily_summary_cached(snap_date, **kwargs):
    cache_key = (
        "facts:daily-summary:"
        f"{snap_date}|{kwargs.get('lineid')}|{kwargs.get('processid')}|{kwargs.get('areaname')}|{kwargs.get('layerid')}|"
        f"{int(bool(kwargs.get('include_measure')))}|{int(bool(kwargs.get('include_emergency')))}|"
        f"{int(bool(kwargs.get('exclude_skiprule_100')))}|{int(bool(kwargs.get('tip_mode')))}"
    )
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    rows = build_step_dataset(snap_date=snap_date, **kwargs)
    if not rows:
        cache.set(cache_key, None, 300)
        return None

    summary = summarize_steps(rows, use_tip=bool(kwargs.get("tip_mode")))
    cache.set(cache_key, summary, 300)
    return summary


def _summary_for_dates(date_list, **kwargs):
    total_cnt = 0
    body_cnt = 0
    cham_exclusive_cnt = 0
    compatible_cnt = 0

    for d in date_list:
        summary = _get_daily_summary_cached(d, **kwargs)
        if not summary:
            continue

        total_cnt += summary["total_steps"]
        body_cnt += summary["body_cnt"]
        cham_exclusive_cnt += summary["cham_cnt"]
        compatible_cnt += summary["compatible_steps"]

    if total_cnt == 0:
        return None

    return {
        "total_rate": round((compatible_cnt / total_cnt) * 100, 1),
        "body_rate": round((body_cnt / total_cnt) * 100, 1),
        "cham_rate_cum": round(((body_cnt + cham_exclusive_cnt) / total_cnt) * 100, 1),
    }


def get_dashboard_combined_series(
    snap_date,
    processid=None,
    areaname=None,
    layerid=None,
    lineid=None,
    include_measure=True,
    include_emergency=True,
    exclude_skiprule_100=False,
    tip_mode=False,
    target_monthly=None,
):
    common_kwargs = dict(
        processid=processid,
        areaname=areaname,
        layerid=layerid,
        lineid=lineid,
        include_measure=include_measure,
        include_emergency=include_emergency,
        exclude_skiprule_100=exclude_skiprule_100,
        tip_mode=tip_mode,
    )

    labels, total_values, body_values, cham_values, target_values = [], [], [], [], []

    month3 = _month_start(snap_date)
    month2 = _prev_month_start(month3)
    month1 = _prev_month_start(month2)

    for month_start in [month1, month2, month3]:
        next_month = _next_month_start(month_start)
        date_list = []
        cur = month_start
        while cur < next_month and cur <= snap_date:
            date_list.append(cur)
            cur += timedelta(days=1)

        labels.append(f"{month_start.month}월")
        s = _summary_for_dates(date_list, **common_kwargs)
        total_values.append(s["total_rate"] if s else None)
        body_values.append(s["body_rate"] if s else None)
        cham_values.append(s["cham_rate_cum"] if s else None)
        target_values.append(round(float(target_monthly), 1) if target_monthly is not None else None)

    labels.extend(["", ""])
    total_values.extend([None, None])
    body_values.extend([None, None])
    cham_values.extend([None, None])
    target_values.extend([None, None])

    for i in range(3, -1, -1):
        end_date = snap_date - timedelta(days=7 * i)
        start_date = end_date - timedelta(days=6)

        date_list = []
        cur = start_date
        while cur <= end_date:
            date_list.append(cur)
            cur += timedelta(days=1)

        _, week_no, _ = end_date.isocalendar()
        labels.append(f"W{week_no:02d}")
        s = _summary_for_dates(date_list, **common_kwargs)
        total_values.append(s["total_rate"] if s else None)
        body_values.append(s["body_rate"] if s else None)
        cham_values.append(s["cham_rate_cum"] if s else None)
        target_values.append(round(float(target_monthly), 1) if target_monthly is not None else None)

    labels.extend(["", ""])
    total_values.extend([None, None])
    body_values.extend([None, None])
    cham_values.extend([None, None])
    target_values.extend([None, None])

    for i in range(6, -1, -1):
        d = snap_date - timedelta(days=i)
        labels.append(f"{d.month}/{d.day}")

        rows = build_step_dataset(snap_date=d, **common_kwargs)
        if rows:
            summary = summarize_steps(rows, use_tip=tip_mode)
            total_values.append(summary["compat_rate"])
            body_values.append(summary["body_rate"])
            cham_values.append(summary["cham_rate_cum"])
        else:
            total_values.append(None)
            body_values.append(None)
            cham_values.append(None)

        target_values.append(round(float(target_monthly), 1) if target_monthly is not None else None)

    return {
        "labels": labels,
        "total_values": total_values,
        "body_values": body_values,
        "cham_values": cham_values,
        "target_values": target_values,
    }
