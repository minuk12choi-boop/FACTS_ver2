import re
from datetime import date, datetime

FACTS_ACTION_TYPE_LABELS = {
    "override": "스텝수정",
    "plan_add": "호환계획 추가",
    "plan_update": "호환계획 수정",
    "plan_delete": "호환계획 삭제",
    "tip_missing_add": "TIP미등록 호환Path 추가",
    "tip_missing_update": "TIP미등록 호환Path 수정",
    "tip_missing_delete": "TIP미등록 호환Path 삭제",
    "bulk_upload": "엑셀 업로드 반영",
    "dashboard_config_update": "대시보드 기준정보 수정",
    "guide_upload": "가이드 업로드",
    "guide_path_save": "가이드 경로 저장",
    "master_add": "필요평가단계 추가",
    "master_update": "필요평가단계 수정",
    "master_delete": "필요평가단계 삭제",
    "line_master_add": "라인 기준정보 추가",
    "line_master_update": "라인 기준정보 수정",
    "line_master_delete": "라인 기준정보 삭제",
    "kpi_add": "KPI 추가",
    "kpi_update": "KPI 수정/삭제",
    "prevent_rule_add": "PREVENT 기준정보 추가",
    "prevent_rule_update": "PREVENT 기준정보 수정",
    "prevent_rule_delete": "PREVENT 기준정보 삭제",
    "dept_permission_add": "부서권한 기준정보 추가",
    "dept_permission_update": "부서권한 기준정보 수정",
    "dept_permission_delete": "부서권한 기준정보 삭제",
}

ACTION_TYPE_LABELS = FACTS_ACTION_TYPE_LABELS.copy()


def get_action_type_label(action_type, before_json=None, after_json=None):
    label = ACTION_TYPE_LABELS.get(action_type, action_type)
    before = before_json or {}
    after = after_json or {}
    try:
        if action_type == "override":
            if before.get("manual_always_emergency") != after.get("manual_always_emergency"):
                return "상시/비상시 수정"
            if before.get("manual_major_minor") != after.get("manual_major_minor"):
                return "주요/비주요 수정"
        if action_type == "tip_missing_update":
            if before.get("always_emergency") != after.get("always_emergency"):
                return "TIP미등록 호환Path 상시/비상시 수정"
            if before.get("major_minor") != after.get("major_minor"):
                return "TIP미등록 호환Path 주요/비주요 수정"
    except Exception:
        pass
    return label


def normalize_layer_value(value):
    if value is None:
        return ""

    s = str(value).strip()
    if s == "":
        return ""

    if re.fullmatch(r"\d+", s):
        return f"{int(s)}.0"

    if re.fullmatch(r"\d+\.\d+", s):
        try:
            return f"{float(s):.1f}"
        except ValueError:
            return s

    return s


def _natural_sort_key(value):
    s = normalize_layer_value(value) if value is not None else ""
    if s == "":
        return (float("inf"), "")

    if re.fullmatch(r"\d+(\.\d+)?", s):
        return (0, float(s), s)

    parts = re.split(r"(\d+(?:\.\d+)?)", s)
    result = []
    for part in parts:
        if part == "":
            continue
        if re.fullmatch(r"\d+(\.\d+)?", part):
            result.append((0, float(part)))
        else:
            result.append((1, part))
    return (1, result, s)


def _as_of_date(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    s = str(value).strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%Y%m%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _as_of_cutoff(as_of_date):
    as_of = _as_of_date(as_of_date)
    if as_of is None:
        return None
    return datetime.combine(as_of, datetime.max.time())


def _step_group_key(lineid, processid, stepseq):
    return ((lineid or "").strip(), (processid or "").strip(), (stepseq or "").strip())


def _uniq_join(values, upper=False):
    out = []
    for v in values:
        s = str(v or "").strip()
        if upper:
            s = s.upper()
        if s and s not in out:
            out.append(s)
    return " | ".join(out)
