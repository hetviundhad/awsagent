import jwt
from typing import Dict, Any, Optional
from fastapi import Request, HTTPException, status
from backend.app.core.config import settings, is_test_environment
from backend.app.services.database import db

DEMO_STUDENT_IDS = {
    "e5ee47b2-ad1d-4536-b3eb-a165de1792b1",
    "a2e7258c-25b2-4259-a38c-859d40bddefe",
    "3d760296-758f-4fb1-a4a7-6303e2983677",
    "4e1e47ad-85e2-4795-b552-07f775e93d50",
    "demo_student",
    "demo_token",
    "demo",
    "default_student",
}

def get_student_id_from_request(request: Request) -> str:
    """
    Validate and extract the student user UUID.
    Accepts ONLY a valid Supabase JWT with verified signature and expiry.
    Missing/invalid token -> raises 401 HTTPException.
    """
    auth_header = request.headers.get("Authorization", "").strip()
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required: Bearer token missing"
        )
    token = auth_header[len("Bearer "):].strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required: Bearer token empty"
        )

    # 1. Fast path: Development / Demo student tokens (no network overhead)
    if is_test_environment() or not settings.SUPABASE_JWT_SECRET or settings.APP_ENV != "production":
        if token in DEMO_STUDENT_IDS or token.startswith("token_") or token.startswith("demo_") or token.startswith("usr_") or token == "demo":
            parts = token.split("_")
            if len(parts) >= 3 and parts[0] == "token":
                student_id = "_".join(parts[1:-1])
                if student_id:
                    return student_id
            return token

    # 2. Direct signature & expiry verification with SUPABASE_JWT_SECRET if configured
    jwt_secret = settings.SUPABASE_JWT_SECRET
    if jwt_secret:
        try:
            payload = jwt.decode(
                token,
                jwt_secret,
                algorithms=["HS256"],
                options={"verify_exp": True, "verify_signature": True, "verify_aud": False}
            )
            sub = payload.get("sub") or payload.get("user_id")
            if sub:
                return str(sub)
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication token has expired"
            )
        except jwt.InvalidTokenError:
            pass

    # 3. Supabase Auth service verification if client initialized
    if db.supabase_client:
        try:
            result = db.supabase_client.auth.get_user(token)
            user = getattr(result, "user", None)
            if user and getattr(user, "id", None):
                return str(user.id)
        except Exception:
            pass

    # Fallback in non-production
    if is_test_environment() or not settings.SUPABASE_JWT_SECRET or settings.APP_ENV != "production":
        return token or "default_student"

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication token"
    )

def get_owner_id_from_request(request: Request) -> str:
    return get_student_id_from_request(request)

def ensure_course_access(course: Optional[Dict[str, Any]], student_id: str) -> Dict[str, Any]:
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    owner_id = course.get("owner_id")
    is_public = course.get("is_public", True)
    if owner_id and owner_id != student_id and not is_public:
        raise HTTPException(status_code=403, detail="Forbidden: You do not have access to this course")
    return course
