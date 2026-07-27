from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import create_access_token, get_current_admin, verify_password
from app.models import Admin
from app.schemas.auth import AdminOut, LoginIn, TokenOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenOut)
async def login(payload: LoginIn, db: AsyncSession = Depends(get_db)):
    admin = await db.scalar(select(Admin).where(Admin.email == payload.email))
    if admin is None or not verify_password(payload.password, admin.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": "Invalid credentials", "code": "UNAUTHORIZED"},
        )
    token = create_access_token(str(admin.id))
    return TokenOut(access_token=token)


@router.get("/me", response_model=AdminOut)
async def me(admin: Admin = Depends(get_current_admin)):
    return AdminOut(id=admin.id, email=admin.email, full_name=admin.full_name)
