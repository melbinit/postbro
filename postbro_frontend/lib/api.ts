/**
 * API Service Layer
 * Centralized API client for all backend communication
 */

import { userCache } from './storage'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api'

// Global flag to prevent multiple simultaneous redirects
let isRedirectingToLogin = false

/**
 * Get Clerk token for API requests
 * Tries multiple methods to get the token
 */
async function getClerkToken(): Promise<string | null> {
  if (typeof window === 'undefined') return null
  
  // Method 1: Try global token getter (set by login/signup pages)
  const globalGetToken = (window as any).__clerkGetToken
  if (globalGetToken && typeof globalGetToken === 'function') {
    try {
      const token = await globalGetToken()
      if (token) return token
    } catch (error) {
      console.warn('Failed to get token from global getter:', error)
    }
  }
  
  // Method 2: Try to dynamically import and use Clerk's useAuth
  // This works if ClerkProvider is set up and we're in a client component context
  try {
    // Note: This is a workaround - in practice, components should pass tokens
    // But this allows the API client to work without requiring token passing everywhere
    const { useAuth } = await import('@clerk/nextjs')
    // We can't use hooks here, but we can check if Clerk is initialized
    // The actual token will come from the global getter set by components
  } catch (error) {
    // Clerk not available or not imported
  }
  
  // Method 3: Fallback to legacy token manager
  return tokenManager.getAccessToken()
}

// Types
export interface User {
  id: string
  email: string
  full_name: string | null
  company_name: string | null
  profile_image: string | null
  email_verified: boolean
  created_at?: string
  updated_at?: string
}

export interface Plan {
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

export interface Subscription {
  id: string
  plan: Plan
  status: 'active' | 'trial' | 'cancelled' | 'expired'
  start_date: string
  end_date: string | null
  created_at?: string
  updated_at?: string
}

export interface UsageStats {
  plan: {
    id: string
    name: string
    max_handles: number
    max_urls: number
    max_analyses_per_day: number
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
    platforms?: {
      [platform: string]: {
        handle_analyses: number
        url_lookups: number
        post_suggestions: number
      }
    }
  }
}

export interface LoginResponse {
  message: string
  user: User
  session: {
    access_token: string
    refresh_token: string
    expires_at: number
  }
}

export interface SignupResponse {
  message: string
  user: User
  session: {
    access_token: string | null
    refresh_token: string | null
  }
}

export interface ApiError {
  error?: string
  message?: string
  details?: Record<string, string[]>
}

// Token management
export const tokenManager = {
  getAccessToken: (): string | null => {
    if (typeof window === 'undefined') return null
    return localStorage.getItem('access_token')
  },
  getRefreshToken: (): string | null => {
    if (typeof window === 'undefined') return null
    return localStorage.getItem('refresh_token')
  },
  setTokens: (accessToken: string, refreshToken: string, expiresAt: number): void => {
    if (typeof window === 'undefined') return
    localStorage.setItem('access_token', accessToken)
    localStorage.setItem('refresh_token', refreshToken)
    localStorage.setItem('token_expires_at', expiresAt.toString())
  },
  clearTokens: (): void => {
    if (typeof window === 'undefined') return
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('token_expires_at')
  },
  isTokenExpired: (): boolean => {
    if (typeof window === 'undefined') return true
    const expiresAt = localStorage.getItem('token_expires_at')
    if (!expiresAt) return true
    return Date.now() >= parseInt(expiresAt) * 1000
  },
}

// API client
async function apiRequest<T>(
  endpoint: string,
  options: RequestInit & { token?: string | null } = {}
): Promise<T> {
  const requestStartTime = Date.now()
  
  // Get token: use provided token, or try Clerk, or fallback to legacy
  let token: string | null = options.token ?? null
  if (!token) {
    try {
      token = await getClerkToken()
    } catch (error) {
      // Fallback to legacy token manager for backward compatibility
      token = tokenManager.getAccessToken()
    }
  }
  
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> || {}),
  }

  if (token && !endpoint.includes('/signup') && !endpoint.includes('/login')) {
    headers['Authorization'] = `Bearer ${token}`
    console.log(`🔑 [apiRequest] ${endpoint} - Adding Authorization header (token length: ${token.length})`)
  } else if (!endpoint.includes('/signup') && !endpoint.includes('/login')) {
    console.warn(`⚠️ [apiRequest] ${endpoint} - No token available for authenticated endpoint`)
  }

  const url = `${API_BASE_URL}${endpoint}`
  const callTime = Date.now()
  const callTimeISO = new Date().toISOString()
  console.log(`🌐 [apiRequest] Starting ${endpoint} at ${callTimeISO} (${callTime})`)
  
  const fetchStartTime = performance.now()
  const fetchStartTimeDate = Date.now()
  console.log(`🌐 [apiRequest] ${endpoint} - About to call fetch() at ${fetchStartTimeDate} (${fetchStartTime.toFixed(2)}ms)`)
  
  const response = await fetch(url, {
    ...options,
    headers,
  })
  
  const fetchEndTime = performance.now()
  const fetchEndTimeDate = Date.now()
  console.log(`🌐 [apiRequest] ${endpoint} - fetch() completed in ${(fetchEndTime - fetchStartTime).toFixed(2)}ms (wall time: ${fetchEndTimeDate - fetchStartTimeDate}ms), status: ${response.status}`)

  if (!response.ok) {
    const errorData: ApiError = await response.json().catch(() => ({}))
    console.error(`🌐 [apiRequest] ${endpoint} - Error ${response.status}:`, errorData)
    
    // Handle authentication errors globally (401 Unauthorized, 403 Forbidden)
    // This handles cases where the token expires or becomes invalid during a session
    if (response.status === 401 || response.status === 403) {
      // Only redirect if we're not already on a public route
      if (typeof window !== 'undefined') {
        const currentPath = window.location.pathname
        const publicRoutes = ['/', '/login', '/signup', '/reset-password', '/verify-email']
        const isPublicRoute = publicRoutes.some(route => currentPath.startsWith(route))
        
        if (!isPublicRoute && !isRedirectingToLogin) {
          // Set flag immediately to prevent multiple redirects from concurrent API calls
          isRedirectingToLogin = true
          
          console.warn(`🔒 [apiRequest] Auth error (${response.status}) - token expired or invalid, redirecting to login`)
          
          // Use setTimeout to ensure this happens after current execution context
          // This prevents race conditions with component-level checks
          setTimeout(() => {
            // Double-check we're still not on a public route (in case user navigated)
            const finalPath = window.location.pathname
            const stillOnPublicRoute = publicRoutes.some(route => finalPath.startsWith(route))
            
            if (!stillOnPublicRoute && isRedirectingToLogin) {
              // Redirect to login - Clerk middleware will handle authentication state
              // Using window.location.href ensures a full page reload and proper auth state reset
              window.location.href = '/login'
            } else {
              // Reset flag if we're already on a public route
              isRedirectingToLogin = false
            }
          }, 0)
        }
      }
    }
    
    // Create error with full details preserved
    const error = new Error(errorData.message || errorData.error || `API Error: ${response.statusText}`) as any
    error.status = response.status
    error.data = errorData
    error.response = { status: response.status, data: errorData }
    throw error
  }

  const jsonStartTime = Date.now()
  const data = await response.json()
  
  // Debug: Log plans API response structure
  if (endpoint.includes('/accounts/plans/')) {
    console.log('🔍 [apiRequest] Plans API response structure:', {
      hasPlans: 'plans' in data,
      plansCount: data.plans?.length || 0,
      firstPlanKeys: data.plans?.[0] ? Object.keys(data.plans[0]) : [],
      firstPlanMaxQuestions: data.plans?.[0]?.max_questions_per_day,
      fullResponse: data
    })
  }
  
  console.log(`🌐 [apiRequest] ${endpoint} - Total time: ${Date.now() - requestStartTime}ms (json parse: ${Date.now() - jsonStartTime}ms)`)
  return data
}

// Auth API
export const authApi = {
  signup: async (data: {
    email: string
    password: string
    full_name: string
    company_name?: string
  }): Promise<SignupResponse> => {
    return apiRequest<SignupResponse>('/accounts/signup/', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },

  login: async (email: string, password: string): Promise<LoginResponse> => {
    // With Clerk, login is handled by Clerk SDK on frontend
    // This endpoint accepts a token from Clerk
    // For backward compatibility, we can still accept email/password
    // but the preferred flow is: frontend uses Clerk SDK → gets token → sends to backend
    
    // Try to get Clerk token first
    const clerkToken = await getClerkToken()
    
    if (clerkToken) {
      // If we have a Clerk token, use token-based login
      const response = await apiRequest<LoginResponse>('/accounts/login/', {
        method: 'POST',
        body: JSON.stringify({ token: clerkToken }),
      })
      
      // Clear old cache on login (might be from different user)
      userCache.clear()
      
      return response
    } else {
      // Fallback: email/password login (for backward compatibility)
      // Note: Backend may not support this with Clerk - use Clerk SDK instead
      const response = await apiRequest<LoginResponse>('/accounts/login/', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      })
      
      // Store tokens (if backend still returns them)
      if (response.session?.access_token && response.session?.refresh_token) {
        tokenManager.setTokens(
          response.session.access_token,
          response.session.refresh_token,
          response.session.expires_at || Date.now() / 1000 + 3600
        )
      }
      
      // Clear old cache on login (might be from different user)
      userCache.clear()
      
      return response
    }
  },
  
  loginWithToken: async (token: string): Promise<LoginResponse> => {
    // Direct token-based login (preferred with Clerk)
    const response = await apiRequest<LoginResponse>('/accounts/login/', {
      method: 'POST',
      body: JSON.stringify({ token }),
    })
    
    // Clear old cache on login (might be from different user)
    userCache.clear()
    
    return response
  },

  logout: async (): Promise<{ message: string }> => {
    const response = await apiRequest<{ message: string }>('/accounts/logout/', {
      method: 'POST',
    })
    tokenManager.clearTokens()
    userCache.clear() // Clear user cache on logout
    return response
  },

  resetPassword: async (email: string, redirectTo?: string): Promise<{ message: string }> => {
    return apiRequest<{ message: string }>('/accounts/reset-password/', {
      method: 'POST',
      body: JSON.stringify({
        email,
        redirect_to: redirectTo || (typeof window !== 'undefined' ? `${window.location.origin}/reset-password` : '/reset-password'),
      }),
    })
  },
}

// Profile API
export const profileApi = {
  getProfile: async (): Promise<User> => {
    return apiRequest<User>('/accounts/me/')
  },

  updateProfile: async (data: {
    full_name?: string
    company_name?: string
  }): Promise<User> => {
    const updated = await apiRequest<User>('/accounts/me/', {
      method: 'PATCH',
      body: JSON.stringify(data),
    })
    userCache.set(updated) // Update cache with fresh data
    return updated
  },
}

// Plans API
export const plansApi = {
  getAllPlans: async (): Promise<{ plans: Plan[] }> => {
    return apiRequest<{ plans: Plan[] }>('/accounts/plans/')
  },

  getCurrentSubscription: async (): Promise<Subscription> => {
    return apiRequest<Subscription>('/accounts/subscription/')
  },

  subscribeToPlan: async (planId: string, token?: string | null): Promise<{ 
    message: string
    subscription?: Subscription
    checkout_url?: string
    checkout_id?: string
    subscription_id?: string
    plan?: string
  }> => {
    return apiRequest<{ 
      message: string
      subscription?: Subscription
      checkout_url?: string
      checkout_id?: string
      subscription_id?: string
      plan?: string
    }>('/billing/subscribe/', {
      method: 'POST',
      body: JSON.stringify({ plan_id: planId }),
      token: token || null, // Pass token explicitly if provided
    })
  },

  upgradePlan: async (planId: string): Promise<{ message: string; subscription: Subscription }> => {
    return apiRequest<{ message: string; subscription: Subscription }>('/billing/upgrade/', {
      method: 'POST',
      body: JSON.stringify({ plan_id: planId }),
    })
  },

  cancelSubscription: async (): Promise<{ message: string; subscription: Subscription }> => {
    return apiRequest<{ message: string; subscription: Subscription }>('/billing/cancel/', {
      method: 'POST',
    })
  },
}

// Usage API
export const usageApi = {
  getUsageStats: async (): Promise<UsageStats> => {
    return apiRequest<UsageStats>('/accounts/usage/')
  },

  getUsageLimits: async (): Promise<{ plan: Plan; limits: { max_handles: number; max_urls: number; max_analyses_per_day: number } }> => {
    return apiRequest('/accounts/usage/limits/')
  },

  getUsageHistory: async (startDate?: string, endDate?: string): Promise<{
    usage_history: Array<{
      id: string
      platform: string
      date: string
      handle_analyses: number
      url_lookups: number
      post_suggestions: number
      created_at: string
      updated_at: string
    }>
    count: number
    start_date?: string
    end_date?: string
  }> => {
    const params = new URLSearchParams()
    if (startDate) params.append('start_date', startDate)
    if (endDate) params.append('end_date', endDate)
    const query = params.toString() ? `?${params.toString()}` : ''
    return apiRequest(`/accounts/usage/history${query}`)
  },
}

// Billing API
export const billingApi = {
  getSubscriptionHistory: async (): Promise<{
    subscriptions: Subscription[]
    count: number
  }> => {
    return apiRequest('/billing/subscription/history/')
  },
}

// Analysis API
export interface AnalysisStatus {
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

export interface PostAnalysis {
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

export interface AnalysisRequest {
  posts?: Post[]  // Posts are now included in the analysis response
  post_analyses?: PostAnalysis[]  // AI analysis results
  id: string
  platform: 'instagram' | 'x' | 'youtube'
  username?: string  // Display name (for backward compatibility with existing data)
  post_urls: string[]  // Required
  status: 'pending' | 'processing' | 'completed' | 'failed'
  results?: any
  error_message?: string
  status_history?: AnalysisStatus[]
  created_at: string
  updated_at: string
}

export const analysisApi = {
  createAnalysis: async (data: {
    platform: 'instagram' | 'x' | 'youtube'
    post_urls: string[]  // Required
  }): Promise<AnalysisRequest> => {
    const response = await apiRequest<{
      message: string
      analysis_request: AnalysisRequest
      task_id: string
      status: string
      usage_info: any
    }>('/analysis/analyze/', {
      method: 'POST',
      body: JSON.stringify(data),
    })
    // Extract the actual analysis request from nested response
    return response.analysis_request
  },

  getAnalysisRequests: async (params?: {
    limit?: number
    offset?: number
  }): Promise<{
    requests: AnalysisRequest[]
    count: number
    limit: number
    offset: number
    has_more: boolean
  }> => {
    const queryParams = new URLSearchParams()
    if (params?.limit) queryParams.append('limit', params.limit.toString())
    if (params?.offset) queryParams.append('offset', params.offset.toString())
    
    const url = queryParams.toString() 
      ? `/analysis/requests/?${queryParams.toString()}`
      : '/analysis/requests/'
    
    return apiRequest(url)
  },

  getAnalysisRequest: async (requestId: string): Promise<AnalysisRequest> => {
    const response = await apiRequest<{
      analysis_request: AnalysisRequest
    }>(`/analysis/requests/${requestId}/`)
    return response.analysis_request
  },

  getStatusHistory: async (requestId: string): Promise<{
    status_history: AnalysisStatus[]
    count: number
  }> => {
    return apiRequest(`/analysis/requests/${requestId}/status-history/`)
  },
}

// Social/Posts API
export interface PostMedia {
  id: string
  media_type: 'image' | 'video' | 'video_thumbnail' | 'video_frame'
  source_url: string
  supabase_url?: string
  uploaded_to_supabase: boolean
}

export interface Post {
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

export const socialApi = {
  getPostsByAnalysisRequest: async (analysisRequestId: string): Promise<{
    posts: Post[]
    count: number
    analysis_request_id: string
  }> => {
    return apiRequest(`/social/posts/analysis/${analysisRequestId}/`)
  },
}

// Chat API
export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  tokens_used?: number | null
  created_at: string
  status?: 'streaming' | 'complete' // Status for streaming messages
}

export interface ChatSession {
  id: string
  post_analysis_id: string
  status: 'active' | 'archived'
  messages: ChatMessage[]
  message_count: number
  created_at: string
  updated_at: string
}

export interface ChatMessageResponse {
  user_message: ChatMessage
  assistant_message: ChatMessage
  processing_time_seconds: number
}

export const chatApi = {
  createChatSession: async (postAnalysisId: string): Promise<{
    session: ChatSession
    created: boolean
  }> => {
    return apiRequest<{
      session: ChatSession
      created: boolean
    }>('/analysis/chat/sessions/', {
      method: 'POST',
      body: JSON.stringify({ post_analysis_id: postAnalysisId }),
    })
  },

  sendMessage: async (
    sessionId: string,
    message: string
  ): Promise<ChatMessageResponse> => {
    return apiRequest<ChatMessageResponse>(
      `/analysis/chat/sessions/${sessionId}/messages/`,
      {
        method: 'POST',
        body: JSON.stringify({ message }),
      }
    )
  },

  /**
   * Stream a chat message using Server-Sent Events (SSE).
   * Yields chunks as they arrive from the backend.
   */
  streamMessage: async function* (
    sessionId: string,
    message: string,
    onChunk?: (chunk: string) => void,
    onDone?: (data: { message_id: string; tokens_used?: number }) => void,
    onError?: (error: string) => void
  ): AsyncGenerator<string, void, unknown> {
    const url = `${API_BASE_URL}/analysis/chat/sessions/${sessionId}/messages/stream/`
    
    console.log('🚀 [streamMessage] Starting stream request to:', url)
    console.log('📤 [streamMessage] Message:', message.substring(0, 50) + '...')
    
    // Get auth token (same way as apiRequest)
    const token = await getClerkToken() || tokenManager.getAccessToken()
    
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    }
    
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
      console.log('🔑 [streamMessage] Token found, length:', token.length)
    } else {
      console.warn('⚠️ [streamMessage] No token available')
    }
    
    console.log('📡 [streamMessage] Sending fetch request...')
    const response = await fetch(url, {
      method: 'POST',
      headers,
      body: JSON.stringify({ message }),
    })
    
    console.log('📥 [streamMessage] Response status:', response.status, response.statusText)

    if (!response.ok) {
      const error = await response.text()
      onError?.(error)
      throw new Error(`Stream failed: ${response.status} ${error}`)
    }

    if (!response.body) {
      throw new Error('Response body is null')
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    try {
      while (true) {
        const { done, value } = await reader.read()
        
        if (done) {
          break
        }

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        
        // Keep the last incomplete line in buffer
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              
              if (data.type === 'chunk' && data.chunk) {
                console.log('📥 [streamMessage] Received chunk:', data.chunk.substring(0, 50) + '...')
                // Yield chunk to caller
                yield data.chunk
                // Also call callback if provided
                onChunk?.(data.chunk)
              } else if (data.type === 'done' && data.done) {
                console.log('✅ [streamMessage] Stream complete, message_id:', data.message_id)
                // Stream complete
                onDone?.({
                  message_id: data.message_id,
                  tokens_used: data.tokens_used,
                })
                return
              } else if (data.type === 'error' && data.error) {
                console.error('❌ [streamMessage] Stream error:', data.error)
                // Error occurred
                onError?.(data.error)
                throw new Error(data.error)
              }
            } catch (parseError) {
              // Skip invalid JSON lines
              console.warn('⚠️ [streamMessage] Failed to parse SSE data:', line, parseError)
            }
          }
        }
      }
    } finally {
      reader.releaseLock()
    }
  },

  getChatSession: async (sessionId: string): Promise<{
    session: ChatSession
  }> => {
    return apiRequest<{
      session: ChatSession
    }>(`/analysis/chat/sessions/${sessionId}/`)
  },

  listChatSessions: async (postAnalysisId?: string): Promise<{
    sessions: ChatSession[]
    count: number
  }> => {
    const query = postAnalysisId
      ? `?post_analysis_id=${postAnalysisId}`
      : ''
    return apiRequest<{
      sessions: ChatSession[]
      count: number
    }>(`/analysis/chat/sessions/list/${query}`)
  },
}

// Notes API
export interface AnalysisNote {
  id: string
  post_analysis_id: string
  title: string
  content: string
  created_at: string
  updated_at: string
}

export const notesApi = {
  listNotes: async (): Promise<{
    notes: AnalysisNote[]
    count: number
  }> => {
    return apiRequest<{
      notes: AnalysisNote[]
      count: number
    }>('/analysis/notes/')
  },

  getNote: async (postAnalysisId: string): Promise<AnalysisNote | null> => {
    const response = await apiRequest<AnalysisNote | { note: null }>(
      `/analysis/notes/${postAnalysisId}/`
    )
    if ('note' in response && response.note === null) {
      return null
    }
    return response as AnalysisNote
  },

  saveNote: async (postAnalysisId: string, title: string, content: string): Promise<AnalysisNote> => {
    return apiRequest<AnalysisNote>('/analysis/notes/save/', {
      method: 'POST',
      body: JSON.stringify({
        post_analysis_id: postAnalysisId,
        title,
        content,
      }),
    })
  },

  updateNote: async (postAnalysisId: string, title: string, content: string): Promise<AnalysisNote> => {
    return apiRequest<AnalysisNote>('/analysis/notes/save/', {
      method: 'PUT',
      body: JSON.stringify({
        post_analysis_id: postAnalysisId,
        title,
        content,
      }),
    })
  },

  deleteNote: async (noteId: string): Promise<{ message: string }> => {
    return apiRequest<{ message: string }>(`/analysis/notes/${noteId}/delete/`, {
      method: 'DELETE',
    })
  },
}
