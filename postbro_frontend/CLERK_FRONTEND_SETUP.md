# Clerk Frontend Integration - Setup Guide

## ✅ What's Been Done

1. ✅ Installed `@clerk/nextjs@latest`
2. ✅ Created `middleware.ts` with `clerkMiddleware()`
3. ✅ Updated `app/layout.tsx` with `<ClerkProvider>`
4. ✅ Updated API client to support Clerk tokens
5. ✅ Created `lib/clerk-auth.ts` helper utilities

## 📋 Next Steps

### 1. Add Environment Variables

Create or update `.env.local`:

```bash
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_YOUR_PUBLISHABLE_KEY
CLERK_SECRET_KEY=sk_test_YOUR_SECRET_KEY
```

**Get your keys from:** [Clerk Dashboard → API Keys](https://dashboard.clerk.com/last-active?path=api-keys)

### 2. Update Login/Signup Pages

The login and signup pages need to be updated to use Clerk. You have two options:

#### Option A: Use Clerk's Pre-built Components (Easier)

Replace your custom forms with Clerk's `<SignIn />` and `<SignUp />` components:

```tsx
import { SignIn } from '@clerk/nextjs'

export default function LoginPage() {
  return <SignIn />
}
```

#### Option B: Use Clerk Hooks with Custom Forms (More Control)

Keep your custom UI but use Clerk's authentication methods:

```tsx
'use client'
import { useSignIn } from '@clerk/nextjs'
import { useRouter } from 'next/navigation'

export default function LoginPage() {
  const { isLoaded, signIn, setActive } = useSignIn()
  const router = useRouter()
  
  const handleSubmit = async (e) => {
    e.preventDefault()
    const formData = new FormData(e.currentTarget)
    
    try {
      const result = await signIn.create({
        identifier: formData.get('email'),
        password: formData.get('password'),
      })
      
      if (result.status === 'complete') {
        await setActive({ session: result.createdSessionId })
        // Sync with backend
        const token = await signIn.getToken()
        await authApi.loginWithToken(token)
        router.push('/app')
      }
    } catch (error) {
      // Handle error
    }
  }
  
  // ... rest of your form
}
```

### 3. Update Components to Use Clerk

Any component that needs authentication should use Clerk hooks:

```tsx
'use client'
import { useUser, useAuth } from '@clerk/nextjs'
import { useEffect } from 'react'

export default function MyComponent() {
  const { user, isLoaded } = useUser()
  const { getToken } = useAuth()
  
  useEffect(() => {
    // Set up token getter for API client
    if (typeof window !== 'undefined' && getToken) {
      (window as any).__clerkGetToken = getToken
    }
  }, [getToken])
  
  if (!isLoaded) return <div>Loading...</div>
  if (!user) return <div>Please sign in</div>
  
  return <div>Welcome, {user.emailAddresses[0].emailAddress}!</div>
}
```

### 4. Protect Routes

Use Clerk's `<SignedIn>` and `<SignedOut>` components:

```tsx
import { SignedIn, SignedOut, SignInButton } from '@clerk/nextjs'

export default function ProtectedPage() {
  return (
    <>
      <SignedIn>
        {/* Protected content */}
      </SignedIn>
      <SignedOut>
        <SignInButton />
      </SignedOut>
    </>
  )
}
```

Or use middleware to protect routes:

```tsx
// middleware.ts
import { clerkMiddleware, createRouteMatcher } from '@clerk/nextjs/server'

const isProtectedRoute = createRouteMatcher(['/app(.*)', '/profile(.*)'])

export default clerkMiddleware(async (auth, req) => {
  if (isProtectedRoute(req)) {
    await auth.protect()
  }
})
```

### 5. Update API Calls

Components making API calls should pass Clerk tokens:

```tsx
'use client'
import { useAuth } from '@clerk/nextjs'
import { profileApi } from '@/lib/api'

export default function ProfileComponent() {
  const { getToken } = useAuth()
  
  const fetchProfile = async () => {
    const token = await getToken()
    // The API client will automatically use this token
    const profile = await profileApi.getProfile()
  }
}
```

## 🔄 Migration Notes

### Current Flow (Supabase)
1. User submits form → Backend creates user → Returns tokens → Store in localStorage

### New Flow (Clerk)
1. User submits form → Clerk creates user → Frontend gets Clerk token → Send to backend to sync → Use Clerk token for all API calls

### Key Differences

| Feature | Supabase | Clerk |
|---------|----------|-------|
| **Token Storage** | localStorage | Clerk manages (no manual storage needed) |
| **Token Refresh** | Manual refresh logic | Automatic via Clerk |
| **User State** | Custom state management | `useUser()` hook |
| **OAuth** | Manual setup | Built-in dashboard config |

## 🎯 Recommended Approach

For your existing custom forms, I recommend:

1. **Keep your custom UI** (it looks great!)
2. **Use Clerk hooks** (`useSignIn`, `useSignUp`) for authentication
3. **Sync with backend** after Clerk authentication
4. **Use Clerk tokens** for all API calls

This gives you:
- ✅ Full control over UI/UX
- ✅ Clerk's robust authentication
- ✅ Easy OAuth integration
- ✅ Automatic token management

## 📚 Resources

- [Clerk Next.js Docs](https://clerk.com/docs/quickstarts/nextjs)
- [Clerk React Hooks](https://clerk.com/docs/references/react/overview)
- [Clerk Customization](https://clerk.com/docs/customization/overview)





## ✅ What's Been Done

1. ✅ Installed `@clerk/nextjs@latest`
2. ✅ Created `middleware.ts` with `clerkMiddleware()`
3. ✅ Updated `app/layout.tsx` with `<ClerkProvider>`
4. ✅ Updated API client to support Clerk tokens
5. ✅ Created `lib/clerk-auth.ts` helper utilities

## 📋 Next Steps

### 1. Add Environment Variables

Create or update `.env.local`:

```bash
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_YOUR_PUBLISHABLE_KEY
CLERK_SECRET_KEY=sk_test_YOUR_SECRET_KEY
```

**Get your keys from:** [Clerk Dashboard → API Keys](https://dashboard.clerk.com/last-active?path=api-keys)

### 2. Update Login/Signup Pages

The login and signup pages need to be updated to use Clerk. You have two options:

#### Option A: Use Clerk's Pre-built Components (Easier)

Replace your custom forms with Clerk's `<SignIn />` and `<SignUp />` components:

```tsx
import { SignIn } from '@clerk/nextjs'

export default function LoginPage() {
  return <SignIn />
}
```

#### Option B: Use Clerk Hooks with Custom Forms (More Control)

Keep your custom UI but use Clerk's authentication methods:

```tsx
'use client'
import { useSignIn } from '@clerk/nextjs'
import { useRouter } from 'next/navigation'

export default function LoginPage() {
  const { isLoaded, signIn, setActive } = useSignIn()
  const router = useRouter()
  
  const handleSubmit = async (e) => {
    e.preventDefault()
    const formData = new FormData(e.currentTarget)
    
    try {
      const result = await signIn.create({
        identifier: formData.get('email'),
        password: formData.get('password'),
      })
      
      if (result.status === 'complete') {
        await setActive({ session: result.createdSessionId })
        // Sync with backend
        const token = await signIn.getToken()
        await authApi.loginWithToken(token)
        router.push('/app')
      }
    } catch (error) {
      // Handle error
    }
  }
  
  // ... rest of your form
}
```

### 3. Update Components to Use Clerk

Any component that needs authentication should use Clerk hooks:

```tsx
'use client'
import { useUser, useAuth } from '@clerk/nextjs'
import { useEffect } from 'react'

export default function MyComponent() {
  const { user, isLoaded } = useUser()
  const { getToken } = useAuth()
  
  useEffect(() => {
    // Set up token getter for API client
    if (typeof window !== 'undefined' && getToken) {
      (window as any).__clerkGetToken = getToken
    }
  }, [getToken])
  
  if (!isLoaded) return <div>Loading...</div>
  if (!user) return <div>Please sign in</div>
  
  return <div>Welcome, {user.emailAddresses[0].emailAddress}!</div>
}
```

### 4. Protect Routes

Use Clerk's `<SignedIn>` and `<SignedOut>` components:

```tsx
import { SignedIn, SignedOut, SignInButton } from '@clerk/nextjs'

export default function ProtectedPage() {
  return (
    <>
      <SignedIn>
        {/* Protected content */}
      </SignedIn>
      <SignedOut>
        <SignInButton />
      </SignedOut>
    </>
  )
}
```

Or use middleware to protect routes:

```tsx
// middleware.ts
import { clerkMiddleware, createRouteMatcher } from '@clerk/nextjs/server'

const isProtectedRoute = createRouteMatcher(['/app(.*)', '/profile(.*)'])

export default clerkMiddleware(async (auth, req) => {
  if (isProtectedRoute(req)) {
    await auth.protect()
  }
})
```

### 5. Update API Calls

Components making API calls should pass Clerk tokens:

```tsx
'use client'
import { useAuth } from '@clerk/nextjs'
import { profileApi } from '@/lib/api'

export default function ProfileComponent() {
  const { getToken } = useAuth()
  
  const fetchProfile = async () => {
    const token = await getToken()
    // The API client will automatically use this token
    const profile = await profileApi.getProfile()
  }
}
```

## 🔄 Migration Notes

### Current Flow (Supabase)
1. User submits form → Backend creates user → Returns tokens → Store in localStorage

### New Flow (Clerk)
1. User submits form → Clerk creates user → Frontend gets Clerk token → Send to backend to sync → Use Clerk token for all API calls

### Key Differences

| Feature | Supabase | Clerk |
|---------|----------|-------|
| **Token Storage** | localStorage | Clerk manages (no manual storage needed) |
| **Token Refresh** | Manual refresh logic | Automatic via Clerk |
| **User State** | Custom state management | `useUser()` hook |
| **OAuth** | Manual setup | Built-in dashboard config |

## 🎯 Recommended Approach

For your existing custom forms, I recommend:

1. **Keep your custom UI** (it looks great!)
2. **Use Clerk hooks** (`useSignIn`, `useSignUp`) for authentication
3. **Sync with backend** after Clerk authentication
4. **Use Clerk tokens** for all API calls

This gives you:
- ✅ Full control over UI/UX
- ✅ Clerk's robust authentication
- ✅ Easy OAuth integration
- ✅ Automatic token management

## 📚 Resources

- [Clerk Next.js Docs](https://clerk.com/docs/quickstarts/nextjs)
- [Clerk React Hooks](https://clerk.com/docs/references/react/overview)
- [Clerk Customization](https://clerk.com/docs/customization/overview)




