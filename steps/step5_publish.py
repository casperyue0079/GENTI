"""Step 5 – Save, export and publish."""
from __future__ import annotations

import json

import streamlit as st

from core.models import TestProject
from core.storage import auto_save, save_as


def render(proj: TestProject) -> None:
    st.header("步骤 5：保存与发布")

    st.markdown("---")

    col1, col2, col3 = st.columns(3)

    # --- Save ---
    with col1:
        st.markdown("#### 保存项目")
        save_name = st.text_input(
            "项目名称", value=proj.config.theme or "test", key="save_name",
        )
        if st.button("保存到本地"):
            try:
                p = save_as(proj, save_name)
                st.success(f"已保存至 `{p}`")
            except Exception as e:
                st.error(f"保存失败：{e}")

    # --- Export static site ---
    with col2:
        st.markdown("#### 导出静态网站")
        if st.button("导出静态文件"):
            from core.exporter import export_static
            try:
                out_dir = export_static(proj)
                st.success(f"已导出至 `{out_dir}`")
            except Exception as e:
                st.error(f"导出失败：{e}")

    # --- Publish ---
    with col3:
        st.markdown("#### 发布到 GitHub Pages")
        st.caption("发布前会先用**当前编辑器中的项目**重新导出到 `output/`，再上传，与步骤 4 预览一致。")
        if st.button("发布"):
            from core.exporter import export_static
            from core.publisher import publish_to_github_pages
            with st.spinner("正在导出并发布到 GitHub Pages……"):
                try:
                    export_static(proj)
                    url = publish_to_github_pages()
                    st.success("发布成功！（已按当前项目重新导出）")
                    st.markdown(f"[点击访问]({url})")
                except Exception as e:
                    st.error(f"发布失败：{e}")

    st.markdown("---")
    st.markdown("#### 下载项目 JSON")
    json_data = proj.model_dump_json(indent=2)
    st.download_button(
        "下载 JSON",
        data=json_data,
        file_name=f"{proj.config.theme or 'test'}_project.json",
        mime="application/json",
    )

    # navigation
    st.markdown("---")
    if st.button("← 上一步"):
        proj.current_step = 4
        st.rerun()
