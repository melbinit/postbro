import { useEffect } from "react"
import { type AnalysisRequest, type Post, socialApi, analysisApi, chatApi } from "@/lib/api"
import { type AnalysisState } from "./use-analysis-state"

interface UseAnalysisLoaderProps {
  analysisId: string | null
  isLoaded: boolean
  isSignedIn: boolean
  getToken: (() => Promise<string | null>) | undefined
  latestStatus: any
  state: AnalysisState
}

/**
 * Manages all data fetching and loading logic for analysis
 * Handles initial load, parallel loading for completed analyses, and realtime updates
 */
export function useAnalysisLoader({
  analysisId,
  isLoaded,
  isSignedIn,
  getToken,
  latestStatus,
  state,
}: UseAnalysisLoaderProps) {
  const {
    currentRequest,
    setCurrentRequest,
    posts,
    setPosts,
    setIsLoadingAnalysis,
    setIsLoadingPosts,
    setPostAnalysisId,
    setChatSessionId,
    setMessagesLoaded,
    setIsTypingComplete,
    setIsTypingActive,
    setIsFormMinimized,
    postsFetchedForRef,
    postsFetchingRef,
    analysisLoadingRef,
    postsFetchAttemptsRef,
    chatSessionFetchedRef,
    hasScrolledToBottomRef,
    wasCompletedOnLoadRef,
    isTypingActiveRef,
    prevStatusRef,
  } = state
  
  // Load analysis when URL changes
  useEffect(() => {
    if (!analysisId) {
      // Clear state when navigating away
      setCurrentRequest(null)
      setPosts([])
      postsFetchedForRef.current = null
      postsFetchingRef.current = null
      analysisLoadingRef.current = null
      chatSessionFetchedRef.current.clear()
      setChatSessionId(null)
      setPostAnalysisId(null)
      setMessagesLoaded(false)
      setIsFormMinimized(false)
      return
    }
    
    if (!isLoaded || !isSignedIn || !getToken) {
      console.log('⏳ [AppContent] Waiting for Clerk auth before loading analysis...')
      return
    }
    
    if (analysisLoadingRef.current === analysisId) {
      return // Already loading
    }
    
    const loadAnalysis = async () => {
      // CRITICAL: Wait for token to be available before making API calls
      // This prevents 403 errors on page refresh
      let token: string | null = null
      try {
        token = await getToken()
        if (!token) {
          console.log('⏳ [AppContent] Token not available yet, waiting...')
          return
        }
      } catch (error) {
        console.error('Failed to get token:', error)
        return
      }
      analysisLoadingRef.current = analysisId
      setIsLoadingAnalysis(true)
      setPosts([])
      postsFetchedForRef.current = null
      postsFetchingRef.current = null
      
      // Reset scroll tracking
      if (analysisId) {
        hasScrolledToBottomRef.current.delete(analysisId)
        console.log('🔄 [Load] Reset scroll tracking for analysis:', analysisId)
      }
      
      try {
        const analysis = await analysisApi.getAnalysisRequest(analysisId)
        setCurrentRequest(analysis)
        
        // Track if completed on load
        if (analysis.status === 'completed' && analysis.id) {
          wasCompletedOnLoadRef.current.add(analysis.id)
          console.log('📌 [Load] Analysis was already completed on load:', analysis.id)
        } else if (analysis.id) {
          wasCompletedOnLoadRef.current.delete(analysis.id)
        }
        
        // Reset typing state
        setIsTypingComplete(false)
        setIsTypingActive(false)
        isTypingActiveRef.current = false
        
        // Reset chat session state
        if (analysis.id) {
          chatSessionFetchedRef.current.delete(analysis.id)
          setChatSessionId(null)
          setPostAnalysisId(null)
          setMessagesLoaded(false)
        }
        
        setIsFormMinimized(true)
        
        // Handle posts and chat loading
        if (analysis.posts && analysis.posts.length > 0) {
          setPosts(analysis.posts)
          postsFetchedForRef.current = analysisId
          
          // Load chat session in parallel for completed analyses
          if (analysis.status === 'completed' && analysis.post_analyses && analysis.post_analyses.length > 0) {
            const firstPostAnalysisId = analysis.post_analyses[0].id
            setPostAnalysisId(firstPostAnalysisId)
            
            chatApi.listChatSessions(firstPostAnalysisId)
              .then((chatSessions) => {
                if (chatSessions.sessions.length > 0) {
                  const session = chatSessions.sessions[0]
                  console.log('✅ [Load] Found chat session:', session.id, 'with', session.message_count, 'messages')
                  setChatSessionId(session.id)
                }
              })
              .catch((err) => {
                console.error('Failed to fetch chat session:', err)
              })
          }
        } else if (analysis.status === 'completed') {
          // Parallel loading for completed analyses without posts
          console.log('🔄 [Load] Loading posts and chat in parallel for completed analysis')
          
          if (postsFetchingRef.current === analysisId) return
          
          if (postsFetchedForRef.current !== analysisId) {
            postsFetchingRef.current = analysisId
            setIsLoadingPosts(true)
            
            const loadPromises: Promise<any>[] = []
            
            // Load posts
            loadPromises.push(
              socialApi.getPostsByAnalysisRequest(analysisId)
                .then((response) => {
                  if (response.posts && response.posts.length > 0) {
                    setPosts(response.posts)
                    postsFetchedForRef.current = analysisId
                    console.log('✅ [Load] Posts loaded:', response.posts.length)
                  }
                })
                .catch((err) => {
                  console.error('❌ [Load] Failed to fetch posts:', err)
                })
            )
            
            // Load chat session
            if (analysis.post_analyses && analysis.post_analyses.length > 0) {
              const firstPostAnalysisId = analysis.post_analyses[0].id
              setPostAnalysisId(firstPostAnalysisId)
              
              loadPromises.push(
                chatApi.listChatSessions(firstPostAnalysisId)
                  .then((chatSessions) => {
                    if (chatSessions.sessions.length > 0) {
                      const session = chatSessions.sessions[0]
                      console.log('✅ [Load] Chat session loaded:', session.id, 'with', session.message_count, 'messages')
                      setChatSessionId(session.id)
                    } else {
                      console.log('⚠️ [Load] No chat session found')
                    }
                  })
                  .catch((err) => {
                    console.error('❌ [Load] Failed to fetch chat session:', err)
                  })
              )
            }
            
            Promise.all(loadPromises)
              .then(() => {
                console.log('✅ [Load] Completed parallel loading for existing analysis')
              })
              .finally(() => {
                setIsLoadingPosts(false)
                postsFetchingRef.current = null
              })
          }
        } else if (analysis.status === 'processing') {
          // Only fetch posts for processing analyses
          if (postsFetchingRef.current === analysisId) return
          
          if (postsFetchedForRef.current !== analysisId) {
            postsFetchingRef.current = analysisId
            setIsLoadingPosts(true)
            try {
              const response = await socialApi.getPostsByAnalysisRequest(analysisId)
              if (response.posts && response.posts.length > 0) {
                setPosts(response.posts)
                postsFetchedForRef.current = analysisId
              }
            } catch (err) {
              console.error('Failed to fetch posts:', err)
            } finally {
              setIsLoadingPosts(false)
              postsFetchingRef.current = null
            }
          }
        }
      } catch (err: any) {
        console.error('Failed to load analysis:', err)
        setCurrentRequest(null)
      } finally {
        setIsLoadingAnalysis(false)
        analysisLoadingRef.current = null
      }
    }
    
    loadAnalysis()
  }, [analysisId, isLoaded, isSignedIn, getToken])
  
  // Fetch posts when social data is fetched (realtime updates)
  useEffect(() => {
    if (!currentRequest?.id || !analysisId) return
    
    if (currentRequest.posts && currentRequest.posts.length > 0) return
    if (postsFetchingRef.current === currentRequest.id) return
    if (postsFetchedForRef.current === currentRequest.id && posts.length > 0) return
    
    const shouldFetchPosts = latestStatus?.stage === 'social_data_fetched' || 
                             latestStatus?.stage === 'displaying_content' ||
                             latestStatus?.stage === 'analysis_complete'
    
    const statusKey = `${currentRequest.id}-${latestStatus?.stage || 'none'}`
    const fetchAttempts = postsFetchAttemptsRef.current.get(statusKey) || 0
    const MAX_RETRY_ATTEMPTS = 2
    
    if (shouldFetchPosts && posts.length === 0 && !state.isLoadingPosts && fetchAttempts < MAX_RETRY_ATTEMPTS) {
      console.log('🔄 [Realtime] Fetching posts for analysis', currentRequest.id, 'Status:', latestStatus?.stage, `(attempt ${fetchAttempts + 1}/${MAX_RETRY_ATTEMPTS})`)
      postsFetchingRef.current = currentRequest.id
      postsFetchAttemptsRef.current.set(statusKey, fetchAttempts + 1)
      setIsLoadingPosts(true)
      socialApi.getPostsByAnalysisRequest(currentRequest.id)
        .then((response) => {
          console.log('✅ [Realtime] Fetched posts:', response.posts.length)
          if (response.posts && response.posts.length > 0) {
            setPosts(response.posts)
            postsFetchedForRef.current = currentRequest.id
            postsFetchAttemptsRef.current.delete(statusKey)
          } else {
            console.log('⚠️ [Realtime] No posts returned (attempt', fetchAttempts + 1, ')')
            if (fetchAttempts + 1 >= MAX_RETRY_ATTEMPTS) {
              console.log('🛑 [Realtime] Max retry attempts reached for status', latestStatus?.stage, '- stopping retries')
              postsFetchedForRef.current = currentRequest.id
            }
          }
        })
        .catch((error) => {
          console.error('❌ [Realtime] Failed to fetch posts:', error)
          if (fetchAttempts + 1 >= MAX_RETRY_ATTEMPTS) {
            postsFetchedForRef.current = currentRequest.id
          }
        })
        .finally(() => {
          setIsLoadingPosts(false)
          postsFetchingRef.current = null
        })
    }
  }, [latestStatus?.stage, currentRequest?.id, currentRequest?.posts, state.isLoadingPosts, analysisId])
  
  // Update status when analysis completes/fails
  useEffect(() => {
    if (!currentRequest?.id || !latestStatus) return
    
    let newStatus: string | null = null
    
    if (latestStatus.stage === 'analysis_complete') {
      newStatus = 'completed'
    } else if (latestStatus.is_error) {
      newStatus = 'failed'
    } else if (latestStatus.stage) {
      newStatus = 'processing'
    }
    
    if (newStatus && newStatus !== prevStatusRef.current && newStatus !== currentRequest.status) {
      prevStatusRef.current = newStatus
      
      setCurrentRequest((prev) => {
        if (!prev || prev.id !== currentRequest.id) return prev
        return { ...prev, status: newStatus as any }
      })
    }
  }, [latestStatus?.stage, latestStatus?.is_error, currentRequest?.id, currentRequest?.status])
  
  // Fetch chat session when analysis completes
  useEffect(() => {
    if (!currentRequest?.id || !latestStatus) return
    
    if (latestStatus.stage === 'analysis_complete' && !chatSessionFetchedRef.current.has(currentRequest.id)) {
      console.log(`🔄 [Realtime] Analysis complete - fetching chat session for ${currentRequest.id}`)
      chatSessionFetchedRef.current.add(currentRequest.id)
      
      const timeoutId = setTimeout(async () => {
        try {
          const updatedAnalysis = await analysisApi.getAnalysisRequest(currentRequest.id)
          
          if (updatedAnalysis.post_analyses && updatedAnalysis.post_analyses.length > 0) {
            const firstPostAnalysisId = updatedAnalysis.post_analyses[0].id
            setPostAnalysisId(firstPostAnalysisId)
            
            const chatSessions = await chatApi.listChatSessions(firstPostAnalysisId)
            
            if (chatSessions.sessions.length > 0) {
              const session = chatSessions.sessions[0]
              console.log('✅ [Realtime] Found chat session:', session.id, 'with', session.message_count, 'messages')
              setChatSessionId(session.id)
            } else {
              console.log('⚠️ [Realtime] No chat session found yet, will be created when user sends first message')
            }
          } else {
            console.log('⚠️ [Realtime] No post_analyses found - chat-first approach may need backend update')
          }
        } catch (error) {
          console.error('❌ [Realtime] Failed to fetch chat session:', error)
        }
      }, 1000)
      
      return () => clearTimeout(timeoutId)
    }
  }, [latestStatus?.stage, currentRequest?.id])
}



