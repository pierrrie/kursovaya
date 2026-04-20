# app/auth/security.py
from datetime import datetime, timedelta
from typing import Optional
import bcrypt  # Используем чистый bcrypt

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlmodel import Session

from app.core.config import settings
from app.db.session import get_session
from app.models.user import User, UserRole

# URL, который используется для получения токена
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# УБИРАЕМ passlib.context - используем чистый bcrypt
# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ===== Пароли =====

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверка пароля с помощью bcrypt"""
    try:
        # bcrypt.checkpw принимает байты
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """Хеширование пароля с помощью bcrypt"""
    # Обрезаем пароль если слишком длинный
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
        print(f"⚠️ Пароль обрезан до 72 байт")
    
    # Генерируем соль и хешируем
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


# ===== JWT токен =====

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()

    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    return encoded_jwt


# ===== Текущий пользователь по токену =====

def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_session),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не удалось подтвердить учетные данные",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        username: str = payload.get("sub")
        user_id: int = payload.get("user_id")
        if username is None or user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = session.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь заблокирован",
        )

    return user