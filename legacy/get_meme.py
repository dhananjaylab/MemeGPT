import json
import os
from pathlib import Path
from typing import TypedDict

from dotenv import load_dotenv
from openai import OpenAI

from load_meme_data import MemeData, load_meme_data, load_meme_data_flat_string
from meme_image_editor import overlay_text_on_image
from system_instructions import get_system_instructions


class MemeGPTOutput(TypedDict):
    meme_id: int
    meme_name: str
    meme_text: list[str]


load_dotenv()

CLIENT = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MEME_DATA_TEXT = load_meme_data_flat_string() 
SYSTEM_MESSAGE = {
    "role": "system",
    "content": [
        {
            "type": "text", 
            "text": get_system_instructions(MEME_DATA_TEXT),
        }
    ],
}


def call_chatgpt(user_message):
    response = CLIENT.chat.completions.create(
        model="gpt-4o",
        messages=[SYSTEM_MESSAGE, user_message], # type: ignore
        temperature=1,
        max_tokens=2048,
        response_format={"type": "json_object"},
    )
    return response.choices[0].message.content


def generate_memes(user_input: str) -> list[str] | None:
    user_message = {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": user_input,
            }
        ],
    }
    response = call_chatgpt(user_message)
    print(response)

    if not response:
        print("No response from the model, something went wrong.")
        return
    
    try:
        meme_output: list[MemeGPTOutput] = json.loads(response)['output']
    except json.JSONDecodeError:
        print("Invalid response from the model.")
        return
    
    meme_data: list[MemeData] = load_meme_data()
    images = []
    for ai_meme in meme_output:
        chosen_meme_index = int(ai_meme["meme_id"])
        print(f"MemeGPT chose the meme: {meme_data[chosen_meme_index]['name']}")
        print(f"Meme text: {ai_meme['meme_text']}")
        image_path: Path = overlay_text_on_image(meme_data[chosen_meme_index], ai_meme["meme_text"])
        images.append(str(image_path))
    return images


if __name__ == "__main__":
    print("Welcome to the meme generator!")
    print("You can provide a situation or a topic to generate a meme.")
    generate_memes(user_input=input("Please provide a topic or situation: "))