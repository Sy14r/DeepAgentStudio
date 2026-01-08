"""
Session Title Generator Service.

Automatically generates concise, descriptive titles for sessions
based on the user's first message using LLM analysis.

Uses a system-level LLM provider (from environment variables) for
fast, immediate title generation independent of agent configuration.
"""
from typing import Optional
import logging
import asyncio
import os

from sqlalchemy.orm import Session as DBSession
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage

from ..models.session import Session

logger = logging.getLogger(__name__)

# System prompt for title generation
TITLE_GENERATION_PROMPT = """You are a session title generator. Generate a single sentence that describes what the topic of conversation appears to be based on the user's message.

Rules:
- Output ONLY the sentence, nothing else
- No quotes or extra formatting
- Be descriptive but concise
- Use sentence case (capitalize first word only, unless proper nouns)
- If the message is a greeting or unclear, output "General conversation"

Examples:
- "What's the weather in NYC?" → "Asking about the current weather in New York City"
- "Help me write a Python script to sort a list" → "Requesting help writing a Python sorting script"
- "Can you explain quantum computing?" → "Seeking an explanation of quantum computing concepts"
- "I need to debug this React component that's not rendering" → "Debugging a React component rendering issue"
- "Hi there!" → "General conversation"
"""


def _get_system_llm():
    """
    Get a system-level LLM for title generation from environment variables.

    Tries OpenAI first (gpt-4o-mini is fast and cheap), falls back to Anthropic.
    Uses minimal settings for fast, cheap title generation.

    Returns:
        LLM instance or None if no API key is configured
    """
    # Try OpenAI first (preferred for speed/cost)
    openai_key = os.environ.get("OPENAI_API_KEY")
    if openai_key:
        return ChatOpenAI(
            api_key=openai_key,
            model="gpt-4o-mini",  # Fast and cheap
            temperature=0.3,
            max_tokens=60,  # Enough for a full sentence
            timeout=10,  # Short timeout for responsiveness
        )

    # Fall back to Anthropic
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    if anthropic_key:
        return ChatAnthropic(
            api_key=anthropic_key,
            model="claude-3-haiku-20240307",  # Fast and cheap
            temperature=0.3,
            max_tokens=60,
            timeout=10,
        )

    logger.warning("No system LLM API key found for title generation")
    return None


def generate_title_sync(user_message: str, fallback_title: str = "New Conversation") -> str:
    """
    Synchronously generate a title from the user's message.

    Uses system-level LLM provider from environment variables.

    Args:
        user_message: The user's first message in the session
        fallback_title: Title to use if generation fails

    Returns:
        Generated title string
    """
    try:
        llm = _get_system_llm()
        if not llm:
            return fallback_title

        messages = [
            SystemMessage(content=TITLE_GENERATION_PROMPT),
            HumanMessage(content=f"User's message: {user_message[:500]}")  # Truncate for safety
        ]

        response = llm.invoke(messages)
        generated_title = response.content.strip() if hasattr(response, 'content') else str(response).strip()

        # Clean up the title (remove quotes if present)
        generated_title = generated_title.strip('"\'')

        # Validate title length
        if len(generated_title) > 100:
            generated_title = generated_title[:97] + "..."
        elif len(generated_title) < 2:
            return fallback_title

        logger.info(f"Generated session title: '{generated_title}'")
        return generated_title

    except Exception as e:
        logger.warning(f"Error generating session title: {e}")
        return fallback_title


async def generate_title_async(user_message: str, fallback_title: str = "New Conversation") -> str:
    """
    Asynchronously generate a title from the user's message.

    Runs the synchronous generation in a thread pool.

    Args:
        user_message: The user's first message
        fallback_title: Fallback title if generation fails

    Returns:
        Generated title string
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: generate_title_sync(user_message, fallback_title)
    )


async def generate_and_update_session_title(
    db: DBSession,
    session_id: int,
    user_message: str,
) -> Optional[str]:
    """
    Generate a title and update the session in the database.

    This is meant to be called as a fire-and-forget task from the
    WebSocket handler immediately when a new session is created.

    Args:
        db: Database session
        session_id: Session to update
        user_message: User's first message

    Returns:
        Generated title or None if failed
    """
    try:
        # Generate title asynchronously
        new_title = await generate_title_async(user_message)

        # Update session in database
        session = db.query(Session).filter(Session.id == session_id).first()
        if session:
            session.title = new_title
            db.commit()
            logger.info(f"Updated session {session_id} title to: '{new_title}'")
            return new_title
        else:
            logger.warning(f"Session {session_id} not found for title update")
            return None

    except Exception as e:
        logger.exception(f"Failed to generate/update session title: {e}")
        return None
