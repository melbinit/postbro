# Frontend API Reference

Quick reference for all API endpoints used in the frontend.

## Base URL
```typescript
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api'
```

## Authentication

All authenticated endpoints require a Clerk JWT token in the Authorization header:
```
Authorization: Bearer <clerk_token>
```

The API client automatically includes the token from `window.__clerkGetToken()`.

---

## Authentication Endpoints

### Signup
```typescript
POST /api/accounts/signup/
Body: {
  email: string
  password: string
  full_name: string
  company_name?: string
}
Response: {
  message: string
  user: User
}
```

### Login
```typescript
POST /api/accounts/login/
Body: {
  token: string  // Clerk JWT token (preferred)
  // OR
  email: string
  password: string
}
Response: {
  message: string
  user: User
}
```

### Logout
```typescript
POST /api/accounts/logout/
Response: {
  message: string
}
```

### Reset Password
```typescript
POST /api/accounts/reset-password/
Body: {
  email: string
  redirect_to?: string
}
Response: {
  message: string
}
```

---

## Profile Endpoints

### Get Profile
```typescript
GET /api/accounts/me/
Response: User
```

### Update Profile
```typescript
PATCH /api/accounts/me/
Body: {
  full_name?: string
  company_name?: string
}
Response: User
```

---

## Subscription Endpoints

### Get All Plans
```typescript
GET /api/accounts/plans/
Response: {
  plans: Plan[]
}
```

### Get Current Subscription
```typescript
GET /api/accounts/subscription/
Response: {
  subscription: Subscription | null
}
```

### Subscribe to Plan
```typescript
POST /api/billing/subscribe/
Body: {
  plan_id: string
}
Response: {
  message: string
  checkout_url?: string
  checkout_id?: string
  subscription_id?: string
  subscription?: Subscription
}
```

### Upgrade Plan
```typescript
POST /api/billing/upgrade/
Body: {
  plan_id: string
}
Response: {
  message: string
  subscription: Subscription
}
```

### Cancel Subscription
```typescript
POST /api/billing/cancel/
Response: {
  message: string
  subscription: Subscription
}
```

### Get Subscription History
```typescript
GET /api/billing/subscription/history/
Response: {
  subscriptions: Subscription[]
  count: number
}
```

### Check Subscription Success
```typescript
GET /api/billing/subscription/success/?checkout_id=...&subscription_id=...
Response: {
  success: boolean
  pending?: boolean
  failed?: boolean
  message: string
  subscription?: Subscription
}
```

---

## Usage Endpoints

### Get Usage Stats
```typescript
GET /api/accounts/usage/?platform=twitter
Response: UsageStats
```

### Get Usage Limits
```typescript
GET /api/accounts/usage/limits/
Response: {
  plan: Plan
  limits: {
    max_handles: number
    max_urls: number
    max_analyses_per_day: number
    max_questions_per_day: number
  }
}
```

### Get Usage History
```typescript
GET /api/accounts/usage/history/?platform=twitter&days=7
Response: {
  usage_history: UsageRecord[]
  count: number
  start_date: string
  end_date: string
}
```

---

## Analysis Endpoints

### Create Analysis
```typescript
POST /api/analysis/analyze/
Body: {
  platform: 'instagram' | 'x' | 'youtube'
  post_urls: string[]  // Required
}
Response: {
  message: string
  analysis_request: AnalysisRequest
  task_id: string
  status: string
  usage_info: any
}
```

### Get Analysis Requests
```typescript
GET /api/analysis/requests/?limit=20&offset=0
Response: {
  requests: AnalysisRequest[]
  count: number
  limit: number
  offset: number
  has_more: boolean
}
```

### Get Analysis Request
```typescript
GET /api/analysis/requests/{request_id}/
Response: {
  analysis_request: AnalysisRequest
}
```

### Retry Analysis
```typescript
POST /api/analysis/requests/{request_id}/retry/
Response: {
  message: string
  analysis_request: AnalysisRequest
  task_id: string
}
```

### Get Status History
```typescript
GET /api/analysis/requests/{request_id}/status-history/
Response: {
  status_history: AnalysisStatus[]
  count: number
}
```

---

## Social/Posts Endpoints

### Get Posts by Analysis Request
```typescript
GET /api/social/posts/analysis/{analysis_request_id}/
Response: {
  posts: Post[]
  count: number
  analysis_request_id: string
}
```

---

## Chat Endpoints

### Create Chat Session
```typescript
POST /api/analysis/chat/sessions/
Body: {
  post_analysis_id: string
}
Response: {
  session: ChatSession
  created: boolean
}
```

### Send Message (Non-streaming)
```typescript
POST /api/analysis/chat/sessions/{session_id}/messages/
Body: {
  message: string
}
Response: {
  user_message: ChatMessage
  assistant_message: ChatMessage
  processing_time_seconds: number
}
```

### Send Message (Streaming)
```typescript
POST /api/analysis/chat/sessions/{session_id}/messages/stream/
Body: {
  message: string
}
Response: Server-Sent Events (SSE)
Format: data: {"type": "chunk", "chunk": "..."}
        data: {"type": "done", "message_id": "...", "tokens_used": 123}
```

### Get Chat Session
```typescript
GET /api/analysis/chat/sessions/{session_id}/
Response: {
  session: ChatSession
}
```

### List Chat Sessions
```typescript
GET /api/analysis/chat/sessions/list/?post_analysis_id=...
Response: {
  sessions: ChatSession[]
  count: number
}
```

---

## Notes Endpoints

### List All Notes
```typescript
GET /api/analysis/notes/
Response: {
  notes: AnalysisNote[]
  count: number
}
```

### Get Note for Analysis
```typescript
GET /api/analysis/notes/{post_analysis_id}/
Response: AnalysisNote | { note: null }
```

### Create/Update Note
```typescript
POST /api/analysis/notes/save/
PUT /api/analysis/notes/save/
Body: {
  post_analysis_id: string
  title: string
  content: string
}
Response: AnalysisNote
```

### Delete Note
```typescript
DELETE /api/analysis/notes/{note_id}/delete/
Response: {
  message: string
}
```

---

## Type Definitions

### User
```typescript
interface User {
  id: string
  email: string
  full_name: string | null
  company_name: string | null
  profile_image: string | null
  email_verified: boolean
  created_at?: string
  updated_at?: string
}
```

### Plan
```typescript
interface Plan {
  id: string
  name: string
  description: string
  price: string
  max_handles: number
  max_urls: number
  max_analyses_per_day: number
  max_questions_per_day: number
  is_active: boolean
  created_at?: string
}
```

### Subscription
```typescript
interface Subscription {
  id: string
  plan: Plan
  status: 'active' | 'trial' | 'pending' | 'failed' | 'canceling' | 'cancelled' | 'expired'
  start_date: string
  end_date: string | null
  downgrade_to_plan?: Plan
  created_at?: string
  updated_at?: string
}
```

### AnalysisRequest
```typescript
interface AnalysisRequest {
  id: string
  platform: 'instagram' | 'x' | 'youtube'
  username?: string
  post_urls: string[]
  status: 'pending' | 'processing' | 'completed' | 'failed'
  results?: any
  error_message?: string
  status_history?: AnalysisStatus[]
  posts?: Post[]
  post_analyses?: PostAnalysis[]
  created_at: string
  updated_at: string
}
```

### Post
```typescript
interface Post {
  id: string
  platform: 'instagram' | 'twitter' | 'youtube'
  platform_post_id: string
  username: string
  content: string
  url: string
  engagement_score: number
  metrics: Record<string, any>
  posted_at: string
  thumbnail?: string
  media: PostMedia[]
  transcript?: string
  formatted_transcript?: any[]
}
```

### PostAnalysis
```typescript
interface PostAnalysis {
  id: string
  post: string
  task_id: string
  is_viral: boolean
  virality_reasoning: string
  creator_context?: string
  quick_takeaways?: string[]
  content_observation?: {
    caption_observation: string
    visual_observation: string
    engagement_context: string
    platform_signals: string
  }
  replicable_elements?: string[]
  analysis_data: {
    platform: string
    framework_used?: string
    strengths: string[]
    weaknesses: string[]
    deep_analysis: {
      hook: string
      structure_or_editing: string
      audience_psychology: string
    }
  }
  improvements: string[]
  suggestions_for_future_posts: Array<{
    hook: string
    outline: string
    why_it_works: string
    engagement_potential?: 'high' | 'medium' | 'low'
  }>
  viral_formula?: string
  metadata_used: {
    username: string
    posted_at: string
    requested_at: string
    media_count: number
    platform_metrics: {
      likes: number
      comments: number
      views_or_impressions: number
    }
  }
  llm_model: string
  processing_time_seconds?: number
  created_at: string
  updated_at: string
}
```

### AnalysisStatus
```typescript
interface AnalysisStatus {
  id: string
  analysis_request_id: string
  stage: string
  message: string
  metadata: Record<string, any>
  is_error: boolean
  error_code?: string
  retryable: boolean
  actionable_message?: string
  progress_percentage: number
  duration_seconds?: number
  api_calls_made: number
  cost_estimate?: number
  created_at: string
}
```

### ChatSession
```typescript
interface ChatSession {
  id: string
  post_analysis_id: string
  status: 'active' | 'archived'
  messages: ChatMessage[]
  message_count: number
  created_at: string
  updated_at: string
}
```

### ChatMessage
```typescript
interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  tokens_used?: number | null
  created_at: string
  status?: 'streaming' | 'complete'
}
```

### AnalysisNote
```typescript
interface AnalysisNote {
  id: string
  post_analysis_id: string
  title: string
  content: string
  created_at: string
  updated_at: string
}
```

### UsageStats
```typescript
interface UsageStats {
  plan: {
    id: string
    name: string
    max_handles: number
    max_urls: number
    max_analyses_per_day: number
    max_questions_per_day: number
  }
  usage: {
    platform?: string
    date: string
    handle_analyses?: {
      used: number
      limit: number
      remaining: number
    }
    url_lookups?: {
      used: number
      limit: number
      remaining: number
    }
    post_suggestions?: {
      used: number
      limit: number
      remaining: number
    }
    questions_asked?: {
      used: number
      limit: number
      remaining: number
    }
    platforms?: {
      [platform: string]: {
        handle_analyses: number
        url_lookups: number
        post_suggestions: number
        questions_asked: number
      }
    }
  }
}
```

---

## Error Responses

All endpoints may return errors in this format:

```typescript
{
  error?: string
  message?: string
  details?: Record<string, string[]>
}
```

**Status Codes:**
- `200` - Success
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized (redirects to login)
- `403` - Forbidden (redirects to login)
- `404` - Not Found
- `500` - Internal Server Error
- `503` - Service Unavailable

---

## Rate Limiting

- Analysis: 20 requests/hour per user
- Chat: 100 requests/hour per user

Rate limit headers (if implemented):
```
X-RateLimit-Limit: 20
X-RateLimit-Remaining: 19
X-RateLimit-Reset: 1234567890
```

---

## Real-time Updates

Status updates are delivered via Supabase Realtime, not REST API.

**Table:** `analysis_analysisstatushistory`
**Event:** `INSERT`
**Filter:** `analysis_request_id=eq.{id}`

**Payload:**
```typescript
{
  new: AnalysisStatus
}
```

---

## Streaming Responses

Chat streaming uses Server-Sent Events (SSE).

**Format:**
```
data: {"type": "chunk", "chunk": "Hello"}
data: {"type": "chunk", "chunk": " world"}
data: {"type": "done", "message_id": "...", "tokens_used": 123}
```

**Event Types:**
- `chunk`: Text chunk
- `done`: Stream complete
- `error`: Error occurred

---

## Usage Examples

### Creating an Analysis
```typescript
import { analysisApi } from '@/lib/api'

const analysis = await analysisApi.createAnalysis({
  platform: 'instagram',
  post_urls: ['https://instagram.com/p/ABC123/']
})
```

### Streaming Chat Message
```typescript
import { chatApi } from '@/lib/api'

for await (const chunk of chatApi.streamMessage(sessionId, message)) {
  // Update UI with chunk
  setMessage(prev => prev + chunk)
}
```

### Subscribing to Real-time Updates
```typescript
import { supabase } from '@/lib/supabase'

const channel = supabase
  .channel(`analysis-${analysisId}`)
  .on('postgres_changes', {
    event: 'INSERT',
    schema: 'public',
    table: 'analysis_analysisstatushistory',
    filter: `analysis_request_id=eq.${analysisId}`,
  }, (payload) => {
    console.log('New status:', payload.new)
  })
  .subscribe()
```

---

**Last Updated**: 2025-01-XX

