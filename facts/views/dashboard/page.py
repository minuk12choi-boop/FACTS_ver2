from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie

from ...models import *
from ... import services
from ...permissions import _check_page_permission
from ..common import _ensure_browser_close_session, _record_access_history
from .helpers import (
    _build_dashboard_api_urls_json,
    _build_guide_pages_json,
    _get_dashboard_common_filters,
)

@login_required
@ensure_csrf_cookie
def dashboard_view(request):
    _ensure_browser_close_session(request)
    permission_response = _check_page_permission(request, "dashboard", ignore_blank_scope=True)
    if permission_response is not None:
        return permission_response

    _record_access_history(request, 'dashboard')
    f = _get_dashboard_common_filters(request)
    filters = services.get_filter_options(f["snap_date"])

    context = {
        "page_title": "FACTS Dashboard",
        "snap_date": f["snap_date"],
        "filters": filters,
        "selected_lineid": f["lineid"],
        "selected_processid": f["processid"],
        "selected_areaname": f["areaname"],
        "selected_layerid": f["layerid"],
        "include_measure": f["include_measure"],
        "include_emergency": f["include_emergency"],
        "exclude_skiprule_100": f["exclude_skiprule_100"],
        "tip_mode": f["tip_mode"],
        "summary": {
            "compat_rate": 0.0,
            "total_steps": 0,
            "single_cnt": 0,
            "body_cnt": 0,
            "cham_cnt": 0,
        },
        "rows": [],
        "combined_series_json": {
            "labels": [],
            "total_values": [],
            "body_values": [],
            "cham_values": [],
            "target_values": [],
        },
        "guide_pages_json": _build_guide_pages_json(),
        "dashboard_api_urls_json": _build_dashboard_api_urls_json(),
        "target_monthly": None,
        "inquiry_contact": f["inquiry_contact"],
        "eval_stages": FactsEvalStageMaster.objects.filter(is_active=True).order_by("sort_order", "stage_code"),
        "table_line_options": [],
        "table_prp_options": [],
    }
    return render(request, "facts/dashboard.html", context)

