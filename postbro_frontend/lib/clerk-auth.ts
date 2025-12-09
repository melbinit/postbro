/**
 * Clerk Authentication Utilities
 * Helper functions for working with Clerk in client components
 */

import { logger } from './logger'

/**
 * Get Clerk token for API requests
 * Use this in client components that have access to useAuth()
 * 
 * @example
 * ```tsx
 * 'use client'
 * import { useAuth } from '@clerk/nextjs'
 * import { getClerkTokenForApi } from '@/lib/clerk-auth'
 * 
 * function MyComponent() {
 *   const { getToken } = useAuth()
 *   const token = await getClerkTokenForApi(getToken)
 * }
 * ```
 */
export async function getClerkTokenForApi(getToken: () => Promise<string | null>): Promise<string | null> {
  try {
    return await getToken()
  } catch (error) {
    logger.error('Error getting Clerk token:', error)
    return null
  }
}

/**
 * Make authenticated API request with Clerk token
 * Use this in client components
 * 
 * @example
 * ```tsx
 * 'use client'
 * import { useAuth } from '@clerk/nextjs'
 * import { apiRequestWithClerk } from '@/lib/clerk-auth'
 * 
 * function MyComponent() {
 *   const { getToken } = useAuth()
 *   const data = await apiRequestWithClerk('/api/endpoint', { getToken })
 * }
 * ```
 */
export async function apiRequestWithClerk<T>(
  endpoint: string,
  options: {
    getToken: () => Promise<string | null>
    method?: string
    body?: any
    headers?: Record<string, string>
  }
): Promise<T> {
  const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api'
  
  const token = await options.getToken()
  
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  }
  
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    method: options.method || 'GET',
    headers,
    body: options.body ? JSON.stringify(options.body) : undefined,
  })
  
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    const error = new Error(errorData.message || errorData.error || `API Error: ${response.statusText}`) as any
    error.status = response.status
    error.data = errorData
    throw error
  }
  
  return response.json()
}



