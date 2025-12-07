# PostBro Frontend - Complete Documentation

## Table of Contents
1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Tech Stack](#tech-stack)
4. [Project Structure](#project-structure)
5. [Key Features](#key-features)
6. [Authentication](#authentication)
7. [State Management](#state-management)
8. [Real-time Updates](#real-time-updates)
9. [API Integration](#api-integration)
10. [Component Architecture](#component-architecture)
11. [Routing & Navigation](#routing--navigation)
12. [Styling & Theming](#styling--theming)
13. [Performance Optimizations](#performance-optimizations)
14. [Configuration](#configuration)

---

## Project Overview

PostBro Frontend is a Next.js 16 application that provides a ChatGPT-like interface for analyzing social media posts. Users can submit Instagram, X (Twitter), or YouTube post URLs, receive real-time AI-powered analysis, and interact with results through a conversational chat interface.

**Key Capabilities:**
- Real-time post analysis with live status updates
- Interactive chat interface for follow-up questions
- Note-taking system for saving insights
- Subscription management and usage tracking
- Responsive design with dark/light theme support

---

## Architecture

### Framework
- **Next.js 16** with App Router
- **React 19** with Server Components and Client Components
- **TypeScript** for type safety

### Key Patterns
1. **Component Composition**: Modular, reusable components
2. **Custom Hooks**: Encapsulated logic (state, effects, real-time)
3. **Context API**: Global state (user, analyses list)
4. **Event-Driven**: Custom events for cross-component communication
5. **Optimistic Updates**: Immediate UI feedback

---

## Tech Stack

### Core
- **Next.js 16.0.3**: React framework with App Router
- **React 19.2.0**: UI library
- **TypeScript 5**: Type safety

### Authentication
- **Clerk (@clerk/nextjs 6.35.5)**: User authentication and session management

### UI Components
- **Radix UI**: Headless component primitives
- **Tailwind CSS 4.1.9**: Utility-first styling
- **shadcn/ui**: Pre-built component library
- **Lucide React**: Icon library
- **Framer Motion**: Animations

### Data & State
- **Supabase Client**: Real-time database subscriptions
- **React Context**: Global state management
- **Custom Hooks**: Encapsulated business logic

### Content Rendering
- **React Markdown**: Markdown rendering
- **Highlight.js**: Code syntax highlighting
- **Rehype/Remark**: Markdown processing plugins

### Forms & Validation
- **React Hook Form**: Form management
- **Zod**: Schema validation
- **@hookform/resolvers**: Form validation integration

### Utilities
- **date-fns**: Date manipulation
- **clsx & tailwind-merge**: Conditional class names
- **class-variance-authority**: Component variants

---

## Project Structure

```
postbro_frontend/
├── app/                          # Next.js App Router pages
│   ├── layout.tsx               # Root layout (ClerkProvider, ThemeProvider)
│   ├── page.tsx                 # Landing page
│   ├── login/                   # Clerk login pages
│   ├── signup/                  # Clerk signup pages
│   ├── app/                     # Main application
│   │   ├── page.tsx             # App home (redirects to /app)
│   │   ├── [id]/                # Dynamic analysis page (/app/{id})
│   │   ├── layout.tsx           # App layout (sidebar, header)
│   │   └── _components/         # App-specific components
│   │       ├── app-content.tsx  # Main content orchestrator
│   │       ├── hooks/           # Custom hooks
│   │       ├── ui/              # UI components
│   │       └── utils/           # Utilities
│   ├── analyze/                 # Analysis creation page
│   ├── profile/                 # User profile page
│   ├── billing/                 # Billing pages
│   └── globals.css              # Global styles
├── components/                   # Shared components
│   ├── app/                     # Analysis-related components
│   ├── billing/                 # Billing components
│   ├── landing/                 # Landing page components
│   ├── layout/                  # Layout components
│   ├── profile/                 # Profile components
│   └── ui/                      # shadcn/ui components
├── contexts/                     # React Context providers
│   └── app-context.tsx         # Global app state
├── hooks/                        # Shared custom hooks
│   ├── use-realtime-analyses.ts # Real-time analysis updates
│   ├── use-realtime-status.ts   # Real-time status updates
│   └── use-mobile.ts           # Mobile detection
├── lib/                          # Utilities and services
│   ├── api.ts                   # API client (all endpoints)
│   ├── auth.ts                  # Auth utilities (legacy)
│   ├── clerk-auth.ts           # Clerk integration
│   ├── storage.ts               # LocalStorage utilities
│   ├── supabase.ts             # Supabase client
│   └── utils.ts                # General utilities
├── public/                       # Static assets
├── styles/                       # Additional styles
└── mdfiles/                      # Documentation
```

---

## Key Features

### 1. Real-time Analysis
- Live status updates via Supabase Realtime
- Progress indicators with percentage
- Error handling with retry capability
- ChatGPT-like sidebar with username updates

### 2. Chat Interface
- Streaming responses (Server-Sent Events)
- Message history persistence
- Context-aware responses (includes post analysis)
- Token usage tracking

### 3. Note-taking System
- Save notes per analysis
- Drawer-based UI
- Markdown support
- Auto-save functionality

### 4. Subscription Management
- Plan selection and upgrades
- Usage tracking and limits
- Billing history
- Payment processing (Dodo Payments)

### 5. Responsive Design
- Mobile-first approach
- Dark/light theme support
- Adaptive layouts
- Touch-friendly interactions

---

## Authentication

### Clerk Integration

**Setup:**
- ClerkProvider wraps the entire app in `app/layout.tsx`
- Middleware protects routes (except public routes)
- Token-based API authentication

**Public Routes:**
- `/` (landing page)
- `/login/*`
- `/signup/*`
- `/reset-password/*`
- `/verify-email/*`

**Protected Routes:**
- All `/app/*` routes
- `/profile/*`
- `/billing/*`

**Token Management:**
- Clerk tokens obtained via `useAuth().getToken()`
- Global token getter: `window.__clerkGetToken`
- API client automatically includes token in requests
- Auto-redirect to login on 401/403 errors

**Implementation:**
```typescript
// Middleware (middleware.ts)
export default clerkMiddleware(async (auth, req) => {
  if (!isPublicRoute(req)) {
    await auth.protect()
  }
})

// API Client (lib/api.ts)
async function getClerkToken(): Promise<string | null> {
  const globalGetToken = (window as any).__clerkGetToken
  if (globalGetToken) {
    return await globalGetToken()
  }
  return null
}
```

---

## State Management

### Global State (AppContext)

**Location:** `contexts/app-context.tsx`

**State:**
- `user`: Current user profile
- `analyses`: List of analysis requests
- `isLoadingUser`: User loading state
- `isLoadingAnalyses`: Analyses loading state
- `hasMoreAnalyses`: Pagination flag

**Features:**
- User profile caching (30min TTL)
- Paginated analysis loading (15 initial, 20 per load)
- Real-time status updates via Supabase
- Event-driven updates (analysis-created, analysis-status-updated)

**Usage:**
```typescript
const { user, analyses, refreshAnalyses } = useAppContext()
```

### Local State (Component-level)

**Analysis State Hook:** `app/app/_components/hooks/use-analysis-state.ts`
- Manages current analysis request
- Posts, messages, loading states
- Scroll behavior refs
- Typing effect state

**Key State:**
- `currentRequest`: Active analysis request
- `posts`: Posts for current analysis
- `messages`: Chat messages
- `postAnalysisId`: Selected post analysis ID
- `isLoadingAnalysis`: Loading flag
- `isLoadingPosts`: Posts loading flag

---

## Real-time Updates

### Supabase Realtime Integration

**Purpose:** Live status updates during analysis processing

**Implementation:**

1. **Status Updates** (`hooks/use-realtime-status.ts`)
   - Subscribes to `analysis_analysisstatushistory` table
   - Filters by `analysis_request_id`
   - Updates UI on INSERT events
   - Handles connection status

2. **Analysis List Updates** (`hooks/use-realtime-analyses.ts`)
   - Subscribes to all processing analyses
   - Updates sidebar when analysis completes
   - Updates username when social data fetched
   - Auto-cleanup on completion

**Subscription Pattern:**
```typescript
const channel = supabase
  .channel(`analysis-status-${analysisId}`)
  .on('postgres_changes', {
    event: 'INSERT',
    schema: 'public',
    table: 'analysis_analysisstatushistory',
    filter: `analysis_request_id=eq.${analysisId}`,
  }, (payload) => {
    // Handle status update
  })
  .subscribe()
```

**Status Stages:**
- `request_created`
- `fetching_posts`
- `social_data_fetched`
- `collecting_media`
- `transcribing`
- `displaying_content`
- `analysing`
- `analysis_complete`
- `error`, `retrying`, `partial_success`

---

## API Integration

### API Client (`lib/api.ts`)

**Centralized API client for all backend communication**

**Features:**
- Automatic token injection (Clerk)
- Error handling with auto-redirect
- Request/response logging
- Type-safe interfaces

**API Modules:**

1. **Auth API** (`authApi`)
   - `signup()`: Create account
   - `login()`: Login with Clerk token
   - `logout()`: Logout
   - `resetPassword()`: Password reset

2. **Profile API** (`profileApi`)
   - `getProfile()`: Get user profile
   - `updateProfile()`: Update profile

3. **Plans API** (`plansApi`)
   - `getAllPlans()`: List all plans
   - `getCurrentSubscription()`: Get active subscription
   - `subscribeToPlan()`: Subscribe to plan
   - `upgradePlan()`: Upgrade plan
   - `cancelSubscription()`: Cancel subscription

4. **Usage API** (`usageApi`)
   - `getUsageStats()`: Get usage statistics
   - `getUsageLimits()`: Get plan limits
   - `getUsageHistory()`: Get usage history

5. **Analysis API** (`analysisApi`)
   - `createAnalysis()`: Create analysis request
   - `getAnalysisRequests()`: List analyses (paginated)
   - `getAnalysisRequest()`: Get specific analysis
   - `getStatusHistory()`: Get status history

6. **Social API** (`socialApi`)
   - `getPostsByAnalysisRequest()`: Get posts for analysis

7. **Chat API** (`chatApi`)
   - `createChatSession()`: Create chat session
   - `sendMessage()`: Send message (non-streaming)
   - `streamMessage()`: Send message (streaming SSE)
   - `getChatSession()`: Get chat session
   - `listChatSessions()`: List chat sessions

8. **Notes API** (`notesApi`)
   - `listNotes()`: List all notes
   - `getNote()`: Get note for analysis
   - `saveNote()`: Create/update note
   - `deleteNote()`: Delete note

**Streaming Implementation:**
```typescript
// Chat streaming via SSE
async function* streamMessage(sessionId, message) {
  const response = await fetch(url, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({ message }),
  })
  
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    
    const data = JSON.parse(decoder.decode(value))
    if (data.type === 'chunk') {
      yield data.chunk
    }
  }
}
```

---

## Component Architecture

### App Components (`components/app/`)

**Analysis Display:**
- `analysis-display.tsx`: Main analysis results display
- `post-card.tsx`: Individual post card
- `content-observation.tsx`: Content observation display
- `suggestion-item.tsx`: Future post suggestions

**Chat Interface:**
- `chat-interface.tsx`: Chat container
- `chat-messages.tsx`: Messages list
- `chat-message.tsx`: Individual message
- `chat-input.tsx`: Message input
- `streaming-markdown.tsx`: Streaming markdown renderer
- `typing-effect.tsx`: Typing animation

**Analysis Form:**
- `analysis-form.tsx`: URL input form
- `notes-drawer.tsx`: Notes drawer
- `notes-button.tsx`: Notes toggle button
- `notes-list.tsx`: Notes list

**UI Components:**
- `markdown-renderer.tsx`: Markdown rendering
- `settings-modal.tsx`: Settings modal

### Layout Components (`components/layout/`)

- `header.tsx`: Main header
- `landing-header.tsx`: Landing page header
- `app-header.tsx`: App header
- `footer.tsx`: Footer

### Profile Components (`components/profile/`)

- `profile-content.tsx`: Profile page content
- `profile-form.tsx`: Profile edit form
- `profile-header.tsx`: Profile header
- `subscription-view.tsx`: Subscription display
- `subscription-plan.tsx`: Plan card
- `usage-stats.tsx`: Usage statistics
- `billing-history.tsx`: Billing history

### Billing Components (`components/billing/`)

- `plan-selector.tsx`: Plan selection UI
- `upgrade-plans.tsx`: Upgrade plans display

### Landing Components (`components/landing/`)

- `hero-section.tsx`: Hero section
- `features-section.tsx`: Features showcase
- `pricing-section.tsx`: Pricing display
- `how-it-works-section.tsx`: How it works
- `faq-section.tsx`: FAQ section
- `social-proof-section.tsx`: Social proof

### UI Components (`components/ui/`)

**shadcn/ui components:**
- Button, Input, Textarea, Select
- Dialog, Drawer, Sheet
- Card, Badge, Avatar
- Toast, Alert, Skeleton
- Tabs, Accordion, Collapsible
- And 50+ more components

---

## Routing & Navigation

### App Router Structure

**Routes:**
- `/` - Landing page
- `/login/[[...rest]]` - Clerk login (catch-all)
- `/signup/[[...rest]]` - Clerk signup (catch-all)
- `/app` - App home (redirects to first analysis or empty state)
- `/app/[id]` - Specific analysis view
- `/analyze` - Analysis creation page
- `/profile` - User profile
- `/billing/callback` - Payment callback
- `/billing/cancel` - Payment cancel

### Navigation Flow

1. **Landing → Signup/Login**
   - User clicks CTA
   - Redirects to Clerk signup/login
   - After auth, redirects to `/app`

2. **App Home → Analysis**
   - Shows sidebar with analyses
   - Click analysis → `/app/{id}`
   - Or create new → `/analyze`

3. **Analysis View**
   - URL: `/app/{analysisId}`
   - Loads analysis request
   - Shows posts and analysis
   - Enables chat interface

### Dynamic Routing

**Analysis Page:** `app/app/[id]/page.tsx`
- Extracts ID from URL
- Loads analysis data
- Sets up real-time subscriptions
- Handles loading/error states

---

## Styling & Theming

### Tailwind CSS

**Configuration:**
- Tailwind 4.1.9
- Custom color scheme
- Dark mode support
- Responsive breakpoints

**Theme Provider:**
- `next-themes` for theme management
- System preference detection
- Manual theme toggle
- Persistent theme selection

**Implementation:**
```typescript
<ThemeProvider 
  attribute="class" 
  defaultTheme="dark" 
  enableSystem={false}
>
  {children}
</ThemeProvider>
```

### Component Styling

**Pattern:**
- Utility classes (Tailwind)
- Component variants (CVA)
- Conditional classes (clsx, tailwind-merge)
- CSS variables for theming

**Example:**
```typescript
const buttonVariants = cva(
  "inline-flex items-center justify-center rounded-md",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground",
        outline: "border border-input",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-9 rounded-md px-3",
      },
    },
  }
)
```

---

## Performance Optimizations

### 1. Code Splitting
- Next.js automatic code splitting
- Dynamic imports for heavy components
- Route-based splitting

### 2. Caching
- User profile caching (30min TTL)
- Analysis list pagination
- React Query (future consideration)

### 3. Optimistic Updates
- Immediate UI feedback
- Background sync
- Error rollback

### 4. Lazy Loading
- Images with Next.js Image
- Component lazy loading
- Infinite scroll for analyses

### 5. Real-time Optimization
- Selective subscriptions (only processing analyses)
- Auto-cleanup on completion
- Connection pooling

### 6. Bundle Optimization
- Tree shaking
- Dynamic imports
- Image optimization

---

## Configuration

### Environment Variables

**Required:**
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000/api
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_...
NEXT_PUBLIC_SUPABASE_URL=https://...
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=...
```

**Optional:**
```bash
NEXT_PUBLIC_CLERK_SIGN_IN_URL=/login
NEXT_PUBLIC_CLERK_SIGN_UP_URL=/signup
NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL=/app
NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL=/app
```

### Next.js Configuration

**`next.config.mjs`:**
- TypeScript errors ignored in build
- Image optimization disabled (for external URLs)
- Remote image patterns configured

### TypeScript Configuration

**`tsconfig.json`:**
- Strict mode enabled
- Path aliases (`@/*` → `./*`)
- React JSX transform
- ES6 target

---

## Key Hooks

### Custom Hooks

**`use-realtime-analyses.ts`**
- Subscribes to all processing analyses
- Updates sidebar status
- Handles username updates

**`use-realtime-status.ts`**
- Subscribes to status history for one analysis
- Returns latest status
- Handles connection status

**`use-analysis-state.ts`**
- Manages analysis page state
- Posts, messages, loading states
- Scroll behavior refs

**`use-analysis-loader.ts`**
- Loads analysis data
- Handles loading states
- Error handling

**`use-analysis-events.ts`**
- Handles custom events
- Sidebar updates
- Navigation

**`use-scroll-behavior.ts`**
- Auto-scroll management
- User interaction detection
- Typing effect coordination

---

## Event System

### Custom Events

**Analysis Events:**
- `analysis-created`: New analysis created
- `analysis-status-updated`: Status changed
- `analysis-username-updated`: Username extracted

**Chat Events:**
- `chat-message-sent`: Message sent

**Usage:**
```typescript
// Dispatch
window.dispatchEvent(new CustomEvent('analysis-created', {
  detail: analysisRequest
}))

// Listen
window.addEventListener('analysis-created', (event) => {
  const analysis = (event as CustomEvent).detail
  // Handle
})
```

---

## Error Handling

### API Errors

**Automatic Handling:**
- 401/403 → Redirect to login
- Network errors → Retry with exponential backoff
- Validation errors → Display user-friendly messages

**Error Display:**
- Toast notifications (Sonner)
- Inline error messages
- Error boundaries (future)

### User-Friendly Messages

**Error Utils:** `app/app/_components/utils/error-utils.ts`
- Maps error codes to messages
- Provides actionable guidance
- Retry suggestions

---

## Data Flow

### Analysis Creation Flow

1. User submits form → `AnalysisForm`
2. `createAnalysis()` API call
3. Backend creates request → Queues Celery task
4. Frontend receives request → Adds to sidebar
5. Real-time subscription starts
6. Status updates arrive → UI updates
7. Analysis completes → Shows results
8. Chat interface enabled

### Chat Flow

1. User sends message → `ChatInput`
2. `streamMessage()` API call (SSE)
3. Backend streams response
4. Frontend receives chunks → `StreamingMarkdown`
5. Message saved → Added to history
6. UI updates with new message

### Real-time Update Flow

1. Backend creates status → Supabase INSERT
2. Supabase Realtime broadcasts
3. Frontend subscription receives
4. Hook updates state
5. Component re-renders
6. UI reflects new status

---

## Best Practices

### 1. Component Organization
- Co-locate related components
- Separate concerns (UI, logic, data)
- Use composition over inheritance

### 2. State Management
- Global state for shared data
- Local state for component-specific
- Context for app-wide state
- Props for parent-child communication

### 3. Performance
- Memoize expensive computations
- Use React.memo for pure components
- Lazy load heavy components
- Optimize re-renders

### 4. Type Safety
- Type all API responses
- Use TypeScript interfaces
- Avoid `any` types
- Validate at boundaries

### 5. Error Handling
- Graceful degradation
- User-friendly messages
- Logging for debugging
- Retry mechanisms

### 6. Accessibility
- Semantic HTML
- ARIA labels
- Keyboard navigation
- Screen reader support

---

## Development Workflow

### Setup

```bash
# Install dependencies
pnpm install

# Set up environment variables
cp .env.example .env.local

# Run development server
pnpm dev
```

### Building

```bash
# Build for production
pnpm build

# Start production server
pnpm start
```

### Linting

```bash
# Run ESLint
pnpm lint
```

---

## Testing Considerations

### Current State
- Manual testing
- Browser DevTools
- Console logging

### Future Improvements
- Unit tests (Jest, Vitest)
- Integration tests (Playwright)
- E2E tests
- Visual regression tests

---

## Deployment

### Vercel (Recommended)

**Configuration:**
- Automatic deployments from Git
- Environment variables in dashboard
- Preview deployments for PRs

**Build Settings:**
- Framework: Next.js
- Build command: `pnpm build`
- Output directory: `.next`

### Other Platforms

**Docker:**
- Dockerfile for containerization
- Multi-stage builds
- Environment variable injection

**Static Export:**
- Not recommended (requires API)
- Use SSR/ISR instead

---

## Troubleshooting

### Common Issues

**1. Authentication Errors**
- Check Clerk keys in environment
- Verify token is being sent
- Check middleware configuration

**2. Real-time Not Working**
- Verify Supabase keys
- Check network connectivity
- Verify table permissions

**3. API Errors**
- Check API URL in environment
- Verify CORS settings
- Check network tab for details

**4. Build Errors**
- Clear `.next` directory
- Reinstall dependencies
- Check TypeScript errors

---

## Future Enhancements

### Planned Features
1. Offline support (PWA)
2. Advanced filtering/search
3. Export functionality
4. Collaboration features
5. Mobile app (React Native)

### Technical Improvements
1. React Query integration
2. Error boundaries
3. Performance monitoring
4. Analytics integration
5. A/B testing framework

---

## Support & Resources

### Documentation
- Next.js: https://nextjs.org/docs
- Clerk: https://clerk.com/docs
- Supabase: https://supabase.com/docs
- Tailwind: https://tailwindcss.com/docs

### Internal Docs
- Backend documentation: `../postbro_backend/mdfiles/BACKEND_DOCUMENTATION.md`
- Clerk setup: `mdfiles/during build/CLERK_FRONTEND_SETUP.md`
- Refactor summary: `mdfiles/during build/REFACTOR_SUMMARY.md`

---

**Last Updated**: 2025-01-XX
**Version**: 1.0.0
**Maintainer**: Frontend Team

