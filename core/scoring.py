from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.models import Axis, NormalResult, Question, RareResult


@dataclass
class ScoringResult:
    dimension_scores: dict[str, float] = field(default_factory=dict)
    normal_result_id: str = ""
    normal_result_name: str = ""
    rare_tags: list[str] = field(default_factory=list)
    override_result_id: str | None = None
    override_result_name: str | None = None


def compute_dimension_scores(
    axes: list[Axis],
    questions: list[Question],
    answers: dict[str, int],
) -> dict[str, float]:
    """Accumulate raw scores per axis, then normalize to [-1, 1]."""
    raw: dict[str, float] = {a.id: 0.0 for a in axes}
    max_possible: dict[str, float] = {a.id: 0.0 for a in axes}

    for q in questions:
        ans = answers.get(q.id)
        if ans is None:
            continue

        raw[q.primary_axis_id] += ans
        max_possible[q.primary_axis_id] += 2.0

        for w in q.weak_axes:
            if w.axis_id in raw:
                raw[w.axis_id] += ans * w.coefficient
                max_possible[w.axis_id] += 2.0 * w.coefficient

    normalized: dict[str, float] = {}
    for axis_id in raw:
        cap = max_possible[axis_id]
        if cap > 0:
            normalized[axis_id] = max(-1.0, min(1.0, raw[axis_id] / cap))
        else:
            normalized[axis_id] = 0.0

    return normalized


def _cosine_similarity(
    user_vec: dict[str, float], result_combo: dict[str, int]
) -> float:
    dot = 0.0
    mag_a = 0.0
    mag_b = 0.0
    for axis_id, direction in result_combo.items():
        u = user_vec.get(axis_id, 0.0)
        dot += u * direction
        mag_a += u * u
        mag_b += direction * direction
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a**0.5 * mag_b**0.5)


def map_normal_result(
    dimension_scores: dict[str, float],
    normal_results: list[NormalResult],
) -> NormalResult:
    best: NormalResult | None = None
    best_score = -999.0
    for r in normal_results:
        sim = _cosine_similarity(dimension_scores, r.dimension_combo)
        if sim > best_score:
            best_score = sim
            best = r
    assert best is not None
    return best


def check_rare_results(
    dimension_scores: dict[str, float],
    questions: list[Question],
    answers: dict[str, int],
    rare_results: list[RareResult],
) -> list[RareResult]:
    triggered: list[RareResult] = []
    for rr in rare_results:
        dims_met = all(
            dimension_scores.get(c.axis_id, 0.0) * c.direction >= c.threshold
            for c in rr.threshold_conditions
        )
        if not dims_met:
            continue

        special_hits = 0
        for q in questions:
            if q.is_special and q.linked_rare_id == rr.id:
                ans = answers.get(q.id, 0)
                if abs(ans) >= 1:
                    special_hits += 1
        if special_hits >= rr.min_special_hits:
            triggered.append(rr)

    return triggered


def score_test(
    axes: list[Axis],
    questions: list[Question],
    normal_results: list[NormalResult],
    rare_results: list[RareResult],
    answers: dict[str, int],
) -> ScoringResult:
    dim_scores = compute_dimension_scores(axes, questions, answers)
    normal = map_normal_result(dim_scores, normal_results)

    result = ScoringResult(
        dimension_scores=dim_scores,
        normal_result_id=normal.id,
        normal_result_name=normal.name,
    )

    triggered = check_rare_results(dim_scores, questions, answers, rare_results)
    for rr in triggered:
        if rr.type.value == "覆盖":
            result.override_result_id = rr.id
            result.override_result_name = rr.name
        else:
            result.rare_tags.append(rr.name)

    return result
