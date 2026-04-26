import json
from enum import Enum
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
import google.generativeai as genai
from core.config import settings
from pathlib import Path


class AIProvider(str, Enum):
    """Available AI providers for caption generation"""
    OPENAI = "openai"
    GEMINI = "gemini"
    BOTH = "both"  # Uses both providers and combines results


# Initialize OpenAI client
openai_client = AsyncOpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None

# Initialize Gemini client
if settings.gemini_api_key:
    genai.configure(api_key=settings.gemini_api_key)

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
    if not openai_client:
        print("OpenAI API key not configured")
        return None
    
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


def get_gemini_system_instructions(meme_data_text: str) -> str:
    """Generate system instructions for Gemini AI"""
    SYSTEM_INSTRUCTIONS = f"""You are a meme-generating AI assistant. You will receive a situation or text from the user.

You have access to these meme templates: {meme_data_text}

Your job is to choose appropriate templates and generate meme text that matches the template structure.

Output exactly 3 different meme options as a valid JSON array. Each option must have:
- meme_id: The ID of the chosen template (integer)
- meme_name: The name of the template (string)
- meme_text: Array of text strings matching the template's text field count
- reasoning: Brief explanation of why this template fits the prompt

Generate creative, humorous, and fitting meme captions for the user's prompt. Follow the structure exactly."""
    return SYSTEM_INSTRUCTIONS


async def generate_meme_captions_with_gemini(user_prompt: str) -> Optional[List[Dict[str, Any]]]:
    """Call Google Gemini to generate meme content"""
    if not settings.gemini_api_key:
        print("Gemini API key not configured")
        return None
    
    meme_data_text = load_meme_data_from_json()
    system_message = get_gemini_system_instructions(meme_data_text)
    
    try:
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=system_message,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=2048,
                temperature=1.0,
            )
        )
        
        response = model.generate_content(user_prompt)
        
        if not response.text:
            return None
        
        # Extract JSON from response
        data = json.loads(response.text)
        return data.get("output", [])
    except Exception as e:
        print(f"Error calling Gemini: {e}")
        return None


async def get_caption_generator(provider: str = None):
    """Factory function to get the appropriate caption generator"""
    if provider is None:
        provider = settings.ai_provider
    
    provider = provider.lower()
    
    if provider == AIProvider.GEMINI.value:
        return generate_meme_captions_with_gemini
    elif provider == AIProvider.OPENAI.value:
        return generate_meme_captions
    elif provider == AIProvider.BOTH.value:
        # Return OpenAI as primary, but both are available
        return generate_meme_captions
    else:
        # Default to OpenAI
        return generate_meme_captions
