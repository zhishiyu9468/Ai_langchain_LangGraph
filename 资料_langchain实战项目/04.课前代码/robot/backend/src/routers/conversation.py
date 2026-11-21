from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ..database import get_db
from ..auth import get_current_user_id

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


class CreateConversationRequest(BaseModel):
    title: str = Field(default="New Chat", max_length=100)


class ConversationResponse(BaseModel):
    id: int
    title: str
    created_at: str
    updated_at: str


class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    created_at: str


@router.get("", response_model=list[ConversationResponse])
def list_conversations(
    user_id: int = Depends(get_current_user_id),
    conn=Depends(get_db),
):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, title, created_at, updated_at FROM conversations "
            "WHERE user_id = %s ORDER BY updated_at DESC",
            (user_id,),
        )
        rows = cur.fetchall()
    return [
        ConversationResponse(
            id=r["id"],
            title=r["title"],
            created_at=str(r["created_at"]),
            updated_at=str(r["updated_at"]),
        )
        for r in rows
    ]


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
def create_conversation(
    req: CreateConversationRequest,
    user_id: int = Depends(get_current_user_id),
    conn=Depends(get_db),
):
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO conversations (user_id, title) VALUES (%s, %s)",
            (user_id, req.title),
        )
        conn.commit()
        conv_id = cur.lastrowid
        cur.execute("SELECT id, title, created_at, updated_at FROM conversations WHERE id = %s", (conv_id,))
        row = cur.fetchone()
    return ConversationResponse(
        id=row["id"],
        title=row["title"],
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    conversation_id: int,
    user_id: int = Depends(get_current_user_id),
    conn=Depends(get_db),
):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM conversations WHERE id = %s AND user_id = %s",
            (conversation_id, user_id),
        )
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Conversation not found")

        cur.execute("DELETE FROM conversations WHERE id = %s", (conversation_id,))
        conn.commit()


@router.get("/{conversation_id}/messages", response_model=list[MessageResponse])
def get_messages(
    conversation_id: int,
    user_id: int = Depends(get_current_user_id),
    conn=Depends(get_db),
):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM conversations WHERE id = %s AND user_id = %s",
            (conversation_id, user_id),
        )
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Conversation not found")

        cur.execute(
            "SELECT id, role, content, created_at FROM messages "
            "WHERE conversation_id = %s ORDER BY created_at",
            (conversation_id,),
        )
        rows = cur.fetchall()
    return [
        MessageResponse(
            id=r["id"],
            role=r["role"],
            content=r["content"],
            created_at=str(r["created_at"]),
        )
        for r in rows
    ]
