# RBAC Gateway Microservice

An asynchronous API Gateway built with FastAPI, demonstrating enterprise-grade security, Role-Based Access Control (RBAC), and microservice proxying.

## Core Features
* **JWT Authentication:** Secure password hashing (bcrypt) and token generation (access/refresh).
* **Role-Based Access Control:** Custom FastAPI dependencies to intercept requests and validate user permissions (`get_current_user`, `require_permissions`).
* **Session Lifecycle Management:** Redis integration for stateless token revocation (blacklisting) upon logout.
* **Microservice Proxying:** Asynchronous HTTP request forwarding (`httpx`) to downstream microservices with graceful error handling (503 Service Unavailable).
* **Containerized Infrastructure:** Automated local development environment using Docker Compose (PostgreSQL & Redis).
* **Database Migrations:** SQLAlchemy ORM models tracked and managed via Alembic.

## Tech Stack
* **Framework:** FastAPI
* **Database:** PostgreSQL (async), Redis
* **ORM & Migrations:** SQLAlchemy, Alembic
* **Security:** PyJWT, passlib, bcrypt
* **Infrastructure:** Docker, Docker Compose