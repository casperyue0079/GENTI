"""Scoring engine for multi-dimension mode.

Pipeline:  questions → dimension scores → normalise → archetype matching → rare tags
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from core.models import Dimension, MultiDimQuestion, RareTag, ResultArchetype


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def cosine_similarity(vec_a: dict[str, float], vec_b: dict[str, float]) -> float:
    """General-purpose cosine similarity between two sparse vectors."""
    all_keys = set(vec_a) | set(vec_b)
    dot = 0.0
    mag_a = 0.0
    mag_b = 0.0
    for k in all_keys:
        a = vec_a.get(k, 0.0)
        b = vec_b.get(k, 0.0)
        dot += a * b
        mag_a += a * a
        mag_b += b * b
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a ** 0.5 * mag_b ** 0.5)


# ---------------------------------------------------------------------------
# Step 1 – accumulate raw scores
# ---------------------------------------------------------------------------

def compute_dimension_scores(
    dimensions: list[Dimension],
    questions: list[MultiDimQuestion],
    answers: dict[str, int],
) -> dict[str, float]:
    """Accumulate effects and normalise each dimension to [-1, 1].

    ``answers`` maps question id → chosen option index (0-based).
    """
    raw: dict[str, float] = {d.id: 0.0 for d in dimensions}
    max_abs: dict[str, float] = {d.id: 0.0 for d in dimensions}

    for q in questions:
        opt_idx = answers.get(q.id)
        if opt_idx is None or opt_idx < 0 or opt_idx >= len(q.options):
            continue
        effects = q.options[opt_idx].effects
        for dim_id, val in effects.items():
            if dim_id in raw:
                raw[dim_id] += val
                max_abs[dim_id] += abs(val)

    normalised: dict[str, float] = {}
    for dim_id in raw:
        cap = max_abs[dim_id]
        if cap > 0:
            normalised[dim_id] = max(-1.0, min(1.0, raw[dim_id] / cap))
        else:
            normalised[dim_id] = 0.0

    return normalised


# ---------------------------------------------------------------------------
# Step 2 – match archetype
# ---------------------------------------------------------------------------

def match_archetype(
    dim_scores: dict[str, float],
    archetypes: list[ResultArchetype],
) -> tuple[ResultArchetype, float]:
    """Return the best-matching archetype and its cosine similarity."""
    best: ResultArchetype | None = None
    best_sim = -999.0
    for arch in archetypes:
        sim = cosine_similarity(dim_scores, arch.vector)
        if sim > best_sim:
            best_sim = sim
            best = arch
    assert best is not None, "No archetypes to match against"
    return best, best_sim


# ---------------------------------------------------------------------------
# Step 3 – rare tag triggering
# ---------------------------------------------------------------------------

def check_rare_tags(
    dim_scores: dict[str, float],
    questions: list[MultiDimQuestion],
    answers: dict[str, int],
    rare_tags: list[RareTag],
) -> list[RareTag]:
    """Evaluate rare-tag rules after the main result has been determined."""
    triggered: list[RareTag] = []

    cluster_hits: dict[str, int] = {}
    for q in questions:
        if q.is_special and q.special_cluster:
            opt_idx = answers.get(q.id)
            if opt_idx is not None and 0 <= opt_idx < len(q.options):
                effects = q.options[opt_idx].effects
                if any(abs(v) >= 1 for v in effects.values()):
                    cluster_hits[q.special_cluster] = cluster_hits.get(q.special_cluster, 0) + 1

    for rt in rare_tags:
        if _evaluate_rules(rt, dim_scores, cluster_hits):
            triggered.append(rt)

    return triggered


def _evaluate_rules(
    rt: RareTag,
    dim_scores: dict[str, float],
    cluster_hits: dict[str, int],
) -> bool:
    for gate, rules in rt.rules.items():
        results = [_eval_single_rule(r, dim_scores, cluster_hits) for r in rules]
        if gate == "all" and not all(results):
            return False
        if gate == "any" and not any(results):
            return False
    return True


def _eval_single_rule(
    rule: Any,
    dim_scores: dict[str, float],
    cluster_hits: dict[str, int],
) -> bool:
    if rule.type == "dimension_min":
        return dim_scores.get(rule.dimension or "", 0.0) >= rule.value
    if rule.type == "dimension_max":
        return dim_scores.get(rule.dimension or "", 0.0) <= rule.value
    if rule.type == "special_cluster_min_hits":
        return cluster_hits.get(rule.cluster or "", 0) >= int(rule.value)
    return False


# ---------------------------------------------------------------------------
# Convenience wrapper
# ---------------------------------------------------------------------------

def score_dim_test(
    dimensions: list[Dimension],
    questions: list[MultiDimQuestion],
    archetypes: list[ResultArchetype],
    rare_tags: list[RareTag],
    answers: dict[str, int],
) -> dict[str, Any]:
    """Run the full scoring pipeline and return a flat result dict."""
    dim_scores = compute_dimension_scores(dimensions, questions, answers)
    archetype, similarity = match_archetype(dim_scores, archetypes)
    triggered = check_rare_tags(dim_scores, questions, answers, rare_tags)

    return {
        "dimension_scores": dim_scores,
        "archetype_id": archetype.id,
        "archetype_name": archetype.name,
        "archetype_description": archetype.description,
        "archetype_image": archetype.image_path,
        "similarity": similarity,
        "rare_tag_names": [t.name for t in triggered],
        "rare_tag_ids": [t.id for t in triggered],
    }
