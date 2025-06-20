from fastapi import HTTPException
from .hh_client import HHClient
from .redis_service import RedisService
from ..core.auth import create_access_token
from ..models.schemas import AuthResponse

class AuthService:
    def __init__(self):
        self.hh_client = HHClient()
        self.redis_service = RedisService()

    async def handle_oauth_callback(self, code: str) -> AuthResponse:
        """Handle HH OAuth callback"""
        try:
            # Exchange code for token
            token_data = await self.hh_client.exchange_code_for_token(code)
            
            # Get user info
            user_data = await self.hh_client.get_user_info(token_data["access_token"])
            
            # Store tokens in Redis
            await self.redis_service.set_user_token(
                user_data['id'], 
                token_data["access_token"],
                token_data.get("expires_in", 86400)
            )
            
            # Store refresh token if provided
            if token_data.get("refresh_token"):
                await self.redis_service.set_refresh_token(
                    user_data['id'],
                    token_data["refresh_token"]
                )
            
            # Generate JWT
            jwt_token = create_access_token({"sub": str(user_data["id"])})
            
            return AuthResponse(
                token=jwt_token,
                refresh_token=token_data.get("refresh_token"),
                user={
                    "id": user_data.get("id"),
                    "email": user_data.get("email"),
                    "first_name": user_data.get("first_name"),
                    "last_name": user_data.get("last_name"),
                    "middle_name": user_data.get("middle_name")
                }
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Authentication failed: {str(e)}"
            )
    
    async def refresh_token(self, refresh_token: str) -> AuthResponse:
        """Refresh HH access token"""
        try:
            # Get new token from HH
            token_data = await self.hh_client.refresh_access_token(refresh_token)
            
            # Get user info with new token
            user_data = await self.hh_client.get_user_info(token_data["access_token"])
            
            # Update tokens in Redis
            await self.redis_service.set_user_token(
                user_data['id'], 
                token_data["access_token"],
                token_data.get("expires_in", 86400)
            )
            
            if token_data.get("refresh_token"):
                await self.redis_service.set_refresh_token(
                    user_data['id'],
                    token_data["refresh_token"]
                )
            
            # Generate new JWT
            jwt_token = create_access_token({"sub": str(user_data["id"])})
            
            return AuthResponse(
                token=jwt_token,
                refresh_token=token_data.get("refresh_token"),
                user={
                    "id": user_data.get("id"),
                    "email": user_data.get("email"),
                    "first_name": user_data.get("first_name"),
                    "last_name": user_data.get("last_name")
                }
            )
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Token refresh failed: {str(e)}"
            )