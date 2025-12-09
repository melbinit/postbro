/**
 * LocalStorage utilities with expiration support
 * Used for caching user data and other frequently accessed data
 */

import { logger } from './logger'

const CACHE_PREFIX = 'postbro_cache_'
const USER_CACHE_KEY = `${CACHE_PREFIX}user`
const USER_CACHE_TTL = 30 * 60 * 1000 // 30 minutes in milliseconds

interface CachedData<T> {
  data: T
  timestamp: number
  expiresAt: number
}

/**
 * Store data in localStorage with expiration
 */
export function setCachedData<T>(key: string, data: T, ttl: number = USER_CACHE_TTL): void {
  if (typeof window === 'undefined') return

  try {
    const cached: CachedData<T> = {
      data,
      timestamp: Date.now(),
      expiresAt: Date.now() + ttl,
    }
    localStorage.setItem(key, JSON.stringify(cached))
  } catch (error) {
    // localStorage might be full or disabled
    logger.warn('Failed to cache data:', error)
  }
}

/**
 * Get cached data from localStorage if not expired
 */
export function getCachedData<T>(key: string): T | null {
  if (typeof window === 'undefined') return null

  try {
    const cachedStr = localStorage.getItem(key)
    if (!cachedStr) return null

    const cached: CachedData<T> = JSON.parse(cachedStr)

    // Check if expired
    if (Date.now() > cached.expiresAt) {
      // Remove expired cache
      localStorage.removeItem(key)
      return null
    }

    return cached.data
  } catch (error) {
    // Invalid cache or parse error - remove it
    logger.warn('Failed to read cached data:', error)
    try {
      localStorage.removeItem(key)
    } catch {
      // Ignore removal errors
    }
    return null
  }
}

/**
 * Get cached data from localStorage with its metadata (timestamp, expiresAt)
 */
export function getCachedDataWithMetadata<T>(key: string): CachedData<T> | null {
  if (typeof window === 'undefined') return null

  try {
    const cachedStr = localStorage.getItem(key)
    if (!cachedStr) return null

    const cached: CachedData<T> = JSON.parse(cachedStr)

    // Check if expired
    if (Date.now() > cached.expiresAt) {
      localStorage.removeItem(key)
      return null
    }

    return cached
  } catch (error) {
    console.warn('Failed to read cached data with metadata:', error)
    try {
      localStorage.removeItem(key)
    } catch {
      // Ignore removal errors
    }
    return null
  }
}

/**
 * Check if cached data exists and is fresh
 */
export function isCacheFresh(key: string): boolean {
  if (typeof window === 'undefined') return false

  try {
    const cachedStr = localStorage.getItem(key)
    if (!cachedStr) return false

    const cached: CachedData<any> = JSON.parse(cachedStr)
    return Date.now() <= cached.expiresAt
  } catch {
    return false
  }
}

/**
 * Clear cached data
 */
export function clearCachedData(key: string): void {
  if (typeof window === 'undefined') return

  try {
    localStorage.removeItem(key)
  } catch (error) {
    console.warn('Failed to clear cached data:', error)
  }
}

/**
 * User data cache helpers
 */
export const userCache = {
  set: (user: any) => setCachedData(USER_CACHE_KEY, user, USER_CACHE_TTL),
  get: () => getCachedData<any>(USER_CACHE_KEY),
  getWithMetadata: () => getCachedDataWithMetadata<any>(USER_CACHE_KEY),
  clear: () => clearCachedData(USER_CACHE_KEY),
  isFresh: () => isCacheFresh(USER_CACHE_KEY),
}
