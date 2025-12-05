# Docker Setup for PostBro Backend

## Quick Start

1. **Create `.env` file** (copy from your existing `.env` or use the template below)
2. **Build and run:**
   ```bash
   docker-compose up -d
   ```
3. **Check logs:**
   ```bash
   docker-compose logs -f
   ```

## Environment Variables

Create a `.env` file in `postbro_backend/` with these variables:

```bash
# Django
SECRET_KEY=your-secret-key
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,postbro.app

# Database (Supabase PostgreSQL)
SUPABASE_DB_URL=postgresql://user:password@host:port/database

# Redis (will use internal Docker network)
REDIS_URL=redis://redis:6379/0

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:3000,https://postbro.app

# Gemini API
GEMINI_API_KEY=your-gemini-api-key

# BrightData
BRIGHTDATA_API_KEY=your-brightdata-key

# Optional: Self-hosted LLM
AI_PROVIDER=gemini
SELF_HOSTED_LLM_URL=http://localhost:8000
```

## Services

- **backend**: Django API (Gunicorn) on port 8000
- **celery-worker**: Celery worker for async tasks
- **celery-beat**: Celery beat for scheduled tasks
- **redis**: Redis for Celery broker

## Volumes

- `media_volume`: Media files (uploads, processed images/videos)
- `static_volume`: Static files (collected by Django)
- `logs_volume`: Application logs
- `redis_data`: Redis persistence

## Commands

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# View logs
docker-compose logs -f backend
docker-compose logs -f celery-worker

# Rebuild after code changes
docker-compose up -d --build

# Run migrations
docker-compose exec backend python manage.py migrate

# Create superuser
docker-compose exec backend python manage.py createsuperuser

# Access Django shell
docker-compose exec backend python manage.py shell

# Restart a specific service
docker-compose restart backend
```

## Health Checks

- Backend: `http://localhost:8000/api/analysis/`
- Redis: `redis-cli ping` (inside container)
- Celery: `celery inspect ping`

## Notes

- **No PostgreSQL container**: Using Supabase PostgreSQL (external)
- **Media files**: Stored in Docker volume, consider backing up
- **Static files**: Collected on container start
- **Logs**: Available in `logs_volume` and via `docker-compose logs`

## Production Considerations

1. **Use proper secrets management** (not `.env` file)
2. **Set up SSL/TLS** with Nginx reverse proxy
3. **Configure backups** for media volume
4. **Monitor resource usage** (CPU, memory)
5. **Set up log rotation**
6. **Use Docker secrets** or environment variable injection

