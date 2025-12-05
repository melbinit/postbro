import { useEffect, useCallback, useRef } from "react"
import { type AnalysisRequest } from "@/lib/api"

interface UseScrollBehaviorProps {
  currentRequest: AnalysisRequest | null
  messagesContainerRef: React.RefObject<HTMLDivElement>
  hasScrolledToBottomRef: React.MutableRefObject<Set<string>>
  userHasInteractedRef: React.MutableRefObject<boolean>
  wasCompletedOnLoadRef: React.MutableRefObject<Set<string>>
  isTypingActiveRef: React.MutableRefObject<boolean>
  latestStatus: any
  isLoadingAnalysis: boolean
  isLoadingPosts: boolean
  postAnalysisId: string | null
  posts: any[]
  messagesLoaded: boolean
  setIsTypingActive: (active: boolean) => void
  setIsTypingComplete: (complete: boolean) => void
}

/**
 * Manages all scroll behavior for the analysis component
 * 
 * SCROLL RULES:
 * 1. On initial load of existing analysis → scroll to bottom (once)
 * 2. When user sends a message → scroll user message to top (handled by chat-messages.tsx)
 * 3. During AI streaming → NO auto-scroll (user controls)
 * 4. Never scroll again after user has interacted
 */
export function useScrollBehavior({
  currentRequest,
  messagesContainerRef,
  hasScrolledToBottomRef,
  userHasInteractedRef,
  wasCompletedOnLoadRef,
  isTypingActiveRef,
  latestStatus,
  isLoadingAnalysis,
  isLoadingPosts,
  postAnalysisId,
  posts,
  messagesLoaded,
  setIsTypingActive,
  setIsTypingComplete,
}: UseScrollBehaviorProps) {
  
  // Track if we've attempted scroll for this analysis
  const scrollAttemptedRef = useRef<Set<string>>(new Set())
  
  /**
   * Scroll to bottom - simple and reliable
   */
  const scrollToBottom = useCallback(() => {
    const container = messagesContainerRef.current
    if (!container) {
      console.warn('⚠️ [Scroll] No container ref')
      return false
    }
    
    const scrollHeight = container.scrollHeight
    const clientHeight = container.clientHeight
    const maxScroll = scrollHeight - clientHeight
    
    if (maxScroll <= 0) {
      console.log('⚠️ [Scroll] Nothing to scroll (content fits in viewport)')
      return false
    }
    
    container.scrollTop = maxScroll
    console.log('✅ [Scroll] Scrolled to bottom:', { scrollHeight, clientHeight, maxScroll, actualScrollTop: container.scrollTop })
    return true
  }, [messagesContainerRef])
  
  /**
   * Main scroll effect for existing analyses
   * Triggers when messages are loaded for a completed analysis
   */
  useEffect(() => {
    // Guard conditions
    if (!currentRequest?.id) return
    if (isLoadingAnalysis || isLoadingPosts) return
    if (!messagesLoaded) return
    if (posts.length === 0) return
    
    // Only scroll for completed analyses that were completed on load
    const wasCompletedOnLoad = wasCompletedOnLoadRef.current.has(currentRequest.id)
    if (!wasCompletedOnLoad) {
      console.log('⏭️ [Scroll] Skipping - analysis was not completed on load')
      return
    }
    
    // Don't scroll if user has interacted
    if (userHasInteractedRef.current) {
      console.log('⏭️ [Scroll] Skipping - user has interacted')
      return
    }
    
    // Don't scroll twice for same analysis
    if (hasScrolledToBottomRef.current.has(currentRequest.id)) {
      console.log('⏭️ [Scroll] Skipping - already scrolled for this analysis')
      return
    }
    
    // Don't attempt twice
    if (scrollAttemptedRef.current.has(currentRequest.id)) {
      console.log('⏭️ [Scroll] Skipping - already attempted for this analysis')
      return
    }
    
    scrollAttemptedRef.current.add(currentRequest.id)
    
    console.log('🎯 [Scroll] Will scroll to bottom for existing analysis:', currentRequest.id)
    
    // Use multiple attempts with increasing delays to ensure content is rendered
    const attemptScroll = (attemptNum: number) => {
      if (userHasInteractedRef.current) {
        console.log(`⏭️ [Scroll] Attempt ${attemptNum} cancelled - user interacted`)
        return
      }
      
      if (hasScrolledToBottomRef.current.has(currentRequest.id)) {
        console.log(`⏭️ [Scroll] Attempt ${attemptNum} cancelled - already scrolled`)
        return
      }
      
      requestAnimationFrame(() => {
        const success = scrollToBottom()
        if (success && currentRequest.id) {
          hasScrolledToBottomRef.current.add(currentRequest.id)
          console.log(`✅ [Scroll] Attempt ${attemptNum} succeeded`)
        } else {
          console.log(`⚠️ [Scroll] Attempt ${attemptNum} failed, will retry`)
        }
      })
    }
    
    // Attempt scrolls at increasing intervals
    // First attempt immediately after RAF
    setTimeout(() => attemptScroll(1), 100)
    setTimeout(() => attemptScroll(2), 300)
    setTimeout(() => attemptScroll(3), 600)
    setTimeout(() => attemptScroll(4), 1000)
    
  }, [
    currentRequest?.id,
    isLoadingAnalysis,
    isLoadingPosts,
    messagesLoaded,
    posts.length,
    wasCompletedOnLoadRef,
    userHasInteractedRef,
    hasScrolledToBottomRef,
    scrollToBottom
  ])
  
  // Listen for typing progress events (no auto-scroll during typing)
  useEffect(() => {
    const handleTypingProgress = () => {
      isTypingActiveRef.current = true
      setIsTypingActive(true)
      setIsTypingComplete(false)
    }
    
    const handleTypingComplete = () => {
      isTypingActiveRef.current = false
      setIsTypingActive(false)
      setIsTypingComplete(true)
    }
    
    window.addEventListener('analysis-typing-progress', handleTypingProgress)
    window.addEventListener('analysis-typing-complete', handleTypingComplete)
    
    return () => {
      window.removeEventListener('analysis-typing-progress', handleTypingProgress)
      window.removeEventListener('analysis-typing-complete', handleTypingComplete)
    }
  }, [isTypingActiveRef, setIsTypingActive, setIsTypingComplete])
  
  // Listen for user sending messages - disable auto-scroll
  useEffect(() => {
    const handleMessageSending = () => {
      console.log('🚫 [Scroll] User sent message - disabling auto-scroll')
      userHasInteractedRef.current = true
    }
    
    window.addEventListener('chat-message-sending', handleMessageSending)
    
    return () => {
      window.removeEventListener('chat-message-sending', handleMessageSending)
    }
  }, [userHasInteractedRef])
  
  // Reset scroll tracking when analysis changes
  useEffect(() => {
    if (currentRequest?.id) {
      // Reset user interaction flag when switching analyses
      userHasInteractedRef.current = false
      scrollAttemptedRef.current.clear()
      console.log('🔄 [Scroll] Reset interaction flag for new analysis:', currentRequest.id)
    }
  }, [currentRequest?.id, userHasInteractedRef])
  
  return {
    scrollToBottom,
  }
}
