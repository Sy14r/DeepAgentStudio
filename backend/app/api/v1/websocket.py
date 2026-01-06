"""
WebSocket Endpoint for Real-Time Agent Streaming.

Provides WebSocket-based streaming of agent execution events,
enabling real-time updates in the frontend as tools are called and return.
"""
from typing import Optional
import logging
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from sqlalchemy.orm import Session

from ...database import SessionLocal
from ...security import decode_access_token
from ...models.user import User
from ...services.streaming_executor import StreamingAgentExecutorService

router = APIRouter()
logger = logging.getLogger(__name__)


async def get_user_from_token(token: str, db: Session) -> Optional[User]:
    """
    Validate JWT token and return user.

    Args:
        token: JWT token from query parameter
        db: Database session

    Returns:
        User if valid, None otherwise
    """
    if not token:
        return None

    payload = decode_access_token(token)
    if payload is None:
        return None

    username = payload.get("sub")
    if username is None:
        return None

    user = db.query(User).filter(User.username == username).first()
    if user is None or not user.is_active:
        return None

    return user


@router.websocket("/agents/{agent_id}/stream")
async def websocket_agent_stream(
    websocket: WebSocket,
    agent_id: int,
    token: str = Query(..., description="JWT access token")
):
    """
    WebSocket endpoint for streaming agent execution.

    Authenticates via JWT token in query parameter (browsers don't support
    Authorization header in WebSocket connections).

    Client sends:
        {type: "invoke", message: "...", session_id?: number}
        {type: "ping"}

    Server sends:
        {type: "session_start", session_id, timestamp, payload: {agent_id, agent_name}}
        {type: "tool_call", session_id, timestamp, payload: {step_number, tool_name, tool_input}}
        {type: "tool_result", session_id, timestamp, payload: {step_number, tool_name, tool_output, latency_ms}}
        {type: "error", session_id, timestamp, payload: {error, error_type}}
        {type: "final_answer", session_id, timestamp, payload: {output, token_usage, latency_ms}}
        {type: "session_end", session_id, timestamp, payload: {success, total_steps}}
        {type: "pong"}

    Args:
        websocket: FastAPI WebSocket connection
        agent_id: ID of agent to stream
        token: JWT access token
    """
    # Create database session
    db = SessionLocal()

    try:
        # Authenticate user
        user = await get_user_from_token(token, db)
        if user is None:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            logger.warning(f"WebSocket auth failed for agent {agent_id}")
            return

        # Accept the connection
        await websocket.accept()
        logger.info(f"WebSocket connected: user={user.username}, agent_id={agent_id}")

        # Create streaming executor service
        service = StreamingAgentExecutorService(db=db, user_id=user.id)

        # Message handling loop
        while True:
            try:
                # Wait for client message
                data = await websocket.receive_text()
                message = json.loads(data)

                msg_type = message.get("type")

                if msg_type == "ping":
                    await websocket.send_json({"type": "pong"})

                elif msg_type == "invoke":
                    input_message = message.get("message", "")
                    session_id = message.get("session_id")
                    config_override = message.get("config")
                    timeout = message.get("timeout")

                    if not input_message:
                        await websocket.send_json({
                            "type": "error",
                            "session_id": 0,
                            "payload": {
                                "error": "Message is required",
                                "error_type": "ValidationError"
                            }
                        })
                        continue

                    # Execute with streaming
                    try:
                        result = await service.invoke_streaming(
                            agent_id=agent_id,
                            input_message=input_message,
                            websocket=websocket,
                            session_id=session_id,
                            config_override=config_override,
                            timeout_seconds=timeout
                        )

                        logger.info(
                            f"Streaming execution complete: session={result.session_id}, "
                            f"success={result.success}"
                        )

                    except Exception as e:
                        logger.exception(f"Streaming execution error: {e}")
                        await websocket.send_json({
                            "type": "error",
                            "session_id": 0,
                            "payload": {
                                "error": str(e),
                                "error_type": type(e).__name__
                            }
                        })

                else:
                    await websocket.send_json({
                        "type": "error",
                        "session_id": 0,
                        "payload": {
                            "error": f"Unknown message type: {msg_type}",
                            "error_type": "ValidationError"
                        }
                    })

            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "session_id": 0,
                    "payload": {
                        "error": "Invalid JSON",
                        "error_type": "ParseError"
                    }
                })

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: agent_id={agent_id}")

    except Exception as e:
        logger.exception(f"WebSocket error: {e}")
        try:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        except Exception:
            pass

    finally:
        db.close()
