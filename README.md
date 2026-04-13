# GENTI — 主题人格测试生成器

GENTI 是一个基于 **Streamlit** 的本地工具：用自然语言主题驱动大模型，自动设计维度、结果类型、题目与稀有标签，并导出为**可离线打开的静态网页**，也可一键发布到 **GitHub Pages**。

仓库地址：<https://github.com/casperyue0079/GENTI>

---

## 功能概览

- **两种测试模式**：多向轴（量表题 + 轴得分）与多维度（多选题 effects + 原型匹配）
- **命名模式**：抽象名称、角色对标或两者兼用；内置严肃 / 幽默风格与自定义 Prompt
- **稀有结果 / 稀有标签**：系统生成或「指定角色 + 形容词」由模型推断规则；支持上传形象图
- **步骤化向导**：骨架 → 稀有项 → 题目 → 嵌入式预览（本地图自动内嵌为 Data URL）→ 导出与发布
- **静态导出**：单文件 `index.html`（内联 CSS/JS），便于托管；图片复制到 `output/images/`
- **GitHub Pages**：在配置好 Token 与仓库名后，从应用内推送到 `gh-pages` 分支

---

## 技术栈

- Python 3.10+（建议）
- [Streamlit](https://streamlit.io/)
- [OpenAI兼容 API](https://platform.openai.com/docs/api-reference)（`openai` Python SDK）
- [Pydantic v2](https://docs.pydantic.dev/) · PyYAML · Jinja2 · [PyGithub](https://pygithub.readthedocs.io/)（可选，用于发布）

---

## 目录结构（主要部分）

```text
GENTI/
├── app.py                 # Streamlit 入口
├── config.yaml            # 本地配置（自建，勿提交）
├── config.example.yaml    # 配置模板
├── core/                  # 模型、Prompt、AI调用、导出、校验、发布
├── steps/                 # 各步骤 UI
├── templates/             # 静态站 style.css、engine.js、test.html
├── projects/              # 本地保存的项目 JSON与上传图片（默认部分被 .gitignore）
└── output/                # 导出静态站输出目录（默认忽略）
```

---

## 部署与运行方案

### 一、本地开发运行（推荐先做）

1. **克隆仓库**

   ```bash
   git clone https://github.com/casperyue0079/GENTI.git
   cd GENTI
   ```

2. **创建虚拟环境并安装依赖**

   ```bash
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # macOS / Linux
   source .venv/bin/activate

   pip install -r requirements.txt
   ```

3. **配置 API**

   ```bash
   copy config.example.yaml config.yaml
   # 或: cp config.example.yaml config.yaml
   ```

   编辑 `config.yaml`：填写 `ai.base_url`、`ai.api_key`、`ai.model`（需为你实际使用的兼容 OpenAI 的服务）。

4. **启动应用**

   ```bash
   streamlit run app.py
   ```

   浏览器访问终端中提示的本地地址（通常为 `http://localhost:8501`）。

5. **（可选）GitHub 发布**

   在 `config.yaml` 的 `github` 段填写 Personal Access Token 与目标仓库名；在应用 **步骤 5** 中先 **导出静态文件**，再 **发布**（发布前会按当前项目重新写入 `output/`）。  
   Token 需具备对应仓库的内容写入及 Pages 配置权限；详见 GitHub 文档：[创建个人访问令牌](https://docs.github.com/zh/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token)、[GitHub Pages](https://docs.github.com/zh/pages)。

### 二、仅使用生成好的静态站

在应用内完成 **导出静态文件** 后，将 `output/` 下全部文件（含 `index.html` 与 `images/`）部署到任意静态托管：

- GitHub Pages（根目录或 `gh-pages` 分支）
- Netlify / Cloudflare Pages / 自有 Nginx 等

无需 Python 运行环境即可访问。

### 三、注意事项

- **勿将 `config.yaml` 提交到公开仓库**，其中含密钥；本仓库已通过 `.gitignore` 排除。
- 若曾误提交密钥，请在服务商处**轮换** API Key 与 GitHub Token。
- 嵌入式预览依赖浏览器安全策略，本地图片在预览中会转为 **Data URL**；线上站点使用相对路径 `images/文件名`。

---

## 开源协议

若未另行声明，默认以仓库内许可证文件为准；无许可证文件时请自行补充。

---

## 致谢

交互与视觉参考了常见「爆款人格测试」式静态单页体验；具体实现与数据模型由本项目独立维护。
