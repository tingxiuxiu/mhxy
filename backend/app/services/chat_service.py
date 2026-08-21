from typing import List, Optional
import time

from ..game.enums import ChatChannel
from ..redis_client import redis_client
from ..utils.sensitive import sensitive_filter
from ..exceptions import ValidationException, RateLimitException
from ..config import settings


class ChatService:
    @staticmethod
    async def send_message(
        char_id: int,
        char_name: str,
        channel: ChatChannel,
        content: str,
        target_id: Optional[int] = None,
        target_name: Optional[str] = None,
    ) -> dict:
        content = content.strip()
        if not content or len(content) > 200:
            raise ValidationException("消息长度1-200字")
        content = sensitive_filter.filter(content)
        if channel == ChatChannel.WORLD:
            level_req = 10
            cd_key = f"wx:chat:world:cd:{char_id}"
            if await redis_client.exists(cd_key):
                ttl = await redis_client.client.ttl(cd_key)
                raise RateLimitException(f"世界频道冷却中，请{ttl}秒后再发")
            await redis_client.set(cd_key, "1", ex=settings.CHAT_WORLD_COOLDOWN_SEC)
        msg = {
            "channel": channel.value,
            "speaker_id": char_id,
            "speaker_name": char_name,
            "content": content,
            "target_id": target_id,
            "target_name": target_name,
            "send_time": int(time.time()),
        }
        channel_key = f"wx:chat:channel:{channel.value}"
        if channel == ChatChannel.PRIVATE and target_id:
            channel_key = f"wx:chat:private:{min(char_id, target_id)}:{max(char_id, target_id)}"
        elif channel == ChatChannel.TEAM:
            pass
        elif channel == ChatChannel.GUILD:
            pass
        await redis_client.lpush(channel_key, __import__("json").dumps(msg, ensure_ascii=False))
        await redis_client.ltrim(channel_key, 0, 99)
        return msg

    @staticmethod
    async def get_history(channel: ChatChannel, char_id: int, target_id: Optional[int] = None, count: int = 50) -> List[dict]:
        channel_key = f"wx:chat:channel:{channel.value}"
        if channel == ChatChannel.PRIVATE and target_id:
            channel_key = f"wx:chat:private:{min(char_id, target_id)}:{max(char_id, target_id)}"
        data = await redis_client.lrange(channel_key, 0, count - 1)
        import json
        msgs = []
        for d in data:
            try:
                msgs.append(json.loads(d))
            except Exception:
                pass
        return list(reversed(msgs))


chat_service = ChatService()
