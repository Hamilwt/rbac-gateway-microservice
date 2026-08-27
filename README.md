# RBAC Auth & Gateway Microservice

Built an auth gateway microservice with JWT-based auth, refresh-token rotation, and a hand-implemented Redis token-bucket rate limiter (atomic via Lua scripting). The gateway reverse-proxies authorized, RBAC-checked requests to a separate deployed API.

## Core Features
*   **JWT Authentication:** Secure password hashing (bcrypt) and token generation.
*   **Refresh Token Rotation:** Blacklists used refresh tokens in Redis to prevent replay attacks.
*   **Atomic Rate Limiting:** Custom Lua script executed in Redis to enforce strict (auth) and standard (general) token buckets without race conditions. Fail-open design ensures API availability if Redis drops.
*   **Role-Based Access Control (RBAC):** 5-table SQLAlchemy schema mapping Users ↔ Roles ↔ Permissions.
*   **Reverse Proxy Gateway:** Wildcard async HTTP routing (`httpx`) that dynamically maps HTTP methods to required RBAC permissions before forwarding traffic to downstream microservices.

## Architecture

```text
Client → Gateway (FastAPI) 
           │  ├─ Auth Check (JWT)
           │  ├─ RBAC Check (Postgres/Claims)
           │  └─ Rate Limit (Redis + Lua)
           │
           └─ [Forward Request] → Downstream Inventory API