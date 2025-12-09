"use client"

import { createContext, useContext, useState, useEffect, useCallback, useRef, ReactNode } from "react"
import { profileApi, analysisApi, type User, type AnalysisRequest } from "@/lib/api"
import { userCache } from "@/lib/storage"
import { useRealtimeAnalyses } from "@/hooks/use-realtime-analyses"
import { useAuth } from "@clerk/nextjs"
import { logger } from "@/lib/logger"

interface AppContextType {
  user: User | null
  analyses: AnalysisRequest[]
  isLoadingUser: boolean
  isLoadingAnalyses: boolean
  isLoadingMoreAnalyses: boolean
  hasMoreAnalyses: boolean
  loadMoreAnalyses: () => Promise<void>
  refreshAnalyses: () => Promise<void>
  refreshUser: () => Promise<void>
}

const AppContext = createContext<AppContextType | undefined>(undefined)

const INITIAL_ANALYSES_LIMIT = 15 // Load first 15 analyses initially
const LOAD_MORE_LIMIT = 20 // Load 20 more each time

export function AppProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [analyses, setAnalyses] = useState<AnalysisRequest[]>([])
  const [isLoadingUser, setIsLoadingUser] = useState(true)
  const [isLoadingAnalyses, setIsLoadingAnalyses] = useState(true)
  const [isLoadingMoreAnalyses, setIsLoadingMoreAnalyses] = useState(false)
  const [hasLoadedUser, setHasLoadedUser] = useState(false)
  const [hasLoadedAnalyses, setHasLoadedAnalyses] = useState(false)
  const [hasMoreAnalyses, setHasMoreAnalyses] = useState(true) // Assume there might be more
  const [analysesOffset, setAnalysesOffset] = useState(0)
  const [isMounted, setIsMounted] = useState(false) // Track client-side mount
  const isLoadingUserRef = useRef(false) // Prevent duplicate calls
  const isLoadingAnalysesRef = useRef(false) // Prevent duplicate calls
  
  // Get Clerk auth for token access - CRITICAL: Check isLoaded for signup redirects
  const { getToken, isSignedIn, isLoaded } = useAuth()

  // Set up Clerk token getter for API client
  useEffect(() => {
    if (typeof window !== 'undefined' && getToken && isLoaded) {
      (window as any).__clerkGetToken = getToken
      logger.debug('[AppContext] Token getter set up')
    }
  }, [getToken, isLoaded])

  // Mark as mounted on client (prevents hydration mismatch)
  useEffect(() => {
    setIsMounted(true)
  }, [])

  // Load user profile - simple cache (username rarely changes)
  const loadUser = async () => {
    // Prevent duplicate calls
    if (isLoadingUserRef.current) {
      return
    }
    if (hasLoadedUser && user) {
      return // Already loaded
    }
    
    // Only check cache on client side (after mount)
    if (isMounted) {
      const cached = userCache.get()
      if (cached) {
        logger.debug('[AppContext] Using cached user')
        setUser(cached)
        setHasLoadedUser(true)
        setIsLoadingUser(false)
        // Don't fetch if cache is fresh (< 30 min) - username rarely changes
        return
      }
    }
    
    // No cache or expired - fetch fresh
    try {
      isLoadingUserRef.current = true
      setIsLoadingUser(true)
      const data = await profileApi.getProfile()
      setUser(data)
      userCache.set(data)
      setHasLoadedUser(true)
    } catch (error) {
      logger.error('[AppContext] Failed to fetch profile:', error)
      // Keep cached data on error if available
      const fallbackCache = userCache.get()
      if (fallbackCache) {
        setUser(fallbackCache)
        setHasLoadedUser(true)
      }
    } finally {
      setIsLoadingUser(false)
      isLoadingUserRef.current = false
    }
  }

  // Load initial batch of analyses (first 15) - with backend pagination
  const loadAnalyses = async () => {
    // Prevent duplicate calls
    if (isLoadingAnalysesRef.current) {
      return
    }
    if (hasLoadedAnalyses) {
      return // Already loaded (even if empty)
    }
    
    // Set flags immediately to prevent duplicate calls
    isLoadingAnalysesRef.current = true
    
    // Fire API call IMMEDIATELY - don't wait for React state updates
    // Use a separate async function to avoid blocking
    const fetchData = async () => {
      try {
        setIsLoadingAnalyses(true) // Set loading state
        const data = await analysisApi.getAnalysisRequests({
          limit: INITIAL_ANALYSES_LIMIT,
          offset: 0
        })
        
        setAnalyses(data.requests || [])
        setAnalysesOffset(INITIAL_ANALYSES_LIMIT)
        setHasMoreAnalyses(data.has_more || false)
        setHasLoadedAnalyses(true)
      } catch (error) {
        logger.error('[AppContext] Failed to fetch analyses:', error)
        setHasLoadedAnalyses(true) // Mark as loaded even on error
      } finally {
        setIsLoadingAnalyses(false)
        isLoadingAnalysesRef.current = false
      }
    }
    
    // Fire immediately - don't wait
    fetchData()
  }

  // Load more analyses (lazy loading) - with backend pagination
  const loadMoreAnalyses = async () => {
    if (isLoadingMoreAnalyses || !hasMoreAnalyses) return
    
    try {
      setIsLoadingMoreAnalyses(true)
      const data = await analysisApi.getAnalysisRequests({
        limit: LOAD_MORE_LIMIT,
        offset: analysesOffset
      })
      
      if (data.requests && data.requests.length > 0) {
        setAnalyses((prev) => [...prev, ...data.requests])
        setAnalysesOffset((prev) => prev + data.requests.length)
        setHasMoreAnalyses(data.has_more || false)
      } else {
        setHasMoreAnalyses(false)
      }
    } catch (error) {
      logger.error('[AppContext] Failed to load more analyses:', error)
    } finally {
      setIsLoadingMoreAnalyses(false)
    }
  }

  // Refresh analyses (called when new analysis is created)
  // Reset to initial batch when refreshing
  const refreshAnalyses = async () => {
    try {
      const data = await analysisApi.getAnalysisRequests({
        limit: INITIAL_ANALYSES_LIMIT,
        offset: 0
      })
      setAnalyses(data.requests || [])
      setAnalysesOffset(INITIAL_ANALYSES_LIMIT)
      setHasMoreAnalyses(data.has_more || false)
    } catch (error) {
      logger.error('[AppContext] Failed to refresh analyses:', error)
    }
  }

  // Refresh user (explicit refresh - clears cache and fetches fresh)
  const refreshUser = async () => {
    try {
      userCache.clear() // Clear cache to force fresh fetch
      const data = await profileApi.getProfile()
      setUser(data)
      userCache.set(data) // Update cache with fresh data
    } catch (error) {
      logger.error('[AppContext] Failed to refresh user:', error)
    }
  }

  // Update analysis status in the cached list when it changes
  const updateAnalysisStatus = useCallback((analysisId: string, status: string) => {
    setAnalyses((prev) =>
      prev.map((analysis) => {
        if (analysis.id === analysisId) {
          return { ...analysis, status: status as any }
        }
        return analysis
      })
    )
  }, [])

  // Update analysis username in the cached list (ChatGPT-like behavior)
  const updateAnalysisUsername = useCallback((analysisId: string, username: string) => {
    logger.debug(`[AppContext] Updating username: ${analysisId} -> ${username}`)
    setAnalyses((prev) => {
      const updated = prev.map((analysis) => {
        if (analysis.id === analysisId) {
          // Update both username (input) and display_name (derived)
          return { ...analysis, username: username, display_name: username }
        }
        return analysis
      })
      return updated
    })
  }, [])

  // Subscribe to realtime updates for all processing analyses
  // This keeps subscriptions active even when not viewing them (better UX)
  useRealtimeAnalyses(
    analyses.filter((a) => a.status === 'pending' || a.status === 'processing'),
    updateAnalysisStatus,
    updateAnalysisUsername
  )

  // Load data immediately on mount - only once (after client-side mount)
  // CRITICAL: Wait for Clerk to be fully loaded (especially after signup redirects)
  useEffect(() => {
    if (!isMounted) {
      return // Wait for client-side mount to prevent hydration issues
    }
    
    // Wait for Clerk to be fully loaded - this is critical after signup/email verification redirects
    // Without this, API calls happen before the token is available, causing 403 errors
    if (!isLoaded) {
      logger.debug('[AppContext] Waiting for Clerk to load...')
      return
    }
    
    // If user is signed in, ensure token getter is available
    if (isSignedIn && !getToken) {
      logger.debug('[AppContext] Waiting for token getter...')
      return
    }
    
    // Fire both immediately in parallel - don't wait
    loadAnalyses() // Start this immediately
    loadUser() // This can use cache, won't block
  }, [isMounted, isSignedIn, isLoaded, getToken]) // Added isLoaded - critical for signup flow

  // Set up event listeners separately (don't reload data when these change)
  useEffect(() => {
    // Listen for new analysis created - refresh analyses list
    const handleAnalysisCreated = (event: Event) => {
      const customEvent = event as CustomEvent<AnalysisRequest>
      const newAnalysis = customEvent.detail
      
      // Add new analysis to the top of the list (optimistic update)
      setAnalyses((prev) => {
        if (prev.some(a => a.id === newAnalysis.id)) {
          return prev
        }
        return [newAnalysis, ...prev]
      })
    }

    // Listen for analysis status updates (from realtime)
    // This updates the sidebar when analysis completes/fails
    const handleAnalysisStatusUpdate = (event: Event) => {
      const customEvent = event as CustomEvent<{
        analysis_request_id: string
        status: string
      }>
      const { analysis_request_id, status } = customEvent.detail
      
      // Update the analysis in the cached list
      updateAnalysisStatus(analysis_request_id, status)
    }

    // Listen for username updates (ChatGPT-like behavior)
    // Updates sidebar display name when social data is fetched
    const handleAnalysisUsernameUpdate = (event: Event) => {
      const customEvent = event as CustomEvent<{
        analysis_request_id: string
        username: string
      }>
      const { analysis_request_id, username } = customEvent.detail
      
      // Update the analysis username in the cached list
      updateAnalysisUsername(analysis_request_id, username)
    }
    
    window.addEventListener('analysis-created', handleAnalysisCreated)
    window.addEventListener('analysis-status-updated', handleAnalysisStatusUpdate)
    window.addEventListener('analysis-username-updated', handleAnalysisUsernameUpdate)
    
    return () => {
      window.removeEventListener('analysis-created', handleAnalysisCreated)
      window.removeEventListener('analysis-status-updated', handleAnalysisStatusUpdate)
      window.removeEventListener('analysis-username-updated', handleAnalysisUsernameUpdate)
    }
  }, [updateAnalysisStatus, updateAnalysisUsername]) // Only re-setup listeners if callbacks change

  return (
    <AppContext.Provider
      value={{
        user,
        analyses,
        isLoadingUser,
        isLoadingAnalyses,
        isLoadingMoreAnalyses,
        hasMoreAnalyses,
        loadMoreAnalyses,
        refreshAnalyses,
        refreshUser,
      }}
    >
      {children}
    </AppContext.Provider>
  )
}

export function useAppContext() {
  const context = useContext(AppContext)
  if (context === undefined) {
    throw new Error('useAppContext must be used within an AppProvider')
  }
  return context
}
