import json
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from ...models import *
from ... import services
from ...permissions import _check_page_permission
from ..common import (
    _ensure_browser_close_session,
    _ensure_current_day_editable,
    _get_actor,
    _normalize_upper,
    _tip_missing_to_json,
)

@require_GET
@login_required
def dashboard_tip_missing_detail_api(request):
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

    scope_response = _check_page_permission(request, "dashboard", lineid=lineid, processid=processid, popup=True)
    if scope_response is not None:
        return scope_response

    snap_date = datetime.strptime(snap_date_str, "%Y-%m-%d").date()
    rows = services.get_tip_missing_detail_rows_as_of(snap_date, lineid, processid, stepseq)

    return JsonResponse({
        "ok": True,
        "rows": rows,
    })

@require_POST
@login_required
def dashboard_tip_missing_save_api(request):
    _ensure_browser_close_session(request)

    payload = json.loads(request.body.decode("utf-8"))
    snap_date = datetime.strptime(payload["snap_date"], "%Y-%m-%d").date()
    date_block_response = _ensure_current_day_editable(snap_date)
    if date_block_response is not None:
        return date_block_response
    items = payload.get("items", [])
    actor = _get_actor(request)
    lineid = (payload.get("lineid") or "").strip()
    first_processid = (items[0].get("processid") if items else "") or ""
    permission_response = _check_page_permission(request, "dashboard", lineid=lineid, processid=first_processid, require_edit=True, popup=True)
    if permission_response is not None:
        return permission_response

    always_emergency = (payload.get("always_emergency") or "").strip()
    major_minor = (payload.get("major_minor") or "").strip()
    eqp_body_name = _normalize_upper(payload.get("eqp_body_name"))
    eqp_cham_name = _normalize_upper(payload.get("eqp_cham_name"))
    tip_missing_id = payload.get("tip_missing_id")

    if not always_emergency:
        return JsonResponse({"ok": False, "message": "상시/비상시는 필수기재입니다."}, status=400)
    if not major_minor:
        return JsonResponse({"ok": False, "message": "주요/비주요는 필수기재입니다."}, status=400)
    if not eqp_body_name:
        return JsonResponse({"ok": False, "message": "호환EQPBODY명은 필수기재입니다."}, status=400)
    if not items:
        return JsonResponse({"ok": False, "message": "대상 step이 없습니다."}, status=400)

    for item in items:
        item_lineid = (item.get("lineid") or lineid or "").strip()
        processid = item["processid"]
        stepseq = item["stepseq"]

        if tip_missing_id:
            obj = FactsTipMissingCompatPath.objects.filter(
                id=tip_missing_id,
                lineid=item_lineid,
                processid=processid,
                stepseq=stepseq,
                is_active=True,
            ).first()
            if not obj:
                return JsonResponse({"ok": False, "message": "수정 대상 미등록TIP호환Path가 없습니다."}, status=404)

            before_json = _tip_missing_to_json(obj)
            obj.always_emergency = always_emergency
            obj.major_minor = major_minor
            obj.eqp_body_name = eqp_body_name
            obj.eqp_cham_name = eqp_cham_name
            obj.updated_by = actor
            obj.save()

            FactsEditHistory.objects.create(
                action_type="tip_missing_update",
                snap_date=snap_date,
                lineid=item_lineid,
                processid=processid,
                stepseq=stepseq,
                recipeid=obj.recipeid or "",
                changed_by=actor,
                before_json=before_json,
                after_json=_tip_missing_to_json(obj),
            )
        else:
            obj = FactsTipMissingCompatPath.objects.create(
                snap_date=snap_date,
                lineid=item_lineid,
                processid=processid,
                stepseq=stepseq,
                recipeid="",
                always_emergency=always_emergency,
                major_minor=major_minor,
                eqp_body_name=eqp_body_name,
                eqp_cham_name=eqp_cham_name,
                is_active=True,
                created_by=actor,
                updated_by=actor,
            )

            FactsEditHistory.objects.create(
                action_type="tip_missing_add",
                snap_date=snap_date,
                lineid=item_lineid,
                processid=processid,
                stepseq=stepseq,
                recipeid="",
                changed_by=actor,
                before_json={},
                after_json=_tip_missing_to_json(obj),
            )

    cache.clear()
    return JsonResponse({"ok": True})

@require_POST
@login_required
def dashboard_tip_missing_delete_api(request):
    _ensure_browser_close_session(request)

    payload = json.loads(request.body.decode("utf-8"))
    tip_missing_id = payload.get("tip_missing_id")
    actor = _get_actor(request)
    snap_date_str = (payload.get("snap_date") or "").strip()
    snap_date = datetime.strptime(snap_date_str, "%Y-%m-%d").date() if snap_date_str else None
    date_block_response = _ensure_current_day_editable(snap_date)
    if date_block_response is not None:
        return date_block_response
    lineid = (payload.get("lineid") or "").strip()
    processid = (payload.get("processid") or "").strip()

    permission_response = _check_page_permission(
        request,
        "dashboard",
        lineid=lineid,
        processid=processid,
        require_edit=True,
        popup=True,
    )
    if permission_response is not None:
        return permission_response

    obj = FactsTipMissingCompatPath.objects.filter(id=tip_missing_id, lineid=lineid, is_active=True).first()
    if not obj:
        return JsonResponse({"ok": False, "message": "삭제 대상 미등록TIP호환Path가 없습니다."}, status=404)

    before_json = _tip_missing_to_json(obj)
    obj.is_active = False
    obj.updated_by = actor
    obj.save()

    FactsEditHistory.objects.create(
        action_type="tip_missing_delete",
        snap_date=obj.snap_date,
        lineid=lineid,
        processid=obj.processid,
        stepseq=obj.stepseq,
        recipeid=obj.recipeid or "",
        changed_by=actor,
        before_json=before_json,
        after_json={"deleted": True, "id": obj.id},
    )

    cache.clear()
    return JsonResponse({"ok": True})

