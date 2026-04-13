"""Step 3 – Generate and edit questions."""
from __future__ import annotations

import streamlit as st

from core.models import TestMode, TestProject
from core.storage import auto_save


def render(proj: TestProject) -> None:
    st.header("步骤 3：生成题目")

    is_axis_mode = proj.config.mode == TestMode.MULTI_AXIS

    # config summary
    st.markdown("### 当前配置摘要")
    c1, c2, c3 = st.columns(3)
    if is_axis_mode:
        c1.metric("轴数", len(proj.axes))
        c2.metric("普通结果数", len(proj.normal_results))
        c3.metric("稀有结果数", len(proj.rare_results))
    else:
        c1.metric("维度数", len(proj.dimensions))
        c2.metric("结果原型数", len(proj.archetypes))
        c3.metric("稀有标签数", len(proj.rare_tags))

    st.markdown(f"**主题**：{proj.config.theme}　　**风格**：{proj.config.style.value}")
    st.markdown("---")

    style_key = (
        proj.config.custom_style
        if proj.config.style.value == "自定义"
        else proj.config.style.value
    )

    if is_axis_mode:
        _render_axis_questions(proj, style_key)
    else:
        _render_dim_questions(proj, style_key)

    # navigation
    st.markdown("---")
    col_prev, col_next = st.columns(2)
    with col_prev:
        if st.button("← 上一步"):
            proj.current_step = 2
            st.rerun()
    with col_next:
        has_qs = bool(proj.questions) if is_axis_mode else bool(proj.dim_questions)
        if st.button("确认题目，进入下一步 →", type="primary", disabled=not has_qs):
            proj.current_step = 4
            auto_save(proj)
            st.rerun()


# ---------------------------------------------------------------------------
# Multi-axis questions
# ---------------------------------------------------------------------------

def _render_axis_questions(proj: TestProject, style_key: str) -> None:
    from core.style_prompts import get_style_prompt

    if st.button("生成题目", type="primary", key="gen_q_axis"):
        with st.spinner("正在调用 AI 生成题目……"):
            from core.ai_service import generate_questions
            try:
                questions = generate_questions(
                    axes=proj.axes,
                    normal_results=proj.normal_results,
                    rare_results=proj.rare_results,
                    style=get_style_prompt(style_key, "question"),
                    questions_per_axis=proj.config.questions_per_axis,
                    max_special=proj.config.max_special_questions,
                )
                proj.questions = questions
                st.success(f"成功生成 {len(questions)} 道题目！")
            except Exception as e:
                st.error(f"生成题目失败：{e}")

    if proj.questions:
        from core.validator import validate_questions
        report = validate_questions(proj.questions, proj.config, [a.id for a in proj.axes])
        _show_validation(report)

        normal_qs = [q for q in proj.questions if not q.is_special]
        special_qs = [q for q in proj.questions if q.is_special]

        st.markdown(f"**普通题** ({len(normal_qs)} 道)")
        for q in normal_qs:
            with st.expander(f"{q.id} [{q.primary_axis_id}]: {q.text[:50]}…"):
                new_text = st.text_area("题干", value=q.text, key=f"qt_{q.id}")
                if new_text != q.text:
                    q.text = new_text
                st.markdown(f"**主测轴**：{q.primary_axis_id}")
                if q.weak_axes:
                    weak_str = ", ".join(f"{w.axis_id}(×{w.coefficient})" for w in q.weak_axes)
                    st.markdown(f"**弱影响轴**：{weak_str}")
                for opt in q.options:
                    st.markdown(f"- [{opt.value:+d}] {opt.text}")

        if special_qs:
            st.markdown(f"**特殊题** ({len(special_qs)} 道)")
            for q in special_qs:
                with st.expander(f"{q.id} [特殊→{q.linked_rare_id}]: {q.text[:50]}…"):
                    new_text = st.text_area("题干", value=q.text, key=f"qt_{q.id}")
                    if new_text != q.text:
                        q.text = new_text
                    for opt in q.options:
                        st.markdown(f"- [{opt.value:+d}] {opt.text}")


# ---------------------------------------------------------------------------
# Multi-dimension questions
# ---------------------------------------------------------------------------

def _render_dim_questions(proj: TestProject, style_key: str) -> None:
    from core.style_prompts import get_style_prompt

    if st.button("生成题目", type="primary", key="gen_q_dim"):
        with st.spinner("正在调用 AI 生成题目……"):
            from core.ai_service import generate_dim_questions
            try:
                questions = generate_dim_questions(
                    dimensions=proj.dimensions,
                    archetypes=proj.archetypes,
                    rare_tags=proj.rare_tags,
                    style=get_style_prompt(style_key, "question"),
                    questions_per_dim=proj.config.questions_per_dimension,
                    max_special=proj.config.max_special_questions,
                )
                proj.dim_questions = questions
                st.success(f"成功生成 {len(questions)} 道题目！")
            except Exception as e:
                st.error(f"生成题目失败：{e}")

    if proj.dim_questions:
        from core.validator import validate_dim_questions
        report = validate_dim_questions(
            proj.dim_questions, proj.config, [d.id for d in proj.dimensions],
        )
        _show_validation(report)

        normal_qs = [q for q in proj.dim_questions if not q.is_special]
        special_qs = [q for q in proj.dim_questions if q.is_special]

        st.markdown(f"**普通题** ({len(normal_qs)} 道)")
        for q in normal_qs:
            with st.expander(f"{q.id} [{q.primary_dimension}]: {q.stem[:50]}…"):
                new_stem = st.text_area("题干", value=q.stem, key=f"dqt_{q.id}")
                if new_stem != q.stem:
                    q.stem = new_stem
                st.markdown(f"**主维度**：{q.primary_dimension}")
                if q.secondary_dimensions:
                    st.markdown(f"**副维度**：{', '.join(q.secondary_dimensions)}")
                for j, opt in enumerate(q.options):
                    eff_str = ", ".join(f"{k}: {v:+d}" for k, v in opt.effects.items())
                    st.markdown(f"- 选项{j+1}: {opt.text}　`[{eff_str}]`")

        if special_qs:
            st.markdown(f"**特殊题** ({len(special_qs)} 道)")
            for q in special_qs:
                with st.expander(f"{q.id} [特殊·{q.special_cluster}]: {q.stem[:50]}…"):
                    new_stem = st.text_area("题干", value=q.stem, key=f"dqt_{q.id}")
                    if new_stem != q.stem:
                        q.stem = new_stem
                    for j, opt in enumerate(q.options):
                        eff_str = ", ".join(f"{k}: {v:+d}" for k, v in opt.effects.items())
                        st.markdown(f"- 选项{j+1}: {opt.text}　`[{eff_str}]`")


def _show_validation(report) -> None:  # type: ignore[type-arg]
    if report.passed:
        st.success("所有校验通过！")
    else:
        for issue in report.errors:
            st.error(issue.message)
    for issue in report.warnings:
        st.warning(issue.message)
