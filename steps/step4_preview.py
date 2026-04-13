"""Step 4 – Preview the test via embedded HTML or Streamlit fallback."""
from __future__ import annotations

import base64
import copy
import json
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from core.models import TestMode, TestProject
from core.storage import auto_save

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"


def _embed_images_as_data_urls(test_data: dict) -> dict:
    """Iframe预览无法加载本地磁盘路径；将可读文件转为 data URL供 <img src> 使用。"""
    d = copy.deepcopy(test_data)

    def to_data_url(path: str) -> str:
        p = Path(path)
        if not p.is_file():
            return path
        ext = p.suffix.lower()
        mime = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
        }.get(ext, "application/octet-stream")
        b64 = base64.standard_b64encode(p.read_bytes()).decode("ascii")
        return f"data:{mime};base64,{b64}"

    def patch(obj: dict) -> None:
        v = obj.get("image_path")
        if v and isinstance(v, str) and not v.startswith("data:"):
            obj["image_path"] = to_data_url(v)

    mode = d.get("mode")
    if mode == "多向轴":
        for r in d.get("normal_results") or []:
            patch(r)
        for rr in d.get("rare_results") or []:
            patch(rr)
    elif mode == "多维度":
        for a in d.get("archetypes") or []:
            patch(a)
        for rt in d.get("rare_tags") or []:
            patch(rt)

    return d


def render(proj: TestProject) -> None:
    st.header("步骤 4：预览测试")

    preview_mode = st.radio(
        "预览方式",
        ["嵌入式预览（推荐）", "简易预览"],
        horizontal=True,
        label_visibility="collapsed",
    )

    if preview_mode == "嵌入式预览（推荐）":
        _render_embedded_preview(proj)
    else:
        _render_simple_preview(proj)

    # navigation
    st.markdown("---")
    col_prev, col_next = st.columns(2)
    with col_prev:
        if st.button("← 上一步"):
            proj.current_step = 3
            st.rerun()
    with col_next:
        if st.button("确认，进入发布 →", type="primary"):
            proj.current_step = 5
            auto_save(proj)
            st.rerun()


def _render_embedded_preview(proj: TestProject) -> None:
    """Render the actual exported HTML inside an iframe-like component."""
    from core.exporter import _flatten_project

    css_text = (_TEMPLATES_DIR / "style.css").read_text(encoding="utf-8")
    js_text = (_TEMPLATES_DIR / "engine.js").read_text(encoding="utf-8")

    test_data = _embed_images_as_data_urls(_flatten_project(proj))
    test_data_json = json.dumps(test_data, ensure_ascii=False)

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>{css_text}</style>
</head>
<body>
  <div class="container" id="app"></div>
  <script>window.__TEST_DATA__ = {test_data_json};</script>
  <script>{js_text}</script>
</body>
</html>"""

    st.caption("以下是导出后的实际测试效果（可交互）")
    components.html(html, height=800, scrolling=True)


# ---------------------------------------------------------------------------
# Streamlit-native simple preview (fallback)
# ---------------------------------------------------------------------------

def _render_simple_preview(proj: TestProject) -> None:
    is_axis_mode = proj.config.mode == TestMode.MULTI_AXIS

    if "preview_answers" not in st.session_state:
        st.session_state.preview_answers = {}
    if "preview_done" not in st.session_state:
        st.session_state.preview_done = False

    if not st.session_state.preview_done:
        if is_axis_mode:
            _preview_axis_questions(proj)
        else:
            _preview_dim_questions(proj)
    else:
        if is_axis_mode:
            _show_axis_result(proj)
        else:
            _show_dim_result(proj)


def _preview_axis_questions(proj: TestProject) -> None:
    total = len(proj.questions)
    for idx, q in enumerate(proj.questions):
        st.markdown(f"**第 {idx + 1}/{total} 题**")
        st.markdown(q.text)
        option_texts = [opt.text for opt in q.options]
        choice = st.radio(
            "选择", option_texts, key=f"pv_q_{q.id}", index=2,
            horizontal=True, label_visibility="collapsed",
        )
        selected_idx = option_texts.index(choice)
        st.session_state.preview_answers[q.id] = q.options[selected_idx].value
        st.markdown("---")

    if st.button("查看结果", type="primary", key="pv_submit"):
        st.session_state.preview_done = True
        st.rerun()


def _show_axis_result(proj: TestProject) -> None:
    from core.scoring import score_test

    result = score_test(
        axes=proj.axes,
        questions=proj.questions,
        normal_results=proj.normal_results,
        rare_results=proj.rare_results,
        answers=st.session_state.preview_answers,
    )

    st.markdown("#### 测试结果")
    if result.override_result_name:
        st.markdown(f"### {result.override_result_name}")
    else:
        st.markdown(f"### {result.normal_result_name}")

    if result.rare_tags:
        st.markdown("**隐藏标签**：" + " | ".join(f"✨ {t}" for t in result.rare_tags))

    for axis in proj.axes:
        score = result.dimension_scores.get(axis.id, 0)
        c1, c2 = st.columns([1, 3])
        c1.markdown(f"**{axis.left_name} ← → {axis.right_name}**")
        c2.progress((score + 1) / 2, text=f"{score:+.2f}")

    if st.button("重新预览", key="pv_reset"):
        st.session_state.preview_answers = {}
        st.session_state.preview_done = False
        st.rerun()


def _preview_dim_questions(proj: TestProject) -> None:
    total = len(proj.dim_questions)
    for idx, q in enumerate(proj.dim_questions):
        st.markdown(f"**第 {idx + 1}/{total} 题**")
        st.markdown(q.stem)
        option_texts = [opt.text for opt in q.options]
        choice = st.radio(
            "选择", option_texts, key=f"pv_dq_{q.id}", index=1,
            horizontal=True, label_visibility="collapsed",
        )
        selected_idx = option_texts.index(choice)
        st.session_state.preview_answers[q.id] = selected_idx
        st.markdown("---")

    if st.button("查看结果", type="primary", key="pv_submit_dim"):
        st.session_state.preview_done = True
        st.rerun()


def _show_dim_result(proj: TestProject) -> None:
    from core.dim_scoring import score_dim_test

    result = score_dim_test(
        dimensions=proj.dimensions,
        questions=proj.dim_questions,
        archetypes=proj.archetypes,
        rare_tags=proj.rare_tags,
        answers=st.session_state.preview_answers,
    )

    st.markdown("#### 测试结果")
    st.markdown(f"### {result['archetype_name']}")
    if result.get("archetype_description"):
        st.markdown(result["archetype_description"])
    sim_pct = result.get("similarity", 0) * 100
    st.caption(f"匹配度：{sim_pct:.0f}%")

    if result.get("rare_tag_names"):
        st.markdown(
            "**稀有标签**：" + " | ".join(f"✨ {t}" for t in result["rare_tag_names"])
        )

    for dim in proj.dimensions:
        score = result["dimension_scores"].get(dim.id, 0)
        c1, c2 = st.columns([1, 3])
        c1.markdown(f"**{dim.low_label} ← → {dim.high_label}**")
        c2.progress((score + 1) / 2, text=f"{score:+.2f}")

    if st.button("重新预览", key="pv_reset_dim"):
        st.session_state.preview_answers = {}
        st.session_state.preview_done = False
        st.rerun()
