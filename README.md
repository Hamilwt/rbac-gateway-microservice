# RBAC Auth & Gateway Microservice

A production-style authentication and authorization microservice built with FastAPI. Beyond standard JWT auth, it implements **refresh-token rotation**, a **hand-built atomic Redis rate limiter**, and acts as a genuine **reverse-proxy API gateway** — enforcing auth, RBAC, and rate limits before forwarding authorized traffic to a separately deployed downstream service.

## Core Features

- **JWT Authentication** — bcrypt password hashing (used directly, not via the now-unmaintained `passlib`) and PyJWT-based token issuance (not `python-jose`, which has been unmaintained since 2021).
- **Refresh Token Rotation** — every `/auth/refresh` call issues a brand-new refresh token and immediately blacklists the old one's `jti` in Redis. A stolen refresh token becomes unusable the moment the legitimate user refreshes again. The revocation check itself **fails closed**: if Redis is unreachable, refresh requests are rejected rather than silently trusting an unverifiable token.
- **Atomic Rate Limiting** — a custom Lua script executed inside Redis enforces token-bucket limits (`strict`: 5 req/60s on auth endpoints, `standard`: 60 req/60s elsewhere) with no read-modify-write race condition. Keyed by authenticated `user_id` when available, falling back to IP only for anonymous requests. Fails **open** on a Redis outage — a limiter outage shouldn't take the whole API down.
- **Role-Based Access Control** — a 5-table schema (`users`, `roles`, `permissions`, plus two association tables) so both "which roles does a user have" and "which permissions does a role grant" are genuine many-to-many relationships, not a single hardcoded role string.
- **Reverse Proxy Gateway** — a wildcard async route that maps HTTP methods to required permissions, then forwards authorized requests via `httpx` to a downstream service, transparently following redirects and stripping headers (`Content-Encoding`, `Content-Length`) that no longer apply once the body's already been decoded.

## Architecture

```text
Client
  │
  ▼
Gateway (FastAPI)
  ├─ Auth Check        → JWT validated (PyJWT)
  ├─ RBAC Check        → required permission resolved from HTTP method
  ├─ Rate Limit        → Redis + Lua token bucket, keyed by user or IP
  │
  └─ [Authorized] → httpx.AsyncClient → Downstream Inventory API
                                          (separately built & deployed service)
```

## Tech Stack

| Layer | Choice |
|---|---|
| Framework | FastAPI |
| ORM | SQLAlchemy 2.0 (sync engine) |
| Database | PostgreSQL 16 |
| Cache / rate-limit store | Redis 7 |
| Migrations | Alembic |
| Auth | PyJWT + bcrypt |
| Reverse proxy | httpx (async) |
| Testing | pytest |
| API docs | Scalar |
| Containerization | Docker + Docker Compose |

## Getting Started

**Prerequisites:** Docker Desktop running.

```bash
git clone https://github.com/Hamilwt/rbac-gateway-microservice.git
cd rbac-gateway-microservice
cp .env.example .env
```

Edit `.env` and set:
- `SECRET_KEY` — any long random string for local dev
- `INVENTORY_API_BASE_URL` — the downstream service this gateway should protect

Then:

```bash
docker-compose up -d --build
docker exec -it rbac-gateway-microservice-app-1 alembic upgrade head
docker exec -it rbac-gateway-microservice-app-1 python app/scripts/seed_roles.py
```

The API is now running at `http://localhost:8000`, seeded with a default `admin` role (all permissions) and `viewer` role (read-only).

## API Documentation

Interactive docs (Scalar UI): **http://localhost:8000/docs**

Use the Authorize button with a token from `/auth/login` to try protected routes directly from the browser.

## Running Tests

```bash
pytest tests/ -v
```

12 tests covering registration, login, refresh-token rotation (including reuse-after-rotation failure), fail-closed behavior on a Redis outage, RBAC enforcement (401 vs 403), user-scoped rate limiting, and gateway forwarding.

## Example: Calling the Gateway

```bash
# 1. Log in to get an access token
curl -X POST http://localhost:8000/auth/login \
  -d "username=admin@example.com&password=<seeded-admin-password>"

# 2. Use it to call a downstream route through the gateway
curl http://localhost:8000/gateway/inventory/products \
  -H "Authorization: Bearer <access_token>"
```

## Deployment

Designed to run as a single container plus Postgres/Redis, making it deployable to any container platform (Azure Container Apps, Render, etc.) with `DATABASE_URL`, `REDIS_URL`, `SECRET_KEY`, and `INVENTORY_API_BASE_URL` supplied as environment variables — no code changes needed between local and cloud.