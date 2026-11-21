import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ..database import get_db, get_connection
from ..auth import get_current_user_id
from ..deepseek import stream_chat

router = APIRouter(prefix="/api", tags=["chat"])


class ChatRequest(BaseModel):
    conversation_id: int
    message: str = Field(min_length=1)


@router.post("/chat")
async def chat(
    req: ChatRequest,
    user_id: int = Depends(get_current_user_id),
    conn=Depends(get_db),
):
    # Verify ownership
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, title FROM conversations WHERE id = %s AND user_id = %s",
            (req.conversation_id, user_id),
        )
        conv = cur.fetchone()
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Save user message
        cur.execute(
            "INSERT INTO messages (conversation_id, role, content) VALUES (%s, %s, %s)",
            (req.conversation_id, "user", req.message),
        )

        # Update title if first message
        if conv["title"] == "New Chat":
            new_title = req.message[:30] + ("..." if len(req.message) > 30 else "")
            cur.execute("UPDATE conversations SET title = %s WHERE id = %s", (new_title, req.conversation_id))

        conn.commit()

        # Build context
        cur.execute(
            "SELECT role, content FROM messages WHERE conversation_id = %s ORDER BY created_at",
            (req.conversation_id,),
        )
        context = [{"role": r["role"], "content": r["content"]} for r in cur.fetchall()]

    async def event_generator():
        full_response = ""
        try:
            async for chunk in stream_chat(context):
                full_response += chunk
                yield f"data: {json.dumps({'content': chunk})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            return

        # Save assistant message with a new connection
        save_conn = get_connection()
        try:
            with save_conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO messages (conversation_id, role, content) VALUES (%s, %s, %s)",
                    (req.conversation_id, "assistant", full_response),
                )
                save_conn.commit()
        finally:
            save_conn.close()

        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
