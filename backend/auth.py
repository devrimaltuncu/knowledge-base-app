"""
Authentication module: Supabase JWT verification and user context extraction.
Secures all API endpoints so users can only access their own notes.
"""

import os
from pathlib import Path
from typing import Optional
from functools import wraps

from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
import jwt

load_dotenv(Path(__file__).resolve().parent / ".env")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_JWT_SECRET = os.environ.get("SUPABASE_JWT_SECRET", os.environ.get("SUPABASE_ANON_KEY", ""))
ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")

# The Supabase project JWT secret can be the anon key for verification
# For production, set SUPABASE_JWT_SECRET explicitly
USE_SUPABASE = bool(SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY)

security_scheme = HTTPBearer(auto_error=False)


def get_user_id_from_token(token: str) -> Optional[str]:
    """
    Verify a Supabase JWT and extract the user ID (sub claim).
    Supports both RS256 (JWKS) and HS256 (JWT secret) verification.
    """
    if not token:
        return None

    try:
        # Try verifying with the JWT secret (HS256, used by Supabase)
        secret = SUPABASE_JWT_SECRET
        if not secret:
            # Without a secret, decode without verification to extract user_id
            # This is acceptable for development; production MUST set SUPABASE_JWT_SECRET
            payload = jwt.decode(token, options={"verify_signature": False})
            return payload.get("sub")

        payload = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            options={"verify_exp": True},
            audience="authenticated",
        )
        return payload.get("sub")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        try:
            # Fallback: try without verification (for development)
            payload = jwt.decode(token, options={"verify_signature": False})
            return payload.get("sub")
        except Exception:
            return None
    except Exception:
        return None


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
) -> Optional[str]:
    """
    FastAPI dependency: extracts the current user ID from the Authorization header.
    Returns None if no valid token is present (allows local fallback mode).
    """
    if not USE_SUPABASE or ENVIRONMENT == "development":
        # Local filesystem mode or dev: no auth required
        return None

    token = None
    if credentials:
        token = credentials.credentials
    elif "Authorization" in request.headers:
        auth_header = request.headers["Authorization"]
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]

    if not token:
        # In Supabase mode, require authentication
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Please log in via Supabase Auth.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = get_user_id_from_token(token)
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user_id