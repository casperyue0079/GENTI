# GENTI — 主题人格测试生成器

GENTI 是一个本地运行的主题人格测试生成器。它允许创作者通过可视化界面生成类似 MBTI / SBTI 风格的人格测试，自定义测试主题、维度或轴、普通结果与稀有结果，并将最终测试导出为可公开访问的静态网页。

生成作品概览：https://casperyue0079.github.io/beatles-test/ （披头士主题）
             https://casperyue0079.github.io/evati/ （eva主题）

---

## 使用概览
<img width="1315" height="379" alt="image" src="https://github.com/user-attachments/assets/62ac2058-04d1-4eb5-af39-7c5ba631a055" />

使用前需先使用修改config.example.yaml文件为真实api和token，并修改文件名为config.yaml，然后即可参考下文的部署与运行方案


<img width="2435" height="1131" alt="image" src="https://github.com/user-attachments/assets/3fb14e82-916d-4ff1-b766-46902da81c95" />
PAGE1负责指定题目的基础框架如

测试主题：任意领域或梗，例如乐队、剧集、恋爱等。
题目风格：严肃 / 幽默 / 自定义（自定义会作为一整段 prompt 交给模型）。
测试模式（二选一）：
多向轴：每题 5 档量表，按各轴计分，用「轴上的倾向组合」匹配 普通结果（偏传统量表）。
多维度：每题 3 个情景选项，选项带对各维度的加减分，先算维度分，再和 结果原型 的向量匹配（偏情景选择题）。
设置轴数/维度数等后，点 生成 得到轴或维度 + 普通结果/原型；可改文案、上传形象图。
结果命名方式：抽象名 / 角色对标 / 两者兼用。

<img width="2285" height="1155" alt="image" src="https://github.com/user-attachments/assets/cdefc067-41ec-48b2-947b-9df365347f76" />
生成后可以对名进行自定义，并上传形象图

<img width="2418" height="706" alt="image" src="https://github.com/user-attachments/assets/690eae39-14a5-4c76-a7fe-5a306c2810bb" />

PAGE2负责指定稀有结果（多向轴为稀有结果，多维度为稀有标签）
可关闭「加入稀有结果」。
系统生成：由模型自动生成；稀有标签会参考步骤 1 的原型，并尽量不要和主原型对标人物重复（仍可能偶发重复，可改用下面一种方式）。
指定角色或形容词：你填「人物/角色 + 气质词」，由模型推断触发规则和文案。
支持 上传形象图；重新生成/重新推断 后界面会与数据对齐（已处理 Streamlit 输入框缓存问题）。

<img width="2385" height="542" alt="image" src="https://github.com/user-attachments/assets/49bd9bd0-77fc-4f98-a039-78e635e35391" />

PAGE3为生成结果题目页，生成后的题目可自定义编辑

<img width="2471" height="990" alt="image" src="https://github.com/user-attachments/assets/76832061-4a67-4f70-aa8d-96de5f735522" />
PAGE4为预览测试页
嵌入式预览：交互效果接近最终网页；本地图片在预览里会以 Data URL 内嵌（避免 iframe 无法读本地路径）。
简易预览：Streamlit 原生界面，作备用。

<img width="2380" height="782" alt="image" src="https://github.com/user-attachments/assets/cb6bb3e0-2231-4575-8b40-417114ee28b0" />
PAGE5为发布页
保存到本地：项目 JSON。
导出静态文件：写入 output/（含 index.html 与 images/）。
发布到 GitHub Pages：会 先用当前编辑器里的项目再导出，再上传，避免线上还是旧主题。
配置好 Token 后，若仓库不存在会尝试创建；Pages 需在仓库设置里指向 gh-pages 分支 等（若 API 未成功打开 Pages，需在 GitHub 网页里手动开一次）。

---

## 技术栈

- Python 3.10+（建议）
- [Streamlit](https://streamlit.io/)
- [LLM API]（测试用的gemini 2.5）
- [Pydantic v2](https://docs.pydantic.dev/) · PyYAML · Jinja2 · [PyGithub](https://pygithub.readthedocs.io/)（可选，用于发布）

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
