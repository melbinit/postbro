# Supabase Migration Guide for PostBro

## 🎯 Why Supabase?

- **Managed Database**: No need to manage PostgreSQL yourself
- **Built-in Auth**: Email/password, OAuth, magic links out of the box
- **Auto-scaling**: Handles 1000+ users easily
- **Real-time**: Built-in real-time subscriptions
- **Storage**: File uploads handled automatically
- **Free Tier**: Generous free tier to start

## 📋 Step-by-Step Setup

### Step 1: Create Supabase Project

1. Go to [https://supabase.com](https://supabase.com)
2. Sign up / Log in
3. Click "New Project"
4. Fill in:
   - **Name**: `postbro` (or your choice)
   - **Database Password**: Generate a strong password (SAVE THIS!)
   - **Region**: Choose closest to your users
   - **Pricing Plan**: Free tier is fine to start

5. Wait 2-3 minutes for project to initialize

### Step 2: Get Your Supabase Credentials

1. Go to **Settings** → **API** in your Supabase dashboard
2. You'll see either **NEW API Keys** or **Legacy API Keys** (or both)
3. Copy these values:

**For NEW API Keys (Recommended - Supabase is migrating to these):**
   - **Project URL** → `SUPABASE_URL`
   - **Publishable key** → `SUPABASE_PUBLISHABLE_KEY` (safe for frontend)
   - **Secret key** → `SUPABASE_SECRET_KEY` (backend only, keep secret!)

**For Legacy API Keys (Still work, but deprecated in 2026):**
   - **Project URL** → `SUPABASE_URL`
   - **anon/public key** → `SUPABASE_KEY`
   - **service_role key** → `SUPABASE_SERVICE_ROLE_KEY` (keep secret!)

> **Note:** Supabase introduced new API keys in 2024. New projects get both, but you should use the new keys (publishable/secret) going forward. The Supabase Python client works with both formats.

3. Go to **Settings** → **Database**
4. Under "Connection string", copy the **URI** format
   - Replace `[YOUR-PASSWORD]` with your database password
   - This becomes `SUPABASE_DB_URL`

### Step 3: Create .env File

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Fill in all the Supabase values you copied

3. Generate a Django secret key:
   ```bash
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```
   Paste this into `SECRET_KEY`

### Step 4: Install Supabase Python Client

```bash
pip install supabase
```

Or add to `requirements.txt` and install:
```bash
pip install -r requirements.txt
```

### Step 5: Create Database Schema in Supabase

You have two options:

#### Option A: Use Supabase SQL Editor (Recommended for Migration)

1. Go to **SQL Editor** in Supabase dashboard
2. Create tables matching your Django models (see `SUPABASE_SCHEMA.sql`)

#### Option B: Use Django Migrations (Hybrid Approach)

1. Update `settings.py` to use Supabase database
2. Run migrations: `python manage.py migrate`
3. This creates tables in Supabase

### Step 6: Update Django Settings

Update `postbro/settings.py`:

```python
import os
from pathlib import Path
import dj_database_url

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Database - Use Supabase
DATABASES = {
    'default': dj_database_url.config(
        default=os.getenv('SUPABASE_DB_URL'),
        conn_max_age=600
    )
}

# Supabase Client
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
```

### Step 7: Update Authentication

**Remove Django Auth, Use Supabase Auth:**

1. **Remove** from `INSTALLED_APPS`:
   - `django.contrib.auth` (keep for admin)
   - `rest_framework.authtoken`
   - `djangorestframework-simplejwt`
   - `allauth` related apps

2. **Update REST Framework** to use Supabase tokens:
   ```python
   REST_FRAMEWORK = {
       'DEFAULT_AUTHENTICATION_CLASSES': (
           'accounts.authentication.SupabaseAuthentication',
       ),
       'DEFAULT_PERMISSION_CLASSES': (
           'rest_framework.permissions.IsAuthenticated',
       ),
   }
   ```

3. **Create Supabase Auth middleware** (see `accounts/authentication.py`)

### Step 8: Update User Model

Since Supabase handles users, you have two options:

**Option A: Sync with Supabase Users (Recommended)**
- Keep your custom User model for additional fields
- Sync with Supabase Auth users via webhooks or triggers
- Use Supabase user ID as foreign key

**Option B: Use Supabase Users Only**
- Remove custom User model
- Reference Supabase user UUID directly in other models
- Store additional user data in Supabase `auth.users` metadata or separate table

## 🔄 Migration Strategy

### Phase 1: Database Migration
1. Create Supabase project
2. Create schema in Supabase (SQL or Django migrations)
3. Update Django to connect to Supabase database
4. Test connection

### Phase 2: Auth Migration
1. Set up Supabase Auth
2. Create authentication middleware
3. Update API endpoints to use Supabase tokens
4. Test authentication flow

### Phase 3: Data Migration (if you have existing data)
1. Export existing users/data
2. Import into Supabase
3. Map user IDs if needed

## 📁 New File Structure

```
postbro_backend/
├── accounts/
│   ├── authentication.py    # Supabase auth middleware
│   ├── supabase_client.py   # Supabase client singleton
│   └── views.py             # Updated to use Supabase
├── postbro/
│   └── settings.py          # Updated with Supabase config
└── .env                      # Your credentials (gitignored)
```

## 🔐 Security Notes

1. **Never commit `.env` file** - it's in `.gitignore`
2. **Service Role Key** is powerful - only use server-side
3. **Anon Key** is safe for frontend
4. **Database Password** - store securely
5. **Enable Row Level Security (RLS)** in Supabase for security

## 🚀 What You Get

✅ **No Database Management**: Supabase handles backups, scaling, maintenance
✅ **Built-in Auth**: Signup, login, password reset, email verification
✅ **Real-time**: Subscribe to database changes
✅ **Storage**: Upload profile images directly to Supabase
✅ **Dashboard**: Visual database editor, logs, monitoring
✅ **Free Tier**: 500MB database, 2GB bandwidth, 50,000 monthly active users

## 📚 Next Steps

1. Follow steps 1-3 to set up Supabase
2. Create `.env` file with credentials
3. We'll update the codebase together
4. Test authentication flow
5. Deploy!

## 🆘 Troubleshooting

**Connection Issues:**
- Check database password is correct
- Verify connection string format
- Check if IP is allowed (Supabase allows all by default)

**Auth Issues:**
- Verify API keys are correct
- Check Supabase Auth settings
- Ensure email templates are configured

**Migration Issues:**
- Run migrations one at a time
- Check for foreign key constraints
- Verify table names match

---

**Ready to start?** Let's begin with Step 1! 🎉

