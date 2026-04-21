from ..models import FactsWipSource
from .common import normalize_layer_value


def _base_source_queryset(
    snap_date,
    processid=None,
    areaname=None,
    layerid=None,
    lineid=None,
    include_measure=True,
    exclude_skiprule_100=False,
):
    qs = FactsWipSource.objects.filter(snap_date=snap_date)

    if processid:
        qs = qs.filter(processid=processid)
    if areaname:
        qs = qs.filter(areaname=areaname)
    if lineid:
        qs = qs.filter(lineid=lineid)
    if not include_measure:
        qs = qs.exclude(stepseq_type="계측")
    if exclude_skiprule_100:
        qs = qs.exclude(skiprule="100")

    qs = qs.order_by("lineid", "processid", "stepseq", "recipeid", "path", "id")
    rows = list(qs)

    if layerid:
        layer_norm = normalize_layer_value(layerid)
        rows = [r for r in rows if normalize_layer_value(r.layerid) == layer_norm]

    return rows


def _build_step_key(row):
    return (row.lineid or "", row.processid or "", row.stepseq or "")


def _build_path_key(lineid, processid, stepseq, recipeid, path, eqpline, childeqp):
    return (
        lineid or "",
        processid or "",
        stepseq or "",
        recipeid or "",
        path or "",
        eqpline or "",
        childeqp or "",
    )
