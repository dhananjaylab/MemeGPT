import json
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from ..core.config import settings
from pathlib import Path

# Initialize OpenAI client
openai_client = AsyncOpenAI(api_key=settings.openai_api_key)

ROOT_DIRECTORY = Path(__file__).resolve().parent.parent.parent

def load_meme_data_from_json() -> str:
    """Load meme template data of the public/meme_data.json"""
    meme_data_path = ROOT_DIRECTORY / "public" / "meme_data.json"
    with open(meme_data_path, "r", encoding="utf-8") as file:
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

Example output:
{{
    "output": [
        {{
            "meme_id": 6,
            "meme_name": "Hide the Pain Harold",
            "meme_text": [
                "Ate all the chocolate.",
                "Realized now I have nothing for dessert."
            ]
        }},
        ... (2 more options)
    ]
}}
"""
    return SYSTEM_INSTRUCTIONS_TEMPLATE.format(meme_data_text=meme_data_text)

async def generate_meme_captions(user_prompt: str) -> Optional[List[Dict[str, Any]]]:
    """Call OpenAI GPT-4o to generate meme content"""
    meme_data_text = load_meme_data_from_json()
    system_message = get_system_instructions(meme_data_text)
    
    try:
        response = await openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_prompt}
            ],
            temperature=1,
            max_tokens=2048,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        if not content:
            return None
            
        data = json.loads(content)
        return data.get("output", [])
    except Exception as e:
        print(f"Error calling OpenAI: {e}")
        return None
