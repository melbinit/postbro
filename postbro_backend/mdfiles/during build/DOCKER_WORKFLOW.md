# Docker Workflow - Updating Backend Changes

## 🔄 Standard Workflow (Most Common)

When you make **code changes** (views, serializers, models, etc.):

```bash
# 1. Stop containers
docker-compose down

# 2. Rebuild images (gets new code)
docker-compose build

# 3. Start containers (migrations run automatically)
docker-compose up -d

# 4. Check logs to verify
docker-compose logs -f backend
```

**One-liner:**
```bash
docker-compose down && docker-compose build && docker-compose up -d
```

---

## 📊 When You Add/Change Database Models

If you **create new migrations** (changed models):

```bash
# 1. Create migrations locally (outside Docker)
cd postbro_backend
source venv/bin/activate
python manage.py makemigrations

# 2. Rebuild and restart Docker
docker-compose down
docker-compose build
docker-compose up -d

# Migrations run automatically on startup ✅
```

**Verify migrations applied:**
```bash
docker-compose exec backend python manage.py showmigrations
```

---

## 🚀 Quick Restart (Code Changes Only, No Migrations)

If you **only changed code** (no model changes):

```bash
# Just restart (faster, no rebuild needed)
docker-compose restart backend

# Or rebuild specific service
docker-compose up -d --build backend
```

---

## 🔍 Check What Changed

**See if migrations are pending:**
```bash
docker-compose exec backend python manage.py showmigrations
```

**Check if code changes are reflected:**
```bash
# View backend logs
docker-compose logs backend

# Check if server is running
curl http://localhost:8000/health/
```

---

## 📋 Common Scenarios

### Scenario 1: Changed Python Code (views, serializers, utils)
```bash
docker-compose down && docker-compose build && docker-compose up -d
```

### Scenario 2: Changed Models (need migrations)
```bash
# Locally: Create migrations
python manage.py makemigrations

# Docker: Rebuild and restart
docker-compose down && docker-compose build && docker-compose up -d
```

### Scenario 3: Changed .env file
```bash
# Just restart (env_file is loaded on startup)
docker-compose restart backend celery-worker
```

### Scenario 4: Changed requirements.txt
```bash
# Rebuild (installs new packages)
docker-compose down
docker-compose build --no-cache  # Force fresh install
docker-compose up -d
```

### Scenario 5: Just want to see logs
```bash
docker-compose logs -f backend
```

---

## ⚡ Fastest Workflow (Development)

For **rapid development**, use volume mounts to see changes instantly:

**Option A: Use volumes (changes reflect immediately)**
```yaml
# In docker-compose.yml, add:
volumes:
  - .:/app  # Mounts current directory
```

Then just restart:
```bash
docker-compose restart backend
```

**Option B: Rebuild only when needed**
```bash
# Quick rebuild and restart
docker-compose up -d --build backend
```

---

## 🐛 Troubleshooting

**Container won't start:**
```bash
# Check logs
docker-compose logs backend

# Try rebuilding from scratch
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

**Migrations not running:**
```bash
# Run manually
docker-compose exec backend python manage.py migrate
```

**Code changes not showing:**
```bash
# Force rebuild
docker-compose down
docker-compose build --no-cache backend
docker-compose up -d
```

---

## 📝 Quick Reference Card

```bash
# 🔄 Standard update (most common)
docker-compose down && docker-compose build && docker-compose up -d

# ⚡ Quick restart (code only, no migrations)
docker-compose restart backend

# 📊 Check status
docker-compose ps
docker-compose logs backend

# 🔍 Verify migrations
docker-compose exec backend python manage.py showmigrations

# 🧹 Clean rebuild (if issues)
docker-compose down -v  # ⚠️ Removes volumes!
docker-compose build --no-cache
docker-compose up -d
```

---

## 💡 Pro Tips

1. **Use `--build` flag** to rebuild while starting:
   ```bash
   docker-compose up -d --build
   ```

2. **Watch logs in real-time:**
   ```bash
   docker-compose logs -f backend celery-worker
   ```

3. **Rebuild only one service:**
   ```bash
   docker-compose up -d --build backend
   ```

4. **Check container status:**
   ```bash
   docker-compose ps
   ```

5. **Access Django shell in container:**
   ```bash
   docker-compose exec backend python manage.py shell
   ```

---

## 🎯 TL;DR - Most Common Command

**For 90% of backend changes:**
```bash
docker-compose down && docker-compose build && docker-compose up -d
```

That's it! Migrations run automatically on startup. ✅

