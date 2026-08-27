import time
from fastapi import HTTPException, Request, status
from redis.exceptions import RedisError
from app.core.redis import redis_client

# The exact atomic Lua script from the spec
LUA_SCRIPT = """
-- KEYS[1] = bucket key, ARGV[1] = max_tokens, ARGV[2] = refill_rate_per_sec, ARGV[3] = now
local bucket = redis.call("HMGET", KEYS[1], "tokens", "last_refill")
local tokens = tonumber(bucket[1])
local last_refill = tonumber(bucket[2])
local max_tokens = tonumber(ARGV[1])
local refill_rate = tonumber(ARGV[2])
local now = tonumber(ARGV[3])

if tokens == nil then
  tokens = max_tokens
  last_refill = now
end

local elapsed = now - last_refill
tokens = math.min(max_tokens, tokens + (elapsed * refill_rate))

local allowed = 0
if tokens >= 1 then
  allowed = 1
  tokens = tokens - 1
end

redis.call("HMSET", KEYS[1], "tokens", tokens, "last_refill", now)
redis.call("EXPIRE", KEYS[1], 3600)
return allowed
"""

# Register the script once with Redis for performance
try:
    rate_limit_script = redis_client.register_script(LUA_SCRIPT)
except RedisError as e:
    print(f"Failed to register Lua script: {e}")
    rate_limit_script = None

class rate_limit:
    """
    FastAPI Dependency for token-bucket rate limiting.
    Tiers: 'strict' (login/register) or 'standard' (everything else)
    """
    def __init__(self, tier: str):
        self.tier = tier
        if tier == "strict":
            self.max_tokens = 5
            self.refill_rate = 5 / 60.0  # 5 requests per 60s
        else:
            self.max_tokens = 60
            self.refill_rate = 60 / 60.0 # 60 requests per 60s

    def __call__(self, request: Request):
        if not rate_limit_script:
            return  # Fail open if script didn't load
            
        client_ip = request.client.host if request.client else "127.0.0.1"
        bucket_key = f"rate_limit:{self.tier}:{client_ip}"
        now = time.time()

        try:
            allowed = rate_limit_script(
                keys=[bucket_key],
                args=[self.max_tokens, self.refill_rate, now]
            )
            if not allowed:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests",
                    headers={"Retry-After": "60"}
                )
        except RedisError as e:
            # Spec req: Fail open. Allow the request, but log loudly.
            print(f"Redis rate limiter outage: {e}")
            pass