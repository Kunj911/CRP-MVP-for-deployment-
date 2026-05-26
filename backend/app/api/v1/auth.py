"""
app/api/v1/auth.py

Authentication route handlers — thin HTTP layer only.
All business logic lives in app/services/auth_service.py.

Endpoints:
  POST   /api/v1/auth/login              → issue token pair
  POST   /api/v1/auth/refresh            → rotate refresh token + new access token
  POST   /api/v1/auth/logout             → revoke session
  GET    /api/v1/auth/me                 → current user profile
  POST   /api/v1/auth/change-password    → update password
  POST   /api/v1/auth/mfa/setup          → initiate MFA setup
  POST   /api/v1/auth/mfa/verify         → confirm MFA setup
  POST   /api/v1/auth/mfa/login-verify   → complete MFA login challenge
  POST   /api/v1/auth/mfa/disable        → disable MFA (SUPER_ADMIN)

Security hardening:
  - Refresh token only in HttpOnly cookie (never in JSON body)
  - Refresh token rotation on every refresh
  - CSRF token set on login for double-submit protection
  - MFA support for admin accounts
"""

import logging
import secrets
from typing import Optional

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app import services
from app.core.limiter import limiter
from app.api.deps import CurrentUser, DbSession, SuperAdminUser, get_current_user
from app.models.user import User
from app.schemas.auth import (
    AccessTokenResponse,
    ChangePasswordRequest,
    LoginRequest,
    LogoutResponse,
    MFAChallengeResponse,
    MFADisableRequest,
    MFALoginRequest,
    MFASetupResponse,
    MFAVerifyRequest,
    TokenResponse,
    UserMeResponse,
    SessionResponse,
    RevokeSessionRequest,
)
from app.schemas.common import SuccessResponse
from app.services import auth_service
from app.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ── Cookie helper ─────────────────────────────────────────────────────────────

def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    """Set the refresh token as an HttpOnly secure cookie."""
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/api/v1/auth",  # restrict cookie to auth endpoints only
    )


def _delete_refresh_cookie(response: Response) -> None:
    """Delete the refresh token cookie."""
    response.delete_cookie(
        key="refresh_token",
        httponly=True,
        secure=True,
        samesite="lax",
        path="/api/v1/auth",
    )


def _set_csrf_cookie(response: Response) -> None:
    """Set a CSRF token cookie (readable by JS for double-submit pattern)."""
    csrf_token = secrets.token_urlsafe(32)
    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        httponly=False,  # JS must read this to send as header
        secure=True,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
    )


# ── POST /auth/login ──────────────────────────────────────────────────────────

@router.post(
    "/login",
    summary="Login with email and password",
    description=(
        "Authenticates a user with email + password. "
        "Returns a JWT access token (short-lived). "
        "Refresh token is set as an HttpOnly cookie — never returned in JSON body. "
        "If MFA is enabled, returns an MFA challenge instead of tokens. "
        "All roles supported: SUPER_ADMIN, ADMIN, WAREHOUSE, QA, DOCUMENTATION, CUSTOMER."
    ),
)
@limiter.limit("5/15minutes")
def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    db: DbSession,
):
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")

    result = auth_service.login(data=body, db=db, ip_address=ip, user_agent=ua)

    # MFA challenge — don't issue tokens yet
    if result.get("mfa_required"):
        return MFAChallengeResponse(
            mfa_required=True,
            user_id=result["user_id"],
            message=result["message"],
        )

    # Set HttpOnly cookie for refresh token
    _set_refresh_cookie(response, result["refresh_token"])
    _set_csrf_cookie(response)

    return TokenResponse(
        access_token=result["access_token"],
        token_type=result["token_type"],
        expires_in=result["expires_in"],
        user=result.get("user"),
    )


# ── POST /auth/refresh ────────────────────────────────────────────────────────

@router.post(
    "/refresh",
    response_model=AccessTokenResponse,
    summary="Refresh access token (with rotation)",
    description=(
        "Exchange a valid refresh token (from HttpOnly cookie) for a new "
        "access token AND a new refresh token. The old refresh token is "
        "immediately invalidated (rotation). This limits token theft damage."
    ),
)
def refresh_token(
    request: Request,
    response: Response,
    db: DbSession,
) -> AccessTokenResponse:
    refresh_token_cookie = request.cookies.get("refresh_token")
    if not refresh_token_cookie:
        from app.core.exceptions import UnauthorizedException
        raise UnauthorizedException("No refresh token cookie found")

    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")

    result = auth_service.refresh_access_token(
        refresh_token=refresh_token_cookie,
        db=db,
        ip_address=ip,
        user_agent=ua,
    )

    # Set new rotated refresh token cookie
    _set_refresh_cookie(response, result["refresh_token"])
    _set_csrf_cookie(response)

    return AccessTokenResponse(
        access_token=result["access_token"],
        token_type=result["token_type"],
        expires_in=result["expires_in"],
    )


# ── POST /auth/logout ─────────────────────────────────────────────────────────

@router.post(
    "/logout",
    response_model=LogoutResponse,
    summary="Logout — revoke session",
    description=(
        "Invalidates the user's refresh token from the database. "
        "The client should also discard the access token locally. "
        "Requires a valid access token in the Authorization header."
    ),
)
def logout(
    request: Request,
    response: Response,
    current_user: CurrentUser,
    db: DbSession,
) -> LogoutResponse:
    # Revoke access token immediately
    jti = getattr(request.state, "jti", None)
    exp = getattr(request.state, "exp", None)
    if jti and exp:
        from app.core.security import revoke_access_token
        revoke_access_token(jti, exp)

    refresh_token_cookie = request.cookies.get("refresh_token")

    if refresh_token_cookie:
        auth_service.logout(
            user_id=current_user.id,
            refresh_token=refresh_token_cookie,
            db=db,
        )

    _delete_refresh_cookie(response)
    # Also clear CSRF cookie on logout
    response.delete_cookie(key="csrf_token")

    return LogoutResponse()


# ── GET /auth/me ──────────────────────────────────────────────────────────────

@router.get(
    "/me",
    response_model=UserMeResponse,
    summary="Get current user profile",
    description=(
        "Returns the profile of the currently authenticated user. "
        "Useful for the frontend to display the logged-in user's name and role. "
        "Also used for session bootstrap on page reload."
    ),
)
def get_me(current_user: CurrentUser) -> UserMeResponse:
    return UserMeResponse.model_validate(current_user)


# ── POST /auth/change-password ────────────────────────────────────────────────

@router.post(
    "/change-password",
    response_model=SuccessResponse[str],
    summary="Change authenticated user's password",
    description=(
        "Allows any authenticated user to change their own password. "
        "Requires the current password for verification. "
        "Invalidates all existing sessions on success (forces re-login everywhere)."
    ),
)
@limiter.limit("3/15minutes")
def change_password(
    body: ChangePasswordRequest,
    request: Request,
    response: Response,
    current_user: CurrentUser,
    db: DbSession,
) -> SuccessResponse[str]:
    auth_service.change_password(
        user_id=current_user.id,
        data=body,
        db=db,
    )
    _delete_refresh_cookie(response)
    return SuccessResponse(
        data="Password updated successfully",
        message="All existing sessions have been invalidated. Please log in again.",
    )


# ── MFA endpoints ─────────────────────────────────────────────────────────────

@router.post(
    "/mfa/setup",
    summary="Initiate MFA setup",
    description=(
        "Generates a TOTP secret and provisioning URI for QR code display. "
        "The user must verify with a valid code to complete setup."
    ),
)
def mfa_setup(
    current_user: CurrentUser,
    db: DbSession,
):
    result = auth_service.setup_mfa(user_id=current_user.id, db=db)
    return MFASetupResponse(**result)


@router.post(
    "/mfa/verify",
    summary="Verify MFA setup",
    description=(
        "Verifies a TOTP code to confirm the authenticator app is configured. "
        "Enables MFA on the user account upon success."
    ),
)
def mfa_verify(
    body: MFAVerifyRequest,
    current_user: CurrentUser,
    db: DbSession,
):
    return auth_service.verify_mfa_setup(
        user_id=current_user.id,
        otp_code=body.otp_code,
        db=db,
    )


@router.post(
    "/mfa/login-verify",
    summary="Complete MFA login challenge",
    description=(
        "After a login returns mfa_required=true, the client submits "
        "user_id + OTP code here to complete authentication."
    ),
)
@limiter.limit("5/15minutes")
def mfa_login_verify(
    body: MFALoginRequest,
    request: Request,
    response: Response,
    db: DbSession,
):
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")

    result = auth_service.verify_mfa_login(
        user_id=body.user_id,
        otp_code=body.otp_code,
        db=db,
        ip_address=ip,
        user_agent=ua,
    )

    _set_refresh_cookie(response, result["refresh_token"])
    _set_csrf_cookie(response)

    return TokenResponse(
        access_token=result["access_token"],
        token_type=result["token_type"],
        expires_in=result["expires_in"],
        user=result.get("user"),
    )


@router.post(
    "/mfa/disable",
    summary="Disable MFA for a user (SUPER_ADMIN only)",
    description=(
        "Disables MFA for the specified user. Only SUPER_ADMIN can use this."
    ),
)
def mfa_disable(
    body: MFADisableRequest,
    current_user: SuperAdminUser,
    db: DbSession,
):
    return auth_service.disable_mfa(
        user_id=body.user_id,
        acting_user_id=current_user.id,
        db=db,
    )


# ── Session Management Endpoints ──────────────────────────────────────────────

@router.get(
    "/sessions",
    response_model=list[SessionResponse],
    summary="List active login sessions",
    description="Returns a list of all active login sessions for the current user, marking the current tab's session.",
)
def get_sessions(
    request: Request,
    current_user: CurrentUser,
    db: DbSession,
) -> list[SessionResponse]:
    refresh_token_cookie = request.cookies.get("refresh_token")
    return auth_service.get_active_sessions(
        user_id=current_user.id,
        current_refresh_token=refresh_token_cookie,
        db=db,
    )


@router.post(
    "/sessions/revoke",
    response_model=SuccessResponse[str],
    summary="Revoke a login session",
    description="Terminates an active login session using its session ID.",
)
def revoke_session(
    body: RevokeSessionRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> SuccessResponse[str]:
    auth_service.revoke_session(
        user_id=current_user.id,
        session_id=body.session_id,
        db=db,
    )
    return SuccessResponse(
        data="Session revoked successfully",
        message="The specified session has been terminated.",
    )


@router.post(
    "/sessions/revoke-others",
    response_model=SuccessResponse[str],
    summary="Revoke all other login sessions",
    description="Terminates all active login sessions for the current user except the one currently in use.",
)
def revoke_all_other_sessions(
    request: Request,
    current_user: CurrentUser,
    db: DbSession,
) -> SuccessResponse[str]:
    refresh_token_cookie = request.cookies.get("refresh_token")
    if not refresh_token_cookie:
        from app.core.exceptions import UnauthorizedException
        raise UnauthorizedException("No active refresh token found")
        
    auth_service.revoke_all_other_sessions(
        user_id=current_user.id,
        current_refresh_token=refresh_token_cookie,
        db=db,
    )
    return SuccessResponse(
        data="Other sessions revoked successfully",
        message="All other login sessions have been terminated.",
    )
