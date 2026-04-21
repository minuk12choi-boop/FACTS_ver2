# 1. 임포트 및 상수 (Constants)

from datetime import date, datetime  # 내장 모듈: 날짜와 시간을 다루는 클래스
from django.http import JsonResponse  # 장고 객체: JSON 응답을 생성하는 클래스

from ..models import * # 객체: 상위 디렉토리 models.py의 모든 클래스(DB 모델)
from .. import services  # 모듈: 상위 디렉토리의 비즈니스 로직(서비스) 모음
from ..permissions import (  # 함수: 권한 관련 유틸리티 함수들
    _get_request_department,
    _get_request_login_id,
)


# 딕셔너리 객체: 시스템 내 작업 코드(Key)를 한글 설명(Value)으로 매핑
ACTION_TYPE_LABELS = {
    "override": "스텝수정(상시/비상시 또는 주요/비주요 변경)",
    "plan_add": "호환계획 추가",
    "plan_update": "호환계획 수정",
    "plan_delete": "호환계획 삭제",
    "tip_missing_add": "TIP미등록 호환Path 추가",
    "tip_missing_update": "TIP미등록 호환Path 수정",
    "tip_missing_delete": "TIP미등록 호환Path 삭제",
    "bulk_upload": "엑셀 업로드 반영",
    "dashboard_config_update": "대시보드 기준정보 수정",
    "guide_upload": "사용 가이드 업로드",
    "guide_path_save": "사용 가이드 경로 저장",
    "master_add": "필요평가단계 추가",
    "master_update": "필요평가단계 수정",
    "master_delete": "필요평가단계 삭제",
    "line_master_add": "라인코드 기준정보 추가",
    "line_master_update": "라인코드 기준정보 수정",
    "line_master_delete": "라인코드 기준정보 삭제",
    "kpi_add": "KPI 목표 추가",
    "kpi_update": "KPI 목표 수정/삭제",
    "prevent_rule_add": "PREVENT 기준정보 추가",
    "prevent_rule_update": "PREVENT 기준정보 수정",
    "prevent_rule_delete": "PREVENT 기준정보 삭제",
    "dept_permission_add": "부서권한 기준정보 추가",
    "dept_permission_update": "부서권한 기준정보 수정",
    "dept_permission_delete": "부서권한 기준정보 삭제",
}



# 2. 사용자 및 부서 관련 함수
# 함수: 현재 요청(request)을 보낸 사용자가 로그인 상태인지 확인하고 사용자 객체를 반환
def _get_actor(request):
    if hasattr(request, "user") and getattr(request.user, "is_authenticated", False):
        return request.user  # 로그인된 사용자 객체 반환
    return None

# 함수: 모든 부서 정보를 가져와 {ID: 부서명} 형태의 딕셔너리로 반환
def _get_dept_master_map():
    # FactsDepartmentMaster: Django 모델 클래스
    return {str(row.id): row.department for row in FactsDepartmentMaster.objects.all().order_by("department", "id")}

# 함수: 입력받은 부서 값(ID 또는 명칭)을 부서 맵과 대조하여 정규화된 부서명 반환
def _resolve_department_from_post(raw_value, dept_map):
    raw = (raw_value or "").strip()
    if raw == "" or raw.upper() == "ALL":
        return "ALL"
    if raw in dept_map: # ID로 들어온 경우
        return dept_map[raw]
    return raw if raw in dept_map.values() else "ALL" # 명칭으로 들어온 경우 검증




# 3. 세션 및 이력 관리 함수
# 함수: 브라우저를 닫으면 세션이 만료되도록 설정 (보안용)
def _ensure_browser_close_session(request):
    try:
        if hasattr(request, "user") and getattr(request.user, "is_authenticated", False):
            request.session.set_expiry(0)
    except Exception:
        pass

# 함수: 사용자의 페이지 접속 및 활동 이력을 DB에 기록
def _record_access_history(request, page_code):
    try:
        user = getattr(request, "user", None)
        FactsAccessHistory.objects.create(
            page_code=page_code or "",
            path=(request.path or "")[:500],
            method=(request.method or "GET")[:20],
            username=_get_request_login_id(request),
            sabun=(request.session.get("sso_sabun") or "")[:150],
            department=_get_request_department(request),
            lineid=(request.GET.get("lineid") or request.POST.get("lineid") or "")[:20],
            processid=(request.GET.get("processid") or request.POST.get("processid") or "")[:100],
            snap_date=_resolve_snap_date(request) if (request.GET.get("snap_date") or request.POST.get("snap_date")) else None,
            query_string=(request.META.get("QUERY_STRING") or ""),
            ip_address=(request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip() or request.META.get("REMOTE_ADDR") or "")[:100],
        )
    except Exception:
        pass




# 4. 데이터 파싱 및 정규화 함수
# 다양한 형식의 입력을 시스템이 이해할 수 있는 형태로 바꿉니다.
# 함수: 문자열("true", "1", "y")을 실제 Boolean 값(True/False)으로 변환
def _parse_bool(value, default=False):
    if value is None:
        return default
    return str(value).lower() in ("1", "true", "y", "yes", "on")

# 함수: 요청 데이터에서 날짜를 추출하거나, 없으면 최신 스냅샷 날짜를 반환
def _resolve_snap_date(request):
    snap_date_str = request.GET.get("snap_date") or request.POST.get("snap_date")
    if snap_date_str:
        return datetime.strptime(snap_date_str, "%Y-%m-%d").date()
    return services.get_latest_snap_date()

# 함수: 다양한 날짜 형식(., /, - 등)의 문자열을 파이썬 date 객체로 변환
def _normalize_date_input(value):
    if value is None:
        return None

    if hasattr(value, "strftime"):
        try:
            return value.date() if hasattr(value, "date") else value
        except Exception:
            pass

    s = str(value).strip()
    if not s:
        return None

    candidates = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%Y.%m.%d",
        "%y-%m-%d",
        "%y/%m/%d",
        "%y.%m.%d",
        "%Y %m %d",
        "%y %m %d",
    ]
    for fmt in candidates:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None

# 함수: 문자열을 공백 제거 후 대문자로 변환
def _normalize_upper(value):
    return str(value or "").strip().upper()


# 함수: 주차(Week) 입력값(예: 'W12' 또는 '12')에서 숫자만 추출
def _parse_week_input(value):
    s = str(value or "").strip().upper()
    if not s:
        return None
    if s.startswith("W"):
        s = s[1:]
    if not s.isdigit():
        return None
    n = int(s)
    if n < 1 or n > 53:
        return None
    return n

# 함수: 숫자를 주차 표시 형식(W01, W12 등)으로 변환
def _week_display(value):
    if value in (None, ""):
        return ""
    try:
        n = int(value)
    except (TypeError, ValueError):
        return ""
    if n < 1:
        return ""
    return f"W{n:02d}"


# 5. 결과 직렬화 및 유효성 검사 함수
# 데이터를 내보내거나 수정 가능 여부를 체크합니다.
# 함수: '계획(Plan)' 모델 객체를 프론트엔드로 보낼 수 있게 딕셔너리(JSON용)로 변환
def _plan_to_json(obj):
    return {
        "id": obj.id,
        "lineid": obj.lineid or "",
        "always_emergency": obj.always_emergency or "",
        "major_minor": obj.major_minor or "",
        "eqp_body_name": obj.eqp_body_name or "",
        "eqp_cham_name": obj.eqp_cham_name or "",
        "compatibility_due_date": obj.compatibility_due_date.isoformat() if obj.compatibility_due_date else "",
        "eval_lot_id": obj.eval_lot_id or "",
        "required_eval_stage_id": obj.required_eval_stage_id or "",
        "required_eval_stage_code": obj.required_eval_stage.stage_code if obj.required_eval_stage else "",
        "required_eval_stage_name": obj.required_eval_stage.stage_name if obj.required_eval_stage else "",
        "memo": obj.memo or "",
    }

def _tip_missing_to_json(obj):
    return {
        "id": obj.id,
        "lineid": obj.lineid or "",
        "always_emergency": obj.always_emergency or "",
        "major_minor": obj.major_minor or "",
        "eqp_body_name": obj.eqp_body_name or "",
        "eqp_cham_name": obj.eqp_cham_name or "",
    }

# 함수: 데이터 수정 시, 현재 날짜 데이터가 아니면 수정을 막는 유효성 검
def _ensure_current_day_editable(snap_date):
    if snap_date != date.today():
        return JsonResponse({"ok": False, "message": "현재일로 조회 후 수정바랍니다."}, status=400)
    return None

# 함수: 이력 데이터 목록을 돌며 각 항목에 맞는 한글 라벨을 붙여줌
def _make_history_label_rows(rows):
    for row in rows:
        row.action_type_label = services.get_action_type_label(row.action_type, row.before_json, row.after_json)
    return rows

