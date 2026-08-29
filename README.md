<div align="center">

# RBAC Auth & Gateway Microservice

**A production-style auth service with refresh-token rotation, a hand-built atomic Redis rate limiter, and a real reverse-proxy API gateway — not a CRUD demo.**

![Python](https://img.shields.io/badge/python-3.13-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-DC382D?logo=redis&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)
![Azure](https://img.shields.io/badge/Azure_Container_Apps-0078D4?logo=microsoftazure&logoColor=white)
![License: MIT](https://img.shields.io/badge/license-MIT-green)

[Live Demo](#live-demo) • [Features](#core-features) • [API Reference](#api-reference) • [Getting Started](#getting-started-local) • [Deployment](#deployment-architecture)

</div>

---

## Live Demo

**Interactive API docs (Scalar UI):** `https://rbac-gateway.graysky-397b5d92.centralindia.azurecontainerapps.io/docs`

> Runs on consumption-based, scale-to-zero infrastructure. If the first request is slow, the backend is waking from zero — see [Deployment Architecture](#deployment-architecture) for why that's a deliberate choice, not a bug.

![Scalar UI screenshot](docs/scalar-screenshot.png)

## Core Features

| Feature | What it actually does |
|---|---|
| **JWT Authentication** | `bcrypt` used directly (not the now-unmaintained `passlib`), tokens via `PyJWT` (not `python-jose`, unmaintained since 2021) |
| **Refresh Token Rotation** | Every `/auth/refresh` call issues a new refresh token and blacklists the old one's `jti` in Redis. A stolen token dies the moment the real user refreshes. Fails **closed** if Redis is unreachable — an unverifiable token is rejected, not trusted. |
| **Atomic Rate Limiting** | Hand-written Lua script executed inside Redis — a token-bucket algorithm with no read-modify-write race condition. Keyed by `user_id` when authenticated, IP only for anonymous requests. Fails **open** on a Redis outage. |
| **Role-Based Access Control** | 5-table schema — `users`, `roles`, `permissions`, plus two association tables — so both "roles a user holds" and "permissions a role grants" are real many-to-many relationships. |
| **Reverse Proxy Gateway** | An async route maps HTTP methods to required permissions, then forwards authorized requests to a separately deployed downstream API — following redirects, stripping stale response headers, and controlling `Accept-Encoding` so the downstream can't compress with something this service can't decode. |

## Architecture

```text
Client
  │
  ▼
Gateway (FastAPI, Azure Container Apps — external ingress, scale-to-zero)
  ├─ Auth Check   → JWT validated (PyJWT)
  ├─ RBAC Check   → required permission resolved from HTTP method
  ├─ Rate Limit   → Redis + Lua token bucket, keyed by user or IP
  │
  ├──→ Postgres (Container App, internal-only, scale-to-zero)
  ├──→ Redis     (Container App, internal-only, scale-to-zero)
  │
  └─ [Authorized] → httpx.AsyncClient → Inventory API (separately deployed on Render)
```

## API Reference

| Method | Endpoint | Auth | Permission | Description |
|---|---|---|---|---|
| `POST` | `/auth/register` | — | — | Create an account |
| `POST` | `/auth/login` | — | — | Returns access + refresh tokens |
| `POST` | `/auth/refresh` | Refresh token | — | Rotates both tokens; old refresh token is blacklisted |
| `POST` | `/auth/logout` | Refresh token | — | Immediately revokes the token |
| `GET` | `/users/me` | Access token | — | Current user's profile |
| `GET` | `/users` | Access token | `users:read` | List all users |
| `PATCH` | `/users/{id}/roles` | Access token | `roles:assign` | Change a user's roles |
| `GET` | `/roles` | Access token | `roles:read` | List roles and their permissions |
| `POST` | `/roles` | Access token | `roles:write` | Create a role |
| `ANY` | `/gateway/inventory/{path}` | Access token | `inventory:read` / `inventory:write` (by HTTP method) | Reverse-proxies to the Inventory API |

Full request/response schemas: see the [live Scalar docs](#live-demo), or run locally and visit `/docs`.

## Getting Started (Local)

**Prerequisites:** Docker Desktop running.

```bash
git clone https://github.com/Hamilwt/rbac-gateway-microservice.git
cd rbac-gateway-microservice
cp .env.example .env
```

Edit `.env` — set `SECRET_KEY` (any long random string for local dev) and `INVENTORY_API_BASE_URL` (the downstream service this gateway should protect).

```bash
docker-compose up -d --build
docker exec -it rbac-gateway-microservice-app-1 alembic upgrade head
docker exec -it rbac-gateway-microservice-app-1 python app/scripts/seed_roles.py
```

Running at `http://localhost:8000`, seeded with an `admin` role (all permissions), a `viewer` role (read-only), and a ready-to-use test user.

## Running Tests

```bash
pytest tests/ -v
```

12 tests: registration, login, refresh-token rotation (including reuse-after-rotation failure), fail-closed behavior on a Redis outage, RBAC enforcement (401 vs 403), user-scoped rate limiting, gateway forwarding.

## Example: Calling the Gateway

```bash
curl -X POST http://localhost:8000/auth/login \
  -d "username=admin@example.com&password=<seeded-admin-password>"

curl http://localhost:8000/gateway/inventory/products \
  -H "Authorization: Bearer <access_token>"
```

## Deployment Architecture

Three Azure Container Apps in one Container Apps Environment: `rbac-gateway` (external ingress), `postgres` and `redis` (internal-only TCP ingress, unreachable from the public internet). All three run on the Consumption plan and scale to zero when idle — the deployment costs nothing while not in active use.

**A deliberate trade-off, documented rather than hidden:** Postgres runs on ephemeral storage. The obvious fix — an Azure Files SMB share as the data directory — doesn't actually work for Postgres: the SMB/CIFS protocol can't change file permissions after mount, and Postgres's `initdb` requires exactly that to lock down data-directory ownership. The correct alternative, an NFS-backed share, requires Premium-tier storage behind a VNet, which trades consumption-based pricing for always-billing provisioned storage — defeating the goal of a deployment that costs nothing while idle. Given that, ephemeral storage plus a one-command reseed is the better trade-off here.

```bash
./redeploy.ps1   # wakes Postgres + Redis, re-runs migrations and seeding
./sleep.ps1      # scales Postgres + Redis back to zero when done
```

## License

MIT — see [LICENSE](LICENSE).