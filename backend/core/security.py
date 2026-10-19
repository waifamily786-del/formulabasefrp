"""
FormulaBase Nexus - Security Module
JWT Authentication, Password Hashing, Role-Based Access Control
"""
from datetime import datetime, timedelta
from typing import Optional, List
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from .config import settings

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)

# Role definitions
class UserRoles:
    OWNER = "OWNER"
    ACCOUNTANT = "ACCOUNTANT"
    FACTORY_MANAGER = "FACTORY_MANAGER"
    BRAND_CASHIER = "BRAND_CASHIER"

    ALL_ROLES = [OWNER, ACCOUNTANT, FACTORY_MANAGER, BRAND_CASHIER]

    # Permission mapping: role -> list of allowed modules
    PERMISSIONS = {
        OWNER: ["*"],  # Full access
        ACCOUNTANT: ["accounting", "reports", "pos_invoice", "erp_view"],
        FACTORY_MANAGER: ["erp_formula", "inventory", "production", "raw_materials"],
        BRAND_CASHIER: ["pos_invoice", "customers", "inventory_view"],
    }


class TokenData(BaseModel):
    user_id: Optional[int] = None
    username: Optional[str] = None
    role: Optional[str] = None
    active_brand_id: Optional[int] = None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> Optional[TokenData]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            return None
        return TokenData(
            user_id=int(user_id),
            username=payload.get("username"),
            role=payload.get("role"),
            active_brand_id=payload.get("active_brand_id"),
        )
    except JWTError:
        return None


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> TokenData:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token_data = decode_token(credentials.credentials)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token_data


def require_roles(allowed_roles: List[str]):
    """Dependency factory for role-based access control."""
    async def check_role(current_user: TokenData = Depends(get_current_user)):
        if current_user.role not in allowed_roles and current_user.role != UserRoles.OWNER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {allowed_roles}",
            )
        return current_user
    return check_role


def has_permission(role: str, module: str) -> bool:
    """Check if a role has access to a module."""
    perms = UserRoles.PERMISSIONS.get(role, [])
    return "*" in perms or module in perms
