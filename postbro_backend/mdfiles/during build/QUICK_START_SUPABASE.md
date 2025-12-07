# 🚀 Quick Start: Supabase Setup for PostBro

## Step 1: Create Supabase Account & Project (5 minutes)

1. Go to **[supabase.com](https://supabase.com)** and sign up
2. Click **"New Project"**
3. Fill in:
   - **Name**: `postbro`
   - **Database Password**: Click "Generate" and **SAVE IT** (you'll need it!)
   - **Region**: Choose closest to you
   - **Pricing**: Free tier
4. Click **"Create new project"** and wait 2-3 minutes

## Step 2: Get Your Credentials (2 minutes)

### From API Settings:
1. Go to **Settings** → **API** (left sidebar)
2. You'll see **NEW API KEYS** (recommended) or **Legacy API Keys**
3. Copy these values:

**If you see NEW keys (Publishable/Secret):**
   ```
   Project URL: https://xxxxx.supabase.co
   Publishable key: sb_publishable_...
   Secret key: sb_secret_... (KEEP SECRET! Backend only!)
   ```

**If you see Legacy keys (anon/service_role):**
   ```
   Project URL: https://xxxxx.supabase.co
   anon public key: eyJhbGc...
   service_role key: eyJhbGc... (KEEP SECRET!)
   ```

> **Note:** Supabase is migrating to new keys. New projects get both, but use the new ones (publishable/secret) going forward. Legacy keys will be deprecated in 2026.

### From Database Settings:
1. Go to **Settings** → **Database** (left sidebar)
2. Scroll down to **Connection string** section
3. Click the dropdown and select **URI** (not Session or Transaction)
4. Copy the connection string - it will look like:
   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.xxxxx.supabase.co:5432/postgres
   ```
5. **Important**: Replace `[YOUR-PASSWORD]` with your actual database password (the one you set when creating the project)

**Why you need this:** Django needs this to connect to your Supabase database for your models (Plan, Subscription, UserUsage, etc.)

Example after replacing password:
```
postgresql://postgres:MySecurePassword123@db.xxxxx.supabase.co:5432/postgres
```

## Step 3: Create .env File (1 minute)

1. In your project root (`postbro_backend/`), create a file named `.env`
2. Copy the template from `env.example` or use this:

```bash
# Django
DEBUG=True
SECRET_KEY=generate-this-with-command-below

# Supabase (paste your values from Step 2)
SUPABASE_URL=https://xxxxx.supabase.co

# NEW API Keys (if you see Publishable/Secret keys)
SUPABASE_PUBLISHABLE_KEY=sb_publishable_...
SUPABASE_SECRET_KEY=sb_secret_...

# OR Legacy API Keys (if you see anon/service_role keys)
# SUPABASE_KEY=eyJhbGc...
# SUPABASE_SERVICE_ROLE_KEY=eyJhbGc...

SUPABASE_DB_URL=postgresql://postgres:password@db.xxxxx.supabase.co:5432/postgres

# Other services
REDIS_URL=redis://localhost:6379/0
STRIPE_PUBLIC_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...
ANTHROPIC_API_KEY=sk-ant-...
```

3. Generate Django secret key:
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```
Paste the output into `SECRET_KEY` in `.env`

## Step 4: Install Dependencies (1 minute)

```bash
cd postbro_backend
pip install -r requirements.txt
```

This installs `supabase` and `dj-database-url` packages.

## Step 5: Create Database Schema (2 minutes)

1. In Supabase dashboard, go to **SQL Editor** (left sidebar)
2. Click **"New query"**
3. Copy and paste the entire contents of `SUPABASE_SCHEMA.sql`
4. Click **"Run"** (or press Cmd/Ctrl + Enter)
5. You should see "Success. No rows returned"

This creates:
- ✅ Plans table (with default plans)
- ✅ User profiles table
- ✅ Subscriptions table
- ✅ User usage table
- ✅ Security policies (RLS)

## Step 6: Test Connection (1 minute)

```bash
python manage.py check --database default
```

If it works, you're connected! 🎉

## Step 7: Configure Supabase Auth (Optional - 5 minutes)

1. Go to **Authentication** → **Settings** in Supabase
2. Configure:
   - **Site URL**: `http://localhost:3000` (your frontend)
   - **Redirect URLs**: Add `http://localhost:3000/**`
   - **Email Templates**: Customize if needed (optional)

## ✅ You're Done!

Your Supabase is set up. Next steps:
1. Update Django settings to use Supabase (we'll do this next)
2. Create authentication middleware
3. Update API views

## 🆘 Troubleshooting

**"Connection refused"**
- Check your database password is correct
- Verify connection string format
- Make sure project is fully initialized (wait a few minutes)

**"Authentication failed"**
- Double-check your API keys
- Make sure you copied the full key (they're long!)

**"Table doesn't exist"**
- Run the SQL schema again
- Check SQL Editor for any errors

---

**Total time: ~15 minutes** ⏱️

Ready for the next step? Let me know when you've completed these steps!

