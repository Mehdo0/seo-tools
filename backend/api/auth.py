from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from datetime import datetime, timedelta
import jwt
import bcrypt

from config import settings

router = APIRouter(prefix="/api/auth", tags=["auth"])
security = HTTPBearer()

USERS_DB = {}

class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str = ""

class LoginRequest(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    email: str
    name: str
    created_at: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

def create_token(email: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": email, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, settings.secret_key, algorithms=[settings.jwt_algorithm])
        email = payload.get("sub")
        if email not in USERS_DB:
            raise HTTPException(status_code=401, detail="User not found")
        return USERS_DB[email]
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


@router.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest):
    if req.email in USERS_DB:
        raise HTTPException(status_code=400, detail="Email already registered")
    if len(req.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    user = {
        "email": req.email,
        "name": req.name,
        "password_hash": hash_password(req.password),
        "created_at": datetime.utcnow().isoformat(),
    }
    USERS_DB[req.email] = user
    token = create_token(req.email)
    return TokenResponse(
        access_token=token,
        user=UserResponse(email=user["email"], name=user["name"], created_at=user["created_at"]),
    )


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    user = USERS_DB.get(req.email)
    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_token(req.email)
    return TokenResponse(
        access_token=token,
        user=UserResponse(email=user["email"], name=user["name"], created_at=user["created_at"]),
    )


@router.get("/me", response_model=UserResponse)
async def me(user: dict = Depends(get_current_user)):
    return UserResponse(email=user["email"], name=user["name"], created_at=user["created_at"])
