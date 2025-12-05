import { useState, useRef } from "react"
import { type AnalysisRequest, type Post } from "@/lib/api"

/**
 * Centralized state management for analysis component
 * Manages all state and refs in one place for better organization
 */
export function useAnalysisState() {
  // Core analysis state
  const [currentRequest, setCurrentRequest] = useState<AnalysisRequest | null>(null)
  const [posts, setPosts] = useState<Post[]>([])
  const [isLoadingAnalysis, setIsLoadingAnalysis] = useState(false)
  const [isLoadingPosts, setIsLoadingPosts] = useState(false)
  const [isFormMinimized, setIsFormMinimized] = useState(false)
  
  // Chat state
  const [chatSessionId, setChatSessionId] = useState<string | null>(null)
  const [postAnalysisId, setPostAnalysisId] = useState<string | null>(null)
  const [messagesLoaded, setMessagesLoaded] = useState(false)
  
  // Typing effect state
  const [isTypingActive, setIsTypingActive] = useState(false)
  const [isTypingComplete, setIsTypingComplete] = useState(false)
  
  // Refs for scroll container
  const messagesContainerRef = useRef<HTMLDivElement>(null)
  
  // Refs for tracking fetch state
  const postsFetchedForRef = useRef<string | null>(null)
  const postsFetchingRef = useRef<string | null>(null)
  const analysisLoadingRef = useRef<string | null>(null)
  const postsFetchAttemptsRef = useRef<Map<string, number>>(new Map())
  
  // Refs for chat session tracking
  const chatSessionFetchedRef = useRef<Set<string>>(new Set())
  
  // Refs for scroll behavior
  const hasScrolledToBottomRef = useRef<Set<string>>(new Set())
  const userHasInteractedRef = useRef(false)
  const wasCompletedOnLoadRef = useRef<Set<string>>(new Set())
  const isTypingActiveRef = useRef(false)
  const prevStatusRef = useRef<string | null>(null)
  
  return {
    // State
    currentRequest,
    setCurrentRequest,
    posts,
    setPosts,
    isLoadingAnalysis,
    setIsLoadingAnalysis,
    isLoadingPosts,
    setIsLoadingPosts,
    isFormMinimized,
    setIsFormMinimized,
    chatSessionId,
    setChatSessionId,
    postAnalysisId,
    setPostAnalysisId,
    messagesLoaded,
    setMessagesLoaded,
    isTypingActive,
    setIsTypingActive,
    isTypingComplete,
    setIsTypingComplete,
    
    // Refs
    messagesContainerRef,
    postsFetchedForRef,
    postsFetchingRef,
    analysisLoadingRef,
    postsFetchAttemptsRef,
    chatSessionFetchedRef,
    hasScrolledToBottomRef,
    userHasInteractedRef,
    wasCompletedOnLoadRef,
    isTypingActiveRef,
    prevStatusRef,
  }
}

export type AnalysisState = ReturnType<typeof useAnalysisState>


