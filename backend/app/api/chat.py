import json
import re
from typing import AsyncGenerator
from urllib.parse import unquote

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.messages.ai import AIMessageChunk

from app.api.deps import get_current_user, get_current_user_from_query
from app.core.config import settings
from app.db.user_models import User
from app.schemas.chat import ChatRequest
from app.schemas.conversation import CreateConversationRequest
from app.services.db_service import db_service
from app.services.knowledge_service import knowledge_service
from app.services.llm_service import llm_service

router = APIRouter(tags=["chat"])


def sse_event(data: dict, event: str = "message") -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def has_grounded_citations(answer: str) -> bool:
    return bool(re.search(r"\[(?:K?\d+)\]", answer))


def trim_general_knowledge_explanation(answer: str) -> str:
    patterns = [
        r"[。；，, ]*这个问题不需要参考(?:提供的)?资料[^。！？!?]*[。！？!?]?",
        r"[。；，, ]*这个问题(?:属于|是)?基础(?:的)?(?:算术|常识)[^。！？!?]*[。！？!?]?",
        r"[。；，, ]*这个问题也是基础(?:的)?(?:算术|常识)[^。！？!?]*[。！？!?]?",
        r"[。；，, ]*这(?:个)?问题属于基础(?:的)?(?:算术|常识)[^。！？!?]*[。！？!?]?",
        r"[。；，, ]*不需要参考(?:提供的)?资料[^。！？!?]*[。！？!?]?",
        r"[。；，, ]*它是基础(?:的)?算术知识[。！？!?]?",
        r"[。；，, ]*这是基础(?:的)?算术知识[。！？!?]?",
        r"[。；，, ]*这属于基础(?:的)?常识[^。！？!?]*[。！？!?]?",
        r"[。；，, ]*直接(?:给出|得出)?答案即可[。！？!?]?",
        r"[。；，, ]*直接回答即可[。！？!?]?",
    ]
    cleaned = answer.strip()
    for pattern in patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip(" ，,；;。")
    return cleaned.strip() or answer.strip()


def enforce_grounded_answer(answer: str, retrievals) -> tuple[str, bool]:
    if not retrievals:
        return trim_general_knowledge_explanation(answer), False

    grounded = has_grounded_citations(answer)
    if grounded:
        return answer, True
    return trim_general_knowledge_explanation(answer), False


def build_sources_payload(retrievals, grounded: bool) -> list[dict]:
    if not grounded:
        return []
    return [
        {
            "citation": item.citation,
            "title": item.title,
            "source": item.source,
            "score": round(item.rerank_score, 4),
        }
        for item in retrievals
    ]


def build_chat_messages(
    *,
    history_messages,
    user_message: str,
    use_rag: bool,
    user_id: int,
) -> tuple[list, list]:
    retrievals = knowledge_service.retrieve_context(user_id, user_message) if use_rag else []
    context_lines = [
        f"{item.citation} | source={item.source} | score={item.rerank_score:.2f}\n{item.content}"
        for item in retrievals
    ]

    if context_lines:
        system_parts = [
            "你是一名企业级 AI 助手。",
            "当提供了参考资料时，优先依据参考资料回答。",
            "不要编造资料中没有出现的事实、时间、数字、名称、政策或结论。",
            "如果资料不足以支撑结论，请明确说明资料不足，不要硬猜。",
            "只有在你确实使用了参考资料时，才在正文中保留方括号引用，例如 [1] 或 [K1]。",
            "如果问题属于通用常识、基础算术或无需依赖资料即可正确回答的内容，不要为了凑引用而附加无关资料。",
            "如果多条资料冲突，要指出冲突并优先采用分数更高的资料。",
            "回答保持专业、清晰、简洁。",
            "如果问题属于简单常识或基础算术，直接给出答案，不要额外解释“为什么不需要参考资料”。",
            "以下是可用参考资料：",
            *context_lines,
        ]
    else:
        system_parts = [
            "你是一名企业级 AI 助手。",
            "当前没有可用的知识库参考资料。",
            "你仍然要正常回答用户问题，但要基于通用知识谨慎作答。",
            "不要伪造知识库引用，也不要声称来自资料库。",
            "如果你对答案没有把握，请直接说明不确定点。",
            "回答保持专业、清晰、简洁。",
            "如果问题是简单常识或基础算术，直接回答，不要补充“这不需要参考资料”之类的说明。",
        ]

    messages = [SystemMessage(content="\n".join(system_parts))]
    for message in history_messages:
        if message.role == "user":
            messages.append(HumanMessage(content=message.content))
        elif message.role == "assistant":
            messages.append(AIMessage(content=message.content))
    messages.append(HumanMessage(content=user_message))
    return messages, retrievals


async def stream_chat(
    request: ChatRequest,
    current_user: User,
) -> AsyncGenerator[str, None]:
    model_name = request.model or llm_service.get_default_model()
    model = llm_service.get_chat_model(model_name)
    conversation = db_service.get_conversation(current_user.id, request.conversation_id)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="当前会话没找到")

    use_rag = request.use_rag and conversation.use_rag
    messages, retrievals = build_chat_messages(
        history_messages=conversation.messages,
        user_message=request.message,
        use_rag=use_rag,
        user_id=current_user.id,
    )

    db_service.save_user_message(
        user_id=current_user.id,
        conversation_id=request.conversation_id,
        model=model_name,
        content=request.message,
    )

    full_text = ""
    yield sse_event(
        {
            "conversation_id": request.conversation_id,
            "model": model_name,
            "use_rag": use_rag,
            "grounded": False,
            "sources": [],
        },
        "start",
    )

    try:
        async for chunk in model.astream(messages):
            if isinstance(chunk, AIMessageChunk):
                token = chunk.content if isinstance(chunk.content, str) else ""
            else:
                token = getattr(chunk, "content", "")
            if not token:
                continue

            full_text += token
            yield sse_event({"delta": token, "full_text": full_text}, "delta")

        full_text, grounded = enforce_grounded_answer(full_text, retrievals)
        sources_payload = build_sources_payload(retrievals, grounded)
        db_service.save_assistant_message(
            user_id=current_user.id,
            conversation_id=request.conversation_id,
            model=model_name,
            content=full_text,
            latest_sources=sources_payload,
            latest_grounded=grounded,
        )
        yield sse_event(
            {
                "full_text": full_text,
                "sources": sources_payload,
                "grounded": grounded,
            },
            "end",
        )
    except Exception as exc:
        yield sse_event({"message": str(exc)}, "error")


@router.get("/models")
async def list_models(current_user: User = Depends(get_current_user)):
    return {
        "provider": settings.local_llm_provider,
        "default_model": llm_service.get_default_model(),
        "models": llm_service.get_supported_models(),
        "user": current_user.display_name,
    }


@router.get("/conversations")
async def list_conversations(current_user: User = Depends(get_current_user)):
    return db_service.list_conversations(current_user.id)


@router.post("/conversations")
async def create_conversation(
    request: CreateConversationRequest,
    current_user: User = Depends(get_current_user),
):
    model_name = request.model or settings.default_model
    return db_service.create_conversation(current_user.id, model_name, request.use_rag)


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str, current_user: User = Depends(get_current_user)):
    conversation = db_service.get_conversation(current_user.id, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return conversation


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str, current_user: User = Depends(get_current_user)):
    deleted = db_service.delete_conversation(current_user.id, conversation_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return {"success": True}


@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
):
    return StreamingResponse(
        stream_chat(request, current_user),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/chat/stream/es")
async def chat_stream_eventsource(
    conversation_id: str = Query(...),
    message: str = Query(...),
    model: str | None = Query(default=None),
    use_rag: bool = Query(default=True),
    current_user: User = Depends(get_current_user_from_query),
):
    request = ChatRequest(
        conversation_id=conversation_id,
        message=unquote(message),
        model=model,
        use_rag=use_rag,
    )
    return await chat_stream(request, current_user)
