from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.views.decorators.http import require_GET

from ... import services
from ...permissions import _check_page_permission
from ..common import _ensure_browser_close_session
from .helpers import (
    _apply_prp_filters,
    _get_prp_common_filters,
    _get_prp_request_filters,
    _get_prp_base_rows,
    _validate_prp_filters,
)

@require_GET
@login_required
def prp_export_csv(request):
    _ensure_browser_close_session(request)
    permission_response = _check_page_permission(request, "dashboard", ignore_blank_scope=True)
    if permission_response is not None:
        return permission_response

    prp_f = _get_prp_common_filters(request)
    prp_filters = _get_prp_request_filters(request)

    is_valid, msg = _validate_prp_filters(prp_filters)
    if not is_valid:
        return HttpResponse(msg, content_type="text/plain; charset=utf-8", status=400)

    prp_base_rows = _get_prp_base_rows(prp_f, prp_filters)
    step_rows = _apply_prp_filters(prp_base_rows, prp_filters)
    csv_text = services.export_prp_csv(step_rows)

    response = HttpResponse(csv_text, content_type="text/csv; charset=utf-8-sig")
    response["Content-Disposition"] = 'attachment; filename="facts_prp_table_filtered.csv"'
    return response

@require_GET
@login_required
def prp_export_csv_all(request):
    _ensure_browser_close_session(request)
    permission_response = _check_page_permission(request, "dashboard", ignore_blank_scope=True)
    if permission_response is not None:
        return permission_response

    prp_f = _get_prp_common_filters(request)
    prp_filters = _get_prp_request_filters(request)
    prp_processid = (prp_filters.get("prp_processid") or "").strip()

    if not prp_processid:
        return HttpResponse("PRP조건은 필수입니다.", content_type="text/plain; charset=utf-8", status=400)

    prp_base_rows = _get_prp_base_rows(prp_f, prp_filters)
    step_rows = [r for r in prp_base_rows if (r.get("processid") or "") == prp_processid]
    csv_text = services.export_prp_csv(step_rows)

    response = HttpResponse(csv_text, content_type="text/csv; charset=utf-8-sig")
    response["Content-Disposition"] = f'attachment; filename="facts_prp_table_all_{prp_processid}.csv"'
    return response

