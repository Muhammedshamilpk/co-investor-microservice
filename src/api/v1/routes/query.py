import asyncio
import json
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

from src.api.dependencies import IntentDep, LLMDep, RouterDep, SafetyDep
from src.core.logging import get_logger
from src.schemas.chat import ChatRequest
from src.streaming.sse import stream_agent_sse, sse_dict

log = get_logger(__name__)
router = APIRouter(tags=["Query"])

TIMEOUT_SECONDS = 30.0

@router.post("/query")
async def query_endpoint(
    request: Request,
    payload: ChatRequest,
    safety: SafetyDep,
    classifier: IntentDep,
    agent_router: RouterDep,
    llm: LLMDep,
):
    """
    Streaming endpoint that executes the AI pipeline:
    Safety -> Classifier -> Router -> Agent -> Stream Response
    """
    session_id = payload.session_id or str(uuid.uuid4())
    log.bind(session_id=session_id)
    log.info("query_request_received")

    async def event_generator() -> AsyncGenerator[dict, None]:
        try:
            if await request.is_disconnected():
                return

            # 1. Safety Check
            user_msgs = [m.content for m in payload.messages if m.role == "user"]
            if user_msgs:
                safety_result = await asyncio.wait_for(
                    safety.check(user_msgs[-1]),
                    timeout=TIMEOUT_SECONDS
                )
                if safety_result.blocked:
                    yield {
                        "event": "error",
                        "data": json.dumps({
                            "message": safety_result.message or "Safety violation",
                            "category": safety_result.category
                        })
                    }
                    return

            # 2. Intent Classification
            intent_result = await asyncio.wait_for(
                classifier.classify(payload.messages),
                timeout=TIMEOUT_SECONDS
            )

            # 3. Route to agent
            agent = agent_router._registry.get(intent_result.intent)
            agent_name = agent.name if agent else "unknown"

            # 4. Stream response in chunks
            stream_gen = stream_agent_sse(llm, payload.messages, agent_name)
            
            async for chunk in stream_gen:
                if await request.is_disconnected():
                    log.info("client_disconnected")
                    break
                yield chunk



        except asyncio.TimeoutError:
            log.error("request_timeout")
            yield {
                "event": "error",
                "data": json.dumps({"message": "Request timed out"})
            }
        except Exception as e:
            log.exception("streaming_error")
            yield {
                "event": "error",
                "data": json.dumps({"message": str(e)})
            }

    return EventSourceResponse(event_generator())
