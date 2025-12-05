# 🔄 How to Sync Django Models with Supabase

## The Problem

You have:
- ✅ **Django Models** in `models.py` (Plan, Subscription, UserUsage, Platform, Post, etc.)
- ✅ **Some tables in Supabase** (from `SUPABASE_SCHEMA.sql`: plans, subscriptions, user_usage, user_profiles)
- ❌ **Missing tables in Supabase** (platforms, posts, post_media, post_comments, user_post_activities, app_logs)

## Two Approaches

### **Option A: Django Migrations** (Recommended) ✅

Django can automatically create tables from your models!

**How it works:**
1. Django reads your `models.py` files
2. Generates SQL to create tables
3. Runs the SQL in Supabase database
4. Creates all missing tables

**Steps:**
```bash
# 1. Make sure Django is connected to Supabase (already done ✅)
# 2. Create migration files (if needed)
python manage.py makemigrations

# 3. Apply migrations to Supabase
python manage.py migrate
```

**Pros:**
- ✅ Automatic - Django handles everything
- ✅ Keeps models and database in sync
- ✅ Version controlled (migration files)
- ✅ Can rollback if needed

**Cons:**
- ⚠️ Might conflict with existing tables (plans, subscriptions, etc.)
- ⚠️ Need to handle existing data carefully

---

### **Option B: Manual SQL** (More Control)

Create SQL files and run them in Supabase SQL Editor.

**How it works:**
1. Write SQL matching your Django models
2. Run SQL in Supabase dashboard
3. Tables created manually

**Pros:**
- ✅ Full control over table structure
- ✅ Can add custom indexes, triggers, RLS policies
- ✅ No conflicts with existing tables

**Cons:**
- ❌ Manual work
- ❌ Need to keep SQL and models in sync manually
- ❌ More error-prone

---

## 🎯 Recommended Approach: Hybrid

**For existing tables** (plans, subscriptions, user_usage):
- ✅ Already created in Supabase via SQL
- ✅ Keep them as-is
- ⚠️ Make sure Django models match exactly

**For missing tables** (platforms, posts, etc.):
- ✅ Use Django migrations
- ✅ Run `python manage.py migrate`
- ✅ Django will create them automatically

---

## Step-by-Step: Sync Everything

### Step 1: Check What Tables Exist

**In Supabase:**
```sql
-- Run in SQL Editor
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public'
ORDER BY table_name;
```

**In Django:**
```bash
python manage.py showmigrations
```

### Step 2: Handle Existing Tables

**Option A: Keep Supabase tables, update Django models**
- Make Django models match Supabase schema exactly
- Mark migrations as already applied: `python manage.py migrate --fake`

**Option B: Drop and recreate** (⚠️ loses data)
- Drop tables in Supabase
- Run Django migrations fresh

### Step 3: Create Missing Tables

```bash
# Generate migrations for new/changed models
python manage.py makemigrations

# Apply to Supabase
python manage.py migrate
```

---

## ⚠️ Important: User Model Conflict

**The Big Issue:**
- Django has: `User` model (accounts.User)
- Supabase has: `auth.users` (built-in)

**Solution Options:**

1. **Use Supabase auth.users only** (Recommended)
   - Remove Django User model
   - Reference `auth.users` UUID in other models
   - Use Supabase for all authentication

2. **Sync both** (Complex)
   - Keep Django User model
   - Sync with Supabase auth.users
   - More maintenance

---

## 🚀 Quick Start: Create Missing Tables Now

### For Missing Tables (platforms, posts, etc.):

```bash
# 1. Make sure you're connected
python manage.py check --database default

# 2. Create migrations
python manage.py makemigrations

# 3. Apply to Supabase
python manage.py migrate
```

This will create:
- `social_platform`
- `social_post`
- `social_postmedia`
- `social_postcomment`
- `social_userpostactivity`
- `logs_applog`

(Note: Django adds app prefix to table names)

---

## 📋 Current Status

**Already in Supabase:**
- ✅ `plans` → Django model: `Plan`
- ✅ `subscriptions` → Django model: `Subscription`
- ✅ `user_usage` → Django model: `UserUsage`
- ✅ `user_profiles` → No Django model (Supabase only)

**Missing in Supabase:**
- ❌ `platforms` → Django model: `Platform`
- ❌ `posts` → Django model: `Post`
- ❌ `post_media` → Django model: `PostMedia`
- ❌ `post_comments` → Django model: `PostComment`
- ❌ `user_post_activities` → Django model: `UserPostActivity`
- ❌ `app_logs` → Django model: `AppLog`

**Next:** Run migrations to create missing tables! 🎯

