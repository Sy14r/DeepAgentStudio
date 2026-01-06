"""
Conversation Memory Service for Agent Sessions.

This module provides memory management for agents:
- Loads previous messages from a session
- Converts to LangChain message format
- Applies memory configuration (buffer/window limits)
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session as DBSession
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage

from ..models.session import Session, Message, MessageRole


class ConversationMemoryService:
    """
    Service for loading and managing conversation memory.

    Supports:
    - Buffer memory: Keep last N messages based on context_window
    - Future: Summary memory, vector memory
    """

    def __init__(self, db: DBSession):
        """
        Initialize memory service.

        Args:
            db: Database session
        """
        self.db = db

    def load_chat_history(
        self,
        session_id: int,
        memory_config: Optional[Dict[str, Any]] = None
    ) -> List[BaseMessage]:
        """
        Load chat history from a session and convert to LangChain messages.

        Args:
            session_id: ID of the session to load history from
            memory_config: Optional memory configuration with:
                - type: Memory type ("buffer", "summary", "vector")
                - context_window: Max number of messages to keep
                - retrieval_strategy: For vector memory (not implemented)

        Returns:
            List of LangChain BaseMessage objects (excluding current message)
        """
        if memory_config is None:
            memory_config = {"type": "buffer", "context_window": 10}

        # Get session
        session = self.db.query(Session).filter(Session.id == session_id).first()
        if not session:
            return []

        # Load messages ordered by sequence number
        messages = self.db.query(Message).filter(
            Message.session_id == session_id
        ).order_by(Message.sequence_number.asc()).all()

        if not messages:
            return []

        # Convert to LangChain format
        langchain_messages = self._convert_to_langchain_messages(messages)

        # Apply memory type processing
        memory_type = memory_config.get("type", "buffer")
        context_window = memory_config.get("context_window", 10)

        if memory_type == "buffer":
            return self._apply_buffer_memory(langchain_messages, context_window)
        else:
            # Default to buffer for unsupported types
            return self._apply_buffer_memory(langchain_messages, context_window)

    def _convert_to_langchain_messages(
        self,
        messages: List[Message]
    ) -> List[BaseMessage]:
        """
        Convert database Message objects to LangChain message format.

        Args:
            messages: List of Message objects from database

        Returns:
            List of LangChain BaseMessage objects
        """
        langchain_messages = []

        for msg in messages:
            if msg.role == MessageRole.USER:
                langchain_messages.append(HumanMessage(content=msg.content))
            elif msg.role == MessageRole.ASSISTANT:
                langchain_messages.append(AIMessage(content=msg.content))
            elif msg.role == MessageRole.SYSTEM:
                langchain_messages.append(SystemMessage(content=msg.content))
            # Skip TOOL messages for now - they're recorded separately in traces

        return langchain_messages

    def _apply_buffer_memory(
        self,
        messages: List[BaseMessage],
        context_window: int
    ) -> List[BaseMessage]:
        """
        Apply buffer memory - keep only the last N messages.

        Args:
            messages: All messages in the conversation
            context_window: Maximum number of messages to keep

        Returns:
            Truncated list of messages
        """
        if not messages:
            return []

        # Handle edge case of zero context window
        if context_window <= 0:
            return []

        # Keep the last context_window messages
        # But we typically want pairs (user + assistant), so multiply by 2
        # context_window represents "turns" (a turn = user message + assistant response)
        max_messages = context_window * 2

        if len(messages) <= max_messages:
            return messages

        return messages[-max_messages:]

    def get_message_count(self, session_id: int) -> int:
        """
        Get the count of messages in a session.

        Args:
            session_id: Session ID

        Returns:
            Number of messages in the session
        """
        return self.db.query(Message).filter(
            Message.session_id == session_id
        ).count()


def load_session_memory(
    db: DBSession,
    session_id: int,
    memory_config: Optional[Dict[str, Any]] = None
) -> List[BaseMessage]:
    """
    Convenience function to load session memory.

    Args:
        db: Database session
        session_id: Session ID
        memory_config: Optional memory configuration

    Returns:
        List of LangChain messages representing chat history
    """
    service = ConversationMemoryService(db)
    return service.load_chat_history(session_id, memory_config)
