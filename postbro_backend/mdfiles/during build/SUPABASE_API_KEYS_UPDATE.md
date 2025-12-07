# 🔑 Supabase API Keys Update

## What Changed?

Supabase is transitioning from **legacy API keys** to **new API keys** for better security and management.

### Legacy Keys (Being Deprecated)
- `anon` key (public key)
- `service_role` key (secret key)

### New Keys (Current Standard)
- **Publishable key** (`sb_publishable_...`) - Replaces `anon` key
- **Secret key** (`sb_secret_...`) - Replaces `service_role` key

## Timeline

- **June 2025**: New keys introduced
- **July 2025**: Full feature launch
- **November 2025**: Migration reminders begin
- **Late 2026**: Legacy keys deprecated (mandatory migration)

## Which Keys Should You Use?

**Use the NEW keys if you see them:**
- ✅ Better security
- ✅ Future-proof
- ✅ Better key management

**Legacy keys still work** but will be removed in 2026.

## How to Use in Your Code

### Option 1: New Keys (Recommended)

```python
# .env file
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_PUBLISHABLE_KEY=sb_publishable_...
SUPABASE_SECRET_KEY=sb_secret_...

# Python code
from supabase import create_client

supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_SECRET_KEY')  # Use secret key for backend
)
```

### Option 2: Legacy Keys (Still Works)

```python
# .env file
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=eyJhbGc...  # anon key
SUPABASE_SERVICE_ROLE_KEY=eyJhbGc...  # service_role key

# Python code
from supabase import create_client

supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_ROLE_KEY')  # Use service_role for backend
)
```

## What You Need to Do

1. **Check your Supabase dashboard** - Do you see "Publishable key" or "anon key"?
2. **Use the new keys if available** - They're the future standard
3. **Update your `.env` file** - Use the appropriate variable names
4. **The Supabase Python client works with both** - No code changes needed!

## Your Current Setup

Based on what you're seeing:
- ✅ You have **NEW API keys** (Publishable/Secret)
- ✅ Use `SUPABASE_PUBLISHABLE_KEY` and `SUPABASE_SECRET_KEY` in your `.env`
- ✅ The Supabase client will work with these automatically

## Security Notes

- **Publishable key**: Safe for frontend/browser (if RLS is enabled)
- **Secret key**: Backend only! Never expose in frontend code
- **Service role key**: Same as secret key (legacy name)

---

**Bottom line:** Use the new keys (publishable/secret) if you see them. They work the same way, just with better names and security! 🔒

