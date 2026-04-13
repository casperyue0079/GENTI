"""Export a TestProject to a self-contained static website."""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from jinja2 import Template

from core.models import TestMode

if TYPE_CHECKING:
    from core.models import TestProject

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
_OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"


def _image_path_for_payload(path: str | None, *, static_urls: bool) -> str | None:
    """Preview keeps absolute paths; static export uses images/ basename for GitHub Pages."""
    if not path:
        return None
    if not static_urls:
        return path
    p = Path(path)
    try:
        if p.is_file():
            return f"images/{p.name}"
    except OSError:
        pass
    return path


def _flatten_project(project: TestProject, *, static_urls: bool = False) -> dict:
    """Build the minimal JSON payload consumed by engine.js at runtime."""
    mode = project.config.mode

    base: dict = {
        "title": project.config.theme or "人格测试",
        "description": f"一个关于「{project.config.theme}」的主题人格测试",
        "mode": mode.value,
        "naming_mode": project.config.naming_mode.value,
    }

    if mode == TestMode.MULTI_AXIS:
        base["axes"] = [
            {"id": a.id, "left_name": a.left_name, "right_name": a.right_name}
            for a in project.axes
        ]
        base["normal_results"] = [
            {
                "id": r.id,
                "name": r.name,
                "description": r.description,
                "reference_name": r.reference_name,
                "reference_source": r.reference_source,
                "image_path": _image_path_for_payload(r.image_path, static_urls=static_urls),
                "dimension_combo": r.dimension_combo,
            }
            for r in project.normal_results
        ]
        base["rare_results"] = [
            {
                "id": rr.id,
                "name": rr.name,
                "description": rr.description,
                "reference_name": rr.reference_name,
                "reference_source": rr.reference_source,
                "image_path": _image_path_for_payload(rr.image_path, static_urls=static_urls),
                "type": rr.type.value,
                "threshold_conditions": [
                    {"axis_id": c.axis_id, "direction": c.direction, "threshold": c.threshold}
                    for c in rr.threshold_conditions
                ],
                "min_special_hits": rr.min_special_hits,
                "origin": rr.origin,
                "user_seed_character": rr.user_seed_character,
                "user_seed_traits": rr.user_seed_traits,
            }
            for rr in project.rare_results
        ]
        base["questions"] = [
            {
                "id": q.id,
                "text": q.text,
                "options": [{"text": o.text, "value": o.value} for o in q.options],
                "primary_axis_id": q.primary_axis_id,
                "weak_axes": [
                    {"axis_id": w.axis_id, "coefficient": w.coefficient}
                    for w in q.weak_axes
                ],
                "is_special": q.is_special,
                "linked_rare_id": q.linked_rare_id,
            }
            for q in project.questions
        ]
    else:
        base["dimensions"] = [
            {
                "id": d.id,
                "display_name": d.display_name,
                "low_label": d.low_label,
                "high_label": d.high_label,
            }
            for d in project.dimensions
        ]
        base["archetypes"] = [
            {
                "id": a.id,
                "name": a.name,
                "description": a.description,
                "reference_name": a.reference_name,
                "reference_source": a.reference_source,
                "image_path": _image_path_for_payload(a.image_path, static_urls=static_urls),
                "vector": a.vector,
            }
            for a in project.archetypes
        ]
        base["rare_tags"] = [
            {
                "id": rt.id,
                "name": rt.name,
                "description": rt.description,
                "reference_name": rt.reference_name,
                "reference_source": rt.reference_source,
                "image_path": _image_path_for_payload(rt.image_path, static_urls=static_urls),
                "rules": {
                    gate: [
                        {
                            "type": r.type,
                            "dimension": r.dimension,
                            "cluster": r.cluster,
                            "value": r.value,
                        }
                        for r in rules
                    ]
                    for gate, rules in rt.rules.items()
                },
                "origin": rt.origin,
                "user_seed_character": rt.user_seed_character,
                "user_seed_traits": rt.user_seed_traits,
            }
            for rt in project.rare_tags
        ]
        base["questions"] = [
            {
                "id": q.id,
                "stem": q.stem,
                "primary_dimension": q.primary_dimension,
                "secondary_dimensions": q.secondary_dimensions,
                "options": [
                    {"text": o.text, "effects": o.effects} for o in q.options
                ],
                "is_special": q.is_special,
                "special_cluster": q.special_cluster,
            }
            for q in project.dim_questions
        ]

    return base


def export_static(project: TestProject, output_dir: str | Path | None = None) -> str:
    out = Path(output_dir) if output_dir else _OUTPUT_DIR
    out.mkdir(parents=True, exist_ok=True)

    css_text = (_TEMPLATES_DIR / "style.css").read_text(encoding="utf-8")
    js_text = (_TEMPLATES_DIR / "engine.js").read_text(encoding="utf-8")
    html_template_text = (_TEMPLATES_DIR / "test.html").read_text(encoding="utf-8")

    test_data = _flatten_project(project, static_urls=True)
    test_data_json = json.dumps(test_data, ensure_ascii=False, indent=None)

    template = Template(html_template_text)
    html = template.render(
        title=test_data["title"],
        css=css_text,
        js=js_text,
        test_data=test_data_json,
    )

    (out / "index.html").write_text(html, encoding="utf-8")

    # copy result images if any
    _copy_images(project, out)

    return str(out)


def _copy_images(project: TestProject, out: Path) -> None:
    """Copy uploaded result images into the output directory."""
    images_dir = out / "images"

    all_paths: list[str | None] = []
    if project.config.mode == TestMode.MULTI_AXIS:
        all_paths = (
            [r.image_path for r in project.normal_results]
            + [rr.image_path for rr in project.rare_results]
        )
    else:
        all_paths = (
            [a.image_path for a in project.archetypes]
            + [rt.image_path for rt in project.rare_tags]
        )

    has_images = False
    for img_path in all_paths:
        if not img_path:
            continue
        src = Path(img_path)
        if src.exists():
            if not has_images:
                images_dir.mkdir(parents=True, exist_ok=True)
                has_images = True
            shutil.copy2(src, images_dir / src.name)
