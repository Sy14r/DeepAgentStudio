"""
Image Generation Tools for AI Agents.

This module provides LangChain-compatible tools for generating images
using AI models like DALL-E. Generated images are stored in session
workspaces and returned with content blocks for multimodal output.

IMPORTANT: Keep in sync with builtin_tools.py!
============================================
The tool definition in `app/utils/builtin_tools.py` (under "DALL-E Image Generation")
contains the UI-facing description and function signature that users see.

If you change:
- Function parameters (name, type, defaults)
- Supported options (sizes, models, etc.)
- Tool behavior or capabilities

You MUST also update the corresponding entry in builtin_tools.py to keep
the frontend UI accurate. The builtin_tools.py definition is what gets
displayed in the Tools management page.
"""
import json
import logging
import base64
import httpx
from typing import List, Optional, Dict, Any
from datetime import datetime

from langchain.tools import StructuredTool, BaseTool
from sqlalchemy.orm import Session as DBSession
from pydantic import BaseModel, Field

from .media_storage import MediaStorageService, get_media_storage_service
from ..models.llm_provider import LLMProviderConfig
from ..encryption import decrypt_api_key

logger = logging.getLogger(__name__)

# Constants
DALLE_API_URL = "https://api.openai.com/v1/images/generations"
DEFAULT_TIMEOUT = 60  # DALL-E can take a while


class DalleImageInput(BaseModel):
    """Input schema for DALL-E image generation."""
    prompt: str = Field(
        description="Text description of the image to generate. Be detailed and specific."
    )
    size: str = Field(
        default="1024x1024",
        description="Image size: '256x256', '512x512', or '1024x1024'"
    )


def create_image_generation_tools(
    db: DBSession,
    session_id: int,
    user_id: int
) -> List[BaseTool]:
    """
    Create image generation tools for a specific session.

    Args:
        db: Database session
        session_id: Session ID for storing generated images
        user_id: User ID for finding LLM provider with OpenAI API key

    Returns:
        List of LangChain-compatible image generation tools
    """
    tools = []

    # Try to create DALL-E tool if OpenAI API key is available
    dalle_tool = _create_dalle_tool(db, session_id, user_id)
    if dalle_tool:
        tools.append(dalle_tool)

    return tools


def _get_openai_api_key(db: DBSession, user_id: int) -> Optional[str]:
    """
    Get OpenAI API key from user's LLM provider configurations.

    Args:
        db: Database session
        user_id: User ID

    Returns:
        Decrypted API key if found, None otherwise
    """
    # Look for an OpenAI provider configuration
    from ..models import LLMProviderConfig

    provider = db.query(LLMProviderConfig).filter(
        LLMProviderConfig.user_id == user_id,
        LLMProviderConfig.provider_type == "openai",
        LLMProviderConfig.is_active == True
    ).first()

    if not provider or not provider.encrypted_api_key:
        return None

    try:
        return decrypt_api_key(provider.encrypted_api_key)
    except Exception as e:
        logger.error(f"Failed to decrypt OpenAI API key: {e}")
        return None


def _create_dalle_tool(
    db: DBSession,
    session_id: int,
    user_id: int
) -> Optional[BaseTool]:
    """
    Create DALL-E image generation tool.

    Args:
        db: Database session
        session_id: Session ID
        user_id: User ID

    Returns:
        DALL-E tool if API key available, None otherwise
    """
    api_key = _get_openai_api_key(db, user_id)
    if not api_key:
        logger.warning("No OpenAI API key found - DALL-E tool not available")
        return None

    media_storage = get_media_storage_service(db)

    def generate_image(
        prompt: str,
        size: str = "1024x1024"
    ) -> str:
        """
        Generate an image using DALL-E 2.

        Args:
            prompt: Description of the image to generate
            size: Image dimensions (256x256, 512x512, 1024x1024)

        Returns:
            JSON with success status, image URL, and content block info
        """
        # Validate parameters
        valid_sizes = ["256x256", "512x512", "1024x1024"]
        if size not in valid_sizes:
            return json.dumps({
                "success": False,
                "error": f"Invalid size. Must be one of: {valid_sizes}"
            }, indent=2)

        try:
            # Call DALL-E API
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": "dall-e-2",
                "prompt": prompt,
                "n": 1,
                "size": size,
                "response_format": "b64_json"  # Get base64 to avoid URL expiration
            }

            logger.info(f"Generating DALL-E image: {prompt[:50]}...")

            with httpx.Client(timeout=DEFAULT_TIMEOUT) as client:
                response = client.post(
                    DALLE_API_URL,
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                data = response.json()

            # Extract image data
            image_data = data.get("data", [{}])[0]
            b64_image = image_data.get("b64_json", "")
            revised_prompt = image_data.get("revised_prompt", prompt)

            if not b64_image:
                return json.dumps({
                    "success": False,
                    "error": "No image data in response"
                }, indent=2)

            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = f"dalle_{timestamp}.png"

            # Parse dimensions from size string
            width, height = map(int, size.split("x"))

            # Save image using media storage service
            media_file = media_storage.save_base64_media(
                session_id=session_id,
                base64_content=b64_image,
                file_name=file_name,
                mime_type="image/png",
                file_metadata={
                    "prompt": prompt,
                    "revised_prompt": revised_prompt,
                    "model": "dall-e-2",
                    "size": size,
                    "width": width,
                    "height": height
                }
            )

            if not media_file:
                return json.dumps({
                    "success": False,
                    "error": "Failed to save generated image"
                }, indent=2)

            logger.info(f"Generated image saved: {media_file.url}")

            # Return success with content block info
            return json.dumps({
                "success": True,
                "message": "Image generated successfully",
                "image": {
                    "url": media_file.url,
                    "file_name": media_file.file_name,
                    "size": size,
                    "width": width,
                    "height": height,
                    "mime_type": "image/png",
                    "file_size": media_file.file_size_bytes
                },
                "prompt": prompt,
                "revised_prompt": revised_prompt,
                "model": "dall-e-2",
                # Content block for multimodal output
                "content_block": {
                    "type": "image",
                    "url": media_file.url,
                    "file_name": media_file.file_name,
                    "mime_type": "image/png",
                    "file_size": media_file.file_size_bytes,
                    "metadata": {
                        "width": width,
                        "height": height,
                        "prompt": prompt,
                        "revised_prompt": revised_prompt
                    }
                }
            }, indent=2)

        except httpx.HTTPStatusError as e:
            error_msg = str(e)
            try:
                error_data = e.response.json()
                error_msg = error_data.get("error", {}).get("message", str(e))
            except:
                pass

            logger.error(f"DALL-E API error: {error_msg}")
            return json.dumps({
                "success": False,
                "error": f"DALL-E API error: {error_msg}"
            }, indent=2)

        except httpx.TimeoutException:
            logger.error("DALL-E request timed out")
            return json.dumps({
                "success": False,
                "error": "Image generation timed out. Try a simpler prompt."
            }, indent=2)

        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            return json.dumps({
                "success": False,
                "error": str(e)
            }, indent=2)

    return StructuredTool.from_function(
        func=generate_image,
        name="generate_image",
        description="""Generate an image using DALL-E 2 AI model.

Args:
  - prompt (required): Detailed description of the image to generate
  - size (optional): Image dimensions - '1024x1024' (default), '512x512', or '256x256'

Returns JSON with image URL and metadata. The generated image is saved to the session workspace.

Tips for better results:
- Be specific and detailed in your prompt
- Include artistic style references (e.g., "oil painting", "digital art", "photorealistic")
- Mention lighting, mood, and composition details
- Specify the subject clearly

Example: generate_image(prompt="A serene Japanese garden at sunset with a red wooden bridge over a koi pond, cherry blossoms falling, photorealistic style", size="1024x1024")""",
        args_schema=DalleImageInput,
        return_direct=False
    )


# Image generation tool class names for identification
IMAGE_GENERATION_TOOL_CLASSES = {
    "DalleImageGeneration": "generate_image"
}

IMAGE_GENERATION_TOOL_NAMES = list(IMAGE_GENERATION_TOOL_CLASSES.values())


def is_image_generation_tool_class(langchain_class: str) -> bool:
    """Check if a langchain_class is an image generation tool."""
    return langchain_class in IMAGE_GENERATION_TOOL_CLASSES
