import json
import redis.asyncio as redis
import os
from typing import Optional, Dict, Any, List
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

    async def set_refresh_token(self, user_id: str, refresh_token: str):
        """Store user's refresh token (30 days)"""
        await self.redis.setex(f"refresh_token:{user_id}", 2592000, refresh_token)
    
    async def get_refresh_token(self, user_id: str) -> Optional[str]:
        """Get user's refresh token"""
        token = await self.redis.get(f"refresh_token:{user_id}")
        if not token:
            return None
        return token.decode() if isinstance(token, bytes) else token

    async def get_json(self, key: str) -> Optional[Dict[str, Any]]:
        """Get JSON data from Redis"""
        try:
            data = await self.redis.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            print(f"Redis get error for {key}: {e}")
            return None

    async def set_json(self, key: str, data: Dict[str, Any], expire: int = None):
        """Store JSON data in Redis"""
        try:
            json_data = json.dumps(data, ensure_ascii=False)
            if expire:
                await self.redis.setex(key, expire, json_data)
            else:
                await self.redis.set(key, json_data)
        except Exception as e:
            print(f"Redis set error for {key}: {e}")
    
    async def get_many_json(self, keys: List[str]) -> Dict[str, Optional[Dict[str, Any]]]:
        """Get multiple JSON values from Redis"""
        try:
            values = await self.redis.mget(keys)
            result = {}
            for key, value in zip(keys, values):
                if value:
                    try:
                        result[key] = json.loads(value)
                    except:
                        result[key] = None
                else:
                    result[key] = None
            return result
        except Exception as e:
            print(f"Redis mget error: {e}")
            return {key: None for key in keys}