"use client"

import { useState, useEffect, useRef, useCallback } from "react"
import { chatApi, ChatMessage, ChatSession } from "@/lib/api"
import { ChatMessage as ChatMessageComponent } from "./chat-message"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Spinner } from "@/components/ui/spinner"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Send, AlertCircle, RefreshCw, Sparkles } from "lucide-react"
import { cn } from "@/lib/utils"
import { toast } from "sonner"
import { getSafeErrorMessage } from "@/app/app/_components/utils/error-utils"

interface ChatInterfaceProps {
  postAnalysisId: string
  className?: string
}

export function ChatInterface({ postAnalysisId, className }: ChatInterfaceProps) {
  const [session, setSession] = useState<ChatSession | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [isInitializing, setIsInitializing] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isSending, setIsSending] = useState(false)
  
  const scrollAreaRef = useRef<HTMLDivElement>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const tempMessageIdRef = useRef<string | null>(null)
  const userHasScrolledRef = useRef(false)
  const isNearBottomRef = useRef(true)

  // Initialize chat session
  useEffect(() => {
    let mounted = true
    
    const initializeSession = async () => {
      try {
        setIsInitializing(true)
        setError(null)
        
        // Try to get existing session first
        const existingSessions = await chatApi.listChatSessions(postAnalysisId)
        
        if (existingSessions.sessions.length > 0) {
          // Load existing session
          const existingSession = existingSessions.sessions[0]
          const sessionData = await chatApi.getChatSession(existingSession.id)
          
          if (mounted) {
            setSession(sessionData.session)
            setMessages(sessionData.session.messages)
            setIsInitializing(false)
          }
        } else {
          // Create new session (but don't show it until first message)
          if (mounted) {
            setIsInitializing(false)
          }
        }
      } catch (err: any) {
        console.error("Failed to initialize chat session:", err)
        if (mounted) {
          setError(err.message || "Failed to initialize chat")
          setIsInitializing(false)
        }
      }
    }
    
    initializeSession()
    
    return () => {
      mounted = false
    }
  }, [postAnalysisId])

  // Detect user scroll to pause auto-scroll
  useEffect(() => {
    const scrollContainer = scrollAreaRef.current
    if (!scrollContainer) return

    const handleScroll = () => {
      const viewport = scrollContainer.querySelector('[data-radix-scroll-area-viewport]')
      if (!viewport) return

      const { scrollTop, scrollHeight, clientHeight } = viewport
      const distanceFromBottom = scrollHeight - scrollTop - clientHeight
      
      // User is near bottom (within 100px)
      isNearBottomRef.current = distanceFromBottom < 100
      
      // If user scrolls up significantly, mark as user-scrolled
      if (distanceFromBottom > 100) {
        userHasScrolledRef.current = true
      } else {
        userHasScrolledRef.current = false
      }
    }

    const viewport = scrollContainer.querySelector('[data-radix-scroll-area-viewport]')
    viewport?.addEventListener('scroll', handleScroll, { passive: true })

    return () => {
      viewport?.removeEventListener('scroll', handleScroll)
    }
  }, [])

  // Auto-scroll to bottom when new messages arrive (only if user hasn't scrolled up)
  useEffect(() => {
    if (!messagesEndRef.current || !scrollAreaRef.current) return
    
    // Only auto-scroll if user is near bottom or hasn't manually scrolled up
    if (!userHasScrolledRef.current || isNearBottomRef.current) {
      const viewport = scrollAreaRef.current.querySelector('[data-radix-scroll-area-viewport]')
      if (viewport) {
        // Smooth scroll to bottom
        setTimeout(() => {
          viewport.scrollTo({
            top: viewport.scrollHeight,
            behavior: 'smooth'
          })
        }, 100)
      }
    }
  }, [messages])

  // Auto-resize textarea (responsive max height)
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "44px"
      // Mobile: 160px max, Desktop: 200px max
      const isMobile = typeof window !== 'undefined' && window.innerWidth < 768
      const maxHeight = isMobile ? 160 : 200
      const newHeight = Math.min(textareaRef.current.scrollHeight, maxHeight)
      textareaRef.current.style.height = `${newHeight}px`
    }
  }, [input])

  // Handle sending message
  const handleSend = useCallback(async () => {
    const messageText = input.trim()
    
    if (!messageText || isSending || isLoading) {
      return
    }

    // Clear error
    setError(null)
    setIsSending(true)
    setInput("")

    try {
      let currentSession = session

      // Create session if it doesn't exist
      if (!currentSession) {
        const newSession = await chatApi.createChatSession(postAnalysisId)
        currentSession = newSession.session
        setSession(currentSession)
      }

      // Store temp message ID for cleanup
      tempMessageIdRef.current = `temp-${Date.now()}`
      
      // Add user message optimistically
      const userMessage: ChatMessage = {
        id: tempMessageIdRef.current,
        role: "user",
        content: messageText,
        created_at: new Date().toISOString(),
      }
      
      setMessages((prev) => [...prev, userMessage])

      // Send message to API
      const response = await chatApi.sendMessage(currentSession.id, messageText)

      // Replace temp message and add assistant response
      setMessages((prev) => {
        const filtered = prev.filter((msg) => msg.id !== tempMessageIdRef.current)
        tempMessageIdRef.current = null
        return [...filtered, response.user_message, response.assistant_message]
      })

      // Update session
      if (currentSession) {
        const updatedSession = await chatApi.getChatSession(currentSession.id)
        setSession(updatedSession.session)
      }
    } catch (err: any) {
      console.error("Failed to send message:", err)
      
      // Remove optimistic message on error
      if (tempMessageIdRef.current) {
        setMessages((prev) => prev.filter((msg) => msg.id !== tempMessageIdRef.current))
        tempMessageIdRef.current = null
      }
      
      const errorMessage = getSafeErrorMessage(err) || "Failed to send message. Please try again."
      setError(errorMessage)
      toast.error(errorMessage)
      
      // Restore input
      setInput(messageText)
    } finally {
      setIsSending(false)
      tempMessageIdRef.current = null
    }
  }, [input, session, postAnalysisId, isSending, isLoading])

  // Handle Enter key (Shift+Enter for new line)
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  // Retry initialization
  const handleRetry = () => {
    setError(null)
    setIsInitializing(true)
    // Re-run initialization
    const initializeSession = async () => {
      try {
        const existingSessions = await chatApi.listChatSessions(postAnalysisId)
        
        if (existingSessions.sessions.length > 0) {
          const existingSession = existingSessions.sessions[0]
          const sessionData = await chatApi.getChatSession(existingSession.id)
          setSession(sessionData.session)
          setMessages(sessionData.session.messages)
        }
      } catch (err: any) {
        setError(err.message || "Failed to initialize chat")
      } finally {
        setIsInitializing(false)
      }
    }
    initializeSession()
  }

  // Loading state
  if (isInitializing) {
    return (
      <div className={cn("flex items-center justify-center p-8", className)}>
        <div className="flex flex-col items-center gap-3">
          <Spinner className="h-6 w-6" />
          <p className="text-sm text-muted-foreground">Loading chat...</p>
        </div>
      </div>
    )
  }

  // Error state
  if (error && !session) {
    return (
      <div className={cn("p-6", className)}>
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription className="flex items-center justify-between">
            <span>{error}</span>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleRetry}
              className="ml-4"
            >
              <RefreshCw className="h-4 w-4 mr-2" />
              Retry
            </Button>
          </AlertDescription>
        </Alert>
      </div>
    )
  }

  return (
    <div className={cn("flex flex-col h-full", className)}>
      {/* Messages Area */}
      <ScrollArea className="flex-1" ref={scrollAreaRef}>
        <div className="space-y-4 md:space-y-6 px-3 py-4 md:px-4 md:py-6">
          {messages.map((message) => (
            <ChatMessageComponent key={message.id} message={message} />
          ))}
          
          {/* Loading indicator when sending */}
          {isSending && (
            <div className="flex gap-3 md:gap-4">
              <div className="flex-shrink-0 mt-0.5">
                <div className="size-7 md:size-8 rounded-full bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center ring-2 ring-background">
                  <Sparkles className="h-3.5 w-3.5 md:h-4 md:w-4 text-white" />
                </div>
              </div>
              <div className="flex-1 min-w-0 pt-1">
                <div className="flex items-center gap-1.5">
                  <span className="text-sm text-muted-foreground">Thinking</span>
                  <span className="flex gap-0.5">
                    <span className="size-1 rounded-full bg-muted-foreground/50 animate-bounce [animation-delay:0ms]" />
                    <span className="size-1 rounded-full bg-muted-foreground/50 animate-bounce [animation-delay:150ms]" />
                    <span className="size-1 rounded-full bg-muted-foreground/50 animate-bounce [animation-delay:300ms]" />
                  </span>
                </div>
              </div>
            </div>
          )}
          
          {/* Error message - clean inline style */}
          {error && session && (
            <div className="flex gap-3 md:gap-4">
              <div className="flex-shrink-0 mt-0.5">
                <div className="size-7 md:size-8 rounded-full bg-destructive/10 flex items-center justify-center ring-2 ring-background">
                  <AlertCircle className="h-3.5 w-3.5 md:h-4 md:w-4 text-destructive" />
                </div>
              </div>
              <div className="flex-1 min-w-0 pt-0.5">
                <p className="text-sm text-destructive">{error}</p>
                <button
                  onClick={() => setError(null)}
                  className="mt-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
                >
                  Dismiss
                </button>
              </div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>
      </ScrollArea>

      {/* Suggestion chips - only show when no messages */}
      {messages.length === 0 && !isSending && (
        <div className="px-3 pb-3 md:px-4 md:pb-4">
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => setInput("Can you generate more content ideas like this?")}
              className="px-3 py-1.5 text-xs font-medium rounded-full border border-border/60 hover:border-primary/40 hover:bg-primary/5 text-muted-foreground hover:text-foreground transition-all touch-manipulation"
            >
              Generate more ideas
            </button>
            <button
              onClick={() => setInput("Explain the viral formula in simple terms")}
              className="px-3 py-1.5 text-xs font-medium rounded-full border border-border/60 hover:border-primary/40 hover:bg-primary/5 text-muted-foreground hover:text-foreground transition-all touch-manipulation"
            >
              Explain viral formula
            </button>
            <button
              onClick={() => setInput("How can I apply this to my content?")}
              className="px-3 py-1.5 text-xs font-medium rounded-full border border-border/60 hover:border-primary/40 hover:bg-primary/5 text-muted-foreground hover:text-foreground transition-all touch-manipulation"
            >
              How to apply this
            </button>
          </div>
        </div>
      )}

      {/* Input Area - Modern floating style */}
      <div className="p-3 md:p-4 pb-safe">
        <div className="flex gap-2 items-end bg-muted/50 rounded-2xl border border-border/40 p-1.5 focus-within:border-primary/30 focus-within:ring-2 focus-within:ring-primary/10 transition-all">
          <Textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about this analysis..."
            className="min-h-[40px] max-h-[140px] md:max-h-[180px] resize-none text-[15px] border-0 bg-transparent focus-visible:ring-0 focus-visible:ring-offset-0 placeholder:text-muted-foreground/60"
            disabled={isSending || isLoading}
            rows={1}
          />
          <Button
            onClick={handleSend}
            disabled={!input.trim() || isSending || isLoading}
            size="icon"
            className="shrink-0 h-9 w-9 rounded-xl bg-primary hover:bg-primary/90 disabled:opacity-30 touch-manipulation transition-all"
          >
            {isSending ? (
              <Spinner className="h-4 w-4" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </Button>
        </div>
        <p className="text-[10px] text-muted-foreground/60 text-center mt-2">
          Press Enter to send, Shift+Enter for new line
        </p>
      </div>
    </div>
  )
}

