from fastapi import APIRouter, HTTPException
from ...services.auth_service import AuthService

router = APIRouter(prefix="/api/auth", tags=["auth"])
auth_service = AuthService()

@router.get("/hh")
async def hh_auth():
    return {
        "url": f"https://hh.ru/oauth/authorize?response_type=code&client_id={auth_service.hh_client.client_id}&redirect_uri=http://localhost:3000"
    }

@router.post("/callback")
async def auth_callback(code: str):
    return await auth_service.handle_oauth_callback(code)

@router.post("/refresh")
async def refresh_token(refresh_token: str):
    """Refresh access token using HH refresh token"""
    return await auth_service.refresh_token(refresh_token)