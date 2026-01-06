"""
Tests for Conversation Memory Service.

Tests the memory service functionality:
- Loading chat history from sessions
- Converting to LangChain message format
- Applying context window limits
"""
import pytest
from sqlalchemy.orm import Session as DBSession
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from app.models.session import Session, Message, MessageRole, SessionStatus
from app.models.user import User
from app.models.agent import Agent, AgentVersion, AgentType
from app.services.memory import ConversationMemoryService, load_session_memory


@pytest.fixture
def test_user(db: DBSession) -> User:
    """Create a test user"""
    user = User(
        username="memorytest",
        email="memory@test.com",
        hashed_password="hashed_password_here"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_agent(db: DBSession, test_user: User) -> Agent:
    """Create a test agent"""
    agent = Agent(
        name="Memory Test Agent",
        description="Agent for memory testing",
        agent_type=AgentType.CONVERSATIONAL,
        user_id=test_user.id
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


@pytest.fixture
def test_session(db: DBSession, test_user: User, test_agent: Agent) -> Session:
    """Create a test session"""
    session = Session(
        user_id=test_user.id,
        agent_id=test_agent.id,
        status=SessionStatus.COMPLETED,
        title="Test Session"
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@pytest.fixture
def session_with_messages(
    db: DBSession,
    test_session: Session
) -> Session:
    """Create a session with messages"""
    messages = [
        Message(
            session_id=test_session.id,
            role=MessageRole.USER,
            content="Hello, who are you?",
            sequence_number=0
        ),
        Message(
            session_id=test_session.id,
            role=MessageRole.ASSISTANT,
            content="I'm an AI assistant. How can I help you?",
            sequence_number=1
        ),
        Message(
            session_id=test_session.id,
            role=MessageRole.USER,
            content="What's the weather like?",
            sequence_number=2
        ),
        Message(
            session_id=test_session.id,
            role=MessageRole.ASSISTANT,
            content="I don't have access to real-time weather data.",
            sequence_number=3
        ),
    ]
    for msg in messages:
        db.add(msg)
    db.commit()
    db.refresh(test_session)
    return test_session


class TestConversationMemoryService:
    """Tests for ConversationMemoryService"""

    def test_load_empty_session_history(
        self,
        db: DBSession,
        test_session: Session
    ):
        """Test loading history from a session with no messages"""
        service = ConversationMemoryService(db)
        history = service.load_chat_history(test_session.id)

        assert history == []

    def test_load_chat_history_with_messages(
        self,
        db: DBSession,
        session_with_messages: Session
    ):
        """Test loading chat history with messages"""
        service = ConversationMemoryService(db)
        history = service.load_chat_history(session_with_messages.id)

        assert len(history) == 4
        assert isinstance(history[0], HumanMessage)
        assert history[0].content == "Hello, who are you?"
        assert isinstance(history[1], AIMessage)
        assert history[1].content == "I'm an AI assistant. How can I help you?"
        assert isinstance(history[2], HumanMessage)
        assert isinstance(history[3], AIMessage)

    def test_load_nonexistent_session(self, db: DBSession):
        """Test loading history from a non-existent session"""
        service = ConversationMemoryService(db)
        history = service.load_chat_history(99999)

        assert history == []

    def test_apply_context_window_limit(
        self,
        db: DBSession,
        test_session: Session
    ):
        """Test that context window limits are applied correctly"""
        # Create many messages
        for i in range(20):
            msg = Message(
                session_id=test_session.id,
                role=MessageRole.USER if i % 2 == 0 else MessageRole.ASSISTANT,
                content=f"Message {i}",
                sequence_number=i
            )
            db.add(msg)
        db.commit()

        service = ConversationMemoryService(db)

        # With context_window=3, should keep 6 messages (3 turns * 2 messages per turn)
        memory_config = {"type": "buffer", "context_window": 3}
        history = service.load_chat_history(test_session.id, memory_config)

        assert len(history) == 6
        # Should be the last 6 messages
        assert history[0].content == "Message 14"
        assert history[-1].content == "Message 19"

    def test_default_memory_config(
        self,
        db: DBSession,
        session_with_messages: Session
    ):
        """Test that default memory config is applied when none provided"""
        service = ConversationMemoryService(db)

        # Pass None as memory_config - should use defaults
        history = service.load_chat_history(session_with_messages.id, None)

        # Should return all messages (4 is less than default 10 turns * 2 = 20)
        assert len(history) == 4

    def test_message_ordering(
        self,
        db: DBSession,
        test_session: Session
    ):
        """Test that messages are returned in correct sequence order"""
        # Add messages out of order
        messages = [
            Message(session_id=test_session.id, role=MessageRole.ASSISTANT,
                    content="Second", sequence_number=1),
            Message(session_id=test_session.id, role=MessageRole.USER,
                    content="First", sequence_number=0),
            Message(session_id=test_session.id, role=MessageRole.USER,
                    content="Third", sequence_number=2),
        ]
        for msg in messages:
            db.add(msg)
        db.commit()

        service = ConversationMemoryService(db)
        history = service.load_chat_history(test_session.id)

        assert len(history) == 3
        assert history[0].content == "First"
        assert history[1].content == "Second"
        assert history[2].content == "Third"

    def test_system_message_conversion(
        self,
        db: DBSession,
        test_session: Session
    ):
        """Test that system messages are converted correctly"""
        msg = Message(
            session_id=test_session.id,
            role=MessageRole.SYSTEM,
            content="You are a helpful assistant.",
            sequence_number=0
        )
        db.add(msg)
        db.commit()

        service = ConversationMemoryService(db)
        history = service.load_chat_history(test_session.id)

        assert len(history) == 1
        assert isinstance(history[0], SystemMessage)
        assert history[0].content == "You are a helpful assistant."

    def test_get_message_count(
        self,
        db: DBSession,
        session_with_messages: Session
    ):
        """Test getting message count for a session"""
        service = ConversationMemoryService(db)
        count = service.get_message_count(session_with_messages.id)

        assert count == 4

    def test_get_message_count_empty_session(
        self,
        db: DBSession,
        test_session: Session
    ):
        """Test getting message count for empty session"""
        service = ConversationMemoryService(db)
        count = service.get_message_count(test_session.id)

        assert count == 0


class TestLoadSessionMemory:
    """Tests for the convenience function load_session_memory"""

    def test_load_session_memory_function(
        self,
        db: DBSession,
        session_with_messages: Session
    ):
        """Test the convenience function"""
        history = load_session_memory(db, session_with_messages.id)

        assert len(history) == 4
        assert isinstance(history[0], HumanMessage)
        assert isinstance(history[1], AIMessage)

    def test_load_session_memory_with_config(
        self,
        db: DBSession,
        test_session: Session
    ):
        """Test convenience function with memory config"""
        # Add more messages
        for i in range(10):
            msg = Message(
                session_id=test_session.id,
                role=MessageRole.USER if i % 2 == 0 else MessageRole.ASSISTANT,
                content=f"Msg {i}",
                sequence_number=i
            )
            db.add(msg)
        db.commit()

        history = load_session_memory(
            db,
            test_session.id,
            {"type": "buffer", "context_window": 2}
        )

        # context_window=2 means 2 turns = 4 messages
        assert len(history) == 4


class TestBufferMemoryEdgeCases:
    """Tests for edge cases in buffer memory"""

    def test_single_message(
        self,
        db: DBSession,
        test_session: Session
    ):
        """Test buffer memory with single message"""
        msg = Message(
            session_id=test_session.id,
            role=MessageRole.USER,
            content="Single message",
            sequence_number=0
        )
        db.add(msg)
        db.commit()

        service = ConversationMemoryService(db)
        history = service.load_chat_history(
            test_session.id,
            {"type": "buffer", "context_window": 1}
        )

        assert len(history) == 1
        assert history[0].content == "Single message"

    def test_context_window_larger_than_messages(
        self,
        db: DBSession,
        session_with_messages: Session
    ):
        """Test when context window is larger than available messages"""
        service = ConversationMemoryService(db)
        history = service.load_chat_history(
            session_with_messages.id,
            {"type": "buffer", "context_window": 100}
        )

        # Should return all 4 messages
        assert len(history) == 4

    def test_zero_context_window(
        self,
        db: DBSession,
        session_with_messages: Session
    ):
        """Test with zero context window"""
        service = ConversationMemoryService(db)
        history = service.load_chat_history(
            session_with_messages.id,
            {"type": "buffer", "context_window": 0}
        )

        # Zero context window means 0 turns = 0 messages
        assert len(history) == 0
