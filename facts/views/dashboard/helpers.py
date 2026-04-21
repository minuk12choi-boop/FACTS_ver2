from django.core.cache import cache
from django.templatetags.static import static

from ...models import *
from ... import services
from ...permissions import (
    _get_permission_scope_defaults,
    _get_request_department,
    _get_request_login_id,
)
from ..common import (
    _normalize_date_input,
    _parse_bool,
    _resolve_snap_date,
)

def _get_dashboard_common_filters(request):
    snap_date = _resolve_snap_date(request)
    username = _get_request_login_id(request)
    dept = _get_request_department(request)
    permission_defaults = _get_permission_scope_defaults("dashboard", username, dept)
    dashboard_cfg = services.get_dashboard_config()

    if hasattr(dashboard_cfg, "default_prp"):
        default_prp = dashboard_cfg.default_prp or "P1SD"
        inquiry_contact = dashboard_cfg.inquiry_contact or "minuk12.choi"
    else:
        default_prp = dashboard_cfg["default_prp"]
        inquiry_contact = dashboard_cfg["inquiry_contact"]

    processid = request.GET.get("processid")
    if processid is None or processid == "":
        processid = permission_defaults["processid"] or default_prp

    if processid == "미설정":
        processid = ""

    areaname = request.GET.get("areaname") or ""
    layerid = services.normalize_layer_value(request.GET.get("layerid") or "")
    lineid = (request.GET.get("lineid") or permission_defaults["lineid"] or "").strip()
    include_measure = _parse_bool(request.GET.get("include_measure"), default=("include_measure" not in request.GET))
    include_emergency = _parse_bool(request.GET.get("include_emergency"), default=("include_emergency" not in request.GET))
    exclude_skiprule_100 = _parse_bool(request.GET.get("exclude_skiprule_100"), default=("exclude_skiprule_100" not in request.GET))
    tip_mode = _parse_bool(request.GET.get("tip_mode"), default=True)

    return {
        "snap_date": snap_date,
        "processid": processid,
        "areaname": areaname,
        "layerid": layerid,
        "lineid": lineid,
        "include_measure": include_measure,
        "include_emergency": include_emergency,
        "exclude_skiprule_100": exclude_skiprule_100,
        "tip_mode": tip_mode,
        "inquiry_contact": inquiry_contact,
    }

def _get_prp_common_filters(request):
    prp_snap_date = _normalize_date_input(request.GET.get("prp_snap_date") or "")
    if prp_snap_date is None:
        prp_snap_date = services.get_latest_snap_date()

    return {
        "snap_date": prp_snap_date,
        "include_measure": True,
        "include_emergency": True,
        "exclude_skiprule_100": True,
        "tip_mode": True,
    }

def _build_guide_pages_json():
    active_guide = FactsGuideDocument.objects.filter(is_active=True).order_by("-updated_at", "-id").first()
    if not active_guide:
        return []

    pages_payload = []
    for page in active_guide.pages.all().order_by("page_no"):
        static_path = page.image_path or ""
        if static_path:
            pages_payload.append({
                "page_no": page.page_no,
                "image_url": static_path,
            })

    return pages_payload

def _build_dashboard_api_urls_json():
    return {
        "dashboardDataApi": "/facts/dashboard/data-api/",
        "dashboardPrpOptionsApi": "/facts/dashboard/prp-options-api/",
        "dashboardOverrideSaveApi": "/facts/dashboard/override-save-api/",
        "dashboardOverrideDetailApi": "/facts/dashboard/override-detail-api/",
        "dashboardOverrideMemberSaveApi": "/facts/dashboard/override-member-save-api/",
        "dashboardPlanDetailApi": "/facts/dashboard/plan-detail-api/",
        "dashboardPlanSaveApi": "/facts/dashboard/plan-save-api/",
        "dashboardPlanDeleteApi": "/facts/dashboard/plan-delete-api/",
        "dashboardTipMissingDetailApi": "/facts/dashboard/tip-missing-detail-api/",
        "dashboardTipMissingSaveApi": "/facts/dashboard/tip-missing-save-api/",
        "dashboardTipMissingDeleteApi": "/facts/dashboard/tip-missing-delete-api/",
        "dashboardSimilarEqpApi": "/facts/dashboard/similar-eqp-api/",
        "dashboardBulkUploadApi": "/facts/dashboard/bulk-upload-api/",
        "prpExportCsvApi": "/facts/dashboard/prp-export-csv/",
        "prpExportCsvAllApi": "/facts/dashboard/prp-export-csv-all/",
    }

def _build_summary_and_chart_payload(f):
    cache_key = (
        "facts:summary:"
        f"{f['snap_date']}|{f['lineid']}|{f['processid']}|{f['areaname']}|{f['layerid']}|"
        f"{int(bool(f['include_measure']))}|{int(bool(f['include_emergency']))}|"
        f"{int(bool(f['exclude_skiprule_100']))}|{int(bool(f['tip_mode']))}"
    )
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    step_rows = services.build_step_dataset(
        snap_date=f["snap_date"],
        processid=f["processid"] or None,
        areaname=f["areaname"] or None,
        layerid=f["layerid"] or None,
        lineid=f["lineid"] or None,
        include_measure=f["include_measure"],
        include_emergency=f["include_emergency"],
        exclude_skiprule_100=f["exclude_skiprule_100"],
        tip_mode=f["tip_mode"],
        for_prp_table=False,
    )

    summary = services.summarize_steps(step_rows, use_tip=f["tip_mode"])

    target_monthly = services.get_kpi_target_value(
        processid=f["processid"],
        target_type="monthly",
        snap_date=f["snap_date"],
        areaname=f["areaname"],
        lineid=f["lineid"],
    )

    combined_series = services.get_dashboard_combined_series(
        snap_date=f["snap_date"],
        processid=f["processid"] or None,
        areaname=f["areaname"] or None,
        layerid=f["layerid"] or None,
        lineid=f["lineid"] or None,
        include_measure=f["include_measure"],
        include_emergency=f["include_emergency"],
        exclude_skiprule_100=f["exclude_skiprule_100"],
        tip_mode=f["tip_mode"],
        target_monthly=target_monthly,
    )

    result = (summary, target_monthly, combined_series)
    cache.set(cache_key, result, 60)
    return result

def _get_prp_request_filters(request):
    username = _get_request_login_id(request)
    dept = _get_request_department(request)
    permission_defaults = _get_permission_scope_defaults("dashboard", username, dept)

    return {
        "prp_snap_date": (request.GET.get("prp_snap_date") or request.GET.get("snap_date") or "").strip(),
        "prp_lineid": (request.GET.get("prp_lineid") or permission_defaults["lineid"] or "").strip(),
        "prp_processid": (request.GET.get("prp_processid") or permission_defaults["processid"] or "").strip(),
        "prp_area": (request.GET.get("prp_area") or "").strip(),
        "prp_layer": services.normalize_layer_value(request.GET.get("prp_layer") or ""),
        "prp_step": (request.GET.get("prp_step") or "").strip(),
        "prp_descript": (request.GET.get("prp_descript") or "").strip(),
        "prp_recipe": (request.GET.get("prp_recipe") or "").strip(),
        "prp_type": (request.GET.get("prp_type") or "").strip(),
        "prp_body_flag": (request.GET.get("prp_body_flag") or "").strip(),
        "prp_cham_flag": (request.GET.get("prp_cham_flag") or "").strip(),
        "prp_compat_type": (request.GET.get("prp_compat_type") or "").strip(),
        "prp_always": (request.GET.get("prp_always") or "").strip(),
        "prp_major": (request.GET.get("prp_major") or "").strip(),
        "prp_plan": (request.GET.get("prp_plan") or "").strip(),
    }

def _validate_prp_filters(prp_filters):
    prp = prp_filters["prp_processid"]
    if not prp:
        return False, "PRP조건은 필수입니다."

    other_values = [
        prp_filters["prp_lineid"],
        prp_filters["prp_area"],
        prp_filters["prp_layer"],
        prp_filters["prp_step"],
        prp_filters["prp_descript"],
        prp_filters["prp_recipe"],
        prp_filters["prp_type"],
        prp_filters["prp_body_flag"],
        prp_filters["prp_cham_flag"],
        prp_filters["prp_compat_type"],
        prp_filters["prp_always"],
        prp_filters["prp_major"],
        prp_filters["prp_plan"],
    ]

    if not any(str(v or "").strip() for v in other_values):
        return False, "PRP조건과 그 외 필터 조건 최소 1개 이상 설정 후 조회하십시오."

    return True, ""

def _resolve_prp_snap_date(prp_filters, fallback_snap_date):
    snap_date = _normalize_date_input(prp_filters.get("prp_snap_date"))
    return snap_date or fallback_snap_date

def _row_matches_prp_filters(row, prp_filters, exclude_keys=None):
    exclude_keys = set(exclude_keys or [])

    if "prp_snap_date" not in exclude_keys:
        prp_snap_date = (prp_filters.get("prp_snap_date") or "").strip()
        if prp_snap_date:
            row_snap = row.get("snap_date")
            row_snap_str = row_snap.strftime("%Y-%m-%d") if hasattr(row_snap, "strftime") else str(row_snap or "")
            if row_snap_str != prp_snap_date:
                return False

    if "prp_lineid" not in exclude_keys and prp_filters.get("prp_lineid"):
        if (row.get("lineid") or "") != prp_filters["prp_lineid"]:
            return False

    if "prp_processid" not in exclude_keys and prp_filters.get("prp_processid"):
        if (row.get("processid") or "") != prp_filters["prp_processid"]:
            return False

    if "prp_area" not in exclude_keys and prp_filters.get("prp_area"):
        if (row.get("areaname") or "") != prp_filters["prp_area"]:
            return False

    if "prp_layer" not in exclude_keys and prp_filters.get("prp_layer"):
        if services.normalize_layer_value(row.get("layerid") or "") != prp_filters["prp_layer"]:
            return False

    if "prp_step" not in exclude_keys and prp_filters.get("prp_step"):
        if str(row.get("stepseq") or "") != prp_filters["prp_step"]:
            return False

    if "prp_descript" not in exclude_keys and prp_filters.get("prp_descript"):
        if prp_filters["prp_descript"].upper() not in str(row.get("descript") or "").upper():
            return False

    if "prp_recipe" not in exclude_keys and prp_filters.get("prp_recipe"):
        if prp_filters["prp_recipe"].upper() not in str(row.get("recipeid") or "").upper():
            return False

    if "prp_type" not in exclude_keys and prp_filters.get("prp_type"):
        if (row.get("stepseq_type") or "") != prp_filters["prp_type"]:
            return False

    if "prp_body_flag" not in exclude_keys and prp_filters.get("prp_body_flag"):
        if (row.get("body_compat_flag") or "") != prp_filters["prp_body_flag"]:
            return False

    if "prp_cham_flag" not in exclude_keys and prp_filters.get("prp_cham_flag"):
        if (row.get("cham_compat_flag") or "") != prp_filters["prp_cham_flag"]:
            return False

    if "prp_compat_type" not in exclude_keys and prp_filters.get("prp_compat_type"):
        if (row.get("compat_type") or "") != prp_filters["prp_compat_type"]:
            return False

    if "prp_always" not in exclude_keys and prp_filters.get("prp_always"):
        val = "Y" if row.get("has_always") else "N"
        if val != prp_filters["prp_always"]:
            return False

    if "prp_major" not in exclude_keys and prp_filters.get("prp_major"):
        val = "Y" if row.get("has_major") else "N"
        if val != prp_filters["prp_major"]:
            return False

    if "prp_plan" not in exclude_keys and prp_filters.get("prp_plan"):
        val = "Y" if row.get("has_plan") else "N"
        if val != prp_filters["prp_plan"]:
            return False

    return True

def _build_prp_option_values(rows, prp_filters):
    def filtered_rows(exclude_key):
        return [r for r in rows if _row_matches_prp_filters(r, prp_filters, exclude_keys={exclude_key})]

    line_rows = filtered_rows("prp_lineid")
    process_rows = filtered_rows("prp_processid")
    area_rows = filtered_rows("prp_area")
    layer_rows = filtered_rows("prp_layer")
    step_rows = filtered_rows("prp_step")
    type_rows = filtered_rows("prp_type")

    table_line_options = sorted({(r.get("lineid") or "") for r in line_rows if (r.get("lineid") or "")})
    table_prp_options = sorted({(r.get("processid") or "") for r in process_rows if (r.get("processid") or "")})
    table_area_options = sorted({(r.get("areaname") or "") for r in area_rows if (r.get("areaname") or "")})
    table_layer_options = sorted(
        {services.normalize_layer_value(r.get("layerid") or "") for r in layer_rows if services.normalize_layer_value(r.get("layerid") or "")},
        key=lambda x: [float(x)] if str(x).replace(".", "", 1).isdigit() else [x],
    )
    table_step_options = sorted({(r.get("stepseq") or "") for r in step_rows if (r.get("stepseq") or "")})
    table_type_options = sorted({(r.get("stepseq_type") or "") for r in type_rows if (r.get("stepseq_type") or "")})

    return {
        "table_line_options": table_line_options,
        "table_prp_options": table_prp_options,
        "table_area_options": table_area_options,
        "table_layer_options": table_layer_options,
        "table_step_options": table_step_options,
        "table_type_options": table_type_options,
    }

def _apply_prp_filters(rows, prp_filters):
    return [row for row in rows if _row_matches_prp_filters(row, prp_filters)]

def _get_prp_base_rows(f, prp_filters):
    prp_snap_date = _resolve_prp_snap_date(prp_filters, f["snap_date"])

    return services.build_step_dataset(
        snap_date=prp_snap_date,
        lineid=None,
        processid=None,
        areaname=None,
        layerid=None,
        include_measure=f["include_measure"],
        include_emergency=f["include_emergency"],
        exclude_skiprule_100=f["exclude_skiprule_100"],
        tip_mode=f["tip_mode"],
        for_prp_table=True,
    )

def _build_override_detail_rows(snap_date, lineid, processid, stepseq):
    step_rows = services.build_step_dataset(
        snap_date=snap_date,
        processid=processid,
        lineid=lineid,
        include_measure=True,
        include_emergency=True,
        exclude_skiprule_100=False,
        tip_mode=False,
        for_prp_table=True,
    )

    target_row = next(
        (
            x for x in step_rows
            if x["processid"] == processid
            and x["stepseq"] == stepseq
            and (x.get("lineid") or "") == (lineid or "")
        ),
        None,
    )
    if not target_row:
        return []

    result = []
    for item in target_row.get("override_target_list", []):
        source_types = item.get("source_types", [])
        source_display_parts = []

        if "SOURCE_PATH" in source_types:
            source_display_parts.append("TIP등록 Path")
        if "TIP_MISSING" in source_types:
            source_display_parts.append("TIP미등록 호환Path")

        result.append({
            "member_key": item.get("member_key", ""),
            "eqp_body_name": item.get("eqp_body_name", ""),
            "eqp_cham_name": item.get("eqp_cham_name", ""),
            "member_display": item.get("display_name", ""),
            "source_display": " / ".join(source_display_parts),
            "current_flag": "Y" if item.get("has_always") else "N",
            "current_major_flag": "Y" if item.get("has_major") else "N",
            "source_types": source_types,
            "path_refs": item.get("path_refs", []),
        })

    return result

def _is_invalid_single_cham_value(value):
    s = str(value or "").strip().upper()
    if not s:
        return False
    if any(sep in s for sep in [":", ";", ","]):
        return True
    if len(s) > 1:
        return True
    return False

