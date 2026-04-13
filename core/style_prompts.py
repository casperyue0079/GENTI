"""Centralised style prompt templates for the two built-in styles.

Each style provides context-specific instructions for:
- general: overall tone & language
- result_name: naming conventions for results
- result_desc: description / copy style
- question: question wording style
- negative: what to avoid
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# 严肃（类似 MBTI 的语气）
# ---------------------------------------------------------------------------

_SERIOUS_GENERAL = """\
请使用一种相对正式、克制、结构化的人格测试语言风格生成内容。

风格要求如下：
1. 不要使用过于网络化、戏谑化、梗化的表达。
2. 语气应中性、平稳、清晰，像一份人格偏好说明，而不是社交媒体标签。
3. 重点应放在人格倾向、行为偏好和认知方式的描述，而不是制造冒犯感或传播感。
4. 结果名称应偏中性、正式、稳定，不要像外号或戏剧化称呼。
5. 文案应避免绝对化判断，更多使用"通常""倾向于""在某些情境下""可能会"等表达。
6. 内容应强调偏好差异，而不是价值高低。
7. 不要写成心理咨询报告，也不要写成学术论文，应保持可读性。
8. 整体应让用户感觉被客观描述，而不是被贴标签。
9. 避免夸张、尖锐、轻微冒犯、阴阳怪气和强烈情绪色彩。
10. 最终风格应具备：中性、克制、结构清晰、易于接受、具有解释性。"""

_SERIOUS_RESULT_NAME = """\
生成结果名称的要求：
1. 名称应偏中性、稳定、正式。
2. 不要使用网络热词、外号式表达或带戏剧性的称呼。
3. 名称要像人格类型、行为风格或认知倾向类别。
4. 避免夸张、攻击性和明显情绪化表达。
5. 名称应易于理解，并适合长期使用。"""

_SERIOUS_RESULT_DESC = """\
生成结果描述的要求：
1. 一句话总结应概括用户的主要人格倾向，而不是做情绪化判断。
2. 语气中性、客观、克制。
3. 使用"通常""倾向于""可能会"等表达，避免绝对化。
4. 不要写成贴标签式文案，不要刻意追求锋利或传播感。
5. 描述中应包括：主要偏好、常见行为表现、可能优势和潜在盲点。
6. 避免鸡汤、鼓励、安慰和社交媒体梗式语言。"""

_SERIOUS_QUESTION = """\
生成题目的要求：
1. 题目简洁、清晰、中性。
2. 题目重点测量行为偏好、信息处理方式、决策倾向或社交方式。
3. 不使用网络化、戏剧化或情绪化表达。
4. 不要使用正式心理学术语，但要保持测量感和稳定性。
5. 题目应避免明显诱导，不要让用户觉得某个答案更正确。
6. 优先使用"你通常会如何""在大多数情况下""面对某种情境时你更倾向于"等表达。"""

_SERIOUS_NEGATIVE = """\
负面约束——请避免以下问题：
1. 不要写成社交媒体人格梗文案。
2. 不要写成网络热词标签或外号。
3. 不要使用尖锐、冒犯、阴阳怪气或戏谑语气。
4. 不要写成小说人物设定或角色介绍。
5. 不要使用过多夸张修辞。
6. 不要把人格描述写成价值判断。
7. 不要为了"有趣"而牺牲中性与可测量性。"""


# ---------------------------------------------------------------------------
# 幽默（SBTI 风格）
# ---------------------------------------------------------------------------

_HUMOROUS_GENERAL = """\
请使用一种"中文互联网爆款人格测试"的语言风格生成内容。

风格要求如下：
1. 不要使用正式心理学术语，不要写成学术量表或咨询报告。
2. 整体语气是"半认真半调侃"的，像在认真分类一个人，但带有轻微的戏谑感和冒犯感。
3. 输出重点不是理论解释，而是"人格标签命中感"。
4. 结果名称要像社交媒体上会传播的人设外号、人格标签或缩写，而不是标准人格学名称。
5. 文案要短、准、锋利，避免长篇说理。
6. 一句话描述要有"贴脸判断"的效果，让人觉得"有点被冒犯，但确实像我"。
7. 关键词要使用中文互联网语境中常见的标签化表达，避免过于正式或中性。
8. 不要使用鸡汤语气，不要鼓励式表达，不要写成温柔安慰型文案。
9. 不要写成纯搞笑段子，要保留一点"真的在做人格分类"的错觉。
10. 最终风格应具备：高命中感、强标签感、轻微攻击性、可截图传播性。"""

_HUMOROUS_RESULT_NAME = """\
生成结果名称的要求：
1. 名称长度尽量短。
2. 名称要像人格标签、外号、社交媒体可传播的人设名。
3. 不要像小说角色名，不要像正式心理学分类名。
4. 不要太中性，要有鲜明态度或轻微戏剧性。
5. 名称应让用户一眼产生"这很像某种人"的感觉。
6. 允许略带冒犯、自嘲、冷幽默，但不要低俗。"""

_HUMOROUS_RESULT_DESC = """\
生成结果描述的要求：
1. 一句话描述优先追求命中感，而不是完整解释。
2. 风格像社交媒体上被广泛转发的人格判词。
3. 语气半认真半调侃，略带锋利感。
4. 避免鸡汤、安慰、鼓励和过度温柔。
5. 不要长篇分析，不要写成说明书。
6. 用户读完后应产生"被说中了"的感觉，而不是"被教育了"的感觉。"""

_HUMOROUS_QUESTION = """\
生成题目的要求：
1. 题目要短，不要写成长问卷语句。
2. 题目优先使用生活场景、态度选择、社交判断和行为倾向，而不是抽象自评。
3. 不要使用正式心理学术语。
4. 题目要有代入感，像在快速判断一个人的人设。
5. 风格应轻松、直接、略带标签感，但不要写成纯搞笑文案。
6. 每道题都要能服务于人格分类，而不是只是好玩。"""

_HUMOROUS_NEGATIVE = """\
负面约束——请避免以下问题：
1. 不要写成 MBTI 或传统人格测试口吻。
2. 不要写成正式心理学分析。
3. 不要写成小说或诗歌。
4. 不要写成鸡汤、自我疗愈或温柔治愈风。
5. 不要只追求抽象而失去可理解性。
6. 不要为了有梗而完全失去人格测试的判断感。
7. 不要使用非常陈词滥调的褒义词，如"温暖""善良""勇敢""真实"等作为核心结果标签。"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_style_prompt(
    style_key: str,
    context: str = "general",
) -> str:
    """Return the full prompt text for a given style and context.

    Parameters
    ----------
    style_key : str
        "严肃", "幽默", or arbitrary custom text.
    context : str
        One of "general", "result_name", "result_desc", "question".
        Falls back to "general" for unknown contexts.

    For custom styles, returns the raw user text as-is.
    """
    if style_key == "严肃":
        parts = _SERIOUS_PARTS
    elif style_key == "幽默":
        parts = _HUMOROUS_PARTS
    else:
        return style_key

    block = parts.get(context, parts["general"])
    negative = parts["negative"]
    return f"{block}\n\n{negative}"


_SERIOUS_PARTS: dict[str, str] = {
    "general": _SERIOUS_GENERAL,
    "result_name": f"{_SERIOUS_GENERAL}\n\n{_SERIOUS_RESULT_NAME}",
    "result_desc": f"{_SERIOUS_GENERAL}\n\n{_SERIOUS_RESULT_DESC}",
    "question": f"{_SERIOUS_GENERAL}\n\n{_SERIOUS_QUESTION}",
    "negative": _SERIOUS_NEGATIVE,
}

_HUMOROUS_PARTS: dict[str, str] = {
    "general": _HUMOROUS_GENERAL,
    "result_name": f"{_HUMOROUS_GENERAL}\n\n{_HUMOROUS_RESULT_NAME}",
    "result_desc": f"{_HUMOROUS_GENERAL}\n\n{_HUMOROUS_RESULT_DESC}",
    "question": f"{_HUMOROUS_GENERAL}\n\n{_HUMOROUS_QUESTION}",
    "negative": _HUMOROUS_NEGATIVE,
}
