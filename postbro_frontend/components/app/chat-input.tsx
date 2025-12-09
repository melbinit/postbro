"use client"

import { useState, useEffect, useRef, useCallback } from "react"
import { chatApi } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Spinner } from "@/components/ui/spinner"
import { Send } from "lucide-react"
import { toast } from "sonner"
import { getSafeErrorMessage } from "@/app/app/_components/utils/error-utils"

interface ChatInputProps {
  postAnalysisId: string
  onMessageSent?: (userMessage: string) => void
  showSuggestions?: boolean
}

export function ChatInput({ postAnalysisId, onMessageSent, showSuggestions = true }: ChatInputProps) {
  const [input, setInput] = useState("")
  const [isSending, setIsSending] = useState(false)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [hasMessages, setHasMessages] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Listen for messages loaded event
  useEffect(() => {
    const handleMessagesLoaded = (event: CustomEvent) => {
      if (event.detail.postAnalysisId === postAnalysisId) {
        setHasMessages(event.detail.hasMessages)
      }
    }

    window.addEventListener('chat-messages-loaded', handleMessagesLoaded as EventListener)
    return () => {
      window.removeEventListener('chat-messages-loaded', handleMessagesLoaded as EventListener)
    }
  }, [postAnalysisId])

  // Initialize session
  useEffect(() => {
    const initializeSession = async () => {
      try {
        const existingSessions = await chatApi.listChatSessions(postAnalysisId)
        
        if (existingSessions.sessions.length > 0) {
          setSessionId(existingSessions.sessions[0].id)
        } else {
          // Create session lazily on first message
          setSessionId(null)
        }
      } catch (err) {
        console.error("Failed to initialize chat session:", err)
      }
    }
    
    initializeSession()
  }, [postAnalysisId])

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "44px"
      const isMobile = typeof window !== 'undefined' && window.innerWidth < 768
      const maxHeight = isMobile ? 160 : 200
      const newHeight = Math.min(textareaRef.current.scrollHeight, maxHeight)
      textareaRef.current.style.height = `${newHeight}px`
    }
  }, [input])

  const handleSend = useCallback(async () => {
    const messageText = input.trim()
    
    if (!messageText || isSending) {
      return
    }

    // Clear input immediately for better UX
    setInput("")
    setIsSending(true)

    try {
      let currentSessionId = sessionId

      // Create session if it doesn't exist
      if (!currentSessionId) {
        const newSession = await chatApi.createChatSession(postAnalysisId)
        currentSessionId = newSession.session.id
        setSessionId(currentSessionId)
      }

      // Trigger streaming - chat-messages component will handle the stream
      if (typeof window !== 'undefined') {
        window.dispatchEvent(new CustomEvent('chat-message-sending', {
          detail: { 
            postAnalysisId, 
            userMessage: messageText,
            sessionId: currentSessionId
          }
        }))
      }
      
      // Notify parent
      onMessageSent?.(messageText)
      
      // Note: chat-messages component handles the streaming and will trigger
      // 'chat-message-sent' event when streaming completes
      
    } catch (err: any) {
      console.error("Failed to send message:", err)
      const errorMessage = getSafeErrorMessage(err) || "Failed to send message. Please try again."
      toast.error(errorMessage)
      setInput(messageText) // Restore input
      
      // Trigger error event to remove optimistic message
      if (typeof window !== 'undefined') {
        window.dispatchEvent(new CustomEvent('chat-message-error', {
          detail: { postAnalysisId }
        }))
      }
    } finally {
      setIsSending(false)
    }
  }, [input, sessionId, postAnalysisId, isSending, onMessageSent])

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="space-y-3">
      {/* Suggestion chips - only show when enabled, no input, and no messages */}
      {showSuggestions && !input && !hasMessages && (
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
      )}
      
      <div className="flex gap-2 items-end">
        <Textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Message PostBro..."
          className="min-h-[44px] max-h-[160px] md:max-h-[200px] resize-none text-base md:text-sm"
          disabled={isSending}
          rows={1}
        />
        <Button
          onClick={handleSend}
          disabled={!input.trim() || isSending}
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
  )
}

