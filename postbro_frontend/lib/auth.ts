/**
 * Authentication utilities
 * 
 * DEPRECATED: This file contains legacy authentication utilities.
 * Use Clerk's useAuth() hook from @clerk/nextjs instead.
 * 
 * Example:
 *   import { useAuth } from "@clerk/nextjs"
 *   const { isLoaded, isSignedIn } = useAuth()
 */

import { tokenManager } from './api'

/**
 * @deprecated Use Clerk's useAuth() hook instead
 * Check if user is authenticated (legacy - checks localStorage tokens)
 * This will always return false with Clerk since tokens are not stored in localStorage
 */
export function isAuthenticated(): boolean {
  // Legacy check - kept for backward compatibility but should not be used
  const token = tokenManager.getAccessToken()
  if (!token) return false
  
  if (tokenManager.isTokenExpired()) {
    tokenManager.clearTokens()
    return false
  }
  
  return true
}

/**
 * @deprecated Use Clerk's useAuth() hook instead
 * Get auth status (legacy)
 */
export function getAuthStatus(): { isAuthenticated: boolean; hasToken: boolean; isExpired: boolean } {
  const token = tokenManager.getAccessToken()
  const hasToken = !!token
  const isExpired = token ? tokenManager.isTokenExpired() : true
  const isAuth = hasToken && !isExpired
  
  return {
    isAuthenticated: isAuth,
    hasToken,
    isExpired,
  }
}








