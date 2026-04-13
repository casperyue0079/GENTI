"""Question and project validation for both multi-axis and multi-dimension modes."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.models import (
        MultiDimQuestion,
        NormalResult,
        Question,
        RareTag,
        ResultArchetype,
        TestConfig,
    )


@dataclass
class ValidationIssue:
    level: str  # "error" | "warning"
    message: str


@dataclass
class ValidationReport:
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not any(i.level == "error" for i in self.issues)

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.level == "error"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.level == "warning"]


# ---------------------------------------------------------------------------
# Multi-axis validation (original, enhanced)
# ---------------------------------------------------------------------------

def validate_questions(
    questions: list[Question],
    config: TestConfig,
    axis_ids: list[str],
    normal_results: list[NormalResult] | None = None,
) -> ValidationReport:
    report = ValidationReport()

    normal_qs = [q for q in questions if not q.is_special]
    special_qs = [q for q in questions if q.is_special]

    # total question limit
    if len(questions) > config.max_total_questions:
        report.issues.append(
            ValidationIssue("error", f"总题数 {len(questions)} 超过上限 {config.max_total_questions}")
        )

    # axis coverage
    axis_counts: dict[str, int] = {aid: 0 for aid in axis_ids}
    for q in normal_qs:
        if q.primary_axis_id in axis_counts:
            axis_counts[q.primary_axis_id] += 1
        else:
            report.issues.append(
                ValidationIssue("error", f"题目 {q.id} 绑定了不存在的轴 {q.primary_axis_id}")
            )

    for aid, cnt in axis_counts.items():
        if cnt < config.questions_per_axis:
            report.issues.append(
                ValidationIssue("error", f"轴 {aid} 只有 {cnt} 道题，要求至少 {config.questions_per_axis} 道")
            )

    # balance
    counts = list(axis_counts.values())
    if counts and max(counts) - min(counts) > 1:
        report.issues.append(
            ValidationIssue("warning", f"各轴题量不均衡：最多 {max(counts)}，最少 {min(counts)}")
        )

    # special question limit
    if len(special_qs) > config.max_special_questions:
        report.issues.append(
            ValidationIssue("error", f"特殊题 {len(special_qs)} 道，超过上限 {config.max_special_questions}")
        )

    # option structure
    for q in questions:
        if len(q.options) != 5:
            report.issues.append(
                ValidationIssue("error", f"题目 {q.id} 选项数量为 {len(q.options)}，应为 5")
            )
        expected_values = {-2, -1, 0, 1, 2}
        actual_values = {opt.value for opt in q.options}
        if actual_values != expected_values:
            report.issues.append(
                ValidationIssue("error", f"题目 {q.id} 选项分值不正确，应为 -2,-1,0,1,2")
            )

    # result similarity check
    if normal_results and len(normal_results) >= 2:
        _check_result_similarity(report, normal_results)

    return report


def _check_result_similarity(
    report: ValidationReport, results: list[NormalResult],
) -> None:
    from core.scoring import _cosine_similarity

    for i in range(len(results)):
        for j in range(i + 1, len(results)):
            sim = _cosine_similarity(
                {k: float(v) for k, v in results[i].dimension_combo.items()},
                results[j].dimension_combo,
            )
            if sim > 0.9:
                report.issues.append(
                    ValidationIssue(
                        "warning",
                        f"结果 {results[i].id} 与 {results[j].id} 相似度过高 ({sim:.2f})",
                    )
                )


def validate_rare_result_axis_rules(
    rare_results: list,
    axis_ids: set[str],
) -> ValidationReport:
    """Ensure every threshold_condition.axis_id exists in the project."""
    report = ValidationReport()
    valid = set(axis_ids)
    for rr in rare_results:
        for c in rr.threshold_conditions:
            if c.axis_id not in valid:
                report.issues.append(
                    ValidationIssue(
                        "error",
                        f"稀有结果 {rr.id} 的触发条件引用了不存在的轴：{c.axis_id}",
                    )
                )
    return report


# ---------------------------------------------------------------------------
# Multi-dimension validation (new)
# ---------------------------------------------------------------------------

def validate_dim_questions(
    questions: list[MultiDimQuestion],
    config: TestConfig,
    dim_ids: list[str],
    archetypes: list[ResultArchetype] | None = None,
    rare_tags: list[RareTag] | None = None,
) -> ValidationReport:
    report = ValidationReport()

    normal_qs = [q for q in questions if not q.is_special]
    special_qs = [q for q in questions if q.is_special]

    # total limit
    if len(questions) > config.max_total_questions:
        report.issues.append(
            ValidationIssue("error", f"总题数 {len(questions)} 超过上限 {config.max_total_questions}")
        )

    # primary dimension binding check
    dim_counts: dict[str, int] = {did: 0 for did in dim_ids}
    for q in normal_qs:
        if q.primary_dimension in dim_counts:
            dim_counts[q.primary_dimension] += 1
        else:
            report.issues.append(
                ValidationIssue("error", f"题目 {q.id} 绑定了不存在的维度 {q.primary_dimension}")
            )

    # per-dimension coverage (at least 4)
    min_per_dim = max(4, config.questions_per_dimension)
    for did, cnt in dim_counts.items():
        if cnt < min_per_dim:
            report.issues.append(
                ValidationIssue("error", f"维度 {did} 只有 {cnt} 道题，建议至少 {min_per_dim} 道")
            )

    # balance
    counts = list(dim_counts.values())
    if counts and max(counts) - min(counts) > 2:
        report.issues.append(
            ValidationIssue("warning", f"各维度题量不均衡：最多 {max(counts)}，最少 {min(counts)}")
        )

    # special question limit
    if len(special_qs) > config.max_special_questions:
        report.issues.append(
            ValidationIssue("error", f"特殊题 {len(special_qs)} 道，超过上限 {config.max_special_questions}")
        )

    # option count (must be 3)
    for q in questions:
        if len(q.options) != 3:
            report.issues.append(
                ValidationIssue("error", f"题目 {q.id} 选项数量为 {len(q.options)}，应为 3")
            )

    # archetype similarity check
    if archetypes and len(archetypes) >= 2:
        _check_archetype_similarity(report, archetypes)

    # rare tag triggerability
    if rare_tags:
        _check_rare_tag_triggerability(report, rare_tags)

    return report


def _check_archetype_similarity(
    report: ValidationReport, archetypes: list[ResultArchetype],
) -> None:
    from core.dim_scoring import cosine_similarity

    for i in range(len(archetypes)):
        for j in range(i + 1, len(archetypes)):
            sim = cosine_similarity(archetypes[i].vector, archetypes[j].vector)
            if sim > 0.9:
                report.issues.append(
                    ValidationIssue(
                        "warning",
                        f"原型 {archetypes[i].id} 与 {archetypes[j].id} 相似度过高 ({sim:.2f})",
                    )
                )


def validate_rare_tag_dimension_rules(
    rare_tags: list,
    dimension_ids: set[str],
) -> ValidationReport:
    """Ensure dimension_min/max rules reference existing dimension ids."""
    report = ValidationReport()
    valid = set(dimension_ids)
    for rt in rare_tags:
        for gate, rules in rt.rules.items():
            for r in rules:
                if r.type in ("dimension_min", "dimension_max"):
                    dim = r.dimension or ""
                    if dim and dim not in valid:
                        report.issues.append(
                            ValidationIssue(
                                "error",
                                f"稀有标签 {rt.id} 的规则引用了不存在的维度：{dim}",
                            )
                        )
    return report


def _check_rare_tag_triggerability(
    report: ValidationReport, rare_tags: list[RareTag],
) -> None:
    for rt in rare_tags:
        for gate, rules in rt.rules.items():
            if gate != "all":
                continue
            dim_min_rules = [r for r in rules if r.type == "dimension_min"]
            dim_max_rules = [r for r in rules if r.type == "dimension_max"]

            # check for contradictions (same dim requires both >= X and <= Y where Y < X)
            for mn in dim_min_rules:
                for mx in dim_max_rules:
                    if mn.dimension == mx.dimension and mn.value > mx.value:
                        report.issues.append(
                            ValidationIssue(
                                "error",
                                f"稀有标签 {rt.id} 永远不可触发：维度 {mn.dimension} 要求同时 ≥{mn.value} 且 ≤{mx.value}",
                            )
                        )

            # check for overly loose thresholds
            all_thresholds = [abs(r.value) for r in rules if r.type in ("dimension_min", "dimension_max")]
            if all_thresholds and max(all_thresholds) < 0.3:
                report.issues.append(
                    ValidationIssue(
                        "warning",
                        f"稀有标签 {rt.id} 的触发阈值过于宽松（最大绝对值 {max(all_thresholds):.1f}）",
                    )
                )
