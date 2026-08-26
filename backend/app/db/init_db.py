from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import Base, engine
from app.core.security import hash_password, normalize_email
from app.models import User
from app.schemas.user import UserCreate


def create_tables_if_enabled() -> None:
    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)


def bootstrap_admin(db: Session) -> None:
    email = settings.bootstrap_admin_email
    password = settings.bootstrap_admin_password
    name = settings.bootstrap_admin_name or "Administrador"

    if not email or not password:
        return

    validated = UserCreate(name=name, email=email, password=password)
    normalized_email = normalize_email(str(validated.email))
    existing = db.scalar(select(User).where(User.email == normalized_email))
    if existing:
        return

    admin = User(
        name=validated.name,
        email=normalized_email,
        password_hash=hash_password(validated.password),
        role="ADMIN",
        is_active=True,
    )
    db.add(admin)
    db.commit()
