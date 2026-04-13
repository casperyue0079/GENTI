from __future__ import annotations

import base64
from pathlib import Path

import yaml
from github import Github, GithubException

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"
_OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"


def _load_github_config() -> dict:
    with open(_CONFIG_PATH, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return cfg.get("github", {})


def publish_to_github_pages(output_dir: str | Path | None = None) -> str:
    cfg = _load_github_config()
    token = cfg.get("token", "")
    repo_name = cfg.get("repo", "my-personality-test")

    if not token or token == "ghp_xxx":
        raise ValueError("请在 config.yaml 中配置有效的 GitHub token")

    out = Path(output_dir) if output_dir else _OUTPUT_DIR
    if not (out / "index.html").exists():
        raise FileNotFoundError("请先导出静态文件（output/index.html 不存在）")

    g = Github(token)
    user = g.get_user()

    try:
        repo = user.get_repo(repo_name)
    except GithubException:
        # PyGithub 的 create_repo 不支持 has_pages；Pages 在推送后由 _enable_pages 打开。
        repo = user.create_repo(
            repo_name,
            description="AI-generated personality test",
            auto_init=True,
        )

    branch = "gh-pages"
    try:
        repo.get_branch(branch)
    except GithubException:
        default = repo.get_branch(repo.default_branch)
        repo.create_git_ref(
            ref=f"refs/heads/{branch}",
            sha=default.commit.sha,
        )

    for file_path in out.rglob("*"):
        if file_path.is_file():
            relative = file_path.relative_to(out).as_posix()
            content = file_path.read_bytes()

            try:
                existing = repo.get_contents(relative, ref=branch)
                repo.update_file(
                    path=relative,
                    message=f"Update {relative}",
                    content=content,
                    sha=existing.sha,
                    branch=branch,
                )
            except GithubException:
                repo.create_file(
                    path=relative,
                    message=f"Add {relative}",
                    content=content,
                    branch=branch,
                )

    _enable_pages(repo, branch)

    return f"https://{user.login}.github.io/{repo_name}/"


def _enable_pages(repo, branch: str) -> None:
    """Enable GitHub Pages on the repo via API."""
    try:
        repo._requester.requestJsonAndCheck(
            "POST",
            f"{repo.url}/pages",
            input={"source": {"branch": branch, "path": "/"}},
        )
    except GithubException:
        try:
            repo._requester.requestJsonAndCheck(
                "PUT",
                f"{repo.url}/pages",
                input={"source": {"branch": branch, "path": "/"}},
            )
        except GithubException:
            pass
