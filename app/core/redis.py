import redis
from app.core.config import settings

# decode_responses=True automatically converts Redis byte responses to strings
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)