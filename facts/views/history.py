from datetime import date, timedelta

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from ..models import *
from .. import services
from ..permissions import _check_page_permission
from .common import (
    _ensure_browser_close_session,
    _make_history_label_rows,
    _normalize_date_input,
    _parse_bool,
    _parse_week_input,
    _record_access_history,
    _week_display,
)

@login_required
def history_view(request):
    _ensure_browser_close_session(request)
    permission_response = _check_page_permission(request, "history", ignore_blank_scope=True)
    if permission_response is not None:
        return permission_response


    _record_access_history(request, 'history')
    base_snap_date = _normalize_date_input(request.GET.get("snap_date")) or services.get_latest_snap_date() or date.today()
    raw_snap_date = _normalize_date_input(request.GET.get("raw_snap_date")) or base_snap_date
    week_raw = request.GET.get("week") or ""
    lineid = request.GET.get("lineid") or ""
    processid = request.GET.get("processid") or ""
    action_type = request.GET.get("action_type") or ""
    scope_response = _check_page_permission(request, "history", lineid=(lineid or "").strip(), processid=(processid or "").strip(), popup=True, ignore_blank_scope=True)
    if scope_response is not None:
        return scope_response
    include_measure = _parse_bool(request.GET.get("include_measure"), default=("include_measure" not in request.GET))
    include_emergency = _parse_bool(request.GET.get("include_emergency"), default=("include_emergency" not in request.GET))
    exclude_skiprule_100 = _parse_bool(request.GET.get("exclude_skiprule_100"), default=("exclude_skiprule_100" not in request.GET))

    week_no = _parse_week_input(week_raw)
    iso_year, current_week, _ = base_snap_date.isocalendar()
    target_week = week_no or current_week

    monday = base_snap_date - timedelta(days=base_snap_date.isoweekday() - 1)
    week_dates = [monday + timedelta(days=i) for i in range(7)]
    week_dates = [d for d in week_dates if d.isocalendar()[1] == target_week and d.isocalendar()[0] == iso_year]
    if not week_dates:
        week_dates = [monday + timedelta(days=i) for i in range(7)]

    cards = services.get_history_daily_cards(
        week_dates=week_dates,
        lineid=lineid,
        processid=processid,
        include_measure=include_measure,
        include_emergency=include_emergency,
        exclude_skiprule_100=exclude_skiprule_100,
    )

    base_qs = FactsEditHistory.objects.select_related("changed_by").all()
    if lineid:
        base_qs = base_qs.filter(lineid=lineid)
    if processid:
        base_qs = base_qs.filter(processid=processid)
    if raw_snap_date:
        base_qs = base_qs.filter(snap_date=raw_snap_date)
    else:
        base_qs = base_qs.filter(snap_date__gte=min(week_dates), snap_date__lte=max(week_dates))

    action_option_values = list(base_qs.values_list("action_type", flat=True).distinct().order_by("action_type"))
    action_choices = [(v, services.get_action_type_label(v)) for v in action_option_values]

    qs = base_qs
    if action_type:
        qs = qs.filter(action_type=action_type)
    rows = list(qs.order_by("-created_at")[:500])
    _make_history_label_rows(rows)

    cfg = services.get_dashboard_config()
    inquiry_contact = cfg.inquiry_contact if hasattr(cfg, "inquiry_contact") else cfg["inquiry_contact"]
    options = services.get_distinct_master_options(None)

    context = {
        "page_title": "변경 이력 확인",
        "rows": rows,
        "cards": cards,
        "action_choices": action_choices,
        "selected_snap_date": base_snap_date.isoformat(),
        "selected_raw_snap_date": raw_snap_date.isoformat() if raw_snap_date else "",
        "selected_week": _week_display(target_week),
        "selected_lineid": lineid,
        "selected_processid": processid,
        "selected_action_type": action_type,
        "include_measure": include_measure,
        "include_emergency": include_emergency,
        "exclude_skiprule_100": exclude_skiprule_100,
        "week_options": [f"W{i:02d}" for i in range(1, 54)],
        "line_options": options["line_options"],
        "prp_options": options["prp_options"],
        "inquiry_contact": inquiry_contact,
    }
    return render(request, "facts/history.html", context)

