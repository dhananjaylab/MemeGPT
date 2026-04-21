import textwrap
from pathlib import Path
from typing import List, Dict, Any, Union
from uuid import uuid4
from PIL import Image, ImageDraw, ImageFont

# Constants
ROOT_DIRECTORY = Path(__file__).resolve().parent.parent.parent
IMAGE_FOLDER = ROOT_DIRECTORY / "public" / "frames"
FONT_FOLDER = ROOT_DIRECTORY / "public" / "fonts"
OUTPUT_FOLDER = ROOT_DIRECTORY / "public" / "output"
LINE_HEIGHT_MULTIPLIER = 1.4

def handle_text_caps(font_name: str, text: str) -> str:
    """Handle text capitalization based on font"""
    if font_name == "impact.ttf":
        return text.upper()
    elif font_name == "ComicSansMS.ttf":
        return text.lower()
    return text

def get_char_width_in_px(font: ImageFont.FreeTypeFont, font_name: str) -> int:
    """Get character width in pixels for font sizing"""
    representative_character = handle_text_caps(font_name, "A")
    try:
        char_left_top_right_bottom = font.getbbox(representative_character)
        return char_left_top_right_bottom[2] - char_left_top_right_bottom[0]
    except (AttributeError, OSError):
        return 10  # Default character width

def get_unique_filename() -> Path:
    """Generate unique filename for output image"""
    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    return OUTPUT_FOLDER / f"{uuid4()}.png"

def calculate_text_height(
    drawing: ImageDraw.ImageDraw, lines: List[str], font: ImageFont.FreeTypeFont
) -> int:
    """Calculate total text height for multiple lines"""
    total_text_height = 0
    for line in lines:
        bbox_for_line = drawing.textbbox((0, 0), line, font=font)
        bbox_top = bbox_for_line[1]
        bbox_bottom = bbox_for_line[3]
        total_text_height += bbox_bottom - bbox_top
    return int(total_text_height * LINE_HEIGHT_MULTIPLIER)

def overlay_text_on_image(meme: Dict[str, Any], texts: List[str]) -> Path:
    """Create meme image by overlaying text on template"""
    font_name: str = meme["font_path"]
    texts = [handle_text_caps(font_name, text) for text in texts]
    image_path: Path = IMAGE_FOLDER / meme["file_path"]
    font_file: str = str(FONT_FOLDER / font_name)
    bounding_boxes: List[List[int]] = meme["text_coordinates_xy_wh"]

    if not image_path.exists():
        raise FileNotFoundError(f"Template image not found: {image_path}")

    with Image.open(image_path) as img:
        draw = ImageDraw.Draw(img)

        for bounding_box, text in zip(bounding_boxes, texts):
            x, y, box_width, box_height = bounding_box
            font_size = 8
            
            try:
                font = ImageFont.truetype(font_file, font_size)
            except (OSError, IOError):
                font = ImageFont.load_default()
            
            char_width = get_char_width_in_px(font, font_name)
            wrap_width = max(1, box_width // char_width)
            lines = textwrap.wrap(text, break_long_words=False, width=wrap_width)
            total_text_height = calculate_text_height(draw, lines, font)

            while total_text_height < box_height and all(draw.textbbox((0, 0), line, font=font)[2] < box_width for line in lines):
                font_size += 1
                try:
                    font = ImageFont.truetype(font_file, font_size)
                except (OSError, IOError):
                    font = ImageFont.load_default()
                
                char_width = get_char_width_in_px(font, font_name)
                wrap_width = max(1, box_width // char_width)
                lines = textwrap.wrap(text, break_long_words=False, width=wrap_width)
                total_text_height = calculate_text_height(draw, lines, font)

            font_size -= 1
            try:
                font = ImageFont.truetype(font_file, font_size)
            except (OSError, IOError):
                font = ImageFont.load_default()
                
            char_width = get_char_width_in_px(font, font_name)
            wrap_width = max(1, box_width // char_width)
            lines = textwrap.wrap(text, break_long_words=False, width=wrap_width)
            total_text_height = calculate_text_height(draw, lines, font)
            
            text_y = y + (box_height - total_text_height) / 2

            for line in lines:
                bbox = draw.textbbox((0, 0), line, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                text_x = x + (box_width - text_width) / 2

                text_stroke = meme.get("text_stroke", False)
                text_draw_settings = {
                    "xy": (text_x, text_y),
                    "text": line,
                    "font": font,
                    "fill": meme["text_color"],
                }

                if text_stroke:
                    stroke_width = max(1, get_char_width_in_px(font, font_name) // 6)
                    text_draw_settings["stroke_width"] = stroke_width
                    text_draw_settings["stroke_fill"] = "black" if meme["text_color"].lower() == "white" else "white"

                draw.text(**text_draw_settings)
                text_y += text_height * LINE_HEIGHT_MULTIPLIER

        output_path = get_unique_filename()
        img.save(output_path)

    return output_path
