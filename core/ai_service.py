from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from openai import OpenAI

from core.models import (
    Axis,
    Dimension,
    MultiDimOption,
    MultiDimQuestion,
    NormalResult,
    Question,
    QuestionOption,
    RareResult,
    RareResultType,
    RareTag,
    RareTagRule,
    ResultArchetype,
    ThresholdCondition,
    WeakAxisEffect,
)
from core.prompts import (
    build_archetypes_prompt,
    build_axes_prompt,
    build_dim_questions_prompt,
    build_dimensions_prompt,
    build_normal_results_prompt,
    build_questions_prompt,
    build_rare_results_from_seeds_prompt,
    build_rare_results_prompt,
    build_rare_tags_from_seeds_prompt,
    build_rare_tags_prompt,
)

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"


def load_config() -> dict[str, Any]:
    with open(_CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _get_client() -> tuple[OpenAI, str]:
    cfg = load_config()["ai"]
    client = OpenAI(base_url=cfg["base_url"], api_key=cfg["api_key"])
    return client, cfg["model"]


def _parse_rare_result_type(raw: Any) -> RareResultType:
    if isinstance(raw, RareResultType):
        return raw
    if raw == RareResultType.OVERRIDE.value or raw == "覆盖":
        return RareResultType.OVERRIDE
    return RareResultType.APPEND


def _collect_rare_tag_clusters(tags: list[RareTag]) -> frozenset[str]:
    out: set[str] = set()
    for rt in tags:
        for rules in rt.rules.values():
            for r in rules:
                if r.type == "special_cluster_min_hits" and r.cluster:
                    out.add(r.cluster)
    return frozenset(out)


def _chat_json(messages: list[dict], retries: int = 2) -> dict | list:
    client, model = _get_client()
    for attempt in range(retries + 1):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.8,
                response_format={"type": "json_object"},
            )
            text = resp.choices[0].message.content
            return json.loads(text)
        except (json.JSONDecodeError, Exception):
            if attempt == retries:
                raise


_SYSTEM_MSG = "你是一个专业的心理测试设计师。请严格按要求返回 JSON。"


def generate_axes(theme: str, count: int, style: str) -> list[Axis]:
    prompt = build_axes_prompt(theme, count, style)
    messages = [
        {"role": "system", "content": "你是一个专业的心理测试设计师。请严格按要求返回 JSON。"},
        {"role": "user", "content": prompt},
    ]
    data = _chat_json(messages)
    axes = []
    for item in data["axes"]:
        axes.append(
            Axis(
                id=item["id"],
                left_name=item["left_name"],
                right_name=item["right_name"],
                description=item["description"],
            )
        )
    return axes


def generate_normal_results(
    axes: list[Axis], count: int, theme: str, style: str = "",
) -> list[NormalResult]:
    prompt = build_normal_results_prompt(axes, count, theme)
    if style:
        prompt = f"{prompt}\n\n{style}"
    messages = [
        {"role": "system", "content": "你是一个专业的心理测试设计师。请严格按要求返回 JSON。"},
        {"role": "user", "content": prompt},
    ]
    data = _chat_json(messages)
    results = []
    for item in data["results"]:
        results.append(
            NormalResult(
                id=item["id"],
                name=item["name"],
                description=item["description"],
                reference_name=item.get("reference_name"),
                reference_source=item.get("reference_source"),
                dimension_combo={
                    k: int(v) for k, v in item["dimension_combo"].items()
                },
            )
        )
    return results


def generate_rare_results(
    axes: list[Axis],
    normal_results: list[NormalResult],
    count: int,
    theme: str,
) -> list[RareResult]:
    prompt = build_rare_results_prompt(axes, normal_results, count, theme)
    messages = [
        {"role": "system", "content": "你是一个专业的心理测试设计师。请严格按要求返回 JSON。"},
        {"role": "user", "content": prompt},
    ]
    data = _chat_json(messages)
    results = []
    for item in data["rare_results"]:
        conditions = [
            ThresholdCondition(
                axis_id=c["axis_id"],
                direction=int(c["direction"]),
                threshold=float(c.get("threshold", 0.6)),
            )
            for c in item.get("threshold_conditions", [])
        ]
        results.append(
            RareResult(
                id=item["id"],
                name=item["name"],
                description=item["description"],
                reference_name=item.get("reference_name"),
                reference_source=item.get("reference_source"),
                type=_parse_rare_result_type(item.get("type")),
                threshold_conditions=conditions,
                special_question_ids=[],
                min_special_hits=item.get("min_special_hits", 2),
                origin="system",
                user_seed_character=None,
                user_seed_traits=None,
            )
        )
    return results


def generate_rare_results_from_seeds(
    axes: list[Axis],
    normal_results: list[NormalResult],
    theme: str,
    seeds: list[dict[str, str]],
    style_key: str | None = None,
) -> list[RareResult]:
    if not seeds:
        return []
    expected_ids = [f"rare_{i + 1}" for i in range(len(seeds))]
    prompt = build_rare_results_from_seeds_prompt(
        axes, normal_results, theme, seeds, expected_ids, style_key,
    )
    messages = [
        {"role": "system", "content": _SYSTEM_MSG},
        {"role": "user", "content": prompt},
    ]
    data = _chat_json(messages)
    items = data.get("rare_results") or []
    if len(items) != len(seeds):
        raise ValueError(
            f"模型返回 {len(items)} 条稀有结果，与种子数 {len(seeds)} 不一致，请重试",
        )
    results: list[RareResult] = []
    for i, item in enumerate(items):
        conditions = [
            ThresholdCondition(
                axis_id=c["axis_id"],
                direction=int(c["direction"]),
                threshold=float(c.get("threshold", 0.6)),
            )
            for c in item.get("threshold_conditions", [])
        ]
        ch = (seeds[i].get("character") or "").strip()
        tr = (seeds[i].get("traits") or "").strip()
        results.append(
            RareResult(
                id=expected_ids[i],
                name=item["name"],
                description=item["description"],
                reference_name=item.get("reference_name"),
                reference_source=item.get("reference_source"),
                type=_parse_rare_result_type(item.get("type")),
                threshold_conditions=conditions,
                special_question_ids=[],
                min_special_hits=item.get("min_special_hits", 2),
                origin="user_seeded",
                user_seed_character=ch or None,
                user_seed_traits=tr or None,
            )
        )
    return results


def generate_questions(
    axes: list[Axis],
    normal_results: list[NormalResult],
    rare_results: list[RareResult],
    style: str,
    questions_per_axis: int = 4,
    max_special: int = 4,
) -> list[Question]:
    prompt = build_questions_prompt(
        axes, normal_results, rare_results, style, questions_per_axis, max_special
    )
    messages = [
        {"role": "system", "content": "你是一个专业的心理测试设计师。请严格按要求返回 JSON。"},
        {"role": "user", "content": prompt},
    ]
    data = _chat_json(messages)
    questions = []
    for item in data["questions"]:
        options = []
        for opt in item["options"]:
            options.append(QuestionOption(text=opt["text"], value=int(opt["value"])))
        weak = [
            WeakAxisEffect(
                axis_id=w["axis_id"],
                coefficient=float(w.get("coefficient", 0.5)),
            )
            for w in item.get("weak_axes", [])
        ]
        questions.append(
            Question(
                id=item["id"],
                text=item["text"],
                options=options,
                primary_axis_id=item["primary_axis_id"],
                weak_axes=weak,
                is_special=bool(item.get("is_special", False)),
                linked_rare_id=item.get("linked_rare_id"),
            )
        )
    return questions


# ---------------------------------------------------------------------------
# Multi-dimension generators
# ---------------------------------------------------------------------------


def generate_dimensions(theme: str, count: int, style: str) -> list[Dimension]:
    prompt = build_dimensions_prompt(theme, count, style)
    data = _chat_json([
        {"role": "system", "content": _SYSTEM_MSG},
        {"role": "user", "content": prompt},
    ])
    return [
        Dimension(
            id=item["id"],
            display_name=item["display_name"],
            low_label=item["low_label"],
            high_label=item["high_label"],
            description=item["description"],
        )
        for item in data["dimensions"]
    ]


def generate_archetypes(
    dimensions: list[Dimension], count: int, theme: str, style: str = "",
) -> list[ResultArchetype]:
    prompt = build_archetypes_prompt(dimensions, count, theme)
    if style:
        prompt = f"{prompt}\n\n{style}"
    data = _chat_json([
        {"role": "system", "content": _SYSTEM_MSG},
        {"role": "user", "content": prompt},
    ])
    return [
        ResultArchetype(
            id=item["id"],
            name=item["name"],
            description=item["description"],
            reference_name=item.get("reference_name"),
            reference_source=item.get("reference_source"),
            vector={k: float(v) for k, v in item["vector"].items()},
        )
        for item in data["archetypes"]
    ]


def generate_rare_tags(
    dimensions: list[Dimension],
    archetypes: list[ResultArchetype],
    count: int,
    theme: str,
) -> list[RareTag]:
    prompt = build_rare_tags_prompt(dimensions, archetypes, count, theme)
    data = _chat_json([
        {"role": "system", "content": _SYSTEM_MSG},
        {"role": "user", "content": prompt},
    ])
    tags: list[RareTag] = []
    for item in data["rare_tags"]:
        rules_dict: dict[str, list[RareTagRule]] = {}
        for gate, rule_list in item.get("rules", {}).items():
            rules_dict[gate] = [
                RareTagRule(
                    type=r["type"],
                    dimension=r.get("dimension"),
                    cluster=r.get("cluster"),
                    value=float(r.get("value", 0)),
                )
                for r in rule_list
            ]
        tags.append(RareTag(
            id=item["id"],
            name=item["name"],
            description=item["description"],
            reference_name=item.get("reference_name"),
            reference_source=item.get("reference_source"),
            rules=rules_dict,
            origin="system",
            user_seed_character=None,
            user_seed_traits=None,
        ))
    return tags


def generate_rare_tags_from_seeds(
    dimensions: list[Dimension],
    archetypes: list[ResultArchetype],
    theme: str,
    seeds: list[dict[str, str]],
    style_key: str | None = None,
    other_tags_for_cluster: list[RareTag] | None = None,
) -> list[RareTag]:
    if not seeds:
        return []
    occupied = (
        _collect_rare_tag_clusters(other_tags_for_cluster)
        if other_tags_for_cluster
        else frozenset()
    )
    expected_ids = [f"rtag_{i + 1}" for i in range(len(seeds))]
    prompt = build_rare_tags_from_seeds_prompt(
        dimensions, archetypes, theme, seeds, expected_ids, occupied, style_key,
    )
    data = _chat_json([
        {"role": "system", "content": _SYSTEM_MSG},
        {"role": "user", "content": prompt},
    ])
    items = data.get("rare_tags") or []
    if len(items) != len(seeds):
        raise ValueError(
            f"模型返回 {len(items)} 条稀有标签，与种子数 {len(seeds)} 不一致，请重试",
        )
    tags: list[RareTag] = []
    for i, item in enumerate(items):
        rules_dict: dict[str, list[RareTagRule]] = {}
        for gate, rule_list in item.get("rules", {}).items():
            rules_dict[gate] = [
                RareTagRule(
                    type=r["type"],
                    dimension=r.get("dimension"),
                    cluster=r.get("cluster"),
                    value=float(r.get("value", 0)),
                )
                for r in rule_list
            ]
        ch = (seeds[i].get("character") or "").strip()
        tr = (seeds[i].get("traits") or "").strip()
        tags.append(
            RareTag(
                id=expected_ids[i],
                name=item["name"],
                description=item["description"],
                reference_name=item.get("reference_name"),
                reference_source=item.get("reference_source"),
                rules=rules_dict,
                origin="user_seeded",
                user_seed_character=ch or None,
                user_seed_traits=tr or None,
            )
        )
    return tags


def generate_dim_questions(
    dimensions: list[Dimension],
    archetypes: list[ResultArchetype],
    rare_tags: list[RareTag],
    style: str,
    questions_per_dim: int = 4,
    max_special: int = 4,
) -> list[MultiDimQuestion]:
    prompt = build_dim_questions_prompt(
        dimensions, archetypes, rare_tags, style, questions_per_dim, max_special,
    )
    data = _chat_json([
        {"role": "system", "content": _SYSTEM_MSG},
        {"role": "user", "content": prompt},
    ])
    questions: list[MultiDimQuestion] = []
    for item in data["questions"]:
        options = [
            MultiDimOption(
                text=opt["text"],
                effects={k: int(v) for k, v in opt["effects"].items()},
            )
            for opt in item["options"]
        ]
        questions.append(MultiDimQuestion(
            id=item["id"],
            stem=item["stem"],
            primary_dimension=item["primary_dimension"],
            secondary_dimensions=item.get("secondary_dimensions", []),
            options=options,
            is_special=bool(item.get("is_special", False)),
            special_cluster=item.get("special_cluster"),
        ))
    return questions
