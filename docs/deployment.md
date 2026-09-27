# Production Deployment Architecture

PRAMAAN supports containerized deployment on cloud infrastructure (AWS/GCP/MeitY NIC Cloud) as well as offline single-node setups.

---

## 1. Containerized Multi-Tier Deployment

```
                    Internet / Government Intranet
                                  │
                                  ▼
                   ┌─────────────────────────────┐
                   │  Nginx / CloudFront (WAF)   │
                   └──────────────┬──────────────┘
                                  │
          ┌───────────────────────┴───────────────────────┐
          ▼                                               ▼
┌──────────────────┐                            ┌──────────────────┐
│  React Frontend  │                            │  FastAPI Backend │
│  (Nginx Alpine)  │                            │  (Uvicorn Async) │
└──────────────────┘                            └─────────┬────────┘
                                                          │
                                     ┌────────────────────┴────────────────────┐
                                     ▼                                         ▼
                           ┌───────────────────┐                     ┌───────────────────┐
                           │   PostgreSQL 16   │                     │      Redis 7      │
                           │ (System of Record)│                     │(Rate Limit/Queue) │
                           └───────────────────┘                     └───────────────────┘
```

---

## 2. Docker Compose Orchestration (`docker-compose.yml`)

The root `docker-compose.yml` provides a single-command setup that launches the PostgreSQL database, backend service, and frontend dashboard with automatic migrations and seed data.

```bash
# 1. Configure environment
cp .env.example .env

# 2. Build and launch all services
docker compose up --build -d

# 3. Verify container health
docker compose ps
```

---

## 3. Environment Variables & Secret Management

| Variable Name | Default Value | Production Requirement |
| :--- | :--- | :--- |
| `DATABASE_URL` | `sqlite:///./storage/app.db` | Points to managed PostgreSQL (e.g., AWS RDS / Cloud SQL). |
| `JWT_SECRET` | Demo string | Must be 32+ cryptographically random bytes from a secrets manager. |
| `ENCRYPTION_KEY` | None | 32-byte URL-safe base64 Fernet key for field-level encryption. |
| `PORTAL_ADAPTER` | `mock` | Set to `apisetu` for live government gateway integration. |
| `LLM_PROVIDER` | `offline` | Set to `offline`, `ollama` (on-prem), or `openai` (cloud). |
| `EXPECTED_ISSUER_CN` | `Demo DigiLocker Issuing CA` | Swap to authorized CCA / DigiLocker signing CA root CN. |
| `AUTH_RATE_LIMIT_PER_MINUTE` | `20` | Threshold for brute-force protection. |
