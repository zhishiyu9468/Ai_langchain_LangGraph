from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ..database import get_db
from ..auth import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    username: str = Field(min_length=2, max_length=50)
    password: str = Field(min_length=4, max_length=100)


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(req: RegisterRequest, conn=Depends(get_db)):
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM users WHERE username = %s", (req.username,))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="Username already exists")

        hashed = hash_password(req.password)
        cur.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (req.username, hashed))
        conn.commit()
    return {"message": "Register success"}


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, conn=Depends(get_db)):
    with conn.cursor() as cur:
        cur.execute("SELECT id, password FROM users WHERE username = %s", (req.username,))
        row = cur.fetchone()
        if not row or not verify_password(req.password, row["password"]):
            raise HTTPException(status_code=401, detail="Invalid username or password")

        token = create_access_token(row["id"])
    return {"access_token": token}
