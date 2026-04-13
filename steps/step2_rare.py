"""Step 2 – Define rare results / rare tags."""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from core.models import TestMode, TestProject
from core.storage import auto_save

_IMAGES_DIR = Path(__file__).resolve().parent.parent / "projects" / "images"


def _save_rare_upload(uploaded_file, entity_id: str) -> Path:
    _IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    ext = Path(uploaded_file.name).suffix or ".png"
    dest = _IMAGES_DIR / f"{entity_id}{ext}"
    dest.write_bytes(uploaded_file.getvalue())
    return dest


def _show_axis_rare_validation(proj: TestProject) -> None:
    from core.validator import validate_rare_result_axis_rules

    rep = validate_rare_result_axis_rules(
        proj.rare_results,
        {a.id for a in proj.axes},
    )
    for issue in rep.errors:
        st.error(issue.message)
    for issue in rep.warnings:
        st.warning(issue.message)


def _show_dim_rare_validation(proj: TestProject) -> None:
    from core.validator import validate_rare_tag_dimension_rules

    rep = validate_rare_tag_dimension_rules(
        proj.rare_tags,
        {d.id for d in proj.dimensions},
    )
    for issue in rep.errors:
        st.error(issue.message)
    for issue in rep.warnings:
        st.warning(issue.message)


def render(proj: TestProject) -> None:
    st.header("步骤 2：定义稀有结果")

    is_axis_mode = proj.config.mode == TestMode.MULTI_AXIS

    enable_rare = st.toggle("加入稀有结果", value=True)

    if enable_rare:
        style_key = (
            proj.config.custom_style
            if proj.config.style.value == "自定义"
            else proj.config.style.value
        )

        if is_axis_mode:
            _render_axis_rare(proj, style_key)
        else:
            _render_dim_rare(proj, style_key)
    else:
        if is_axis_mode:
            proj.rare_results = []
        else:
            proj.rare_tags = []

    # navigation
    st.markdown("---")
    col_prev, col_next = st.columns(2)
    with col_prev:
        if st.button("← 上一步"):
            proj.current_step = 1
            st.rerun()
    with col_next:
        if st.button("确认，进入下一步 →", type="primary"):
            proj.current_step = 3
            auto_save(proj)
            st.rerun()


# ---------------------------------------------------------------------------
# Axis-mode rare results
# ---------------------------------------------------------------------------

def _render_axis_rare(proj: TestProject, style_key: str) -> None:
    max_rare = min(3, proj.config.max_rare_results)
    mode = st.radio(
        "稀有结果来源",
        ["系统生成", "指定角色或形容词"],
        horizontal=True,
        key="axis_rare_mode",
    )

    if mode == "系统生成":
        rare_count = st.slider(
            "稀有结果数量", min_value=1, max_value=max_rare,
            value=min(2, max_rare),
        )
        if st.button("生成稀有结果", type="primary", key="gen_rare_axis"):
            with st.spinner("正在调用 AI 生成稀有结果……"):
                from core.ai_service import generate_rare_results
                try:
                    rare = generate_rare_results(
                        proj.axes, proj.normal_results, rare_count, proj.config.theme,
                    )
                    proj.rare_results = rare
                    st.success(f"成功生成 {len(rare)} 个稀有结果！")
                    _show_axis_rare_validation(proj)
                except Exception as e:
                    st.error(f"生成稀有结果失败：{e}")
    else:
        st.caption(
            "填写角色/人物名与气质、形容词；AI 会在当前维度轴上推断阈值条件与文案。"
            " 生成将替换当前列表中的全部稀有结果。"
        )
        n_seeds = st.slider(
            "种子条数", min_value=1, max_value=max_rare,
            value=min(2, max_rare), key="axis_n_seeds",
        )
        seeds: list[dict[str, str]] = []
        for j in range(n_seeds):
            st.markdown(f"**种子 {j + 1}**")
            c1, c2 = st.columns(2)
            with c1:
                ch = st.text_input(
                    "角色/人物", value="", key=f"axis_seed_char_{j}",
                    placeholder="如：虚构角色或公众人物名",
                )
            with c2:
                tr = st.text_area(
                    "气质与形容词", value="", key=f"axis_seed_traits_{j}",
                    placeholder="如：阴郁、掌控欲、极端理性",
                    height=68,
                )
            seeds.append({"character": ch, "traits": tr})

        if st.button("由 AI 推断规则并生成", type="primary", key="infer_rare_axis"):
            filled = [s for s in seeds if (s.get("character") or "").strip()]
            if len(filled) != n_seeds:
                st.warning("请为每条种子填写「角色/人物」。")
            else:
                with st.spinner("正在根据种子推断稀有结果……"):
                    from core.ai_service import generate_rare_results_from_seeds
                    try:
                        proj.rare_results = generate_rare_results_from_seeds(
                            proj.axes,
                            proj.normal_results,
                            proj.config.theme,
                            filled,
                            style_key,
                        )
                        st.success(f"已生成 {len(proj.rare_results)} 个稀有结果。")
                        _show_axis_rare_validation(proj)
                    except Exception as e:
                        st.error(f"推断失败：{e}")

    if proj.rare_results:
        st.markdown("### 稀有结果列表")
        to_delete: list[int] = []
        for i, rr in enumerate(proj.rare_results):
            ref_label = f" → {rr.reference_name}" if rr.reference_name else ""
            origin_note = " [指定种子]" if rr.origin == "user_seeded" else ""
            with st.expander(f"{rr.id}: {rr.name}{ref_label}{origin_note}", expanded=True):
                c1, c2 = st.columns([4, 1])
                with c1:
                    if rr.origin == "user_seeded" and (
                        rr.user_seed_character or rr.user_seed_traits
                    ):
                        st.caption(
                            f"用户指定：{rr.user_seed_character or '—'} "
                            f"/ {rr.user_seed_traits or '—'}"
                        )
                    new_name = st.text_input("名称", value=rr.name, key=f"rare_name_{i}")
                    if new_name != rr.name:
                        proj.rare_results[i].name = new_name
                    rc1, rc2 = st.columns(2)
                    with rc1:
                        new_ref = st.text_input(
                            "角色对标", value=rr.reference_name or "", key=f"rare_ref_{i}",
                        )
                        if new_ref != (rr.reference_name or ""):
                            proj.rare_results[i].reference_name = new_ref or None
                    with rc2:
                        new_src = st.text_input(
                            "出处", value=rr.reference_source or "", key=f"rare_src_{i}",
                        )
                        if new_src != (rr.reference_source or ""):
                            proj.rare_results[i].reference_source = new_src or None
                    uploaded = st.file_uploader(
                        "上传形象图", type=["png", "jpg", "jpeg", "webp"],
                        key=f"rare_img_{i}",
                    )
                    if uploaded is not None:
                        img_path = _save_rare_upload(uploaded, rr.id)
                        proj.rare_results[i].image_path = str(img_path)
                        st.image(str(img_path), width=200)
                    elif rr.image_path and Path(rr.image_path).exists():
                        st.image(rr.image_path, width=200)
                    st.text_area("描述", value=rr.description, key=f"rare_desc_{i}", disabled=True)
                    conds = ", ".join(
                        f"{c.axis_id} {'→' if c.direction > 0 else '←'} ≥{c.threshold}"
                        for c in rr.threshold_conditions
                    )
                    st.markdown(f"**触发条件**：{conds}")
                    st.markdown(f"**需命中特殊题数**：{rr.min_special_hits}")
                with c2:
                    if st.button("删除", key=f"del_rare_{i}"):
                        to_delete.append(i)
                    if rr.origin == "user_seeded":
                        if st.button("重新推断", key=f"regen_rare_{i}"):
                            ch = (rr.user_seed_character or rr.reference_name or "").strip()
                            tr = (rr.user_seed_traits or "").strip()
                            if not ch:
                                st.error("缺少用户种子或角色对标，无法重新推断。")
                            else:
                                with st.spinner("重新推断中……"):
                                    from core.ai_service import generate_rare_results_from_seeds
                                    try:
                                        new_rare = generate_rare_results_from_seeds(
                                            proj.axes,
                                            proj.normal_results,
                                            proj.config.theme,
                                            [{"character": ch, "traits": tr}],
                                            style_key,
                                        )
                                        if new_rare:
                                            nr = new_rare[0]
                                            nr.id = rr.id
                                            prev_img = rr.image_path
                                            proj.rare_results[i] = nr
                                            if prev_img:
                                                proj.rare_results[i].image_path = prev_img
                                            st.rerun()
                                    except Exception as e:
                                        st.error(f"重新推断失败：{e}")
                    else:
                        if st.button("重新生成", key=f"regen_rare_{i}"):
                            with st.spinner("重新生成中……"):
                                from core.ai_service import generate_rare_results
                                try:
                                    new_rare = generate_rare_results(
                                        proj.axes, proj.normal_results, 1, proj.config.theme,
                                    )
                                    if new_rare:
                                        nr = new_rare[0]
                                        nr.id = rr.id
                                        prev_img = rr.image_path
                                        proj.rare_results[i] = nr
                                        if prev_img:
                                            proj.rare_results[i].image_path = prev_img
                                        st.rerun()
                                except Exception as e:
                                    st.error(f"重新生成失败：{e}")
        if to_delete:
            for idx in sorted(to_delete, reverse=True):
                proj.rare_results.pop(idx)
            st.rerun()


# ---------------------------------------------------------------------------
# Dimension-mode rare tags
# ---------------------------------------------------------------------------

def _render_dim_rare(proj: TestProject, style_key: str) -> None:
    max_rare = min(3, proj.config.max_rare_results)
    mode = st.radio(
        "稀有标签来源",
        ["系统生成", "指定角色或形容词"],
        horizontal=True,
        key="dim_rare_mode",
    )

    if mode == "系统生成":
        rare_count = st.slider(
            "稀有标签数量", min_value=1, max_value=max_rare,
            value=min(2, max_rare),
        )
        if st.button("生成稀有标签", type="primary", key="gen_rare_dim"):
            with st.spinner("正在调用 AI 生成稀有标签……"):
                from core.ai_service import generate_rare_tags
                try:
                    tags = generate_rare_tags(
                        proj.dimensions, proj.archetypes, rare_count, proj.config.theme,
                    )
                    proj.rare_tags = tags
                    st.success(f"成功生成 {len(tags)} 个稀有标签！")
                    _show_dim_rare_validation(proj)
                except Exception as e:
                    st.error(f"生成稀有标签失败：{e}")
    else:
        st.caption(
            "填写角色/人物与气质关键词；AI 会推断维度规则与特殊题集群名。"
            " 生成将替换当前列表中的全部稀有标签。"
        )
        n_seeds = st.slider(
            "种子条数", min_value=1, max_value=max_rare,
            value=min(2, max_rare), key="dim_n_seeds",
        )
        seeds: list[dict[str, str]] = []
        for j in range(n_seeds):
            st.markdown(f"**种子 {j + 1}**")
            c1, c2 = st.columns(2)
            with c1:
                ch = st.text_input(
                    "角色/人物", value="", key=f"dim_seed_char_{j}",
                    placeholder="如：虚构角色或公众人物名",
                )
            with c2:
                tr = st.text_area(
                    "气质与形容词", value="", key=f"dim_seed_traits_{j}",
                    placeholder="如：偏执、收藏癖、夜型人格",
                    height=68,
                )
            seeds.append({"character": ch, "traits": tr})

        if st.button("由 AI 推断规则并生成", type="primary", key="infer_rare_dim"):
            filled = [s for s in seeds if (s.get("character") or "").strip()]
            if len(filled) != n_seeds:
                st.warning("请为每条种子填写「角色/人物」。")
            else:
                with st.spinner("正在根据种子推断稀有标签……"):
                    from core.ai_service import generate_rare_tags_from_seeds
                    try:
                        proj.rare_tags = generate_rare_tags_from_seeds(
                            proj.dimensions,
                            proj.archetypes,
                            proj.config.theme,
                            filled,
                            style_key,
                            other_tags_for_cluster=None,
                        )
                        st.success(f"已生成 {len(proj.rare_tags)} 个稀有标签。")
                        _show_dim_rare_validation(proj)
                    except Exception as e:
                        st.error(f"推断失败：{e}")

    if proj.rare_tags:
        st.markdown("### 稀有标签列表")
        to_delete: list[int] = []
        for i, rt in enumerate(proj.rare_tags):
            ref_label = f" → {rt.reference_name}" if rt.reference_name else ""
            origin_note = " [指定种子]" if rt.origin == "user_seeded" else ""
            with st.expander(f"{rt.id}: {rt.name}{ref_label}{origin_note}", expanded=True):
                c1, c2 = st.columns([4, 1])
                with c1:
                    if rt.origin == "user_seeded" and (
                        rt.user_seed_character or rt.user_seed_traits
                    ):
                        st.caption(
                            f"用户指定：{rt.user_seed_character or '—'} "
                            f"/ {rt.user_seed_traits or '—'}"
                        )
                    new_name = st.text_input("名称", value=rt.name, key=f"rtag_name_{i}")
                    if new_name != rt.name:
                        proj.rare_tags[i].name = new_name
                    rc1, rc2 = st.columns(2)
                    with rc1:
                        new_ref = st.text_input(
                            "角色对标", value=rt.reference_name or "", key=f"rtag_ref_{i}",
                        )
                        if new_ref != (rt.reference_name or ""):
                            proj.rare_tags[i].reference_name = new_ref or None
                    with rc2:
                        new_src = st.text_input(
                            "出处", value=rt.reference_source or "", key=f"rtag_src_{i}",
                        )
                        if new_src != (rt.reference_source or ""):
                            proj.rare_tags[i].reference_source = new_src or None
                    uploaded = st.file_uploader(
                        "上传形象图", type=["png", "jpg", "jpeg", "webp"],
                        key=f"rtag_img_{i}",
                    )
                    if uploaded is not None:
                        img_path = _save_rare_upload(uploaded, rt.id)
                        proj.rare_tags[i].image_path = str(img_path)
                        st.image(str(img_path), width=200)
                    elif rt.image_path and Path(rt.image_path).exists():
                        st.image(rt.image_path, width=200)
                    st.text_area("描述", value=rt.description, key=f"rtag_desc_{i}", disabled=True)
                    for gate, rules in rt.rules.items():
                        parts = []
                        for r in rules:
                            if r.type == "dimension_min":
                                parts.append(f"{r.dimension} ≥ {r.value}")
                            elif r.type == "dimension_max":
                                parts.append(f"{r.dimension} ≤ {r.value}")
                            elif r.type == "special_cluster_min_hits":
                                parts.append(f"集群 {r.cluster} 命中 ≥ {int(r.value)}")
                        st.markdown(f"**规则 ({gate})**：{' & '.join(parts)}")
                with c2:
                    if st.button("删除", key=f"del_rtag_{i}"):
                        to_delete.append(i)
                    if rt.origin == "user_seeded":
                        if st.button("重新推断", key=f"regen_rtag_{i}"):
                            ch = (rt.user_seed_character or rt.reference_name or "").strip()
                            tr = (rt.user_seed_traits or "").strip()
                            if not ch:
                                st.error("缺少用户种子或角色对标，无法重新推断。")
                            else:
                                with st.spinner("重新推断中……"):
                                    from core.ai_service import (
                                        generate_rare_tags_from_seeds,
                                    )
                                    try:
                                        others = [
                                            p for j, p in enumerate(proj.rare_tags) if j != i
                                        ]
                                        new_tags = generate_rare_tags_from_seeds(
                                            proj.dimensions,
                                            proj.archetypes,
                                            proj.config.theme,
                                            [{"character": ch, "traits": tr}],
                                            style_key,
                                            other_tags_for_cluster=others,
                                        )
                                        if new_tags:
                                            nt = new_tags[0]
                                            nt.id = rt.id
                                            prev_img = rt.image_path
                                            proj.rare_tags[i] = nt
                                            if prev_img:
                                                proj.rare_tags[i].image_path = prev_img
                                            st.rerun()
                                    except Exception as e:
                                        st.error(f"重新推断失败：{e}")
                    else:
                        if st.button("重新生成", key=f"regen_rtag_{i}"):
                            with st.spinner("重新生成中……"):
                                from core.ai_service import generate_rare_tags
                                try:
                                    new_tags = generate_rare_tags(
                                        proj.dimensions, proj.archetypes, 1, proj.config.theme,
                                    )
                                    if new_tags:
                                        nt = new_tags[0]
                                        nt.id = rt.id
                                        prev_img = rt.image_path
                                        proj.rare_tags[i] = nt
                                        if prev_img:
                                            proj.rare_tags[i].image_path = prev_img
                                        st.rerun()
                                except Exception as e:
                                    st.error(f"重新生成失败：{e}")
        if to_delete:
            for idx in sorted(to_delete, reverse=True):
                proj.rare_tags.pop(idx)
            st.rerun()
