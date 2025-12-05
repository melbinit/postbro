# Docker Troubleshooting Guide - PostBro Backend

This document details all the issues encountered while setting up Docker for the PostBro backend and how they were resolved.

## Table of Contents
1. [Initial Setup](#initial-setup)
2. [Issue 1: Logs App Module Not Found](#issue-1-logs-app-module-not-found)
3. [Issue 2: Redis Connection Failed](#issue-2-redis-connection-failed)
4. [Issue 3: Supabase IPv6 Connection Failure](#issue-3-supabase-ipv6-connection-failure)
5. [Issue 4: Host Networking on Mac Docker Desktop](#issue-4-host-networking-on-mac-docker-desktop)
6. [Issue 5: Frontend Connection Refused](#issue-5-frontend-connection-refused)
7. [Final Working Configuration](#final-working-configuration)

---

## Initial Setup

### What We Started With
- Docker Compose file with Redis, Backend, and Celery services
- Dockerfile for Python 3.10 with required dependencies
- `.env` file with configuration

### Initial Commands
```bash
cd postbro_backend
docker-compose build
docker-compose up -d
```

---

## Issue 1: Logs App Module Not Found

### Error
```
ModuleNotFoundError: No module named 'logs.apps'
```

### Root Cause
The `.dockerignore` file was excluding the entire `logs/` directory:
```
logs/
*.log
```

This prevented the Django `logs` app (which is a Python package) from being copied into the Docker image.

### Solution
Updated `.dockerignore` to exclude only log files, not the app directory:
```dockerignore
# Log files (but keep the logs app directory)
logs/*.log
logs/__pycache__/
*.log
```

### Also Fixed
- Volume mount was overwriting the `logs` app directory. Changed from:
  ```yaml
  - logs_volume:/app/logs
  ```
  To:
  ```yaml
  - logs_volume:/app/logs_data
  ```

---

## Issue 2: Redis Connection Failed

### Error
```
[ERROR/MainProcess] consumer: Cannot connect to redis://localhost:6379//: Error 111 connecting to localhost:6379. Connection refused.
```

### Root Cause
The `.env` file had `REDIS_URL=redis://localhost:6379/0`, but in Docker Compose, services should connect using the service name, not `localhost`.

### Solution
Updated `.env`:
```bash
# Changed from:
REDIS_URL=redis://localhost:6379/0

# To:
REDIS_URL=redis://redis:6379/0
```

**Important**: After updating `.env`, you must recreate containers (not just restart):
```bash
docker-compose down
docker-compose up -d
```

`docker-compose restart` does NOT reload `.env` changes - containers need to be recreated.

---

## Issue 3: Supabase IPv6 Connection Failure

### Error
```
django.db.utils.OperationalError: connection to server at "db.nekejilptmnbzhmglmyc.supabase.co" 
(2a05:d014:1c06:5f1c:8913:bb6b:4da8:998b), port 5432 failed: Network is unreachable
```

### Root Cause
1. **Supabase uses IPv6 only**: The hostname resolves to an IPv6 address (`2a05:d014:...`)
2. **Docker default networking doesn't support IPv6**: By default, Docker bridge networks only support IPv4
3. **Password encoding was fine**: The URL-encoded password (`%2FvWHV5T94%23Mu`) was correctly decoded

### Investigation Steps
1. Checked host connectivity:
   ```bash
   nc -zv db.nekejilptmnbzhmglmyc.supabase.co 5432  # ✅ Works from host
   ```

2. Checked DNS resolution in container:
   ```bash
   docker-compose exec backend getent hosts db.nekejilptmnbzhmglmyc.supabase.co
   # Result: Only IPv6 address returned
   ```

3. Verified password encoding:
   ```bash
   python3 -c "from urllib.parse import unquote; print(unquote('%2FvWHV5T94%23Mu'))"
   # Result: /vWHV5T94#Mu ✅ Correct
   ```

### Solution
Enabled IPv6 in Docker Compose network configuration:

```yaml
networks:
  default:
    enable_ipv6: true
    ipam:
      config:
        - subnet: 172.20.0.0/16      # IPv4 subnet
        - subnet: 2001:db8:1::/64    # IPv6 subnet
```

This allows containers to connect to IPv6-only services like Supabase.

---

## Issue 4: Host Networking on Mac Docker Desktop

### Attempted Solution
Tried using `network_mode: host` to solve the IPv6 issue:

```yaml
backend:
  network_mode: host
```

### Why It Failed
- **Docker Desktop on Mac runs in a VM**: `network_mode: host` doesn't work the same way as on Linux
- **Ports not accessible**: Even though Gunicorn was listening on `0.0.0.0:8000`, the port wasn't accessible from the Mac host
- **Health checks worked internally**: The container could reach itself, but external connections failed

### What We Learned
- Health checks inside container: ✅ Working
- External access from Mac: ❌ Failed
- `network_mode: host` is not recommended for Docker Desktop on Mac

### Reverted To
Bridge networking with port mapping:
```yaml
backend:
  ports:
    - "8000:8000"
```

---

## Issue 5: Frontend Connection Refused

### Error
```
POST http://localhost:8000/api/accounts/login/ net::ERR_CONNECTION_REFUSED
```

### Root Cause
After reverting from `network_mode: host`, the backend wasn't accessible because:
1. IPv6 network configuration wasn't applied yet
2. Containers needed to be recreated

### Solution
1. Applied IPv6 network configuration (see Issue 3)
2. Recreated containers:
   ```bash
   docker-compose down
   docker-compose up -d
   ```

### Verification
```bash
# Test health endpoint
curl http://localhost:8000/health/
# Result: ✅ {"status": "healthy", ...}

# Test login endpoint
curl -X POST http://localhost:8000/api/accounts/login/ -H "Content-Type: application/json" -d '{}'
# Result: ✅ {"error":"Email and password are required"}
```

---

## Final Working Configuration

### docker-compose.yml Key Settings

```yaml
services:
  backend:
    build: .
    ports:
      - "8000:8000"  # Map port for Mac access
    # ... other config ...
  
  redis:
    # Uses service name 'redis' for internal connections
  
  celery-worker:
    # Connects to redis using service name

networks:
  default:
    enable_ipv6: true  # ✅ Critical for Supabase
    ipam:
      config:
        - subnet: 172.20.0.0/16
        - subnet: 2001:db8:1::/64
```

### .env Configuration

```bash
# Database - URL encoded password
SUPABASE_DB_URL="postgresql://postgres:%2FvWHV5T94%23Mu@db.nekejilptmnbzhmglmyc.supabase.co:6543/postgres"

# Redis - Use service name, not localhost
REDIS_URL=redis://redis:6379/0
```

### .dockerignore

```dockerignore
# Exclude log files but keep the logs app
logs/*.log
logs/__pycache__/
*.log
```

---

## Key Takeaways

### 1. Environment Variable Changes
**Always recreate containers after `.env` changes:**
```bash
docker-compose down
docker-compose up -d
```
`docker-compose restart` does NOT reload `.env` files.

### 2. Service Names vs Localhost
In Docker Compose, services communicate using service names:
- ✅ `redis://redis:6379/0` (service name)
- ❌ `redis://localhost:6379/0` (won't work in containers)

### 3. IPv6 Support
If connecting to IPv6-only services (like Supabase), enable IPv6 in Docker network:
```yaml
networks:
  default:
    enable_ipv6: true
```

### 4. Mac Docker Desktop Limitations
- `network_mode: host` doesn't work properly
- Use bridge networking with port mapping instead
- IPv6 must be explicitly enabled

### 5. Volume Mounts
Be careful with volume mounts - they can overwrite application code:
- Use different paths for data volumes vs app code
- Example: `/app/logs_data` for data, `/app/logs` for app code

---

## Useful Commands

### Check Container Status
```bash
docker-compose ps
```

### View Logs
```bash
docker-compose logs backend
docker-compose logs celery-worker
docker-compose logs -f  # Follow all logs
```

### Test Connectivity
```bash
# Test from host
curl http://localhost:8000/health/

# Test from container
docker-compose exec backend curl http://localhost:8000/health/
```

### Recreate After Changes
```bash
docker-compose down
docker-compose up -d
```

### Rebuild Images
```bash
docker-compose build --no-cache
docker-compose up -d
```

---

## Common Issues & Quick Fixes

| Issue | Quick Fix |
|-------|-----------|
| Module not found | Check `.dockerignore` isn't excluding app directories |
| Redis connection refused | Use `redis://redis:6379/0` not `localhost` |
| Database connection failed | Enable IPv6 in network config |
| Port not accessible | Check port mapping: `"8000:8000"` |
| .env changes not applied | Run `docker-compose down && docker-compose up -d` |
| Container keeps restarting | Check logs: `docker-compose logs backend` |

---

## Final Status

✅ **All Services Working:**
- Backend: `http://localhost:8000` (healthy)
- Database: Connected to Supabase (IPv6)
- Redis: Connected (service name)
- Celery: Running and connected to Redis

✅ **Frontend can connect:**
- API endpoints accessible
- Login endpoint working
- Health checks passing

---

## Notes

- The password encoding (`%2FvWHV5T94%23Mu`) was never the issue - it was correctly decoded
- The real problem was Docker's lack of IPv6 support by default
- Mac Docker Desktop has limitations compared to Linux Docker
- Always test connectivity from both inside and outside containers

---

*Last Updated: November 2025*

