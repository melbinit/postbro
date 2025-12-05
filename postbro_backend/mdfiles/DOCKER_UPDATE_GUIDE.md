# Docker Update Guide - URLs-Only Changes

## What Changed

1. **Database Migrations** (2 new migrations):
   - `accounts.0005_update_plan_limits_urls_only` - Updates plan limits and prices
   - `analysis.0009_remove_username_fields` - Removes username/date fields from PostAnalysisRequest

2. **Backend Code Changes**:
   - Serializers updated (URL validation, single URL requirement)
   - Views updated (removed username logic)
   - Utils updated (simplified usage checking)

3. **Frontend Code Changes**:
   - Form updated (single URL input, frontend validation)
   - API types updated

## How Docker Handles These Changes

### ✅ Automatic Migration Execution

Your `docker-compose.yml` already runs migrations on startup:

```yaml
command: >
  sh -c "
  python manage.py collectstatic --noinput &&
  python manage.py migrate --noinput &&  # ← Migrations run automatically!
  gunicorn postbro.wsgi:application ...
  "
```

**What this means:**
- When you restart/rebuild containers, migrations will run automatically
- No manual migration steps needed
- Database will be updated to match the new schema

### 🔄 Steps to Deploy Changes to Docker

#### Option 1: Rebuild Containers (Recommended for Code Changes)

```bash
# Stop current containers
docker-compose down

# Rebuild images with new code
docker-compose build

# Start containers (migrations run automatically)
docker-compose up -d

# Check logs to verify migrations ran
docker-compose logs backend | grep -i migration
```

#### Option 2: Just Restart (If Only Migrations Changed)

```bash
# Restart containers (migrations run on startup)
docker-compose restart backend

# Check migration status
docker-compose exec backend python manage.py showmigrations accounts analysis
```

### 📋 Verification Steps

After containers are running:

1. **Check Migrations Applied:**
   ```bash
   docker-compose exec backend python manage.py showmigrations accounts analysis
   ```
   
   Should show:
   ```
   accounts
    [X] 0005_update_plan_limits_urls_only
   analysis
    [X] 0009_remove_username_fields
   ```

2. **Verify Plan Limits:**
   ```bash
   docker-compose exec backend python manage.py shell -c "
   from accounts.models import Plan
   for plan in Plan.objects.all():
       print(f'{plan.name}: {plan.max_urls} URLs/day, \${plan.price}/month')
   "
   ```
   
   Should show:
   ```
   Free: 3 URLs/day, $0.00/month
   Basic: 10 URLs/day, $19.00/month
   Pro: 30 URLs/day, $49.00/month
   ```

3. **Test API Endpoint:**
   ```bash
   curl -X POST http://localhost:8000/api/analysis/analyze/ \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -d '{
       "platform": "x",
       "post_urls": ["https://x.com/test/status/123"]
     }'
   ```

### ⚠️ Important Notes

1. **Database Persistence:**
   - Migrations modify the database schema
   - Your database (Supabase) is external, so changes persist
   - No data loss (we only removed unused fields)

2. **Frontend Changes:**
   - Frontend code changes require rebuilding the frontend container/image
   - If frontend is in a separate Docker setup, rebuild that too
   - Or if frontend is deployed separately, deploy those changes

3. **Rollback (If Needed):**
   ```bash
   # If you need to rollback migrations
   docker-compose exec backend python manage.py migrate accounts 0004
   docker-compose exec backend python manage.py migrate analysis 0008
   ```

### 🚀 Quick Deploy Command

```bash
# One-liner to rebuild and restart
docker-compose down && docker-compose build && docker-compose up -d && docker-compose logs -f backend
```

### 📊 What Happens on Container Start

1. **Backend Container Starts:**
   - Runs `collectstatic` (collects static files)
   - Runs `migrate --noinput` (applies new migrations automatically)
   - Starts Gunicorn server

2. **Migrations Run:**
   - `0005_update_plan_limits_urls_only` updates plan limits
   - `0009_remove_username_fields` removes username fields from database

3. **Server Ready:**
   - API accepts only URLs (no username)
   - Plan limits enforced (3/10/30 URLs per day)
   - URL validation active

### 🔍 Troubleshooting

**If migrations fail:**
```bash
# Check migration status
docker-compose exec backend python manage.py showmigrations

# Check database connection
docker-compose exec backend python manage.py check --database default

# View detailed error
docker-compose logs backend
```

**If containers won't start:**
```bash
# Check logs
docker-compose logs backend

# Try rebuilding from scratch
docker-compose down -v  # ⚠️ Removes volumes (data loss!)
docker-compose build --no-cache
docker-compose up -d
```

### ✅ Summary

**No Docker configuration changes needed!** 

The existing setup already:
- ✅ Runs migrations automatically
- ✅ Copies all code changes
- ✅ Handles database updates

**You just need to:**
1. Rebuild containers to get new code
2. Restart to apply migrations
3. Verify everything works

The migrations will run automatically when containers start! 🎉

