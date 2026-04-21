from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from ...permissions import _check_page_permission
from ..common import _ensure_browser_close_session, _parse_bool
from .helpers import (
    _apply_prp_filters,
    _build_prp_option_values,
    _build_summary_and_chart_payload,
    _get_dashboard_common_filters,
    _get_prp_common_filters,
    _get_prp_request_filters,
    _get_prp_base_rows,
    _validate_prp_filters,
)

@require_GET
@login_required
def dashboard_data_api(request):
    _ensure_browser_close_session(request)
    permission_response = _check_page_permission(request, "dashboard", ignore_blank_scope=True)
    if permission_response is not None:
        return permission_response

    f = _get_dashboard_common_filters(request)
    scope_response = _check_page_permission(request, "dashboard", lineid=f["lineid"], processid=f["processid"], popup=True)
    if scope_response is not None:
        return scope_response
    prp_f = _get_prp_common_filters(request)
    summary_only = _parse_bool(request.GET.get("summary_only"), default=False)
    prp_only = _parse_bool(request.GET.get("prp_only"), default=False)

    payload = {
        "ok": True,
        "summary": {},
        "target_monthly": None,
        "combined_series": {
            "labels": [],
            "total_values": [],
            "body_values": [],
            "cham_values": [],
            "target_values": [],
        },
        "rows": [],
        "table_area_options": [],
        "table_layer_options": [],
        "table_step_options": [],
        "table_type_options": [],
        "message": "",
    }

    if not prp_only:
        summary, target_monthly, combined_series = _build_summary_and_chart_payload(f)
        payload["summary"] = summary
        payload["target_monthly"] = target_monthly
        payload["combined_series"] = combined_series

    if summary_only:
        return JsonResponse(payload)

    prp_filters = _get_prp_request_filters(request)
    prp_scope_response = _check_page_permission(request, "dashboard", lineid=(prp_filters.get("prp_lineid") or "").strip(), processid=(prp_filters.get("prp_processid") or "").strip(), popup=True)
    if prp_scope_response is not None:
        return prp_scope_response
    has_any_prp_param = any(
        str(request.GET.get(k) or "").strip()
        for k in [
            "prp_lineid",
            "prp_processid",
            "prp_area",
            "prp_layer",
            "prp_step",
            "prp_descript",
            "prp_recipe",
            "prp_type",
            "prp_body_flag",
            "prp_cham_flag",
            "prp_compat_type",
            "prp_always",
            "prp_major",
            "prp_plan",
        ]
    )
    if not has_any_prp_param:
        return JsonResponse(payload)

    prp_base_rows = _get_prp_base_rows(prp_f, prp_filters)
    payload.update(_build_prp_option_values(prp_base_rows, prp_filters))

    is_valid, msg = _validate_prp_filters(prp_filters)
    if not is_valid:
        payload["message"] = msg
        return JsonResponse(payload)

    filtered_rows = _apply_prp_filters(prp_base_rows, prp_filters)


    for row in filtered_rows:
        override_items = row.get("override_target_list", []) or []
        row["override_editable"] = any(
            "TIP_MISSING" in (item.get("source_types") or [])
            for item in override_items
        )
        row["override_disabled_reason"] = (
            "" if row["override_editable"]
            else "TIP등록된 설비는 상시, 주요 설정으로 변경이 불가합니다."
        )

    payload["rows"] = filtered_rows
    return JsonResponse(payload)

@require_GET
@login_required
def dashboard_prp_options_api(request):
    _ensure_browser_close_session(request)
    permission_response = _check_page_permission(request, "dashboard", ignore_blank_scope=True)
    if permission_response is not None:
        return permission_response

    prp_f = _get_prp_common_filters(request)
    prp_filters = _get_prp_request_filters(request)

    prp_base_rows = _get_prp_base_rows(prp_f, prp_filters)
    payload = _build_prp_option_values(prp_base_rows, prp_filters)
    payload["ok"] = True
    return JsonResponse(payload)

