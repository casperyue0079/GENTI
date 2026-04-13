import streamlit as st

st.set_page_config(
    page_title="人格测试生成器",
    page_icon="🧩",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Hide the sidebar navigation completely
st.markdown(
    """<style>
    [data-testid="collapsedControl"] { display: none; }
    section[data-testid="stSidebar"] { display: none; }
    </style>""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Initialise / restore project
# ---------------------------------------------------------------------------
if "project" not in st.session_state:
    from core.storage import auto_load
    from core.models import TestProject

    loaded = auto_load()
    st.session_state.project = loaded if loaded is not None else TestProject()

proj = st.session_state.project

# ---------------------------------------------------------------------------
# Top bar: step indicator + project management
# ---------------------------------------------------------------------------
STEP_LABELS = ["基础结构", "稀有结果", "生成题目", "预览测试", "保存发布"]

from core.storage import list_projects, load_project, new_project, save_as

top_cols = st.columns([6, 1, 1])
with top_cols[0]:
    indicators = []
    for i, label in enumerate(STEP_LABELS, start=1):
        if i < proj.current_step:
            indicators.append(f"~~{i}. {label}~~")
        elif i == proj.current_step:
            indicators.append(f"**▶ {i}. {label}**")
        else:
            indicators.append(f"{i}. {label}")
    st.markdown(" → ".join(indicators))

with top_cols[1]:
    if st.button("新建项目", key="btn_new"):
        st.session_state.project = new_project()
        st.rerun()

with top_cols[2]:
    if st.button("读取项目", key="btn_load"):
        st.session_state.show_load_dialog = True

# project load dialog
if st.session_state.get("show_load_dialog", False):
    saved = list_projects()
    lc1, lc2 = st.columns(2)
    with lc1:
        st.markdown("##### 从已保存项目打开")
        if saved:
            names = [s["name"] for s in saved]
            chosen = st.selectbox("选择项目", names, key="open_proj", label_visibility="collapsed")
            if st.button("打开", key="btn_open"):
                match = next((s for s in saved if s["name"] == chosen), None)
                if match:
                    st.session_state.project = load_project(match["path"])
                    st.session_state.show_load_dialog = False
                    st.rerun()
        else:
            st.caption("暂无已保存的项目")
    with lc2:
        st.markdown("##### 从 JSON 文件导入")
        uploaded = st.file_uploader("选择项目 JSON 文件", type=["json"], key="import_json")
        if uploaded is not None:
            import json as _json
            from core.models import TestProject
            try:
                data = _json.loads(uploaded.getvalue().decode("utf-8"))
                st.session_state.project = TestProject.model_validate(data)
                st.session_state.show_load_dialog = False
                st.success("导入成功！")
                st.rerun()
            except Exception as e:
                st.error(f"导入失败：{e}")
    if st.button("取消", key="btn_cancel_load"):
        st.session_state.show_load_dialog = False
        st.rerun()

st.markdown("---")

# ---------------------------------------------------------------------------
# Render current step
# ---------------------------------------------------------------------------
if proj.current_step == 1:
    from steps.step1_skeleton import render
    render(proj)
elif proj.current_step == 2:
    from steps.step2_rare import render
    render(proj)
elif proj.current_step == 3:
    from steps.step3_questions import render
    render(proj)
elif proj.current_step == 4:
    from steps.step4_preview import render
    render(proj)
elif proj.current_step == 5:
    from steps.step5_publish import render
    render(proj)
else:
    st.error(f"未知步骤：{proj.current_step}")
