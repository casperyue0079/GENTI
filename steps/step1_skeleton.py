"""Step 1 – Define test skeleton (mode, axes/dimensions, normal results)."""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from core.models import NamingMode, TestConfig, TestMode, TestProject, TestStyle
from core.storage import auto_save

_IMAGES_DIR = Path(__file__).resolve().parent.parent / "projects" / "images"


def render(proj: TestProject) -> None:
    st.header("步骤 1：定义测试骨架")

    st.markdown("### 基础设置")
    col1, col2 = st.columns(2)

    with col1:
        theme = st.text_input(
            "测试主题 / 领域",
            value=proj.config.theme,
            placeholder="例如：ACG、摇滚、城市、恋爱……",
        )
        mode_options = [TestMode.MULTI_AXIS.value, TestMode.MULTI_DIM.value]
        current_mode_idx = mode_options.index(proj.config.mode.value)
        mode_choice = st.radio("测试模式", mode_options, index=current_mode_idx, horizontal=True)

    with col2:
        style_display = ["严肃（类似MBTI的语气）", "幽默（SBTI风格）", "自定义"]
        style_values = ["严肃", "幽默", "自定义"]
        current_style_idx = (
            style_values.index(proj.config.style.value)
            if proj.config.style.value in style_values
            else 1
        )
        style_display_choice = st.selectbox("题目风格", style_display, index=current_style_idx)
        style_choice = style_values[style_display.index(style_display_choice)]
        custom_style = ""
        if style_choice == "自定义":
            custom_style = st.text_input(
                "自定义风格描述（自定义 prompt，将直接传递给 AI 作为风格指令）",
                value=proj.config.custom_style,
                placeholder="例如：用二次元中二风格、用东北话唠嗑风格、用哲学思辨风格……",
            )

    is_axis_mode = mode_choice == TestMode.MULTI_AXIS.value

    if is_axis_mode:
        axis_count = st.slider("轴数量", min_value=4, max_value=10, value=proj.config.axis_count)
        result_count_map = {4: 8, 5: 10, 6: 12, 7: 14, 8: 16, 9: 16, 10: 16}
        normal_result_count = result_count_map.get(axis_count, 16)
    else:
        dim_count = st.slider("维度数量", min_value=3, max_value=8, value=min(proj.config.dimension_count, 8))
        # dynamic archetype range based on dimension count
        arch_min = dim_count + 1
        arch_max = 2 * dim_count + 4
        arch_default = min(max(proj.config.archetype_count, arch_min), arch_max)
        archetype_count = st.slider(
            "结果原型数量", min_value=arch_min, max_value=arch_max, value=arch_default,
        )
        st.caption(f"{dim_count} 个维度建议 {arch_min}~{arch_max} 个原型")

    # naming mode (shared by both modes)
    naming_options = [NamingMode.ABSTRACT.value, NamingMode.REFERENCE.value, NamingMode.BOTH.value]
    current_naming_idx = naming_options.index(proj.config.naming_mode.value) if proj.config.naming_mode.value in naming_options else 0
    naming_choice = st.radio(
        "结果命名方式",
        naming_options,
        index=current_naming_idx,
        horizontal=True,
        help="抽象形容 = 概括性名称；角色对标 = 该领域名人/角色；两者兼用 = 主名 + 副标注",
    )

    # persist config
    proj.config.theme = theme
    proj.config.mode = TestMode(mode_choice)
    proj.config.style = TestStyle(style_choice)
    proj.config.custom_style = custom_style
    proj.config.naming_mode = NamingMode(naming_choice)
    if is_axis_mode:
        proj.config.axis_count = axis_count
        proj.config.normal_result_count = normal_result_count
    else:
        proj.config.dimension_count = dim_count
        proj.config.archetype_count = archetype_count

    st.markdown("---")
    # resolve style: for built-in styles use the detailed prompt, for custom use raw text
    style_key = custom_style if style_choice == "自定义" else style_choice

    # ----- MULTI-AXIS generation -----
    if is_axis_mode:
        _render_axis_mode(proj, theme, style_key)
    else:
        _render_dim_mode(proj, theme, style_key)

    # ----- Confirm -----
    st.markdown("---")
    can_proceed = _can_proceed(proj)
    if st.button("确认，进入下一步 →", type="primary", disabled=not can_proceed):
        proj.current_step = 2
        auto_save(proj)
        st.rerun()


# ---------------------------------------------------------------------------
# Multi-axis sub-renderer
# ---------------------------------------------------------------------------

def _render_axis_mode(proj: TestProject, theme: str, style_key: str) -> None:
    from core.style_prompts import get_style_prompt

    if st.button("生成轴与普通结果", type="primary", disabled=not theme.strip(), key="gen_axes"):
        if not theme.strip():
            st.error("请先输入测试主题")
        else:
            with st.spinner("正在调用 AI 生成维度轴……"):
                from core.ai_service import generate_axes
                try:
                    axes = generate_axes(theme, proj.config.axis_count, get_style_prompt(style_key, "general"))
                    proj.axes = axes
                    st.success(f"成功生成 {len(axes)} 个维度轴！")
                except Exception as e:
                    st.error(f"生成轴失败：{e}")

            if proj.axes:
                with st.spinner("正在调用 AI 生成普通结果……"):
                    from core.ai_service import generate_normal_results
                    try:
                        results = generate_normal_results(
                            proj.axes, proj.config.normal_result_count, theme,
                            style=get_style_prompt(style_key, "result_name"),
                        )
                        proj.normal_results = results
                        st.success(f"成功生成 {len(results)} 个普通结果！")
                    except Exception as e:
                        st.error(f"生成普通结果失败：{e}")

    if proj.axes:
        st.markdown("### 维度轴")
        for i, axis in enumerate(proj.axes):
            cols = st.columns([1, 3, 3, 5, 1])
            cols[0].markdown(f"**{axis.id}**")
            new_left = cols[1].text_input(
                "左端", value=axis.left_name, key=f"ax_l_{i}", label_visibility="collapsed",
            )
            new_right = cols[2].text_input(
                "右端", value=axis.right_name, key=f"ax_r_{i}", label_visibility="collapsed",
            )
            cols[3].markdown(f"_{axis.description}_")
            if cols[4].button("🔄", key=f"regen_axis_{i}"):
                with st.spinner(f"重新生成轴 {axis.id}……"):
                    from core.ai_service import generate_axes
                    try:
                        new_axes = generate_axes(proj.config.theme, 1, get_style_prompt(style_key, "general"))
                        if new_axes:
                            na = new_axes[0]
                            na.id = axis.id
                            proj.axes[i] = na
                            st.rerun()
                    except Exception as e:
                        st.error(f"重新生成失败：{e}")
            if new_left != axis.left_name:
                proj.axes[i].left_name = new_left
            if new_right != axis.right_name:
                proj.axes[i].right_name = new_right

    if proj.normal_results:
        st.markdown("### 普通结果")
        for i, result in enumerate(proj.normal_results):
            ref_label = f" → {result.reference_name}" if result.reference_name else ""
            with st.expander(f"{result.id}: {result.name}{ref_label}"):
                new_name = st.text_input("抽象名称", value=result.name, key=f"res_name_{i}")
                if new_name != result.name:
                    proj.normal_results[i].name = new_name
                rc1, rc2 = st.columns(2)
                with rc1:
                    new_ref = st.text_input("角色对标", value=result.reference_name or "", key=f"res_ref_{i}")
                    if new_ref != (result.reference_name or ""):
                        proj.normal_results[i].reference_name = new_ref or None
                with rc2:
                    new_src = st.text_input("出处", value=result.reference_source or "", key=f"res_src_{i}")
                    if new_src != (result.reference_source or ""):
                        proj.normal_results[i].reference_source = new_src or None
                st.text_area("描述", value=result.description, key=f"res_desc_{i}", disabled=True)
                combo_str = ", ".join(
                    f"{aid}: {'→' if d > 0 else '←'}" for aid, d in result.dimension_combo.items()
                )
                st.markdown(f"**维度组合**：{combo_str}")
                # image upload
                uploaded = st.file_uploader(
                    "上传形象图", type=["png", "jpg", "jpeg", "webp"],
                    key=f"img_res_{i}",
                )
                if uploaded is not None:
                    img_path = _save_uploaded_image(uploaded, result.id)
                    proj.normal_results[i].image_path = str(img_path)
                    st.image(str(img_path), width=200)
                elif result.image_path and Path(result.image_path).exists():
                    st.image(result.image_path, width=200)


# ---------------------------------------------------------------------------
# Multi-dimension sub-renderer
# ---------------------------------------------------------------------------

def _render_dim_mode(proj: TestProject, theme: str, style_key: str) -> None:
    from core.style_prompts import get_style_prompt

    if st.button("生成维度与结果原型", type="primary", disabled=not theme.strip(), key="gen_dims"):
        if not theme.strip():
            st.error("请先输入测试主题")
        else:
            with st.spinner("正在调用 AI 生成维度……"):
                from core.ai_service import generate_dimensions
                try:
                    dims = generate_dimensions(theme, proj.config.dimension_count, get_style_prompt(style_key, "general"))
                    proj.dimensions = dims
                    st.success(f"成功生成 {len(dims)} 个维度！")
                except Exception as e:
                    st.error(f"生成维度失败：{e}")

            if proj.dimensions:
                with st.spinner("正在调用 AI 生成结果原型……"):
                    from core.ai_service import generate_archetypes
                    try:
                        archetypes = generate_archetypes(
                            proj.dimensions, proj.config.archetype_count, theme,
                            style=get_style_prompt(style_key, "result_name"),
                        )
                        proj.archetypes = archetypes
                        st.success(f"成功生成 {len(archetypes)} 个结果原型！")
                    except Exception as e:
                        st.error(f"生成结果原型失败：{e}")

    if proj.dimensions:
        st.markdown("### 维度列表")
        for i, dim in enumerate(proj.dimensions):
            cols = st.columns([2, 2, 2, 4, 1])
            new_name = cols[0].text_input(
                "名称", value=dim.display_name, key=f"dim_dn_{i}", label_visibility="collapsed",
            )
            new_low = cols[1].text_input(
                "低端", value=dim.low_label, key=f"dim_lo_{i}", label_visibility="collapsed",
            )
            new_high = cols[2].text_input(
                "高端", value=dim.high_label, key=f"dim_hi_{i}", label_visibility="collapsed",
            )
            cols[3].caption(dim.description)
            if cols[4].button("🔄", key=f"regen_dim_{i}"):
                with st.spinner(f"重新生成维度 {dim.id}……"):
                    from core.ai_service import generate_dimensions
                    try:
                        new_dims = generate_dimensions(proj.config.theme, 1, get_style_prompt(style_key, "general"))
                        if new_dims:
                            nd = new_dims[0]
                            nd.id = dim.id
                            proj.dimensions[i] = nd
                            st.rerun()
                    except Exception as e:
                        st.error(f"重新生成失败：{e}")
            if new_name != dim.display_name:
                proj.dimensions[i].display_name = new_name
            if new_low != dim.low_label:
                proj.dimensions[i].low_label = new_low
            if new_high != dim.high_label:
                proj.dimensions[i].high_label = new_high

    if proj.archetypes:
        st.markdown("### 结果原型")
        for i, arch in enumerate(proj.archetypes):
            ref_label = f" → {arch.reference_name}" if arch.reference_name else ""
            with st.expander(f"{arch.id}: {arch.name}{ref_label}"):
                new_name = st.text_input("抽象名称", value=arch.name, key=f"arch_name_{i}")
                if new_name != arch.name:
                    proj.archetypes[i].name = new_name
                ac1, ac2 = st.columns(2)
                with ac1:
                    new_ref = st.text_input("角色对标", value=arch.reference_name or "", key=f"arch_ref_{i}")
                    if new_ref != (arch.reference_name or ""):
                        proj.archetypes[i].reference_name = new_ref or None
                with ac2:
                    new_src = st.text_input("出处", value=arch.reference_source or "", key=f"arch_src_{i}")
                    if new_src != (arch.reference_source or ""):
                        proj.archetypes[i].reference_source = new_src or None
                st.text_area("描述", value=arch.description, key=f"arch_desc_{i}", disabled=True)
                vec_str = ", ".join(f"{k}: {v:+.1f}" for k, v in arch.vector.items())
                st.markdown(f"**原型向量**：{vec_str}")
                # image upload
                uploaded = st.file_uploader(
                    "上传形象图", type=["png", "jpg", "jpeg", "webp"],
                    key=f"img_arch_{i}",
                )
                if uploaded is not None:
                    img_path = _save_uploaded_image(uploaded, arch.id)
                    proj.archetypes[i].image_path = str(img_path)
                    st.image(str(img_path), width=200)
                elif arch.image_path and Path(arch.image_path).exists():
                    st.image(arch.image_path, width=200)


def _save_uploaded_image(uploaded_file, result_id: str) -> Path:
    """Save an uploaded image to the local images directory."""
    _IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    ext = Path(uploaded_file.name).suffix or ".png"
    dest = _IMAGES_DIR / f"{result_id}{ext}"
    dest.write_bytes(uploaded_file.getvalue())
    return dest


def _can_proceed(proj: TestProject) -> bool:
    if proj.config.mode == TestMode.MULTI_AXIS:
        return bool(proj.axes and proj.normal_results)
    return bool(proj.dimensions and proj.archetypes)
