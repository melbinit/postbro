# PostBro Backend - Implementation Documentation

## Overview

PostBro is a scalable SaaS backend built with Django and PostgreSQL. This document details all the features we've planned and implemented for the authentication and user management system.

## Project Structure

```
postbro_backend/
├── accounts/          # User management and authentication
├── social/            # Social media post handling
├── analysis/          # Post analysis and suggestions
├── feedback/          # User feedback system
├── billing/           # Payment processing
├── logs/              # Application logging
└── postbro/           # Main Django project configuration
```

## Tech Stack

- **Django 5.0.14** - Web framework
- **PostgreSQL** - Database
- **Django REST Framework** - API framework
- **djangorestframework-simplejwt** - JWT authentication
- **Django AllAuth** - Authentication library
- **Celery + Redis** - Asynchronous task processing
- **Pillow** - Image processing for profile images

## Authentication System

### 1. User Model (`accounts/models.py`)

We've created a custom User model that extends Django's `AbstractUser` with the following features:

#### Key Features:
- **Email-based authentication** (username disabled)
- **UUID primary keys** for better security and scalability
- **Email verification system** with tokens
- **Profile image support**
- **Password reset functionality**

#### Model Fields:

```python
class User(AbstractUser):
    # Core fields
    id = UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = EmailField(unique=True)  # Used as USERNAME_FIELD
    username = None  # Disabled
    
    # User information
    full_name = CharField(max_length=255, blank=True)
    company_name = CharField(max_length=255, blank=True)
    
    # Email verification
    email_verified = BooleanField(default=False)
    email_verification_token = UUIDField(null=True, blank=True)
    email_verification_sent_at = DateTimeField(null=True, blank=True)
    
    # Profile
    profile_image = ImageField(upload_to='profile_images/', null=True, blank=True)
    
    # Password reset
    password_reset_token = UUIDField(null=True, blank=True)
    password_reset_sent_at = DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
```

#### Related Models:
- **Plan**: Subscription plans with pricing and limits
- **Subscription**: User subscriptions to plans
- **UserUsage**: Daily usage tracking per platform

### 2. Serializers (`accounts/serializers.py`)

#### SignupSerializer
- Validates email uniqueness (case-insensitive)
- Validates password strength using Django's validators
- Creates user with `is_active=False` until email is verified
- Fields: `email`, `password`, `full_name`, `company_name`

#### LoginSerializer
- Authenticates user with email and password
- Validates that user is active
- Validates that email is verified
- Returns user object for JWT token generation

#### ForgotPasswordSerializer
- Validates that email exists in the system
- Used to initiate password reset flow

#### ResetPasswordSerializer
- Validates password reset token
- Checks token expiration (24 hours)
- Validates password match and strength
- Fields: `token`, `email`, `password`, `confirm_password`

#### UserProfileSerializer
- Serializes user profile information
- Read-only fields: `id`, `email`, `created_at`, `updated_at`
- Editable fields: `full_name`, `company_name`, `profile_image`
- Validates minimum length for name fields

### 3. JWT Configuration (`postbro/settings.py`)

JWT authentication is configured using `djangorestframework-simplejwt`:

```python
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=7),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}
```

#### REST Framework Settings:
- Default authentication: JWT
- Default permission: IsAuthenticated
- Pagination: 20 items per page
- Filter backend: DjangoFilterBackend

### 4. Email Configuration

Currently configured for local development:
```python
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = 'noreply@postbro.com'
```

**Note**: For production, update to use SMTP or a service like SendGrid, AWS SES, etc.

### 5. Media Files Configuration

```python
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'
```

Profile images are stored in `media/profile_images/` directory.

## Planned API Endpoints

### ✅ Completed (Model & Serializers)

1. **Signup API** (`POST /api/accounts/signup/`)
   - Status: Serializer ready, view needs implementation
   - Creates new user account
   - Sends email verification token
   - Returns user data (without sensitive info)

2. **Email Verification** (`POST /api/accounts/verify-email/`)
   - Status: Planned, needs implementation
   - Verifies email using token
   - Activates user account

3. **Login API** (`POST /api/accounts/login/`)
   - Status: Serializer ready, view needs implementation
   - Authenticates user
   - Returns access and refresh tokens
   - Requires email verification

4. **Token Refresh** (`POST /api/accounts/token/refresh/`)
   - Status: Provided by simplejwt, needs URL routing
   - Refreshes access token using refresh token

5. **Forgot Password** (`POST /api/accounts/forgot-password/`)
   - Status: Serializer ready, view needs implementation
   - Generates password reset token
   - Sends reset email with token

6. **Reset Password** (`POST /api/accounts/reset-password/`)
   - Status: Serializer ready, view needs implementation
   - Validates token and email
   - Updates user password
   - Token expires after 24 hours

7. **Get Current User** (`GET /api/accounts/me/`)
   - Status: Serializer ready, view needs implementation
   - Returns authenticated user's profile
   - Requires JWT authentication

8. **Update Profile** (`PATCH /api/accounts/me/`)
   - Status: Serializer ready, view needs implementation
   - Updates user profile (full_name, company_name, profile_image)
   - Requires JWT authentication
   - Supports image upload

9. **Logout**
   - Status: Frontend implementation
   - JWT tokens are stateless, so logout is handled on frontend
   - Frontend should delete tokens from storage
   - Optionally, implement token blacklisting for enhanced security

## Database Migrations

### Applied Migrations:

1. **0001_initial.py**: Initial User, Plan, Subscription, UserUsage models
2. **0002_user_password_reset_sent_at_and_more.py**: Added profile_image, password_reset_token, password_reset_sent_at fields
3. **0003_create_default_plans.py**: Creates default subscription plans

## Security Features

1. **Password Hashing**: Django's default PBKDF2 password hasher
2. **Password Validation**: Django's built-in validators (length, common passwords, etc.)
3. **JWT Tokens**: Secure token-based authentication
4. **Email Verification**: Prevents unauthorized account creation
5. **Token Expiration**: Access tokens (7 days), refresh tokens (1 day)
6. **Password Reset Expiration**: 24-hour validity for reset tokens

## Next Steps (Implementation Required)

### Priority 1: Core Authentication
1. Implement signup view with email verification
2. Implement email verification view
3. Implement login view with JWT tokens
4. Set up token refresh endpoint URLs

### Priority 2: Password Management
5. Implement forgot password view
6. Implement reset password view

### Priority 3: User Profile
7. Implement get current user view
8. Implement update profile view with image upload

### Priority 4: Additional Features
9. Add token blacklisting for logout (optional)
10. Add email resend verification endpoint
11. Add change password endpoint (for authenticated users)

## Testing Email Verification Locally

Since we're using console email backend, verification emails will be printed to the console/terminal where Django is running. Look for output like:

```
Content-Type: text/plain; charset="utf-8"
MIME-Version: 1.0
Content-Transfer-Encoding: 7bit
Subject: Verify your PostBro account
From: noreply@postbro.com
To: user@example.com
Date: ...

[Email content with verification link]
```

## Environment Variables

Create a `.env` file with:
```
DEBUG=True
SECRET_KEY=your-secret-key-here
DATABASE_URL=postgres://user:password@localhost:5432/postbro
REDIS_URL=redis://localhost:6379/0
STRIPE_PUBLIC_KEY=your-stripe-public-key
STRIPE_SECRET_KEY=your-stripe-secret-key
ANTHROPIC_API_KEY=your-anthropic-api-key
```

## Dependencies

Key packages used:
- `Django>=5.0.0,<5.1.0`
- `djangorestframework>=3.14.0`
- `djangorestframework-simplejwt` (needs to be added to requirements.txt)
- `psycopg2-binary>=2.9.9`
- `Pillow>=10.2.0`
- `django-allauth>=0.61.1`
- `celery>=5.3.6`
- `redis>=5.0.1`

## Notes

1. **Missing Package**: `djangorestframework-simplejwt` should be added to `requirements.txt`
2. **Views Not Implemented**: All API views need to be implemented in `accounts/views.py`
3. **URLs Not Configured**: `accounts/urls.py` needs to be created and configured
4. **Email Backend**: Currently using console backend for development
5. **Media Files**: Ensure `media/` directory exists and is writable
6. **CORS**: Configured for `localhost:3000` (update for production)

## File Structure Status

- ✅ `accounts/models.py` - Complete
- ✅ `accounts/serializers.py` - Complete
- ⚠️ `accounts/views.py` - Empty (needs implementation)
- ❌ `accounts/urls.py` - Missing (needs creation)
- ✅ `postbro/settings.py` - JWT configured
- ✅ `postbro/urls.py` - Basic structure (needs accounts URLs)

---

**Last Updated**: Based on conversation history
**Status**: Models and serializers complete, views and URLs pending implementation

