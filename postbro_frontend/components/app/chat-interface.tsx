"use client"

import { useState, useEffect, useRef, useCallback } from "react"
import { chatApi, ChatMessage, ChatSession } from "@/lib/api"
import { ChatMessage as ChatMessageComponent } from "./chat-message"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Spinner } from "@/components/ui/spinner"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Send, AlertCircle, RefreshCw } from "lucide-react"
import { cn } from "@/lib/utils"
import { toast } from "sonner"

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
      
      const errorMessage = err.message || err.data?.message || "Failed to send message. Please try again."
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
              <div className="flex-shrink-0">
                <div className="size-7 md:size-8 rounded-full bg-gradient-to-br from-primary to-purple-600 flex items-center justify-center">
                  <span className="text-white text-xs md:text-sm font-bold">PB</span>
                </div>
              </div>
              <div className="flex-1 min-w-0">
                <div className="bg-card/60 backdrop-blur-sm rounded-2xl rounded-tl-sm px-3 py-2.5 md:px-4 md:py-3 border border-border/30 inline-flex items-center gap-2">
                  <Spinner className="h-4 w-4" />
                  <span className="text-sm text-muted-foreground">Thinking...</span>
                </div>
              </div>
            </div>
          )}
          
          {/* Error message as a chat bubble */}
          {error && session && (
            <div className="flex gap-3 md:gap-4">
              <div className="flex-shrink-0">
                <div className="size-7 md:size-8 rounded-full bg-destructive/10 flex items-center justify-center">
                  <AlertCircle className="h-4 w-4 text-destructive" />
                </div>
              </div>
              <div className="flex-1 min-w-0">
                <div className="bg-destructive/5 border border-destructive/20 rounded-2xl rounded-tl-sm px-3 py-2.5 md:px-4 md:py-3">
                  <p className="text-sm text-destructive">{error}</p>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setError(null)}
                    className="mt-2 h-7 text-xs"
                  >
                    Dismiss
                  </Button>
                </div>
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
              className="px-2.5 py-1.5 text-xs rounded-full bg-muted hover:bg-muted/80 transition-colors touch-manipulation"
            >
              Generate more ideas
            </button>
            <button
              onClick={() => setInput("Explain the viral formula in simple terms")}
              className="px-2.5 py-1.5 text-xs rounded-full bg-muted hover:bg-muted/80 transition-colors touch-manipulation"
            >
              Explain viral formula
            </button>
            <button
              onClick={() => setInput("How can I apply this to my content?")}
              className="px-2.5 py-1.5 text-xs rounded-full bg-muted hover:bg-muted/80 transition-colors touch-manipulation"
            >
              How to apply this
            </button>
          </div>
        </div>
      )}

      {/* Input Area */}
      <div className="border-t border-border/50 p-3 md:p-4 pb-safe">
        <div className="flex gap-2 items-end">
          <Textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Message PostBro..."
            className="min-h-[44px] max-h-[160px] md:max-h-[200px] resize-none text-base md:text-sm"
            disabled={isSending || isLoading}
            rows={1}
          />
          <Button
            onClick={handleSend}
            disabled={!input.trim() || isSending || isLoading}
            size="icon"
            className="shrink-0 h-[44px] w-[44px] touch-manipulation"
          >
            {isSending ? (
              <Spinner className="h-4 w-4" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </Button>
        </div>
      </div>
    </div>
  )
}

