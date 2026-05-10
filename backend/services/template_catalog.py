from __future__ import annotations

from pathlib import Path
from typing import Any


BACKEND_ROOT = Path(__file__).resolve().parent.parent
FRAMES_DIR = BACKEND_ROOT / "public" / "frames"


def local_frame_exists(file_path: str | None) -> bool:
    return bool(file_path) and (FRAMES_DIR / file_path).is_file()


def template_source(template_data: dict[str, Any]) -> str:
    if local_frame_exists(template_data.get("file_path")):
        return "local"
    if template_data.get("imgflip_id"):
        return "imgflip"
    return "database"


def template_image_url(template_data: dict[str, Any]) -> str | None:
    file_path = template_data.get("file_path")
    if local_frame_exists(file_path):
        return f"/frames/{file_path}"
    return template_data.get("fallback_url")


def build_template_fields(template_data: dict[str, Any]) -> dict[str, Any]:
    image_url = template_image_url(template_data)
    source = template_source(template_data)
    box_count = template_data.get("box_count") or template_data["number_of_text_fields"]

    return {
        "name": template_data["name"],
        "alternative_names": template_data.get("alternative_names", []),
        "file_path": template_data.get("file_path") or "",
        "font_path": template_data.get("font_path", "impact.ttf"),
        "text_color": template_data.get("text_color", "white"),
        "text_stroke": template_data.get("text_stroke", True),
        "usage_instructions": template_data["usage_instructions"],
        "number_of_text_fields": template_data["number_of_text_fields"],
        "text_coordinates_xy_wh": template_data["text_coordinates_xy_wh"],
        "text_coordinates": template_data["text_coordinates_xy_wh"],
        "example_output": template_data.get("example_output", []),
        "image_url": image_url,
        "preview_image_url": image_url,
        "fallback_url": template_data.get("fallback_url"),
        "source": source,
        "imgflip_id": str(template_data["imgflip_id"]) if template_data.get("imgflip_id") else None,
        "box_count": box_count if source == "imgflip" else None,
        "gen_z_ready": True,
        "vibe_tags": template_data.get("vibe_tags"),
    }

