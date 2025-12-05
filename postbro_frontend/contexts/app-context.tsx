"use client"

import { createContext, useContext, useState, useEffect, useCallback, useRef, ReactNode } from "react"
import { profileApi, analysisApi, type User, type AnalysisRequest } from "@/lib/api"
import { userCache } from "@/lib/storage"
import { useRealtimeAnalyses } from "@/hooks/use-realtime-analyses"
import { useAuth } from "@clerk/nextjs"

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
  
  // Get Clerk auth for token access
  const { getToken, isSignedIn } = useAuth()

  // Set up Clerk token getter for API client
  useEffect(() => {
    if (typeof window !== 'undefined' && getToken) {
      (window as any).__clerkGetToken = getToken
      console.log('✅ [AppContext] Clerk token getter set up')
    }
  }, [getToken])

  // Mark as mounted on client (prevents hydration mismatch)
  useEffect(() => {
    console.log('🔵 [AppContext] Setting isMounted to true')
    setIsMounted(true)
  }, [])

  // Load user profile - simple cache (username rarely changes)
  const loadUser = async () => {
    console.log('👤 [loadUser] Called', { isLoadingUserRef: isLoadingUserRef.current, hasLoadedUser, hasUser: !!user, isMounted })
    
    // Prevent duplicate calls
    if (isLoadingUserRef.current) {
      console.log('👤 [loadUser] Already loading, skipping')
      return
    }
    if (hasLoadedUser && user) {
      console.log('👤 [loadUser] Already loaded, skipping')
      return // Already loaded
    }
    
    // Only check cache on client side (after mount)
    if (isMounted) {
      console.log('👤 [loadUser] Checking cache...')
      const cached = userCache.get()
      if (cached) {
        console.log('👤 [loadUser] Found cache, using it')
        setUser(cached)
        setHasLoadedUser(true)
        setIsLoadingUser(false)
        // Don't fetch if cache is fresh (< 30 min) - username rarely changes
        return
      }
      console.log('👤 [loadUser] No cache found')
    } else {
      console.log('👤 [loadUser] Not mounted yet, skipping cache check')
    }
    
    // No cache or expired - fetch fresh
    try {
      console.log('👤 [loadUser] Fetching from API...')
      isLoadingUserRef.current = true
      setIsLoadingUser(true)
      const startTime = Date.now()
      const data = await profileApi.getProfile()
      console.log(`👤 [loadUser] API call took ${Date.now() - startTime}ms`)
      setUser(data)
      userCache.set(data)
      setHasLoadedUser(true)
    } catch (error) {
      console.error('👤 [loadUser] Failed to fetch profile:', error)
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
    console.log('📊 [loadAnalyses] Called', { isLoadingAnalysesRef: isLoadingAnalysesRef.current, hasLoadedAnalyses, isMounted })
    
    // Prevent duplicate calls
    if (isLoadingAnalysesRef.current) {
      console.log('📊 [loadAnalyses] Already loading, skipping')
      return
    }
    if (hasLoadedAnalyses) {
      console.log('📊 [loadAnalyses] Already loaded, skipping')
      return // Already loaded (even if empty)
    }
    
    // Set flags immediately to prevent duplicate calls
    isLoadingAnalysesRef.current = true
    
    // Fire API call IMMEDIATELY - don't wait for React state updates
    // Use a separate async function to avoid blocking
    const fetchData = async () => {
      try {
        console.log('📊 [loadAnalyses] Starting API call...')
        setIsLoadingAnalyses(true) // Set loading state
        const startTime = Date.now()
        const data = await analysisApi.getAnalysisRequests({
          limit: INITIAL_ANALYSES_LIMIT,
          offset: 0
        })
        console.log(`📊 [loadAnalyses] API call took ${Date.now() - startTime}ms`)
        
        setAnalyses(data.requests || [])
        setAnalysesOffset(INITIAL_ANALYSES_LIMIT)
        setHasMoreAnalyses(data.has_more || false)
        setHasLoadedAnalyses(true)
      } catch (error) {
        console.error('📊 [loadAnalyses] Failed to fetch analyses:', error)
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
      console.error('Failed to load more analyses:', error)
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
      console.error('Failed to refresh analyses:', error)
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
      console.error('Failed to refresh user:', error)
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
    console.log(`👤 [AppContext] updateAnalysisUsername called: ${analysisId} -> ${username}`)
    setAnalyses((prev) => {
      const updated = prev.map((analysis) => {
        if (analysis.id === analysisId) {
          console.log(`✅ [AppContext] Updating analysis ${analysisId}: ${analysis.display_name || analysis.username} -> ${username}`)
          // Update both username (input) and display_name (derived)
          return { ...analysis, username: username, display_name: username }
        }
        return analysis
      })
      console.log(`📊 [AppContext] Updated analyses list, count: ${updated.length}`)
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
  // Also wait for Clerk to be ready if user is signed in
  useEffect(() => {
    console.log('🚀 [AppContext] useEffect triggered', { isMounted, hasLoadedUser, hasLoadedAnalyses, isSignedIn })
    
    if (!isMounted) {
      console.log('🚀 [AppContext] Not mounted yet, waiting...')
      return // Wait for client-side mount to prevent hydration issues
    }
    
    // If user is signed in, wait a bit for Clerk token to be available
    if (isSignedIn && !getToken) {
      console.log('🚀 [AppContext] Waiting for Clerk token getter...')
      return
    }
    
    console.log('🚀 [AppContext] Mounted! Starting data load...')
    const startTime = Date.now()
    
    // Fire both immediately in parallel - don't wait
    loadAnalyses() // Start this immediately
    loadUser() // This can use cache, won't block
    
    console.log(`🚀 [AppContext] Data load functions called in ${Date.now() - startTime}ms`)
  }, [isMounted, isSignedIn, getToken]) // Run once after mount and when Clerk is ready

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
