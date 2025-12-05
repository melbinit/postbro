# 🚀 Clerk Migration Quick Start

## ✅ What's Been Done

All backend code has been updated to use Clerk instead of Supabase Auth:

1. ✅ Created `accounts/clerk_client.py` - Clerk API client
2. ✅ Updated `accounts/authentication.py` - ClerkAuthentication class
3. ✅ Updated `accounts/models.py` - Added `clerk_user_id` field
4. ✅ Updated `accounts/views.py` - All auth endpoints use Clerk
5. ✅ Updated `postbro/settings.py` - Clerk configuration
6. ✅ Updated `requirements.txt` - Added dependencies

## 📋 Next Steps

### 1. Install Dependencies

```bash
cd postbro_backend
pip install -r requirements.txt
```

### 2. Create Database Migration

```bash
python manage.py makemigrations accounts
python manage.py migrate
```

This will:
- Add `clerk_user_id` field to User model
- Keep `supabase_user_id` for backward compatibility (can remove later)

### 3. Set Up Clerk Account

1. Go to [https://clerk.com](https://clerk.com) and sign up
2. Create a new application
3. Get your API keys from **"API Keys"** section:
   - Publishable Key (starts with `pk_test_` or `pk_live_`)
   - Secret Key (starts with `sk_test_` or `sk_live_`)

### 4. Configure Clerk

#### Enable Email/Password Auth
- Go to **"User & Authentication"** → **"Email, Phone, Username"**
- Enable **"Email address"** and **"Password"**

#### Enable Google OAuth
- Go to **"User & Authentication"** → **"Social Connections"**
- Click **"Configure"** on Google
- Add Google OAuth credentials (Client ID & Secret)
- Get redirect URL from Clerk and add to Google OAuth settings

#### Configure Password Reset
- Go to **"Email & Phone"** → **"Password reset"**
- Enable password reset
- Set redirect URL: `http://localhost:3000/reset-password` (or your frontend URL)

### 5. Update Environment Variables

Add to your `.env` file:

```bash
# Clerk Configuration
CLERK_PUBLISHABLE_KEY=pk_test_...
CLERK_SECRET_KEY=sk_test_...
CLERK_FRONTEND_URL=http://localhost:3000
```

**Note:** You can keep Supabase keys if you're still using Supabase for database:
```bash
# Supabase (for database only, not auth)
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_SECRET_KEY=...  # Only needed if using Supabase database
```

### 6. Test the Migration

#### Test Signup:
```bash
curl -X POST http://localhost:8000/api/accounts/signup/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "test123456",
    "full_name": "Test User"
  }'
```

#### Test Login (Token-based):
```bash
# First, get token from Clerk frontend SDK, then:
curl -X POST http://localhost:8000/api/accounts/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "token": "YOUR_CLERK_JWT_TOKEN"
  }'
```

#### Test Protected Endpoint:
```bash
curl -X GET http://localhost:8000/api/accounts/me/ \
  -H "Authorization: Bearer YOUR_CLERK_JWT_TOKEN"
```

### 7. Update Frontend

Your frontend needs to use Clerk's SDK:

```bash
# Install Clerk SDK
npm install @clerk/nextjs
# or
npm install @clerk/clerk-react
```

Wrap your app:
```tsx
import { ClerkProvider } from '@clerk/nextjs'

export default function RootLayout({ children }) {
  return (
    <ClerkProvider publishableKey={process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY}>
      {children}
    </ClerkProvider>
  )
}
```

Use Clerk hooks:
```tsx
import { useUser, useAuth } from '@clerk/nextjs'

function MyComponent() {
  const { user, isSignedIn } = useUser()
  const { getToken } = useAuth()
  
  // Get token for API calls
  const token = await getToken()
  
  // Make API request
  fetch('/api/endpoint', {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  })
}
```

## 🔄 Key Changes from Supabase

| Feature | Supabase | Clerk |
|---------|----------|-------|
| **User ID Field** | `supabase_user_id` (UUID) | `clerk_user_id` (string) |
| **Signup** | `supabase.auth.sign_up()` | `clerk.create_user()` |
| **Login** | `supabase.auth.sign_in_with_password()` | Token verification (frontend handles login) |
| **Token Verification** | Manual JWT decode | `clerk.verify_token()` |
| **Password Reset** | `supabase.auth.reset_password_for_email()` | `clerk.create_password_reset_token()` |

## ⚠️ Important Notes

1. **Login Flow Changed**: With Clerk, the frontend typically handles login using Clerk SDK, then sends the JWT token to your backend. The backend endpoint accepts a `token` parameter.

2. **User ID Format**: Clerk user IDs are strings (not UUIDs), so the `clerk_user_id` field is a `CharField`.

3. **Email Verification**: Clerk handles this automatically - no manual verification endpoints needed.

4. **OAuth**: Google OAuth is configured in Clerk dashboard, not in your backend code.

5. **Migration**: Your existing test account will need to be recreated in Clerk, or you can migrate it using Clerk's API.

## 🐛 Troubleshooting

### "Clerk secret key must be set"
- Make sure `CLERK_SECRET_KEY` is in your `.env` file
- Restart your Django server after adding it

### "Invalid token" errors
- Make sure you're sending the token in the `Authorization: Bearer <token>` header
- Check that the token is from Clerk (not Supabase)

### "Failed to create user" errors
- Check Clerk dashboard to see if user already exists
- Verify email/password requirements in Clerk settings
- Check API key permissions

### Database migration errors
- Make sure you've run `python manage.py makemigrations accounts`
- If you have existing data, the migration will preserve `supabase_user_id` and add `clerk_user_id`

## 📚 Resources

- [Full Migration Guide](./CLERK_MIGRATION_GUIDE.md)
- [Clerk Documentation](https://clerk.com/docs)
- [Clerk Python SDK](https://github.com/clerk/clerk-sdk-python)
- [Clerk React/Next.js SDK](https://clerk.com/docs/quickstarts/nextjs)

---

**Ready to go!** After completing these steps, your backend will be fully migrated to Clerk. 🎉





## ✅ What's Been Done

All backend code has been updated to use Clerk instead of Supabase Auth:

1. ✅ Created `accounts/clerk_client.py` - Clerk API client
2. ✅ Updated `accounts/authentication.py` - ClerkAuthentication class
3. ✅ Updated `accounts/models.py` - Added `clerk_user_id` field
4. ✅ Updated `accounts/views.py` - All auth endpoints use Clerk
5. ✅ Updated `postbro/settings.py` - Clerk configuration
6. ✅ Updated `requirements.txt` - Added dependencies

## 📋 Next Steps

### 1. Install Dependencies

```bash
cd postbro_backend
pip install -r requirements.txt
```

### 2. Create Database Migration

```bash
python manage.py makemigrations accounts
python manage.py migrate
```

This will:
- Add `clerk_user_id` field to User model
- Keep `supabase_user_id` for backward compatibility (can remove later)

### 3. Set Up Clerk Account

1. Go to [https://clerk.com](https://clerk.com) and sign up
2. Create a new application
3. Get your API keys from **"API Keys"** section:
   - Publishable Key (starts with `pk_test_` or `pk_live_`)
   - Secret Key (starts with `sk_test_` or `sk_live_`)

### 4. Configure Clerk

#### Enable Email/Password Auth
- Go to **"User & Authentication"** → **"Email, Phone, Username"**
- Enable **"Email address"** and **"Password"**

#### Enable Google OAuth
- Go to **"User & Authentication"** → **"Social Connections"**
- Click **"Configure"** on Google
- Add Google OAuth credentials (Client ID & Secret)
- Get redirect URL from Clerk and add to Google OAuth settings

#### Configure Password Reset
- Go to **"Email & Phone"** → **"Password reset"**
- Enable password reset
- Set redirect URL: `http://localhost:3000/reset-password` (or your frontend URL)

### 5. Update Environment Variables

Add to your `.env` file:

```bash
# Clerk Configuration
CLERK_PUBLISHABLE_KEY=pk_test_...
CLERK_SECRET_KEY=sk_test_...
CLERK_FRONTEND_URL=http://localhost:3000
```

**Note:** You can keep Supabase keys if you're still using Supabase for database:
```bash
# Supabase (for database only, not auth)
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_SECRET_KEY=...  # Only needed if using Supabase database
```

### 6. Test the Migration

#### Test Signup:
```bash
curl -X POST http://localhost:8000/api/accounts/signup/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "test123456",
    "full_name": "Test User"
  }'
```

#### Test Login (Token-based):
```bash
# First, get token from Clerk frontend SDK, then:
curl -X POST http://localhost:8000/api/accounts/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "token": "YOUR_CLERK_JWT_TOKEN"
  }'
```

#### Test Protected Endpoint:
```bash
curl -X GET http://localhost:8000/api/accounts/me/ \
  -H "Authorization: Bearer YOUR_CLERK_JWT_TOKEN"
```

### 7. Update Frontend

Your frontend needs to use Clerk's SDK:

```bash
# Install Clerk SDK
npm install @clerk/nextjs
# or
npm install @clerk/clerk-react
```

Wrap your app:
```tsx
import { ClerkProvider } from '@clerk/nextjs'

export default function RootLayout({ children }) {
  return (
    <ClerkProvider publishableKey={process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY}>
      {children}
    </ClerkProvider>
  )
}
```

Use Clerk hooks:
```tsx
import { useUser, useAuth } from '@clerk/nextjs'

function MyComponent() {
  const { user, isSignedIn } = useUser()
  const { getToken } = useAuth()
  
  // Get token for API calls
  const token = await getToken()
  
  // Make API request
  fetch('/api/endpoint', {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  })
}
```

## 🔄 Key Changes from Supabase

| Feature | Supabase | Clerk |
|---------|----------|-------|
| **User ID Field** | `supabase_user_id` (UUID) | `clerk_user_id` (string) |
| **Signup** | `supabase.auth.sign_up()` | `clerk.create_user()` |
| **Login** | `supabase.auth.sign_in_with_password()` | Token verification (frontend handles login) |
| **Token Verification** | Manual JWT decode | `clerk.verify_token()` |
| **Password Reset** | `supabase.auth.reset_password_for_email()` | `clerk.create_password_reset_token()` |

## ⚠️ Important Notes

1. **Login Flow Changed**: With Clerk, the frontend typically handles login using Clerk SDK, then sends the JWT token to your backend. The backend endpoint accepts a `token` parameter.

2. **User ID Format**: Clerk user IDs are strings (not UUIDs), so the `clerk_user_id` field is a `CharField`.

3. **Email Verification**: Clerk handles this automatically - no manual verification endpoints needed.

4. **OAuth**: Google OAuth is configured in Clerk dashboard, not in your backend code.

5. **Migration**: Your existing test account will need to be recreated in Clerk, or you can migrate it using Clerk's API.

## 🐛 Troubleshooting

### "Clerk secret key must be set"
- Make sure `CLERK_SECRET_KEY` is in your `.env` file
- Restart your Django server after adding it

### "Invalid token" errors
- Make sure you're sending the token in the `Authorization: Bearer <token>` header
- Check that the token is from Clerk (not Supabase)

### "Failed to create user" errors
- Check Clerk dashboard to see if user already exists
- Verify email/password requirements in Clerk settings
- Check API key permissions

### Database migration errors
- Make sure you've run `python manage.py makemigrations accounts`
- If you have existing data, the migration will preserve `supabase_user_id` and add `clerk_user_id`

## 📚 Resources

- [Full Migration Guide](./CLERK_MIGRATION_GUIDE.md)
- [Clerk Documentation](https://clerk.com/docs)
- [Clerk Python SDK](https://github.com/clerk/clerk-sdk-python)
- [Clerk React/Next.js SDK](https://clerk.com/docs/quickstarts/nextjs)

---

**Ready to go!** After completing these steps, your backend will be fully migrated to Clerk. 🎉




