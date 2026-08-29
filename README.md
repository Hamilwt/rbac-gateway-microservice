<div align="center">

# RBAC Auth & Gateway Microservice

JWT authentication microservice with role-based access control, Redis-based rate limiting, and a reverse-proxy gateway to a separately deployed API.

![Python](https://img.shields.io/badge/python-3.13-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-DC382D?logo=redis&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)
![License: MIT](https://img.shields.io/badge/license-MIT-green)
![CI/CD](https://github.com/Hamilwt/rbac-gateway-microservice/actions/workflows/deploy.yml/badge.svg)

[Live Demo](#live-demo) • [Features](#core-features) • [API Reference](#api-reference) • [Getting Started](#getting-started-local)

</div>

---

## Live Demo

`https://rbac-gateway.graysky-397b5d92.centralindia.azurecontainerapps.io/docs`

Runs on scale-to-zero infrastructure — first request may be slow while the backend wakes up.

## Core Features

| Feature | Details |
|---|---|
| JWT Authentication | `bcrypt` for hashing, `PyJWT` for tokens |
| Refresh Token Rotation | Each `/auth/refresh` call issues a new refresh token and blacklists the old one's `jti` in Redis. Fails closed if Redis is unreachable. |
| Rate Limiting | Redis + Lua script, token-bucket algorithm, atomic. Keyed by `user_id` when authenticated, IP otherwise. Fails open if Redis is unreachable. |
| RBAC | 5-table schema — `users`, `roles`, `permissions`, and two association tables — supporting many-to-many roles and permissions |
| Reverse Proxy Gateway | Maps HTTP methods to required permissions, then forwards authorized requests to a downstream API |

## Architecture

```text
Client
  │
  ▼
Gateway (FastAPI, Azure Container Apps — external ingress, scale-to-zero)
  ├─ Auth Check   → JWT validated (PyJWT)
  ├─ RBAC Check   → required permission resolved from HTTP method
  ├─ Rate Limit   → Redis + Lua token bucket
  │
  ├──→ Postgres (Container App, internal-only, scale-to-zero)
  ├──→ Redis     (Container App, internal-only, scale-to-zero)
  │
  └─ [Authorized] → httpx.AsyncClient → Inventory API (deployed on Render)
```

## API Reference

| Method | Endpoint | Auth | Permission | Description |
|---|---|---|---|---|
| `POST` | `/auth/register` | — | — | Create an account |
| `POST` | `/auth/login` | — | — | Returns access + refresh tokens |
| `POST` | `/auth/refresh` | Refresh token | — | Rotates tokens; old one blacklisted |
| `POST` | `/auth/logout` | Refresh token | — | Revokes the token |
| `GET` | `/users/me` | Access token | — | Current user's profile |
| `GET` | `/users` | Access token | `users:read` | List all users |
| `PATCH` | `/users/{id}/roles` | Access token | `roles:assign` | Change a user's roles |
| `GET` | `/roles` | Access token | `roles:read` | List roles and permissions |
| `POST` | `/roles` | Access token | `roles:write` | Create a role |
| `ANY` | `/gateway/inventory/{path}` | Access token | `inventory:read`/`write` | Proxies to the Inventory API |

## Getting Started (Local)

**Prerequisites:** Docker Desktop running.

```bash
git clone https://github.com/Hamilwt/rbac-gateway-microservice.git
cd rbac-gateway-microservice
cp .env.example .env
```

Set `SECRET_KEY` and `INVENTORY_API_BASE_URL` in `.env`.

```bash
docker-compose up -d --build
docker exec -it rbac-gateway-microservice-app-1 alembic upgrade head
docker exec -it rbac-gateway-microservice-app-1 python app/scripts/seed_roles.py
```

Running at `http://localhost:8000`, seeded with `admin` and `viewer` roles plus a test user.

## Running Tests

```bash
pytest tests/ -v
```

12 tests covering auth, refresh rotation, RBAC, rate limiting, and gateway forwarding.

## CI/CD

Every push to `main` runs the full test suite against real Postgres and Redis containers, then — only if all tests pass — builds the image, pushes it to Docker Hub, and deploys it to Azure Container Apps automatically. See [`.github/workflows/deploy.yml`](.github/workflows/deploy.yml).

## Example

```bash
curl -X POST http://localhost:8000/auth/login \
  -d "username=admin@example.com&password=<seeded-admin-password>"

curl http://localhost:8000/gateway/inventory/products \
  -H "Authorization: Bearer <access_token>"
```

## Deployment

Three Azure Container Apps in one environment: `rbac-gateway` (external ingress), `postgres` and `redis` (internal-only, unreachable from the public internet). All scale to zero when idle.

Postgres and Redis use ephemeral storage — Azure Files isn't compatible with Postgres's data-directory permission requirements, and the alternative (NFS/Premium storage) requires always-on billing. `redeploy.ps1` reseeds the database before use; `sleep.ps1` scales back down after.

## License

MIT — see [LICENSE](LICENSE).