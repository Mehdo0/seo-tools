from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from datetime import datetime, timedelta
import jwt, bcrypt

from config import settings
from database import init_db, create_user, get_user
from rate_limit import limiter

router = APIRouter(prefix="/api/auth", tags=["auth"])
security = HTTPBearer()
security_optional = HTTPBearer(auto_error=False)

init_db()


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
    premium: bool = False


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
    return jwt.encode({"sub": email, "exp": expire}, settings.secret_key, algorithm=settings.jwt_algorithm)


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, settings.secret_key, algorithms=[settings.jwt_algorithm])
        email = payload.get("sub")
        user = get_user(email)
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def optional_user(credentials: HTTPAuthorizationCredentials | None = Depends(security_optional)):
    """Identifie l'appelant sans l'exiger.

    Utilisé par l'analyse publique : elle doit rester ouverte, mais l'historique ne s'écrit
    que pour un compte réel. Avant, chaque analyse — y compris anonyme — créait une ligne
    « anonymous » que personne ne pouvait relire : la fonctionnalité d'historique du compte
    était vide quel que soit l'usage.
    """
    if credentials is None:
        return None
    try:
        payload = jwt.decode(credentials.credentials, settings.secret_key, algorithms=[settings.jwt_algorithm])
        return get_user(payload.get("sub"))
    except jwt.InvalidTokenError:
        return None


@router.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest):
    if get_user(req.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    if len(req.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    now = datetime.utcnow().isoformat()
    create_user(req.email, req.name, hash_password(req.password), now)
    token = create_token(req.email)
    return TokenResponse(
        access_token=token,
        user=UserResponse(email=req.email, name=req.name, created_at=now, premium=False),
    )


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(req: LoginRequest, request: Request):
    user = get_user(req.email)
    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_token(req.email)
    return TokenResponse(
        access_token=token,
        user=UserResponse(email=user["email"], name=user["name"], created_at=user["created_at"],
                          premium=bool(user.get("premium"))),
    )


@router.get("/me", response_model=UserResponse)
async def me(user: dict = Depends(get_current_user)):
    return UserResponse(email=user["email"], name=user["name"], created_at=user["created_at"],
                        premium=bool(user.get("premium")))
