"""
app/schemas/auth.py

Pydantic request and response schemas for the authentication module.

These define the exact shape of:
  - Login request body
  - Token response payload (updated for cookie-based refresh)
  - Current user response (me endpoint)
  - Password change request
  - MFA setup / verify / challenge schemas
"""

import re
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


# ── Request schemas ───────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    """Body for POST /auth/login"""
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=72)

    model_config = {"json_schema_extra": {"example": {
        "email": "admin@livetrace.io",
        "password": "SecurePass123!"
    }}}


class RefreshRequest(BaseModel):
    """Body for POST /auth/refresh (kept for backward compat, but refresh is now cookie-based)"""
    refresh_token: str = Field(..., min_length=10)


class ChangePasswordRequest(BaseModel):
    """Body for POST /auth/change-password"""
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """
        Enforce:
          - At least 8 characters
          - At least one uppercase letter
          - At least one lowercase letter
          - At least one digit
          - At least one special character
        """
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>_\-]", v):
            raise ValueError("Password must contain at least one special character")
        return v


# ── MFA schemas ───────────────────────────────────────────────────────────────

class MFAVerifyRequest(BaseModel):
    """Body for POST /auth/mfa/verify (during setup or login challenge)"""
    otp_code: str = Field(..., min_length=6, max_length=6)


class MFALoginRequest(BaseModel):
    """Body for POST /auth/mfa/login-verify (complete MFA login challenge)"""
    user_id: int
    otp_code: str = Field(..., min_length=6, max_length=6)


class MFADisableRequest(BaseModel):
    """Body for POST /auth/mfa/disable"""
    user_id: int


# ── Response schemas ──────────────────────────────────────────────────────────

class UserBrief(BaseModel):
    """Minimal user info returned in token responses."""
    id: int
    full_name: str
    email: str
    role: str
    customer_id: Optional[int] = None

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """
    Returned on successful login.
    NOTE: refresh_token is no longer sent in the JSON body.
    It is set as an HttpOnly cookie by the route handler.
    """
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 0          # seconds until access token expires
    user: Optional[UserBrief] = None


class AccessTokenResponse(BaseModel):
    """Returned on refresh — new access token only."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 0


class MFAChallengeResponse(BaseModel):
    """Returned when login requires MFA verification."""
    mfa_required: bool = True
    user_id: int
    message: str = "MFA verification required"


class MFASetupResponse(BaseModel):
    """Returned when MFA setup is initiated."""
    secret: str
    provisioning_uri: str
    message: str


class UserMeResponse(BaseModel):
    """Returned by GET /auth/me"""
    id: int
    full_name: str
    email: str
    phone: Optional[str]
    role: str
    customer_id: Optional[int]
    is_active: bool
    mfa_enabled: bool = False

    model_config = {"from_attributes": True}


class LogoutResponse(BaseModel):
    """Returned by POST /auth/logout"""
    success: bool = True
    message: str = "Logged out successfully"


# ── Session schemas ───────────────────────────────────────────────────────────

class SessionResponse(BaseModel):
    session_id: int
    ip_address: str
    user_agent: str
    login_time: str
    expires_at: Optional[str] = None
    is_current: bool


class RevokeSessionRequest(BaseModel):
    session_id: int
