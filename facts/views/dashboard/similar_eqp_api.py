from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from ...models import *
from ... import services
from ...permissions import _check_page_permission
from ..common import _ensure_browser_close_session

@require_GET
@login_required
def dashboard_similar_eqp_api(request):
    _ensure_browser_close_session(request)
    permission_response = _check_page_permission(request, "dashboard", ignore_blank_scope=True)
    if permission_response is not None:
        return permission_response

    snap_date_str = request.GET.get("snap_date", "").strip()
    lineid = request.GET.get("lineid", "").strip()
    processid = request.GET.get("processid", "").strip()
    stepseq = request.GET.get("stepseq", "").strip()

    if not snap_date_str:
        return JsonResponse({"ok": False, "message": "기준일이 없습니다."}, status=400)
    if not processid or not stepseq:
        return JsonResponse({"ok": False, "message": "processid 또는 stepseq가 없습니다."}, status=400)

    scope_response = _check_page_permission(request, "dashboard", lineid=lineid, processid=processid, popup=True)
    if scope_response is not None:
        return scope_response

    snap_date = datetime.strptime(snap_date_str, "%Y-%m-%d").date()

    result = services.get_similar_model_eqp_candidates(
        snap_date=snap_date,
        processid=processid,
        stepseq=stepseq,
        include_current=False,
    )

    rows = []
    for row in result["recommendations"]:
        origin_line_id = row.get("origin_line_id", "")
        line_obj = FactsLineMaster.objects.filter(line_id=origin_line_id, is_active=True).first()

        if line_obj and line_obj.line_name:
            display_location = f"{line_obj.line_name}({line_obj.line_id})"
        else:
            display_location = origin_line_id

        rows.append({
            "eqp_id": row.get("eqp_id", ""),
            "origin_line_id": display_location,
            "eqp_model": row.get("eqp_model", ""),
            "match_type": row.get("match_type", ""),
            "match_score": row.get("match_score", ""),
            "matched_base_model": row.get("matched_base_model", ""),
        })

    return JsonResponse({
        "ok": True,
        "base_eqps": result["base_eqps"],
        "base_models": result["base_models"],
        "rows": rows,
        "notice": "해당 추천은 GPM 등록된 EQP_MODEL을 기준으로 합니다.",
    })

