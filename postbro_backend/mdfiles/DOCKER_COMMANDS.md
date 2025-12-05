# Docker Commands Cheat Sheet

## Basic Commands

### Start containers
```bash
docker-compose up -d
```
- `-d` runs in background (detached mode)
- Starts all services defined in docker-compose.yml

### Stop containers
```bash
docker-compose stop
```
- Stops containers but keeps them (can restart quickly)

### Stop and remove containers
```bash
docker-compose down
```
- Stops and removes containers
- Removes network (but keeps volumes)

### Restart containers
```bash
docker-compose restart
```
- Restarts containers (doesn't reload .env changes)

### Restart with new .env changes
```bash
docker-compose down
docker-compose up -d
```
- Use this when you update .env file

## View Status & Logs

### Check container status
```bash
docker-compose ps
```
- Shows running containers and their status

### View logs
```bash
# All services
docker-compose logs

# Specific service
docker-compose logs backend
docker-compose logs celery-worker
docker-compose logs redis

# Follow logs (live updates)
docker-compose logs -f backend

# Last 50 lines
docker-compose logs --tail=50 backend
```

## Execute Commands

### Run command in container
```bash
docker-compose exec backend python manage.py migrate
docker-compose exec backend python manage.py createsuperuser
docker-compose exec backend bash  # Open shell
```

## Rebuild (after code changes)

### Rebuild and restart
```bash
docker-compose build
docker-compose up -d
```

### Force rebuild (no cache)
```bash
docker-compose build --no-cache
docker-compose up -d
```

## Quick Health Check

### Test health endpoint
```bash
curl http://localhost:8000/health/
```

### Check all services
```bash
docker-compose ps
docker-compose logs --tail=20
```

## Common Workflows

### After updating .env file
```bash
docker-compose down
docker-compose up -d
```

### After code changes
```bash
docker-compose restart backend
# Or rebuild if dependencies changed:
docker-compose build backend
docker-compose up -d
```

### View real-time logs
```bash
docker-compose logs -f
```

### Stop everything
```bash
docker-compose down
```

### Start everything
```bash
docker-compose up -d
```

