import re
from difflib import SequenceMatcher

from django.db.models import Max

from ..models import FactsEqpModel


def _normalize_model_text(value):
    s = str(value or "").strip().upper()
    s = re.sub(r"[\s\-_\/]", "", s)
    return s


def _common_prefix_len(a, b):
    n = min(len(a), len(b))
    cnt = 0
    for i in range(n):
        if a[i] == b[i]:
            cnt += 1
        else:
            break
    return cnt


def _model_similarity_score(base_model, candidate_model):
    base_raw = str(base_model or "").strip().upper()
    cand_raw = str(candidate_model or "").strip().upper()

    if not base_raw or not cand_raw:
        return 0.0
    if base_raw == cand_raw:
        return 1.0

    base_norm = _normalize_model_text(base_raw)
    cand_norm = _normalize_model_text(cand_raw)
    if not base_norm or not cand_norm:
        return 0.0

    if base_norm == cand_norm:
        return 0.98

    prefix_len = _common_prefix_len(base_norm, cand_norm)
    seq_score = SequenceMatcher(None, base_norm, cand_norm).ratio()

    if prefix_len >= 6 and seq_score >= 0.82:
        return max(seq_score, 0.90)
    if prefix_len >= 4 and seq_score >= 0.80:
        return max(seq_score, 0.84)
    if seq_score >= 0.92:
        return seq_score
    if seq_score >= 0.82:
        return seq_score

    return 0.0


def _get_eqp_model_qs_by_snap_or_latest_load(snap_date):
    snap_qs = FactsEqpModel.objects.filter(snap_date=snap_date)
    if snap_qs.exists():
        return snap_qs

    latest_loaded_at = (
        FactsEqpModel.objects.exclude(loaded_at__isnull=True)
        .aggregate(max_loaded_at=Max("loaded_at"))
        .get("max_loaded_at")
    )
    if latest_loaded_at is None:
        return FactsEqpModel.objects.none()

    latest_load = (
        FactsEqpModel.objects.filter(loaded_at=latest_loaded_at)
        .exclude(load_id__isnull=True)
        .exclude(load_id="")
        .order_by("-id")
        .values("load_id")
        .first()
    )

    if latest_load and latest_load.get("load_id"):
        return FactsEqpModel.objects.filter(load_id=latest_load["load_id"])

    return FactsEqpModel.objects.filter(loaded_at=latest_loaded_at)


def get_similar_model_eqp_candidates(snap_date, processid, stepseq, include_current=False):
    from .dataset import build_step_dataset
    from .path_utils import _parse_eqpgroup_tokens

    step_rows = build_step_dataset(
        snap_date=snap_date,
        processid=processid,
        include_measure=True,
        include_emergency=True,
        exclude_skiprule_100=False,
        tip_mode=False,
        for_prp_table=True,
    )

    target_row = next(
        (
            row
            for row in step_rows
            if row["processid"] == processid
            and row["stepseq"] == stepseq
        ),
        None,
    )
    if not target_row:
        return {"base_eqps": [], "base_models": [], "recommendations": []}

    base_eqps = _parse_eqpgroup_tokens(target_row.get("eqpgroup", ""))
    if not base_eqps:
        return {"base_eqps": [], "base_models": [], "recommendations": []}

    eqp_model_qs = _get_eqp_model_qs_by_snap_or_latest_load(snap_date)

    base_model_rows = list(
        eqp_model_qs.filter(
            eqp_id__in=base_eqps,
        ).values("eqp_id", "origin_line_id", "eqp_model")
    )

    base_models = []
    for row in base_model_rows:
        eqp_model = str(row["eqp_model"] or "").strip()
        if eqp_model and eqp_model not in base_models:
            base_models.append(eqp_model)

    if not base_models:
        return {"base_eqps": base_eqps, "base_models": [], "recommendations": []}

    all_candidates = list(
        eqp_model_qs
        .exclude(eqp_model__isnull=True)
        .exclude(eqp_model="")
        .values("eqp_id", "origin_line_id", "eqp_model")
    )

    rec_map = {}
    for cand in all_candidates:
        eqp_id = str(cand["eqp_id"] or "").upper()
        if not eqp_id:
            continue
        if (not include_current) and eqp_id in base_eqps:
            continue

        cand_model = str(cand["eqp_model"] or "").strip()
        if not cand_model:
            continue

        best_score = 0.0
        best_base_model = ""
        for bm in base_models:
            score = _model_similarity_score(bm, cand_model)
            if score > best_score:
                best_score = score
                best_base_model = bm

        if best_score <= 0:
            continue

        base_norm = _normalize_model_text(best_base_model)
        cand_norm = _normalize_model_text(cand_model)

        if best_score >= 0.999:
            match_type = "완전일치"
        elif base_norm == cand_norm:
            match_type = "정규화일치"
        elif best_score >= 0.90:
            match_type = "강유사"
        elif best_score >= 0.82:
            match_type = "유사"
        else:
            continue

        item = {
            "eqp_id": eqp_id,
            "origin_line_id": str(cand["origin_line_id"] or ""),
            "eqp_model": cand_model,
            "match_type": match_type,
            "match_score": round(best_score, 4),
            "matched_base_model": best_base_model,
        }

        prev = rec_map.get(eqp_id)
        if prev is None or item["match_score"] > prev["match_score"]:
            rec_map[eqp_id] = item

    recommendations = list(rec_map.values())
    recommendations.sort(
        key=lambda x: (
            {"완전일치": 0, "정규화일치": 1, "강유사": 2, "유사": 3}.get(x["match_type"], 9),
            -x["match_score"],
            x["eqp_id"],
        )
    )

    return {
        "base_eqps": base_eqps,
        "base_models": base_models,
        "recommendations": recommendations,
    }
