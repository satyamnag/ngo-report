"""Authentication routes: register, login (OAuth2 password flow), me."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Organization, User, record_audit
from ..schemas import Token, UserCreate, UserOut
from ..security import (
    create_access_token,
    create_refresh_token,
    get_current_user,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=201)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        email=payload.email,
        org_name=payload.org_name,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.flush()

    org = Organization(user_id=user.id, name=payload.org_name)
    db.add(org)
    db.flush()

    # Every new organization starts with the bundled templates.
    from ..seed import ensure_bundled_templates_for_org

    ensure_bundled_templates_for_org(db, org)

    db.commit()
    db.refresh(user)
    record_audit(db, "auth.register", user_id=user.id)
    return user


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == form_data.username).first()
    if user is None or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    record_audit(db, "auth.login", user_id=user.id)
    return Token(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user