from fastapi import Header, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .config import settings

bearer=HTTPBearer(auto_error=False)

def get_actor(x_actor_id: str | None = Header(default=None)) -> str:
    return (x_actor_id or "local-dev").strip()[:120]

def require_api_key(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
    # Local development is intentionally frictionless. Production must set RELIABILITY_API_KEY.
    if settings.api_key:
        if credentials is None or credentials.scheme.lower()!="bearer" or credentials.credentials!=settings.api_key:
            raise HTTPException(status_code=401, detail={"error_code":"AUTH_INVALID", "message":"Missing or invalid bearer token"})
