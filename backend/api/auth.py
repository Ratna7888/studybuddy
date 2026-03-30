"""Authentication routes — register, login, JWT."""

from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from db.database import get_db
from models import User
from config import settings

router = APIRouter(prefix="/api/auth", tags=["auth"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()


# ── Schemas ──

class RegisterRequest(BaseModel):
    email: EmailStr
    name: str
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


# ── Helpers ──

def create_token(user_id: int, email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": str(user_id), "email": email, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def verify_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


# ── Dependency: Get current user ──

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    payload = verify_token(credentials.credentials)
    user_id = int(payload["sub"])
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


# ── Routes ──

@router.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    email = req.email.lower().strip()
    name = req.name.strip()

    existing = await db.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=email,
        name=name,
        password_hash=pwd_context.hash(req.password),
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_token(user.id, user.email)
    return TokenResponse(
        access_token=token,
        user={"id": user.id, "email": user.email, "name": user.name},
    )


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    email = req.email.lower().strip()

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user or not pwd_context.verify(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_token(user.id, user.email)
    return TokenResponse(
        access_token=token,
        user={"id": user.id, "email": user.email, "name": user.name},
    )


@router.get("/me")
async def get_me(user: User = Depends(get_current_user)):
    return {"id": user.id, "email": user.email, "name": user.name}