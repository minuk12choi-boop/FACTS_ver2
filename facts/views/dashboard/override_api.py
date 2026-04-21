import json
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from ...models import *
from ...permissions import _check_page_permission
from ..common import (
    _ensure_browser_close_session,
    _ensure_current_day_editable,
    _get_actor,
    _normalize_upper,
    _tip_missing_to_json,
)
from .helpers import _build_override_detail_rows

@login_required
def dashboard_override_save_api(request):
    _ensure_browser_close_session(request)

    payload = json.loads(request.body.decode("utf-8"))
    snap_date = datetime.strptime(payload["snap_date"], "%Y-%m-%d").date()
    date_block_response = _ensure_current_day_editable(snap_date)
    if date_block_response is not None:
        return date_block_response
    lineid = (payload.get("lineid") or "").strip()
    items = payload.get("items", [])
    first_processid = (items[0].get("processid") if items else "") or ""
    permission_response = _check_page_permission(request, "dashboard", lineid=lineid, processid=first_processid, require_edit=True, popup=True)
    if permission_response is not None:
        return permission_response
    field_type = payload["field_type"]
    value = payload["value"]
    actor = _get_actor(request)

    for item in items:
        processid = item["processid"]
        stepseq = item["stepseq"]

        source_rows = FactsWipSource.objects.filter(
            snap_date=snap_date,
            lineid=lineid,
            processid=processid,
            stepseq=stepseq,
        )
        if not source_rows.exists():
            return JsonResponse(
                {"ok": False, "message": "호환Path가 있어야 변경 가능합니다."},
                status=400,
            )

        for src in source_rows:
            obj, _ = FactsStepPathOverride.objects.get_or_create(
                snap_date=snap_date,
                lineid=src.lineid or "",
                processid=src.processid,
                stepseq=src.stepseq,
                recipeid=src.recipeid or "",
                path=src.path or "",
                eqpline=src.eqpline or "",
                childeqp=src.childeqp or "",
                defaults={"created_by": actor},
            )

            before_json = {
                "lineid": obj.lineid or "",
                "manual_always_emergency": obj.manual_always_emergency,
                "manual_major_minor": obj.manual_major_minor,
            }


            if field_type == "always_emergency":
                obj.manual_always_emergency = value
            elif field_type == "major_minor":
                obj.manual_major_minor = value

            obj.updated_by = actor
            obj.is_active = True
            obj.save()

            FactsEditHistory.objects.create(
                action_type="override",
                snap_date=snap_date,
                lineid=src.lineid or "",
                processid=src.processid,
                stepseq=src.stepseq,
                recipeid=src.recipeid or "",
                changed_by=actor,
                before_json=before_json,
                after_json={
                    "lineid": obj.lineid or "",
                    "manual_always_emergency": obj.manual_always_emergency,
                    "manual_major_minor": obj.manual_major_minor,
                },
            )

    cache.clear()
    return JsonResponse({"ok": True})

@require_GET
@login_required
def dashboard_override_detail_api(request):
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
    rows = _build_override_detail_rows(snap_date, lineid, processid, stepseq)

    return JsonResponse({
        "ok": True,
        "rows": rows,
    })

@require_POST
@login_required
def dashboard_override_member_save_api(request):
    _ensure_browser_close_session(request)

    payload = json.loads(request.body.decode("utf-8"))
    snap_date = datetime.strptime(payload["snap_date"], "%Y-%m-%d").date()
    date_block_response = _ensure_current_day_editable(snap_date)
    if date_block_response is not None:
        return date_block_response
    lineid = (payload.get("lineid") or "").strip()
    processid = (payload.get("processid") or "").strip()
    permission_response = _check_page_permission(request, "dashboard", lineid=lineid, processid=processid, require_edit=True, popup=True)
    if permission_response is not None:
        return permission_response
    stepseq = (payload.get("stepseq") or "").strip()
    field_type = (payload.get("field_type") or "").strip()
    member_items = payload.get("member_items", [])
    actor = _get_actor(request)


    if not processid or not stepseq or field_type not in ("always_emergency", "major_minor"):
        return JsonResponse({"ok": False, "message": "필수값이 부족합니다."}, status=400)

    for item in member_items:
        selected_flag = (item.get("selected_flag") or "N").strip().upper()
        eqp_body_name = _normalize_upper(item.get("eqp_body_name"))
        eqp_cham_name = _normalize_upper(item.get("eqp_cham_name"))
        source_types = item.get("source_types") or []
        path_refs = item.get("path_refs") or []

        if field_type == "always_emergency":
            target_value = "상시" if selected_flag == "Y" else "비상시"
        else:
            target_value = "주요" if selected_flag == "Y" else "비주요"

        if "SOURCE_PATH" in source_types:
            for ref in path_refs:
                recipeid = ref.get("recipeid") or ""
                path = ref.get("path") or ""
                eqpline = ref.get("eqpline") or ""
                childeqp = ref.get("childeqp") or ""

                src = FactsWipSource.objects.filter(
                    snap_date=snap_date,
                    lineid=lineid,
                    processid=processid,
                    stepseq=stepseq,
                    recipeid=recipeid,
                    path=path,
                    eqpline=eqpline,
                    childeqp=childeqp,
                ).first()
                if not src:
                    continue

                obj, _ = FactsStepPathOverride.objects.get_or_create(
                    snap_date=snap_date,
                    lineid=lineid,
                    processid=processid,
                    stepseq=stepseq,
                    recipeid=recipeid,
                    path=path,
                    eqpline=eqpline,
                    childeqp=childeqp,
                    defaults={"created_by": actor},
                )

                before_json = {
                    "lineid": obj.lineid or "",
                    "manual_always_emergency": obj.manual_always_emergency,
                    "manual_major_minor": obj.manual_major_minor,
                    "member_key": item.get("member_key") or "",
                }

                if field_type == "always_emergency":
                    obj.manual_always_emergency = target_value
                else:
                    obj.manual_major_minor = target_value

                obj.updated_by = actor
                obj.is_active = True
                obj.save()

                FactsEditHistory.objects.create(
                    action_type="override",
                    snap_date=snap_date,
                    lineid=lineid,
                    processid=processid,
                    stepseq=stepseq,
                    recipeid=recipeid,
                    changed_by=actor,
                    before_json=before_json,
                    after_json={
                        "lineid": obj.lineid or "",
                        "manual_always_emergency": obj.manual_always_emergency,
                        "manual_major_minor": obj.manual_major_minor,
                        "member_key": item.get("member_key") or "",
                    },
                )

        if "TIP_MISSING" in source_types and eqp_body_name:
            manual_qs = FactsTipMissingCompatPath.objects.filter(
                snap_date=snap_date,
                lineid=lineid,
                processid=processid,
                stepseq=stepseq,
                eqp_body_name=eqp_body_name,
                eqp_cham_name=eqp_cham_name,
                is_active=True,
            )

            for obj in manual_qs:
                before_json = _tip_missing_to_json(obj)

                if field_type == "always_emergency":
                    obj.always_emergency = target_value
                else:
                    obj.major_minor = target_value

                obj.updated_by = actor
                obj.save()

                FactsEditHistory.objects.create(
                    action_type="tip_missing_update",
                    snap_date=snap_date,
                    lineid=lineid,
                    processid=processid,
                    stepseq=stepseq,
                    recipeid=obj.recipeid or "",
                    changed_by=actor,
                    before_json=before_json,
                    after_json=_tip_missing_to_json(obj),
                )

    cache.clear()
    return JsonResponse({"ok": True})

