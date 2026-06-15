"""
app/services/auth_service.py

Authentication business logic.

Responsibilities:
  - Validate login credentials against DB
  - Create access + refresh token pairs
  - Handle token refresh flow WITH ROTATION
  - Log login events to login_sessions and audit_logs
  - Handle logout (session invalidation)
  - Change password with validation
  - Brute-force protection via Redis lockout
  - MFA setup and verification (TOTP)

Security hardening:
  - Refresh tokens hashed (SHA-256) before DB storage
  - Refresh token rotation on every refresh
  - Brute-force lockout after 5 failed attempts (15 min)
  - MFA support for admin roles

This service is the ONLY consumer of app.core.security.
Routes call this service — never security.py directly.
"""

import logging
from datetime import datetime, timedelta, UTC
from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import (
    AccountLockedException,
    InvalidCredentialsException,
    NotFoundException,
    TokenExpiredException,
    UnauthorizedException,
    ValidationException,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.core.redis_client import redis_client
from app.models.audit_log import AuditLog
from app.models.login_session import LoginSession
from app.models.user import User
from app.schemas.auth import ChangePasswordRequest, LoginRequest
from app.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Brute-force protection constants ─────────────────────────────────────────
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_SECONDS = 15 * 60  # 15 minutes


# ── Brute-force helpers ──────────────────────────────────────────────────────

def _is_locked_out(email: str, ip: Optional[str]) -> bool:
    """Check if email or IP is currently locked out."""
    email_key = f"failed_login:email:{email.lower().strip()}"
    ip_key = f"failed_login:ip:{ip}" if ip else None

    try:
        email_count = redis_client.get(email_key)
        if email_count and int(email_count) >= MAX_FAILED_ATTEMPTS:
            return True

        if ip_key:
            ip_count = redis_client.get(ip_key)
            if ip_count and int(ip_count) >= MAX_FAILED_ATTEMPTS:
                return True
    except Exception as exc:
        # Redis failure should not block login — log and continue
        logger.warning("Redis lockout check failed: %s", exc)

    return False


def _record_failed_attempt(email: str, ip: Optional[str]) -> None:
    """Increment failed login counters in Redis."""
    email_key = f"failed_login:email:{email.lower().strip()}"
    ip_key = f"failed_login:ip:{ip}" if ip else None

    try:
        pipe = redis_client.pipeline()
        pipe.incr(email_key)
        pipe.expire(email_key, LOCKOUT_DURATION_SECONDS)
        if ip_key:
            pipe.incr(ip_key)
            pipe.expire(ip_key, LOCKOUT_DURATION_SECONDS)
        pipe.execute()
    except Exception as exc:
        logger.warning("Redis failed attempt recording failed: %s", exc)


def _clear_failed_attempts(email: str, ip: Optional[str]) -> None:
    """Reset failed login counters on successful login."""
    email_key = f"failed_login:email:{email.lower().strip()}"
    ip_key = f"failed_login:ip:{ip}" if ip else None

    try:
        redis_client.delete(email_key)
        if ip_key:
            redis_client.delete(ip_key)
    except Exception as exc:
        logger.warning("Redis failed attempt clear failed: %s", exc)


# ── Login ─────────────────────────────────────────────────────────────────────

def login(
    data: LoginRequest,
    db: Session,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> dict:
    """
    Validate credentials and return a token pair.

    Returns a dict matching TokenResponse shape:
      access_token, refresh_token, token_type, expires_in, role, user_id
    
    Security:
      - Checks brute-force lockout before credential validation
      - Hashes refresh token before DB storage
      - Clears lockout counters on success
      - Returns MFA challenge if user has MFA enabled
    """
    normalized_email = data.email.lower().strip()

    # 0. Brute-force lockout check
    if _is_locked_out(normalized_email, ip_address):
        logger.warning(
            "Login blocked — account locked: email=%s ip=%s",
            normalized_email, ip_address,
        )
        db.add(AuditLog(
            user_id=None,
            action_type="LOGIN_BLOCKED",
            target_table="users",
            target_id=None,
            description=(
                f"Login blocked — brute-force lockout: "
                f"email={normalized_email} | ip={ip_address}"
            ),
        ))
        db.commit()
        raise AccountLockedException()

    # 1. Look up user by email
    user = db.query(User).filter(
        User.email == normalized_email
    ).first()

    if not user:
        # Run a dummy password check to mimic bcrypt hashing time (Task 10)
        verify_password(data.password, "$2b$12$yQ3zX8C6B4V2N1M5K7J9O3iP1g2m3s4v5b6n7h8j9k0l1a2s3d4f")
        logger.warning("Login failed - email not found: %s from ip=%s", data.email, ip_address)
        # DATA-002: Log failed login attempts to audit table for security monitoring
        db.add(AuditLog(
            user_id=None,
            action_type="LOGIN_FAILED",
            target_table="users",
            target_id=None,
            description=f"Failed login attempt — email not found: {data.email} | ip={ip_address}",
        ))
        db.commit()
        _record_failed_attempt(normalized_email, ip_address)
        raise InvalidCredentialsException()

    # 2. Verify password FIRST (Task 10)
    if not verify_password(data.password, user.password_hash):
        logger.warning("Login failed - wrong password: user_id=%s from ip=%s", user.id, ip_address)
        db.add(AuditLog(
            user_id=user.id,
            action_type="LOGIN_FAILED",
            target_table="users",
            target_id=user.id,
            description=f"Failed login — wrong password: user_id={user.id} email='{user.email}' | ip={ip_address}",
        ))
        db.commit()
        _record_failed_attempt(normalized_email, ip_address)
        raise InvalidCredentialsException()

    # 3. Check account is active (Task 10 - raising normalized exception)
    if not user.is_active:
        logger.warning("Login attempt on inactive account: user_id=%s from ip=%s", user.id, ip_address)
        db.add(AuditLog(
            user_id=user.id,
            action_type="LOGIN_FAILED",
            target_table="users",
            target_id=user.id,
            description=f"Login attempt on deactivated account: user_id={user.id} | ip={ip_address}",
        ))
        db.commit()
        raise InvalidCredentialsException()

    # 3.5. MFA check — if user has MFA enabled, return challenge instead of full tokens
    if getattr(user, 'mfa_enabled', False) and getattr(user, 'totp_secret', None):
        _clear_failed_attempts(normalized_email, ip_address)
        logger.info("MFA challenge issued for user_id=%s", user.id)
        return {
            "mfa_required": True,
            "user_id": user.id,
            "message": "MFA verification required",
        }

    # 4. Generate token pair
    access_token = create_access_token(user_id=user.id, role=user.role)
    refresh_token = create_refresh_token(user_id=user.id)

    # 5. Persist login session with HASHED refresh token
    hashed_refresh = hash_token(refresh_token)
    expires_at = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    session = LoginSession(
        user_id=user.id,
        jwt_token=hashed_refresh,   # store SHA-256 hash, never raw token
        ip_address=ip_address,
        user_agent=user_agent,
        expires_at=expires_at,
    )
    db.add(session)

    # 6. Audit log
    audit = AuditLog(
        user_id=user.id,
        action_type="LOGIN",
        target_table="users",
        target_id=user.id,
        description=f"User '{user.email}' logged in from {ip_address}",
    )
    db.add(audit)
    db.commit()

    # 7. Clear brute-force counters on successful login
    _clear_failed_attempts(normalized_email, ip_address)

    try:
        from app.services.notification_service import send_login_alert
        send_login_alert(
            user=user,
            ip_address=ip_address,
            user_agent=user_agent,
            login_time=datetime.now(UTC),
        )
    except Exception as exc:
        logger.error("Login alert dispatch failed for user_id=%s: %s", user.id, exc)

    logger.info("User logged in: user_id=%s role=%s", user.id, user.role)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,  # raw token — sent to client via HttpOnly cookie
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "role": user.role,
        "user_id": user.id,
        "user": {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role,
            "customer_id": user.customer_id,
        },
    }


# ── Token refresh (with rotation) ────────────────────────────────────────────

def refresh_access_token(
    refresh_token: str,
    db: Session,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> dict:
    """
    Validate a refresh token and issue a NEW access + refresh token pair.

    Token rotation: the old refresh token is immediately invalidated and
    a new one is issued. This limits the damage from token theft.

    Returns a dict with: access_token, refresh_token, token_type, expires_in
    """
    # 1. Decode and validate the refresh token JWT
    payload = decode_refresh_token(refresh_token)
    user_id = int(payload.get("sub", 0))

    # 2. Hash the incoming token and verify it matches a DB session
    hashed_incoming = hash_token(refresh_token)
    session = db.query(LoginSession).filter(
        LoginSession.jwt_token == hashed_incoming,
        LoginSession.user_id == user_id,
    ).first()

    if not session:
        # Possible token replay attack — log it
        logger.warning(
            "Refresh token replay detected: user_id=%s — revoking all sessions",
            user_id,
        )
        # Revoke ALL sessions for this user as a security measure
        db.query(LoginSession).filter(LoginSession.user_id == user_id).delete(
            synchronize_session=False
        )
        db.add(AuditLog(
            user_id=user_id,
            action_type="SECURITY_ALERT",
            target_table="login_sessions",
            target_id=None,
            description=(
                f"Refresh token replay detected for user_id={user_id}. "
                f"All sessions revoked."
            ),
        ))
        db.commit()
        raise UnauthorizedException("Refresh token has been revoked or is invalid")

    if session.expires_at:
        expires_at = session.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at < datetime.now(UTC):
            raise TokenExpiredException()

    # 3. Look up the user (may have been deactivated since token was issued)
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise UnauthorizedException("User account is no longer active")

    # 4. ROTATION: Delete old session, create new one
    db.delete(session)

    new_access_token = create_access_token(user_id=user.id, role=user.role)
    new_refresh_token = create_refresh_token(user_id=user.id)
    new_hashed_refresh = hash_token(new_refresh_token)

    new_session = LoginSession(
        user_id=user.id,
        jwt_token=new_hashed_refresh,
        ip_address=ip_address,
        user_agent=user_agent,
        expires_at=datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(new_session)
    db.commit()

    logger.info("Token rotated: user_id=%s", user.id)

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,  # new raw token — set via HttpOnly cookie
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


# ── Logout ────────────────────────────────────────────────────────────────────

def logout(user_id: int, refresh_token: Optional[str], db: Session) -> None:
    """
    Invalidate the user's session by removing the hashed refresh token from DB.
    """
    if refresh_token:
        hashed = hash_token(refresh_token)
        db.query(LoginSession).filter(
            LoginSession.jwt_token == hashed,
            LoginSession.user_id == user_id,
        ).delete(synchronize_session=False)

    # Audit log
    db.add(AuditLog(
        user_id=user_id,
        action_type="LOGOUT",
        target_table="users",
        target_id=user_id,
        description=f"User id={user_id} logged out",
    ))
    db.commit()
    logger.info("User logged out: user_id=%s", user_id)


# ── Get current user ──────────────────────────────────────────────────────────

def get_user_by_id(user_id: int, db: Session) -> User:
    """Fetch a User by PK. Raises NotFoundException if not found."""
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise NotFoundException("User", user_id)
    return user


# ── Change password ───────────────────────────────────────────────────────────

def change_password(
    user_id: int,
    data: ChangePasswordRequest,
    db: Session,
) -> None:
    """
    Change the authenticated user's password.
    Validates current password before applying the new one.
    """
    user = get_user_by_id(user_id, db)

    if not verify_password(data.current_password, user.password_hash):
        raise ValidationException("Current password is incorrect")

    if data.current_password == data.new_password:
        raise ValidationException("New password must be different from current password")

    user.password_hash = hash_password(data.new_password)

    # Revoke all existing sessions — force re-login everywhere
    db.query(LoginSession).filter(LoginSession.user_id == user_id).delete(
        synchronize_session=False
    )

    db.add(AuditLog(
        user_id=user_id,
        action_type="UPDATE",
        target_table="users",
        target_id=user_id,
        description="Password changed",
    ))
    db.commit()
    logger.info("Password changed for user_id=%s", user_id)


# ── MFA Setup ─────────────────────────────────────────────────────────────────

def setup_mfa(user_id: int, db: Session) -> dict:
    """
    Generate a TOTP secret and provisioning URI for MFA setup.
    Returns the secret and a provisioning URI for QR code generation.
    """
    try:
        import pyotp
    except ImportError:
        raise ValidationException(
            "MFA is not available — pyotp package is not installed"
        )

    user = get_user_by_id(user_id, db)

    if getattr(user, 'mfa_enabled', False):
        raise ValidationException("MFA is already enabled for this account")

    # Generate a new TOTP secret
    secret = pyotp.random_base32()
    provisioning_uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=user.email,
        issuer_name=settings.APP_NAME,
    )

    # Store secret (not yet enabled — user must verify first)
    from app.core.security import encrypt_mfa_secret, decrypt_mfa_secret
    user.totp_secret = encrypt_mfa_secret(secret)
    db.commit()

    logger.info("MFA setup initiated for user_id=%s", user_id)

    return {
        "secret": secret,
        "provisioning_uri": provisioning_uri,
        "message": "Scan the QR code with your authenticator app, then verify with a code.",
    }


def verify_mfa_setup(user_id: int, otp_code: str, db: Session) -> dict:
    """
    Verify TOTP code during MFA setup to confirm the user has configured
    their authenticator app correctly. Enables MFA on success.
    """
    try:
        import pyotp
    except ImportError:
        raise ValidationException("MFA is not available — pyotp package is not installed")

    user = get_user_by_id(user_id, db)

    stored_secret = getattr(user, 'totp_secret', None)
    if not stored_secret:
        raise ValidationException("MFA setup has not been initiated")

    from app.core.security import decrypt_mfa_secret
    totp = pyotp.TOTP(decrypt_mfa_secret(stored_secret))
    if not totp.verify(otp_code, valid_window=1):
        raise ValidationException("Invalid MFA code. Please try again.")

    user.mfa_enabled = True
    db.add(AuditLog(
        user_id=user_id,
        action_type="MFA_ENABLED",
        target_table="users",
        target_id=user_id,
        description=f"MFA enabled for user_id={user_id}",
    ))
    db.commit()

    logger.info("MFA enabled for user_id=%s", user_id)

    return {"message": "MFA has been enabled successfully."}


def verify_mfa_login(user_id: int, otp_code: str, db: Session,
                     ip_address: Optional[str] = None,
                     user_agent: Optional[str] = None) -> dict:
    """
    Complete MFA login challenge. Called after initial password verification
    returned mfa_required=True.
    """
    try:
        import pyotp
    except ImportError:
        raise ValidationException("MFA is not available — pyotp package is not installed")

    user = get_user_by_id(user_id, db)

    stored_secret = getattr(user, 'totp_secret', None)
    if not getattr(user, 'mfa_enabled', False) or not stored_secret:
        raise ValidationException("MFA is not configured for this account")

    from app.core.security import decrypt_mfa_secret
    totp = pyotp.TOTP(decrypt_mfa_secret(stored_secret))
    if not totp.verify(otp_code, valid_window=1):
        raise InvalidCredentialsException()

    # MFA passed — issue full token pair
    access_token = create_access_token(user_id=user.id, role=user.role)
    refresh_token = create_refresh_token(user_id=user.id)

    hashed_refresh = hash_token(refresh_token)
    expires_at = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    session = LoginSession(
        user_id=user.id,
        jwt_token=hashed_refresh,
        ip_address=ip_address,
        user_agent=user_agent,
        expires_at=expires_at,
    )
    db.add(session)

    db.add(AuditLog(
        user_id=user.id,
        action_type="MFA_LOGIN",
        target_table="users",
        target_id=user.id,
        description=f"MFA login completed for user '{user.email}' from {ip_address}",
    ))
    db.commit()

    logger.info("MFA login completed: user_id=%s", user.id)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "role": user.role,
        "user_id": user.id,
        "user": {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role,
            "customer_id": user.customer_id,
        },
    }


def disable_mfa(user_id: int, acting_user_id: int, db: Session) -> dict:
    """
    Disable MFA for a user. Only SUPER_ADMIN can disable MFA for others.
    """
    user = get_user_by_id(user_id, db)

    user.mfa_enabled = False
    user.totp_secret = None

    db.add(AuditLog(
        user_id=acting_user_id,
        action_type="MFA_DISABLED",
        target_table="users",
        target_id=user_id,
        description=f"MFA disabled for user_id={user_id} by user_id={acting_user_id}",
    ))
    db.commit()

    logger.info("MFA disabled for user_id=%s by user_id=%s", user_id, acting_user_id)

    return {"message": "MFA has been disabled."}


# ── Active Login Session Management ───────────────────────────────────────────

def get_active_sessions(user_id: int, current_refresh_token: Optional[str], db: Session) -> list[dict]:
    """
    Get all active login sessions for a user, indicating which is the current session.
    """
    from app.core.security import hash_token
    from app.models.login_session import LoginSession
    
    current_hash = hash_token(current_refresh_token) if current_refresh_token else None
    
    # Clean up expired sessions first
    now = datetime.now(UTC)
    db.query(LoginSession).filter(LoginSession.expires_at < now).delete()
    db.commit()
    
    sessions = db.query(LoginSession).filter(
        LoginSession.user_id == user_id
    ).order_by(LoginSession.login_time.desc()).all()
    
    result = []
    for s in sessions:
        is_current = (current_hash is not None and s.jwt_token == current_hash)
        result.append({
            "session_id": s.id,
            "ip_address": s.ip_address or "Unknown",
            "user_agent": s.user_agent or "Unknown",
            "login_time": s.login_time.isoformat(),
            "expires_at": s.expires_at.isoformat() if s.expires_at else None,
            "is_current": is_current,
        })
    return result


def revoke_session(user_id: int, session_id: int, db: Session) -> None:
    """
    Revoke a specific login session.
    """
    from app.models.login_session import LoginSession
    session = db.query(LoginSession).filter(
        LoginSession.id == session_id,
        LoginSession.user_id == user_id
    ).first()
    
    if not session:
        raise NotFoundException("Session", session_id)
        
    db.delete(session)
    db.commit()


def revoke_all_other_sessions(user_id: int, current_refresh_token: str, db: Session) -> None:
    """
    Revoke all other login sessions except the current one.
    """
    from app.core.security import hash_token
    from app.models.login_session import LoginSession
    
    current_hash = hash_token(current_refresh_token)
    
    db.query(LoginSession).filter(
        LoginSession.user_id == user_id,
        LoginSession.jwt_token != current_hash
    ).delete()
    db.commit()
