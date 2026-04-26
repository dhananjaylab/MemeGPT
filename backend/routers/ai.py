from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from models.models import User
from services.auth import get_current_user_optional
from services.meme_ai import (
    generate_meme_captions_with_gemini, 
    generate_meme_captions,
    AIProvider
)
from core.config import settings

router = APIRouter()


class AISuggestRequest(BaseModel):
    """Request for AI-generated meme suggestions"""
    prompt: str
    provider: Optional[str] = None  # "openai", "gemini", or None for default


class AIMemeOption(BaseModel):
    """Individual meme option from AI"""
    meme_id: int
    meme_name: str
    meme_text: List[str]
    reasoning: Optional[str] = None


class AISuggestResponse(BaseModel):
    """Response with AI-generated suggestions"""
    options: List[AIMemeOption]
    provider_used: str
    note: Optional[str] = None


@router.post("/suggest", response_model=AISuggestResponse)
async def get_ai_suggestions(
    request: Request,
    body: AISuggestRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Get AI-generated meme suggestions for a prompt.
    
    This is a backend proxy endpoint for Gemini API calls (secure, no exposed keys).
    For development, you can use this with either OpenAI or Gemini.
    
    Args:
        prompt: User's natural language prompt for meme generation
        provider: Optional provider override ("openai" or "gemini")
    
    Returns:
        List of meme suggestions with template IDs and captions
    """
    
    # Validate prompt
    if not body.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")
    
    if len(body.prompt) > 1000:
        raise HTTPException(status_code=400, detail="Prompt too long (max 1000 characters)")
    
    # Determine provider
    provider = body.provider or settings.ai_provider
    provider = provider.lower()
    
    # Validate provider availability
    if provider == AIProvider.GEMINI.value:
        if not settings.has_gemini:
            raise HTTPException(
                status_code=503, 
                detail="Gemini AI provider not configured. Please set GEMINI_API_KEY."
            )
        generator = generate_meme_captions_with_gemini
    elif provider == AIProvider.OPENAI.value:
        if not settings.has_openai:
            raise HTTPException(
                status_code=503,
                detail="OpenAI provider not configured. Please set OPENAI_API_KEY."
            )
        generator = generate_meme_captions
    else:
        # Default based on config
        if settings.has_openai:
            generator = generate_meme_captions
            provider = AIProvider.OPENAI.value
        elif settings.has_gemini:
            generator = generate_meme_captions_with_gemini
            provider = AIProvider.GEMINI.value
        else:
            raise HTTPException(
                status_code=503,
                detail="No AI provider configured. Please set OPENAI_API_KEY or GEMINI_API_KEY."
            )
    
    # Generate suggestions
    try:
        suggestions = await generator(body.prompt)
        if not suggestions:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate suggestions using {provider} provider"
            )
        
        # Convert to response format
        options = []
        for suggestion in suggestions:
            options.append(AIMemeOption(
                meme_id=suggestion.get("meme_id"),
                meme_name=suggestion.get("meme_name"),
                meme_text=suggestion.get("meme_text", []),
                reasoning=suggestion.get("reasoning")
            ))
        
        return AISuggestResponse(
            options=options,
            provider_used=provider,
            note="AI-generated suggestions. Select one to refine or generate directly."
        )
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error generating suggestions: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generating suggestions: {str(e)}"
        )


@router.get("/status")
async def get_ai_status():
    """
    Get status of available AI providers and their configurations.
    Useful for frontend to determine which features are available.
    """
    return {
        "openai": {
            "available": settings.has_openai,
            "provider": "openai"
        },
        "gemini": {
            "available": settings.has_gemini,
            "provider": "gemini"
        },
        "default_provider": settings.ai_provider,
        "environment": settings.environment
    }
