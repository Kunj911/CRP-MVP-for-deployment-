-- =========================================================
-- LIVE-TRACE LOGIN FIX SCRIPT
-- Run this in MySQL Workbench on your existing database
-- =========================================================

USE live_trace_dashboard;

-- ── Step 1: Add missing MFA columns (if they don't exist) ──
-- The backend User model expects these columns.
-- Without them, SQLAlchemy crashes on ANY user query.

ALTER TABLE users 
    ADD COLUMN mfa_enabled BOOLEAN DEFAULT FALSE,
    ADD COLUMN totp_secret VARCHAR(255) NULL;

-- ── Step 2: Verify/fix the admin password hash ──────────────
-- This bcrypt hash corresponds to the password: Admin@123
-- If your password_hash still says 'hashed_password_123', this fixes it.

UPDATE users 
SET password_hash = '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4J/HS.V/Ym'
WHERE email = 'admin@livetrace.com'
  AND (password_hash = 'hashed_password_123' 
       OR password_hash NOT LIKE '$2b$%');

-- ── Step 3: Make sure the admin account is active ───────────
UPDATE users 
SET is_active = TRUE 
WHERE email = 'admin@livetrace.com';

-- ── Step 4: Verify the fix worked ───────────────────────────
SELECT 
    user_id,
    email, 
    role, 
    is_active,
    mfa_enabled,
    LEFT(password_hash, 30) AS password_hash_preview,
    CASE 
        WHEN password_hash LIKE '$2b$%' THEN 'VALID bcrypt hash'
        ELSE 'INVALID — not a bcrypt hash!'
    END AS hash_status
FROM users 
WHERE email = 'admin@livetrace.com';

-- ── Step 5: Show all test users ─────────────────────────────
SELECT user_id, full_name, email, role, is_active, mfa_enabled,
       CASE WHEN password_hash LIKE '$2b$%' THEN 'OK' ELSE 'BAD' END AS hash_ok
FROM users;
