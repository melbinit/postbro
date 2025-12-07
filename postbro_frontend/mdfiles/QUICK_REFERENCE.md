# Frontend Quick Reference

Quick reference guide for common tasks and patterns in the PostBro frontend.

## Common Tasks

### Getting User Data
```typescript
import { useAppContext } from '@/contexts/app-context'

const { user, isLoadingUser } = useAppContext()
```

### Getting Analyses List
```typescript
import { useAppContext } from '@/contexts/app-context'

const { analyses, isLoadingAnalyses, refreshAnalyses } = useAppContext()
```

### Getting Clerk Auth
```typescript
import { useAuth } from '@clerk/nextjs'

const { isSignedIn, isLoaded, getToken, userId } = useAuth()
```

### Making API Calls
```typescript
import { analysisApi, profileApi, chatApi } from '@/lib/api'

// Create analysis
const analysis = await analysisApi.createAnalysis({
  platform: 'instagram',
  post_urls: ['https://...']
})

// Get profile
const user = await profileApi.getProfile()

// Send chat message
const response = await chatApi.sendMessage(sessionId, message)
```

### Streaming Chat Message
```typescript
import { chatApi } from '@/lib/api'

for await (const chunk of chatApi.streamMessage(sessionId, message)) {
  setStreamingText(prev => prev + chunk)
}
```

### Real-time Status Updates
```typescript
import { useRealtimeStatus } from '@/hooks/use-realtime-status'

const { statusHistory, latestStatus, isConnected } = useRealtimeStatus(analysisId)
```

### Using Toast Notifications
```typescript
import { toast } from 'sonner'

toast.success('Analysis created!')
toast.error('Something went wrong')
toast.info('Processing...')
```

### Theme Toggle
```typescript
import { useTheme } from 'next-themes'

const { theme, setTheme } = useTheme()

// Toggle
setTheme(theme === 'dark' ? 'light' : 'dark')
```

---

## Component Patterns

### Client Component
```typescript
'use client'

import { useState } from 'react'

export function MyComponent() {
  const [state, setState] = useState()
  // ...
}
```

### Server Component
```typescript
// No 'use client' directive

export default function MyPage() {
  // Can use async/await
  const data = await fetchData()
  return <div>{data}</div>
}
```

### Form with Validation
```typescript
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'

const schema = z.object({
  email: z.string().email(),
  password: z.string().min(8),
})

export function MyForm() {
  const form = useForm({
    resolver: zodResolver(schema),
  })
  
  const onSubmit = async (data) => {
    // Handle submit
  }
  
  return (
    <form onSubmit={form.handleSubmit(onSubmit)}>
      {/* Form fields */}
    </form>
  )
}
```

### Loading States
```typescript
if (isLoading) {
  return <LoadingScreen message="Loading..." />
}

if (error) {
  return <ErrorDisplay error={error} />
}

return <Content />
```

---

## File Locations

### Pages
- Landing: `app/page.tsx`
- App Home: `app/app/page.tsx`
- Analysis: `app/app/[id]/page.tsx`
- Profile: `app/profile/page.tsx`
- Login: `app/login/[[...rest]]/page.tsx`

### Components
- App: `components/app/`
- UI: `components/ui/`
- Layout: `components/layout/`
- Profile: `components/profile/`

### Hooks
- Shared: `hooks/`
- App-specific: `app/app/_components/hooks/`

### Utilities
- API: `lib/api.ts`
- Storage: `lib/storage.ts`
- Supabase: `lib/supabase.ts`
- Utils: `lib/utils.ts`

### Context
- App Context: `contexts/app-context.tsx`

---

## Environment Variables

```bash
# Required
NEXT_PUBLIC_API_URL=http://localhost:8000/api
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_...
NEXT_PUBLIC_SUPABASE_URL=https://...
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=...

# Optional
NEXT_PUBLIC_CLERK_SIGN_IN_URL=/login
NEXT_PUBLIC_CLERK_SIGN_UP_URL=/signup
NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL=/app
NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL=/app
```

---

## Styling Patterns

### Tailwind Classes
```typescript
<div className="flex items-center gap-4 p-4 bg-background rounded-lg">
  {/* Content */}
</div>
```

### Conditional Classes
```typescript
import { cn } from '@/lib/utils'

<div className={cn(
  "base-classes",
  isActive && "active-classes",
  isDisabled && "disabled-classes"
)}>
```

### Dark Mode
```typescript
<div className="bg-white dark:bg-gray-900 text-gray-900 dark:text-white">
  {/* Content */}
</div>
```

---

## Common Imports

```typescript
// React
import { useState, useEffect, useCallback } from 'react'

// Next.js
import { usePathname, useRouter } from 'next/navigation'
import Link from 'next/link'
import Image from 'next/image'

// Clerk
import { useAuth } from '@clerk/nextjs'

// Context
import { useAppContext } from '@/contexts/app-context'

// API
import { analysisApi, chatApi, profileApi } from '@/lib/api'

// Hooks
import { useRealtimeStatus } from '@/hooks/use-realtime-status'

// UI Components
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { toast } from 'sonner'

// Icons
import { Loader2, AlertCircle } from 'lucide-react'
```

---

## Debugging Tips

### Console Logging
```typescript
console.log('🔍 Debug:', data)
console.error('❌ Error:', error)
console.warn('⚠️ Warning:', warning)
```

### React DevTools
- Install React DevTools browser extension
- Inspect component tree
- View props and state

### Network Tab
- Check API requests
- Verify headers (Authorization)
- Check response data

### Supabase Realtime
- Check Supabase dashboard
- View table data
- Monitor realtime subscriptions

---

## Common Issues & Solutions

### Issue: Token not being sent
**Solution:** Check `window.__clerkGetToken` is set in AppContext

### Issue: Real-time not working
**Solution:** Verify Supabase keys and table permissions

### Issue: Hydration mismatch
**Solution:** Use `useState` with `isMounted` check

### Issue: Build errors
**Solution:** Clear `.next` and `node_modules`, reinstall

---

## Performance Tips

1. **Use React.memo** for expensive components
2. **Lazy load** heavy components
3. **Memoize** expensive computations
4. **Debounce** frequent API calls
5. **Optimize images** with Next.js Image
6. **Code split** large bundles

---

## Testing Checklist

- [ ] User can sign up
- [ ] User can log in
- [ ] User can create analysis
- [ ] Real-time updates work
- [ ] Chat interface works
- [ ] Notes can be saved
- [ ] Profile can be updated
- [ ] Subscription can be managed
- [ ] Mobile responsive
- [ ] Dark mode works

---

**Last Updated**: 2025-01-XX

