import pytest

from app.core.config import Settings


def test_production_without_cookie_secure_is_rejected() -> None:
    with pytest.raises(ValueError, match="COOKIE_SECURE=true"):
        Settings(_env_file=None, environment="production", cookie_secure=False)


def test_production_with_cookie_secure_is_accepted() -> None:
    settings = Settings(_env_file=None, environment="production", cookie_secure=True)
    assert settings.is_production is True


def test_development_without_cookie_secure_is_accepted() -> None:
    settings = Settings(_env_file=None, environment="development", cookie_secure=False)
    assert settings.is_production is False
