import textwrap
from pathlib import Path
from uuid import uuid4

from PIL import Image, ImageDraw, ImageFont

from load_meme_data import MemeData


ROOT_DIRECTORY = Path(__file__).resolve().parent
IMAGE_FOLDER = ROOT_DIRECTORY / "templates"
FONT_FOLDER = ROOT_DIRECTORY / "fonts"
OUTPUT_FOLDER = ROOT_DIRECTORY / "output"
LINE_HEIGHT_MULTIPLIER = 1.4


def handle_text_caps(font_name: str, text: str) -> str:
    if font_name == "impact.ttf":
        return text.upper()
    elif font_name == "ComicSansMS.ttf":
        return text.lower()
    return text


def get_char_width_in_px(font: ImageFont.FreeTypeFont, font_name: str) -> int:
    representative_character = handle_text_caps(font_name, "A")
    char_left_top_right_bottom = font.getbbox(representative_character)
    return char_left_top_right_bottom[2] - char_left_top_right_bottom[0]


def get_unique_filename() -> Path:
    return OUTPUT_FOLDER / f"{uuid4()}.png"


def calculate_text_height(
    drawing, lines: list[str], font: ImageFont.FreeTypeFont
) -> int:
    total_text_height = 0
    for line in lines:
        bbox_for_line = drawing.textbbox((0, 0), line, font=font)
        bbox_top = bbox_for_line[1]
        bbox_bottom = bbox_for_line[3]
        total_text_height += bbox_bottom - bbox_top
    return int(total_text_height * LINE_HEIGHT_MULTIPLIER)


def overlay_text_on_image(meme: MemeData, texts: list[str]) -> Path:
    font_name: str = meme["font_path"]
    texts = [handle_text_caps(font_name, text) for text in texts]
    image_path: Path = IMAGE_FOLDER / meme["file_path"]
    font_file: str = str(FONT_FOLDER / font_name)
    bounding_boxes: list[list[int]] = meme["text_coordinates_xy_wh"]

    with Image.open(image_path) as img:
        draw = ImageDraw.Draw(img)

        for bounding_box, text in zip(bounding_boxes, texts):
            x, y, box_width, box_height = bounding_box

            font_size = 8
            font = ImageFont.truetype(font_file, font_size)
            lines = textwrap.wrap(
                text,
                break_long_words=False,
                width=box_width // get_char_width_in_px(font, font_name),
            )
            total_text_height = calculate_text_height(draw, lines, font)

            def text_height_is_ok():
                return total_text_height < box_height

            def text_width_is_ok():
                return all(
                    draw.textbbox((0, 0), line, font=font)[2] < box_width
                    for line in lines
                )

            while text_height_is_ok() and text_width_is_ok():
                font_size += 1
                font = ImageFont.truetype(font_file, font_size)
                lines = textwrap.wrap(
                    text,
                    break_long_words=False,
                    width=box_width // get_char_width_in_px(font, font_name),
                )
                total_text_height = calculate_text_height(draw, lines, font)

            font_size -= 1
            font = ImageFont.truetype(font_file, font_size)
            lines = textwrap.wrap(
                text,
                break_long_words=False,
                width=box_width // get_char_width_in_px(font, font_name),
            )

            total_text_height = calculate_text_height(draw, lines, font)
            text_y = y + (box_height - total_text_height) / 2

            for line in lines:
                text_width, text_height = draw.textbbox((0, 0), line, font=font)[2:]
                text_x = x + (box_width - text_width) / 2

                text_stroke = meme.get("text_stroke", False)
                text_draw_settings = {
                    "xy": (text_x, text_y),
                    "text": line,
                    "font": font,
                    "fill": meme["text_color"],
                }

                if text_stroke:
                    stroke_width = get_char_width_in_px(font, font_name) // 6
                    text_draw_settings["stroke_width"] = stroke_width
                    text_draw_settings["stroke_fill"] = (
                        "black" if meme["text_color"] == "white" else "white"
                    )

                draw.text(**text_draw_settings)
                text_y += text_height

        image_path = get_unique_filename()
        img.save(image_path)

    print(f"Image saved to {image_path}")
    return image_path


if __name__ == "__main__":
    from load_meme_data import MemeData, load_meme_data

    meme_data: list[MemeData] = load_meme_data()
    chosen_meme = meme_data[4]
    overlay_text_on_image(
        chosen_meme,
        chosen_meme["example_output"]
    )