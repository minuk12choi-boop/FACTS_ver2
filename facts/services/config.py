from django.db.models import Max, Q

from .common import _natural_sort_key, normalize_layer_value
from ..models import FactsDashboardConfig, FactsKpiTarget, FactsWipSource


def get_dashboard_config():
    obj = FactsDashboardConfig.objects.order_by("id").first()
    if obj:
        return obj
    return {
        "default_prp": "P1SD",
        "inquiry_contact": "minuk12.choi",
    }


def get_latest_snap_date():
    return FactsWipSource.objects.aggregate(max_date=Max("snap_date"))["max_date"]


def get_filter_options(snap_date=None):
    qs = FactsWipSource.objects.all()
    if snap_date:
        qs = qs.filter(snap_date=snap_date)

    areas = list(
        qs.exclude(areaname__isnull=True)
        .exclude(areaname="")
        .values_list("areaname", flat=True)
        .distinct()
    )
    areas = sorted(areas, key=lambda x: str(x))

    raw_layers = list(
        qs.exclude(layerid__isnull=True)
        .exclude(layerid="")
        .values_list("layerid", flat=True)
        .distinct()
    )
    norm_layers = sorted(
        {normalize_layer_value(x) for x in raw_layers if normalize_layer_value(x)},
        key=_natural_sort_key,
    )

    processes = list(
        qs.exclude(processid__isnull=True)
        .exclude(processid="")
        .values_list("processid", flat=True)
        .distinct()
        .order_by("processid")
    )

    lineids = list(
        qs.exclude(lineid__isnull=True)
        .exclude(lineid="")
        .values_list("lineid", flat=True)
        .distinct()
        .order_by("lineid")
    )

    return {
        "areas": areas,
        "layers": norm_layers,
        "processes": processes,
        "lineids": list(lineids),
    }


def get_distinct_master_options(snap_date=None):
    qs = FactsWipSource.objects.all()
    if snap_date:
        qs = qs.filter(snap_date=snap_date)
    return {
        "line_options": list(qs.exclude(lineid__isnull=True).exclude(lineid="").values_list("lineid", flat=True).distinct().order_by("lineid")),
        "prp_options": list(qs.exclude(processid="").values_list("processid", flat=True).distinct().order_by("processid")),
        "area_options": list(qs.exclude(areaname="").values_list("areaname", flat=True).distinct().order_by("areaname")),
    }


def _filter_kpi_area(qs, areaname=""):
    area_filter = (areaname or "").strip()
    if area_filter:
        return qs.filter(areaname=area_filter)
    return qs.filter(Q(areaname="") | Q(areaname__isnull=True))


def get_kpi_target_value(processid, target_type, snap_date, areaname="", lineid=""):
    if not processid:
        return None

    if target_type == "monthly":
        qs = FactsKpiTarget.objects.filter(
            is_active=True,
            target_type="monthly",
            target_year=snap_date.year,
            target_month=snap_date.month,
            processid=processid,
        )
        if lineid:
            qs = qs.filter(lineid=lineid)
        qs = _filter_kpi_area(qs, areaname)
        obj = qs.order_by("-updated_at").first()
        return float(obj.target_rate) if obj else None

    iso_year, iso_week, _ = snap_date.isocalendar()
    qs = FactsKpiTarget.objects.filter(
        is_active=True,
        target_type="weekly",
        target_year=iso_year,
        target_week=iso_week,
        processid=processid,
    )
    if lineid:
        qs = qs.filter(lineid=lineid)
    qs = _filter_kpi_area(qs, areaname)
    obj = qs.order_by("-updated_at").first()
    return float(obj.target_rate) if obj else None
