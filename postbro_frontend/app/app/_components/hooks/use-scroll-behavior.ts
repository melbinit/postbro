import { useEffect, useCallback, useRef } from "react"
import { type AnalysisRequest } from "@/lib/api"
import { logger } from "@/lib/logger"

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
 * 2. On NEW analysis completing in real-time → scroll to START of chat section (once)
 * 3. When user sends a message → scroll user message to top (handled by chat-messages.tsx)
 * 4. During AI streaming → NO auto-scroll (user controls)
 * 5. Never scroll again after user has interacted
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
  // Track if we've scrolled for newly completed analyses (real-time completion)
  const newCompletionScrolledRef = useRef<Set<string>>(new Set())
  
  /**
   * Scroll to bottom - simple and reliable
   */
  const scrollToBottom = useCallback(() => {
    const container = messagesContainerRef.current
    if (!container) {
      return false
    }
    
    const scrollHeight = container.scrollHeight
    const clientHeight = container.clientHeight
    const maxScroll = scrollHeight - clientHeight
    
    if (maxScroll <= 0) {
      return false
    }
    
    container.scrollTop = maxScroll
    return true
  }, [messagesContainerRef])
  
  /**
   * Scroll to make the chat section visible (for newly completed analyses)
   * Scrolls to bring the START of the chat into view, not the bottom
   * This allows user to read from the beginning by scrolling down
   */
  const scrollToChatSection = useCallback((analysisId: string) => {
    const container = messagesContainerRef.current
    if (!container) return false

    // Find the chat section by data attribute
    const chatSection = container.querySelector(`[data-chat-section][data-analysis-id="${analysisId}"]`)
    
    if (chatSection) {
      const containerRect = container.getBoundingClientRect()
      const chatRect = chatSection.getBoundingClientRect()
      
      // Calculate scroll position to bring chat section to top of viewport with padding
      const offsetFromContainerTop = chatRect.top - containerRect.top
      const targetScroll = container.scrollTop + offsetFromContainerTop - 80 // 80px padding from top
      
      logger.debug('[Scroll] Scrolling to chat section:', {
        chatTop: chatRect.top.toFixed(2),
        containerTop: containerRect.top.toFixed(2),
        offset: offsetFromContainerTop.toFixed(2),
        targetScroll: targetScroll.toFixed(2)
      })
      
      container.scrollTop = Math.max(0, targetScroll)
      return true
    }
    
    logger.debug('[Scroll] Chat section not found for analysis:', analysisId)
    return false
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
      return
    }
    
    // Don't scroll if user has interacted
    if (userHasInteractedRef.current) {
      return
    }
    
    // Don't scroll twice for same analysis
    if (hasScrolledToBottomRef.current.has(currentRequest.id)) {
      return
    }
    
    // Don't attempt twice
    if (scrollAttemptedRef.current.has(currentRequest.id)) {
      return
    }
    
    scrollAttemptedRef.current.add(currentRequest.id)
    
    // Use multiple attempts with increasing delays to ensure content is rendered
    const attemptScroll = (attemptNum: number) => {
      if (userHasInteractedRef.current) {
        return
      }
      
      if (hasScrolledToBottomRef.current.has(currentRequest.id)) {
        return
      }
      
      requestAnimationFrame(() => {
        const success = scrollToBottom()
        if (success && currentRequest.id) {
          hasScrolledToBottomRef.current.add(currentRequest.id)
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
  
  /**
   * Effect for newly completed analyses (completed in real-time, NOT on load)
   * Listens for chat-messages-loaded event and scrolls to chat section
   * This brings the first PostBro response into view
   */
  useEffect(() => {
    const handleChatMessagesLoaded = (event: CustomEvent) => {
      const { analysisId, wasCompletedOnLoad, messageCount } = event.detail
      
      // Skip if this was already completed on load (handled by main scroll effect)
      if (wasCompletedOnLoad) {
        logger.debug('[Scroll] Skipping new completion scroll - was completed on load:', analysisId)
        return
      }
      
      // Skip if user has already interacted
      if (userHasInteractedRef.current) {
        logger.debug('[Scroll] Skipping new completion scroll - user has interacted')
        return
      }
      
      // Don't scroll twice for the same analysis
      if (newCompletionScrolledRef.current.has(analysisId)) {
        logger.debug('[Scroll] Skipping new completion scroll - already scrolled:', analysisId)
        return
      }
      
      logger.debug('[Scroll] New analysis completed - will scroll to chat section:', analysisId, 'messages:', messageCount)
      newCompletionScrolledRef.current.add(analysisId)
      
      // Multiple attempts to catch when content is fully rendered
      const attemptScroll = (attempt: number) => {
        if (userHasInteractedRef.current) return
        
        requestAnimationFrame(() => {
          const success = scrollToChatSection(analysisId)
          logger.debug(`[Scroll] Attempt ${attempt} to scroll to chat:`, success ? 'success' : 'waiting')
        })
      }
      
      // Attempt at increasing intervals to ensure content is rendered
      setTimeout(() => attemptScroll(1), 100)
      setTimeout(() => attemptScroll(2), 300)
      setTimeout(() => attemptScroll(3), 600)
      setTimeout(() => attemptScroll(4), 1000)
    }
    
    window.addEventListener('chat-messages-loaded', handleChatMessagesLoaded as EventListener)
    
    return () => {
      window.removeEventListener('chat-messages-loaded', handleChatMessagesLoaded as EventListener)
    }
  }, [userHasInteractedRef, scrollToChatSection])
  
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
      newCompletionScrolledRef.current.clear()
    }
  }, [currentRequest?.id, userHasInteractedRef])
  
  return {
    scrollToBottom,
  }
}
