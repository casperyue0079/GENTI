from __future__ import annotations

import json
from typing import TYPE_CHECKING

from core.style_prompts import get_style_prompt

if TYPE_CHECKING:
    from core.models import Axis, Dimension, NormalResult, RareResult, ResultArchetype, RareTag


def build_axes_prompt(theme: str, count: int, style: str) -> str:
    return f"""请为一个主题为「{theme}」的人格测试生成 {count} 个测试维度轴。

风格要求：{style}

每个轴包含两个极端方向，代表一种人格差异维度。

请严格返回如下 JSON 格式：
{{
  "axes": [
    {{
      "id": "axis_1",
      "left_name": "左端名称",
      "right_name": "右端名称",
      "description": "该轴描述什么样的人格差异"
    }}
  ]
}}

要求：
- id 格式为 axis_1, axis_2, ... axis_{count}
- 每个轴的两端名称要鲜明对立、有趣且与主题高度相关
- description 简明扼要（一句话）
- 生成恰好 {count} 个轴
- 返回纯 JSON，不要附带任何其他文字"""


def build_normal_results_prompt(
    axes: list[Axis], count: int, theme: str
) -> str:
    axes_desc = "\n".join(
        f"- {a.id}: {a.left_name}(-1) ←→ {a.right_name}(+1) — {a.description}"
        for a in axes
    )

    return f"""基于以下测试维度轴，为主题「{theme}」的人格测试生成 {count} 个普通结果类型。

维度轴：
{axes_desc}

每个普通结果需要绑定到一组维度方向的组合（选择其中 3-4 个最关键的轴，指定方向为 +1 或 -1）。

每个结果同时提供：
1. 一个抽象名称（name）
2. 一个角色/名人对标（reference_name + reference_source）：与主题「{theme}」相关的真实名人或知名作品角色

请严格返回如下 JSON 格式：
{{
  "results": [
    {{
      "id": "result_1",
      "name": "结果名称（有趣、有画面感）",
      "reference_name": "该领域的名人或角色名",
      "reference_source": "出处（如：某乐队主唱 / 某电影角色）",
      "description": "一段描述这种人格类型的文案（2-3句话）",
      "dimension_combo": {{
        "axis_1": 1,
        "axis_3": -1,
        "axis_5": 1
      }}
    }}
  ]
}}

要求：
- id 格式为 result_1, result_2, ... result_{count}
- 每个结果绑定 3-4 个轴的方向
- 结果之间的维度组合要有足够区分度，不要过于相似
- name 要有个性和画面感
- reference_name 必须是与主题「{theme}」相关的真实名人或知名角色，要有辨识度
- reference_source 简短说明出处或身份
- 生成恰好 {count} 个结果
- 返回纯 JSON，不要附带任何其他文字"""


def build_rare_results_prompt(
    axes: list[Axis],
    normal_results: list[NormalResult],
    count: int,
    theme: str,
) -> str:
    axes_desc = "\n".join(
        f"- {a.id}: {a.left_name}(-1) ←→ {a.right_name}(+1)"
        for a in axes
    )
    results_desc = "\n".join(
        f"- {r.id}: {r.name}" for r in normal_results
    )

    return f"""基于以下测试维度轴和普通结果，为主题「{theme}」的人格测试生成 {count} 个稀有结果。

维度轴：
{axes_desc}

普通结果：
{results_desc}

稀有结果是隐藏的特殊类型，只有在满足特定维度极端组合时才会触发。它应该带有稀缺感和惊喜感。

每个稀有结果需要：
1. 一个有冲击力的抽象名称
2. 一个角色/名人对标（reference_name + reference_source）
3. 一段描述
4. 触发条件：2-3 个维度的阈值条件

请严格返回如下 JSON 格式：
{{
  "rare_results": [
    {{
      "id": "rare_1",
      "name": "稀有结果名称",
      "reference_name": "该领域的名人或角色名",
      "reference_source": "出处",
      "description": "描述文案",
      "threshold_conditions": [
        {{
          "axis_id": "axis_1",
          "direction": 1,
          "threshold": 0.7
        }}
      ],
      "min_special_hits": 2
    }}
  ]
}}

要求：
- id 格式为 rare_1, rare_2, ... rare_{count}
- reference_name 必须是与主题「{theme}」相关的真实名人或角色，且应是极端/独特的代表
- reference_source 简短说明出处或身份
- threshold 范围 0.5-0.9，表示该维度得分（归一化后绝对值）需要达到的最低值
- direction 为 +1 或 -1，表示需要偏向哪一端
- min_special_hits 表示需要命中几道特殊题才能触发（建议 1-3）
- 名称要有神秘感、稀缺感
- 生成恰好 {count} 个稀有结果
- 返回纯 JSON，不要附带任何其他文字"""


def build_rare_results_from_seeds_prompt(
    axes: list[Axis],
    normal_results: list[NormalResult],
    theme: str,
    seeds: list[dict[str, str]],
    expected_ids: list[str],
    style_key: str | None = None,
) -> str:
    """Each seed dict has keys 'character' and 'traits'. Output length must match."""
    axes_desc = "\n".join(
        f"- {a.id}: {a.left_name}(-1) ←→ {a.right_name}(+1) — {a.description}"
        for a in axes
    )
    results_desc = "\n".join(
        f"- {r.id}: {r.name}" for r in normal_results
    )
    seed_lines = "\n".join(
        f"{i + 1}. 用户指定的角色/人物：{s.get('character', '').strip()}\n"
        f"   气质与形容词/关键词：{s.get('traits', '').strip()}"
        for i, s in enumerate(seeds)
    )
    id_list = ", ".join(expected_ids)
    n = len(seeds)
    style_extra = ""
    if style_key:
        style_extra = (
            "\n\n命名与描述风格（须严格遵守）：\n"
            f"{get_style_prompt(style_key, 'result_name')}\n\n"
            f"{get_style_prompt(style_key, 'result_desc')}"
        )

    return f"""你是心理测试设计师。用户已为主题「{theme}」指定了 {n} 个稀有结果的「角色/人物 + 气质关键词」。
请仅根据下列维度轴与普通结果上下文，为每个种子推断完整的稀有结果：抽象名称、描述、角色对标、触发阈值与特殊题命中数。

维度轴：
{axes_desc}

普通结果（供你把握整体风格，勿照抄）：
{results_desc}

用户指定的种子（输出顺序必须与之一一对应）：
{seed_lines}

你必须返回恰好 {n} 条 rare_results，且每条 id 必须**按顺序**严格为：{id_list}。
对每条结果：
- reference_name 应优先采用用户给出的「角色/人物」用语（可微调但需可辨认是同一人/角色）。
- reference_source 简短说明出处或身份（若用户未给出，你可合理补全）。
- threshold_conditions：2-3 条，axis_id 必须来自上表，direction 为 +1 或 -1，threshold 在 0.5-0.9。
- min_special_hits：1-3。
- type 字段填「附加」或「覆盖」（字符串），与常见稀有结果语义一致；默认倾向「附加」。

内容须适合人格测验语境；不提供违法或有害指导。{style_extra}

请严格返回如下 JSON 格式：
{{
  "rare_results": [
    {{
      "id": "{expected_ids[0] if expected_ids else 'rare_1'}",
      "name": "稀有结果名称",
      "type": "附加",
      "reference_name": "角色名",
      "reference_source": "出处",
      "description": "描述文案",
      "threshold_conditions": [
        {{
          "axis_id": "axis_1",
          "direction": 1,
          "threshold": 0.7
        }}
      ],
      "min_special_hits": 2
    }}
  ]
}}

要求：
- rare_results 数组长度恰好为 {n}，id 依次为 {id_list}
- 返回纯 JSON，不要附带任何其他文字"""


def build_rare_tags_from_seeds_prompt(
    dimensions: list[Dimension],
    archetypes: list[ResultArchetype],
    theme: str,
    seeds: list[dict[str, str]],
    expected_ids: list[str],
    occupied_clusters: frozenset[str],
    style_key: str | None = None,
) -> str:
    dim_desc = "\n".join(
        f"- {d.id} ({d.display_name}): {d.low_label}(-1) ←→ {d.high_label}(+1) — {d.description}"
        for d in dimensions
    )
    arch_desc = "\n".join(
        f"- {a.id}: {a.name}" for a in archetypes
    )
    seed_lines = "\n".join(
        f"{i + 1}. 用户指定的角色/人物：{s.get('character', '').strip()}\n"
        f"   气质与形容词/关键词：{s.get('traits', '').strip()}"
        for i, s in enumerate(seeds)
    )
    id_list = ", ".join(expected_ids)
    n = len(seeds)
    cluster_note = ""
    if occupied_clusters:
        cluster_note = (
            "\n以下 special_cluster 名称已被项目中其他标签占用，你生成的新规则中的 "
            f"special_cluster_min_hits 必须使用**不同的**英文下划线集群名，禁止复用：{', '.join(sorted(occupied_clusters))}"
        )
    style_extra = ""
    if style_key:
        style_extra = (
            "\n\n命名与描述风格（须严格遵守）：\n"
            f"{get_style_prompt(style_key, 'result_name')}\n\n"
            f"{get_style_prompt(style_key, 'result_desc')}"
        )

    return f"""你是心理测试设计师。用户已为主题「{theme}」指定了 {n} 个稀有标签的「角色/人物 + 气质关键词」。
请根据下列底层维度与结果原型，为每个种子推断完整的稀有标签：名称、描述、角色对标、以及触发规则（含维度阈值与可选的特殊题集群命中）。

维度：
{dim_desc}

结果原型：
{arch_desc}

用户指定的种子（输出顺序必须与之一一对应）：
{seed_lines}
{cluster_note}

你必须返回恰好 {n} 条 rare_tags，且每条 id 必须**按顺序**严格为：{id_list}。
规则结构：
- rules 中使用 "all" 键，值为规则对象数组。
- 可使用 dimension_min、dimension_max（dimension 必须来自上表维度 id，value 范围 -1 到 1）。
- 若需特殊题配合，使用 special_cluster_min_hits：cluster 为新的英文下划线名称，value 为命中次数（建议 1-3）。
- reference_name 优先贴合用户给出的角色/人物。

内容须适合人格测验语境；不提供违法或有害指导。{style_extra}

请严格返回如下 JSON 格式：
{{
  "rare_tags": [
    {{
      "id": "{expected_ids[0] if expected_ids else 'rtag_1'}",
      "name": "稀有标签名称",
      "reference_name": "角色名",
      "reference_source": "出处",
      "description": "描述文案",
      "rules": {{
        "all": [
          {{ "type": "dimension_min", "dimension": "dim_1", "value": 0.7 }},
          {{ "type": "special_cluster_min_hits", "cluster": "user_seed_cluster_1", "value": 2 }}
        ]
      }}
    }}
  ]
}}

要求：
- rare_tags 数组长度恰好为 {n}，id 依次为 {id_list}
- 同一次输出内各标签若使用 special_cluster_min_hits，cluster 名彼此须互不相同
- 返回纯 JSON，不要附带任何其他文字"""


def build_questions_prompt(
    axes: list[Axis],
    normal_results: list[NormalResult],
    rare_results: list[RareResult],
    style: str,
    questions_per_axis: int = 4,
    max_special: int = 4,
) -> str:
    axes_desc = "\n".join(
        f"- {a.id}: {a.left_name}(-1) ←→ {a.right_name}(+1) — {a.description}"
        for a in axes
    )

    rare_desc = ""
    if rare_results:
        rare_items = "\n".join(
            f"- {r.id}: {r.name} (触发条件涉及的轴: "
            + ", ".join(c.axis_id for c in r.threshold_conditions)
            + ")"
            for r in rare_results
        )
        rare_desc = f"\n稀有结果（需要为这些生成特殊题）：\n{rare_items}"

    total_normal = len(axes) * questions_per_axis
    total = total_normal + min(max_special, len(rare_results) * 2)

    return f"""请为以下人格测试生成题目。

维度轴：
{axes_desc}
{rare_desc}

风格要求：{style}

题目规则：
1. 普通题：每个轴生成恰好 {questions_per_axis} 道，共 {total_normal} 道
2. 特殊题：最多 {max_special} 道（关联稀有结果，用于触发隐藏类型）
3. 总题数不超过 {total} 道

每道题必须是一个情境或陈述，配有 5 个选项，对应五级量表：
- 选项1（强烈偏左，value=-2）
- 选项2（偏左，value=-1）
- 选项3（中立，value=0）
- 选项4（偏右，value=1）
- 选项5（强烈偏右，value=2）

选项文本不要直接写"强烈同意/不同意"，要结合题目情境给出具体的行为或态度描述。

请严格返回如下 JSON 格式：
{{
  "questions": [
    {{
      "id": "q_1",
      "text": "题目文本",
      "options": [
        {{"text": "选项文本", "value": -2}},
        {{"text": "选项文本", "value": -1}},
        {{"text": "选项文本", "value": 0}},
        {{"text": "选项文本", "value": 1}},
        {{"text": "选项文本", "value": 2}}
      ],
      "primary_axis_id": "axis_1",
      "weak_axes": [
        {{"axis_id": "axis_3", "coefficient": 0.5}}
      ],
      "is_special": false,
      "linked_rare_id": null
    }}
  ]
}}

要求：
- 普通题 id 格式 q_1 到 q_{total_normal}
- 特殊题 id 格式 sq_1 到 sq_{max_special}
- 每道普通题必须有且仅有 1 个 primary_axis_id
- weak_axes 可以为空数组或包含 1-2 个弱影响轴
- 特殊题的 is_special 设为 true，linked_rare_id 填对应的稀有结果 id
- 特殊题的 primary_axis_id 填与稀有结果触发条件最相关的轴
- 选项必须恰好 5 个，value 分别为 -2, -1, 0, 1, 2
- 返回纯 JSON，不要附带任何其他文字"""


# ---------------------------------------------------------------------------
# Multi-dimension prompts
# ---------------------------------------------------------------------------

def build_dimensions_prompt(theme: str, count: int, style: str) -> str:
    return f"""请为一个主题为「{theme}」的人格测试设计 {count} 个底层算法维度。

风格要求：{style}

重要：这些维度是**底层计分维度**，不是面向用户展示的花哨标题。
- display_name 必须是简洁的心理学/行为学特征词（2-4个字），类似 "表达力"、"秩序感"、"能量倾向"
- 不要用修辞性的、诗意的、过度包装的名字（如"舞台闪耀度"、"叛逆指数"之类的说法是错误的）
- low_label 和 high_label 各用 1-2 个字的极简对立词，如 "克制/外放"、"冷感/热烈"
- 这些维度将用于内部加权计算，用户最终只看到结果原型名称，不需要维度本身好看

示例维度（仅供理解格式和风格，不要照抄）：
- expression: 克制 / 外放 — 情绪与自我表达的强度
- temperature: 冷感 / 热烈 — 人际交往中的情感温度
- order: 混乱 / 秩序 — 对结构与规则的偏好程度
- burn: 保存 / 燃烧 — 精力与资源的消耗倾向
- distance: 亲近 / 疏离 — 社交距离的偏好
- dramatic: 平淡 / 戏剧化 — 生活节奏与波动的偏好

请严格返回如下 JSON 格式：
{{{{
  "dimensions": [
    {{{{
      "id": "dim_1",
      "display_name": "简洁特征词",
      "low_label": "低端",
      "high_label": "高端",
      "description": "一句话说明测量什么行为/心理特征"
    }}}}
  ]
}}}}

要求：
- id 格式为 dim_1, dim_2, ... dim_{count}
- display_name 必须简短、底层化、算法化，**禁止使用修辞包装**
- low_label 和 high_label 各 1-2 个字
- description 一句话，说明测量的具体心理或行为特征
- 维度之间要有足够区分度，覆盖不同的人格维面
- 生成恰好 {count} 个维度
- 返回纯 JSON，不要附带任何其他文字"""


def build_archetypes_prompt(
    dimensions: list[Dimension], count: int, theme: str,
) -> str:
    dim_desc = "\n".join(
        f"- {d.id} ({d.display_name}): {d.low_label}(-1) ←→ {d.high_label}(+1) — {d.description}"
        for d in dimensions
    )

    return f"""基于以下维度，为主题「{theme}」的人格测试生成 {count} 个结果原型。

维度：
{dim_desc}

每个结果原型包含：
1. 一个向量，表示在每个维度上的理想位置（范围 -1 到 1）
2. 一个抽象名称（name）：概括性的人格类型名
3. 一个角色/名人对标（reference_name + reference_source）：该领域中与此原型最匹配的真实名人或知名作品角色

请严格返回如下 JSON 格式：
{{{{
  "archetypes": [
    {{{{
      "id": "arch_1",
      "name": "原型名称（有个性和画面感）",
      "reference_name": "该领域的名人或角色名",
      "reference_source": "出处（如：某乐队主唱 / 某电影角色 / 某作品）",
      "description": "2-3句话描述这种人格类型",
      "vector": {{{{
        "dim_1": 0.8,
        "dim_2": -0.6,
        "dim_3": 0.3
      }}}}
    }}}}
  ]
}}}}

要求：
- id 格式为 arch_1, arch_2, ... arch_{count}
- vector 必须包含所有 {len(dimensions)} 个维度的值，范围 -1 到 1
- 原型之间的向量要有足够区分度（避免两个原型的余弦相似度过高）
- name 要有个性和画面感，与主题相关
- reference_name 必须是与主题「{theme}」相关的真实名人、艺术家、虚构角色等，要有辨识度
- reference_source 简短说明此人/角色的出处或身份
- 生成恰好 {count} 个原型
- 返回纯 JSON，不要附带任何其他文字"""


def build_rare_tags_prompt(
    dimensions: list[Dimension],
    archetypes: list[ResultArchetype],
    count: int,
    theme: str,
) -> str:
    dim_desc = "\n".join(
        f"- {d.id} ({d.display_name}): {d.low_label}(-1) ←→ {d.high_label}(+1)"
        for d in dimensions
    )
    arch_desc = "\n".join(
        f"- {a.id}: {a.name}" for a in archetypes
    )

    return f"""基于以下维度和结果原型，为主题「{theme}」的人格测试生成 {count} 个稀有标签。

维度：
{dim_desc}

结果原型：
{arch_desc}

稀有标签不替换主结果，而是作为额外标记附加在主结果之上。只有满足极端条件时才会触发。

每个稀有标签的触发规则使用以下结构：
- "dimension_min": 某维度得分 >= 指定值
- "dimension_max": 某维度得分 <= 指定值
- "special_cluster_min_hits": 某个特殊题集群的命中数 >= 指定值

请严格返回如下 JSON 格式：
{{{{
  "rare_tags": [
    {{{{
      "id": "rtag_1",
      "name": "稀有标签名称（有神秘感）",
      "reference_name": "该领域极端/独特的名人或角色",
      "reference_source": "出处",
      "description": "描述文案",
      "rules": {{{{
        "all": [
          {{{{ "type": "dimension_min", "dimension": "dim_1", "value": 0.7 }}}},
          {{{{ "type": "dimension_max", "dimension": "dim_3", "value": -0.4 }}}},
          {{{{ "type": "special_cluster_min_hits", "cluster": "collector", "value": 2 }}}}
        ]
      }}}}
    }}}}
  ]
}}}}

要求：
- id 格式为 rtag_1, rtag_2, ... rtag_{count}
- reference_name 必须是与主题「{theme}」相关的极端/独特代表人物或角色
- reference_source 简短说明出处或身份
- rules 中的 "all" 表示所有条件都必须满足
- dimension_min/dimension_max 的 value 范围 -1 到 1
- special_cluster_min_hits 的 cluster 名自定（英文下划线格式）
- 阈值不要太宽松（建议绝对值 >= 0.5）也不要完全不可能触发
- 名称要有神秘感、稀缺感
- 生成恰好 {count} 个稀有标签
- 返回纯 JSON，不要附带任何其他文字"""


def build_dim_questions_prompt(
    dimensions: list[Dimension],
    archetypes: list[ResultArchetype],
    rare_tags: list[RareTag],
    style: str,
    questions_per_dim: int = 4,
    max_special: int = 4,
) -> str:
    dim_desc = "\n".join(
        f"- {d.id} ({d.display_name}): {d.low_label}(-1) ←→ {d.high_label}(+1) — {d.description}"
        for d in dimensions
    )

    rare_desc = ""
    if rare_tags:
        clusters: set[str] = set()
        for rt in rare_tags:
            for rules in rt.rules.values():
                for r in rules:
                    if r.type == "special_cluster_min_hits" and r.cluster:
                        clusters.add(r.cluster)
        if clusters:
            rare_desc = f"\n需要为以下特殊集群生成特殊题：{', '.join(clusters)}"

    total_normal = len(dimensions) * questions_per_dim
    total = min(40, total_normal + max_special)

    return f"""请为以下多维度人格测试生成题目。

维度：
{dim_desc}
{rare_desc}

风格要求：{style}

题目规则：
1. 普通题：每个维度生成恰好 {questions_per_dim} 道，共 {total_normal} 道
2. 特殊题：最多 {max_special} 道（用于触发稀有标签）
3. 总题数不超过 {total} 道
4. 每道题恰好 3 个选项
5. 每道题必须绑定 1 个主维度，可选绑定 0-2 个副维度
6. 选项不直接对应结果，而是对应 effects（对各维度的加分）

每道题的 effects 值范围：
- 正向最大: 2
- 正向: 1
- 中立: 0
- 负向: -1
- 负向最大: -2

请严格返回如下 JSON 格式：
{{{{
  "questions": [
    {{{{
      "id": "dq_1",
      "stem": "题目文本（情境或陈述）",
      "primary_dimension": "dim_1",
      "secondary_dimensions": ["dim_3"],
      "options": [
        {{{{
          "text": "选项文本A",
          "effects": {{{{ "dim_1": 2, "dim_3": -1 }}}}
        }}}},
        {{{{
          "text": "选项文本B",
          "effects": {{{{ "dim_1": 0, "dim_3": 0 }}}}
        }}}},
        {{{{
          "text": "选项文本C",
          "effects": {{{{ "dim_1": -2, "dim_3": 1 }}}}
        }}}}
      ],
      "is_special": false,
      "special_cluster": null
    }}}}
  ]
}}}}

要求：
- 普通题 id 格式 dq_1 到 dq_{total_normal}
- 特殊题 id 格式 dsq_1 到 dsq_{max_special}
- 每道题恰好 3 个选项
- effects 中只包含主维度和副维度的 key
- 选项的 effects 值要严格按照分数设计，体现不同方向的偏好
- 特殊题的 is_special 设为 true，special_cluster 填对应的集群名
- 选项文本要具体、有情境感，不要用"同意/不同意"
- 返回纯 JSON，不要附带任何其他文字"""
