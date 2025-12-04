import asyncio
import json
import os
import redis.asyncio as redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

redis_client = redis.from_url(REDIS_URL, decode_responses=True)

async def publish(channel: str, message: dict):
    await redis_client.publish(channel, json.dumps(message))

async def subscribe(channel: str):
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(channel)

    async for msg in pubsub.listen():
        if msg["type"] == "message":
            yield json.loads(msg["data"])
