"""Authentication router - Login, token refresh, user management."""
from datetime import timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database.db import get_db
from database.models import User, Company
from core.security import (
    verify_password, get_password_hash, create_access_token,
    get_current_user, TokenData, UserRoles, require_roles
)
from core.config import settings

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str
    brand_id: Optional[int] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str
    full_name: Optional[str]
    role: str
    company_name: str
    active_brand_id: Optional[int] = None


class UserCreate(BaseModel):
    username: str
    full_name: str
    password: str
    role: str = UserRoles.BRAND_CASHIER
    email: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    username: str
    full_name: Optional[str]
    role: str
    is_active: bool

    class Config:
        from_attributes = True


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate user and return JWT access token."""
    user = db.query(User).filter(
        User.username == request.username,
        User.is_active == True,
    ).first()

    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    company = db.query(Company).filter(Company.id == user.company_id).first()

    token_data = {
        "sub": str(user.id),
        "username": user.username,
        "role": user.role,
        "active_brand_id": request.brand_id,
    }
    access_token = create_access_token(
        data=token_data,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    from datetime import datetime
    user.last_login = datetime.utcnow()
    db.commit()

    return TokenResponse(
        access_token=access_token,
        user_id=user.id,
        username=user.username,
        full_name=user.full_name,
        role=user.role,
        company_name=company.name if company else "FormulaBase",
        active_brand_id=request.brand_id,
    )


@router.get("/me")
async def get_current_user_info(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get current authenticated user info."""
    user = db.query(User).filter(User.id == current_user.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "role": user.role,
        "active_brand_id": current_user.active_brand_id,
    }


@router.post("/users", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    current_user: TokenData = Depends(require_roles([UserRoles.OWNER])),
    db: Session = Depends(get_db),
):
    """Create a new user (Owner only)."""
    company = db.query(Company).first()
    existing = db.query(User).filter(User.username == user_data.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")

    user = User(
        company_id=company.id,
        username=user_data.username,
        full_name=user_data.full_name,
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        role=user_data.role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/users", response_model=List[UserResponse])
async def list_users(
    current_user: TokenData = Depends(require_roles([UserRoles.OWNER, UserRoles.ACCOUNTANT])),
    db: Session = Depends(get_db),
):
    """List all users."""
    return db.query(User).filter(User.is_active == True).all()
