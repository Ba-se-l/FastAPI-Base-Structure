from typing import Literal
from pydantic import BaseModel, Field, field_validator


def normalize_seq(seq: str, to: Literal['none','lower','upper'] = 'none') -> str:
    if to == 'none': return seq.strip()
    if to == 'lower': return seq.strip().lower()
    if to == 'upper': return seq.strip().upper()


class RegisterRequest(BaseModel):
    """Schema for user registration request."""

    name: str = Field(..., min_length=1, max_length=100)
    """The user's full display name."""

    email: str = Field(..., min_length=5, max_length=100, pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$')
    """The user's email address. Must be unique across the system."""

    password: str = Field(..., min_length=8, max_length=100)
    """The user's plain-text password. Will be hashed before storage."""

    device_fingerprint: str = Field(
        ...,
        min_length=1,
        max_length=200,
        examples=['DEVICE_ID']
    )
    """Client-provided device identifier for metadata tracking."""

    @field_validator('email', mode='before')
    @classmethod
    def normalize_email(cls, v: str) -> str:
        """Normalizes email to lowercase and strips whitespace.

        Args:
            v: The raw email string from the request.

        Returns:
            Lowercase, stripped email string.
        """
        return normalize_seq(v, 'lower')

    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validates that password meets enterprise security standards.

        Args:
            v: Raw password string.

        Returns:
            Validated password string.

        Raises:
            ValueError: If password lacks required character classes.
        """
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter.")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit.")
        special_chars = set("!@#$%^&*()_+-=[]{}|;':\",./<>?`~")
        if not any(c in special_chars for c in v):
            raise ValueError("Password must contain at least one special character.")
        return v


class LoginRequest(BaseModel):
    """Schema for user login request."""

    email: str = Field(..., pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$')
    """The user's registered email address."""

    password: str = Field(...)
    """The user's plain-text password for verification."""

    @field_validator('email', mode='before')
    @classmethod
    def normalize_email(cls, v: str) -> str:
        """Normalizes email to lowercase and strips whitespace.

        Args:
            v: The raw email string from the request.

        Returns:
            Lowercase, stripped email string.
        """
        return normalize_seq(v, 'lower')


class TokenResponse(BaseModel):
    """Schema for JWT dual-token API responses."""

    access_token: str
    """The short-lived JWT access token string."""

    refresh_token: str
    """The long-lived JWT refresh token string."""

    token_type: str = 'bearer'
    """The token type. Always ``bearer``."""


class RefreshRequest(BaseModel):
    """Schema for token refresh request."""

    refresh_token: str = Field(...)
    """The current valid refresh token to exchange for new tokens."""