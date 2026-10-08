from typing import Literal
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


def normalize_seq(seq: str, to: Literal['none','lower','upper'] = 'none') -> str:
    if to == 'none': return seq.strip()
    if to == 'lower': return seq.strip().lower()
    if to == 'upper': return seq.strip().upper()


def validate_password(password: str) -> str:
    """Validates that password meets enterprise security standards.
    
    Args:
        password: Raw password string.

    Returns:
        Validated password string.

    Raises:
        ValueError: If password lacks required character classes.
    """
    if not any(c.isupper() for c in password):
        raise ValueError("Password must contain at least one uppercase letter.")
    if not any(c.islower() for c in password):
        raise ValueError("Password must contain at least one lowercase letter.")
    if not any(c.isdigit() for c in password):
        raise ValueError("Password must contain at least one digit.")
    special_chars = set("!@#$%^&*()_+-=[]{}|;':\",./<>?`~")
    if not any(c in special_chars for c in password):
        raise ValueError("Password must contain at least one special character.")
    return password


class RegisterRequest(BaseModel):
    """Schema for user registration request."""

    name: str = Field(..., min_length=1, max_length=100)
    """The user's full display name."""

    email: EmailStr
    """The user's email address. Must be unique across the system."""

    password: str = Field(..., min_length=8, max_length=100)
    """The user's plain-text password. Will be hashed before storage."""

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
        return validate_password(password=v)


class LoginRequest(BaseModel):
    """Schema for user login request."""

    email: EmailStr
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



class ChangePasswordRequest(BaseModel):
    """Schema for authenticated user password change request."""

    old_password: str = Field(..., min_length=1, max_length=100)
    """The user's current plain-text password for verification."""

    new_password: str = Field(..., min_length=8, max_length=100)
    """The desired new plain-text password."""

    @field_validator('new_password')
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validates that new password meets enterprise security standards."""
        return validate_password(password=v)


    @model_validator(mode='after')
    def verify_different_passwords(self) -> 'ChangePasswordRequest':
        """Ensures that the new password is not identical to the current password."""
        if self.old_password == self.new_password:
            raise ValueError("New password must be different from the old password.")
        return self