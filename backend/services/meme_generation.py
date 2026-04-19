import json
import os
import textwrap
from pathlib import Path
from typing import List, Dict, Any, Optional, TypedDict
from uuid import uuid4

from openai import AsyncOpenAI
from PIL import Image, ImageDraw, ImageFont
import boto3
from botocore.exceptions import ClientError

from ..core.config import settings


class MemeGPTOutput(TypedDict):
    meme_id: int
    meme_name: str
    meme_text: List[str]


class MemeData(TypedDict):
    id: int
    name: str
    alternative_names: List[str]
    file_path: str
    font_path: str
    text_color: str
    text_stroke: bool
    usage_instructions: str
    number_of_text_fields: int
    text_coordinates_xy_wh: List[List[int]]
    example_output: List[str]


# Initialize OpenAI client
openai_client = AsyncOpenAI(api_key=settings.openai_api_key)

# Initialize R2 client
r2_client = boto3.client(
    's3',
    endpoint_url=settings.r2_endpoint_url,
    aws_access_key_id=settings.r2_access_key,
    aws_secret_access_key=settings.r2_secret_key,
    region_name='auto'
) if settings.r2_access_key else None

# Constants
ROOT_DIRECTORY = Path(__file__).resolve().parent.parent.parent
IMAGE_FOLDER = ROOT_DIRECTORY / "templates"
FONT_FOLDER = ROOT_DIRECTORY / "fonts"
OUTPUT_FOLDER = ROOT_DIRECTORY / "output"
LINE_HEIGHT_MULTIPLIER = 1.4


def load_meme_data() -> List[MemeData]:
    """Load meme template data from JSON file"""
    meme_data_path = ROOT_DIRECTORY / "meme_data.json"
    with open(meme_data_path, "r") as file:
        meme_data: List[dict] = json.load(file)
    return [MemeData(**meme) for meme in meme_data]


def load_meme_data_flat_string() -> str:
    """Load meme data as flat string for system instructions"""
    meme_data_path = ROOT_DIRECTORY / "meme_data.json"
    with open(meme_data_path, "r") as file:
        return file.read()


def get_system_instructions(meme_data_text: str) -> str:
    """Generate system instructions for OpenAI"""
    SYSTEM_INSTRUCTIONS_TEMPLATE = """
You are a meme-generating robot. You will receive a situation or simply some text from the user. If the user describes a situation or even a whole story, use the main situation or topic as much as possible for the meme. If the user simply provides very simple text or even a single word, use the topic to generate a meme.

You can use the following meme templates: {meme_data_text}. It is your job to choose one of these templates and then generate the meme based on the user's input. Your output will be in line with the meme template you choose, so if it has 2 example sentences, you should generate 2 sentences, just like the example. Make sure your example also follows the meme template example sentence structure, so do not suddenly use very long sentences or a different structure.

Provide your output in the form of a valid JSON object with the following keys and values:
meme_id: The ID of the meme template you chose.
meme_name: The name of the meme template you chose.
meme_text: The text you generated, matching the structure of the example, as a list of texts. Stick to the same number of texts as instructed in the meme template data.

I want to have 3 options in the output object, each using a different meme template, so you will provide the above output 3 times wrapped in a JSON list.

Example user input:
I ate all the chocolate.

Example output:
{example_output}
"""

    EXAMPLE_OUTPUT = """
{
    "output": [
        {
            "meme_id": 6,
            "meme_name": "Hide the Pain Harold",
            "meme_text": [
                "Ate all the chocolate.",
                "Realized now I have nothing for dessert."
            ]
        },
        {
            "meme_id": 7,
            "meme_name": "Success Kid",
            "meme_text": [
                "Found the last chocolate bar in the pantry.",
                "Ate it all by myself!"
            ]
        },
        {
            "meme_id": 0,
            "meme_name": "Drake Hotline Bling Meme",
            "meme_text": [
                "Sharing the chocolate.",
                "Eating all the chocolate myself."
            ]
        }
    ]
}
"""

    return SYSTEM_INSTRUCTIONS_TEMPLATE.format(
        meme_data_text=meme_data_text, 
        example_output=EXAMPLE_OUTPUT
    )


async def call_chatgpt(user_message: str) -> Optional[str]:
    """Call OpenAI GPT-4o to generate meme content"""
    meme_data_text = load_meme_data_flat_string()
    system_message = get_system_instructions(meme_data_text)
    
    try:
        response = await openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            temperature=1,
            max_tokens=2048,
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error calling OpenAI: {e}")
        return None


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
        # Fallback for default fonts or font loading issues
        return 10  # Default character width


def get_unique_filename() -> Path:
    """Generate unique filename for output image"""
    OUTPUT_FOLDER.mkdir(exist_ok=True)
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


async def upload_to_r2(file_path: Path, object_key: str) -> Optional[str]:
    """Upload image to Cloudflare R2 and return public URL"""
    if not r2_client:
        return None
        
    try:
        # Use asyncio to run the synchronous file operation in a thread
        import asyncio
        
        def _upload_file():
            with open(file_path, 'rb') as file:
                r2_client.upload_fileobj(
                    file,
                    settings.r2_bucket_name,
                    object_key,
                    ExtraArgs={'ContentType': 'image/png'}
                )
        
        # Run the upload in a thread to avoid blocking
        await asyncio.get_event_loop().run_in_executor(None, _upload_file)
        
        # Return public URL
        return f"{settings.r2_public_url}/{object_key}"
    except ClientError as e:
        print(f"Error uploading to R2: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error uploading to R2: {e}")
        return None


def overlay_text_on_image(meme: MemeData, texts: List[str]) -> Path:
    """Create meme image by overlaying text on template"""
    font_name: str = meme["font_path"]
    texts = [handle_text_caps(font_name, text) for text in texts]
    image_path: Path = IMAGE_FOLDER / meme["file_path"]
    font_file: str = str(FONT_FOLDER / font_name)
    bounding_boxes: List[List[int]] = meme["text_coordinates_xy_wh"]

    # Check if image exists
    if not image_path.exists():
        raise FileNotFoundError(f"Template image not found: {image_path}")

    with Image.open(image_path) as img:
        draw = ImageDraw.Draw(img)

        for bounding_box, text in zip(bounding_boxes, texts):
            x, y, box_width, box_height = bounding_box

            font_size = 8
            
            # Try to load the font, fall back to default if not available
            try:
                font = ImageFont.truetype(font_file, font_size)
            except (OSError, IOError):
                print(f"Warning: Font {font_name} not found, using default font")
                try:
                    # Try to use a system default font
                    font = ImageFont.load_default()
                except:
                    # If all else fails, create a minimal font
                    font = ImageFont.load_default()
            
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
                try:
                    font = ImageFont.truetype(font_file, font_size)
                except (OSError, IOError):
                    # If font loading fails, keep using the default font
                    font = ImageFont.load_default()
                lines = textwrap.wrap(
                    text,
                    break_long_words=False,
                    width=box_width // get_char_width_in_px(font, font_name),
                )
                total_text_height = calculate_text_height(draw, lines, font)

            font_size -= 1
            try:
                font = ImageFont.truetype(font_file, font_size)
            except (OSError, IOError):
                font = ImageFont.load_default()
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


async def generate_memes(user_input: str) -> Optional[List[Dict[str, Any]]]:
    """Generate memes from user input - main function"""
    try:
        # Call OpenAI to generate meme content
        response = await call_chatgpt(user_input)
        print(f"OpenAI response: {response}")

        if not response:
            print("No response from the model, something went wrong.")
            return None
        
        try:
            meme_output: List[MemeGPTOutput] = json.loads(response)['output']
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Invalid response from the model: {e}")
            return None
        
        meme_data: List[MemeData] = load_meme_data()
        generated_memes = []
        
        for ai_meme in meme_output:
            try:
                chosen_meme_index = int(ai_meme["meme_id"])
                if chosen_meme_index >= len(meme_data):
                    print(f"Invalid meme ID: {chosen_meme_index}")
                    continue
                    
                chosen_meme = meme_data[chosen_meme_index]
                print(f"MemeGPT chose the meme: {chosen_meme['name']}")
                print(f"Meme text: {ai_meme['meme_text']}")
                
                # Validate meme text count matches template requirements
                expected_fields = chosen_meme["number_of_text_fields"]
                if len(ai_meme["meme_text"]) != expected_fields:
                    print(f"Warning: Meme text field count mismatch. Expected {expected_fields}, got {len(ai_meme['meme_text'])}")
                    # Pad or truncate as needed
                    if len(ai_meme["meme_text"]) < expected_fields:
                        ai_meme["meme_text"].extend([""] * (expected_fields - len(ai_meme["meme_text"])))
                    else:
                        ai_meme["meme_text"] = ai_meme["meme_text"][:expected_fields]
                
                # Generate image
                image_path: Path = overlay_text_on_image(chosen_meme, ai_meme["meme_text"])
                
                # Upload to R2 if configured
                image_url = None
                if r2_client:
                    object_key = f"memes/{uuid4()}.png"
                    image_url = await upload_to_r2(image_path, object_key)
                
                # If R2 upload failed or not configured, use local path
                if not image_url:
                    image_url = f"/static/output/{image_path.name}"
                
                generated_memes.append({
                    "id": str(uuid4()),
                    "template_id": chosen_meme_index,
                    "template_name": chosen_meme["name"],
                    "meme_text": ai_meme["meme_text"],
                    "image_url": image_url,
                    "local_path": str(image_path)
                })
                
            except Exception as e:
                print(f"Error generating meme: {e}")
                continue
        
        return generated_memes if generated_memes else None
        
    except Exception as e:
        print(f"Error in generate_memes: {e}")
        return None