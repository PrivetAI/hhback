import json
import redis.asyncio as redis
import os
from typing import Optional, Dict, Any
from fastapi import HTTPException

class RedisService:
    def __init__(self):
        self.redis = redis.from_url(
            os.getenv("REDIS_URL", "redis://localhost:6379"),
            decode_responses=True
        )

    async def get_user_token(self, user_id: str) -> Optional[str]:
        """Get user's HH token"""
        token = await self.redis.get(f"token:{user_id}")
        if not token:
            return None
        return token.decode() if isinstance(token, bytes) else token

    async def set_user_token(self, user_id: str, token: str, expires_in: int = 86400):
        """Store user's HH token"""
        await self.redis.setex(f"token:{user_id}", expires_in, token)

    async def get_json(self, key: str) -> Optional[Dict[str, Any]]:
        """Get JSON data from Redis"""
        data = await self.redis.get(key)
        if data:
            try:
                return json.loads(data.decode() if isinstance(data, bytes) else data)
            except json.JSONDecodeError:
                return None
        return None

    async def set_json(self, key: str, data: Dict[str, Any], expire: int = None):
        """Store JSON data in Redis"""
        json_data = json.dumps(data)
        if expire:
            await self.redis.setex(key, expire, json_data)
        else:
            await self.redis.set(key, json_data)