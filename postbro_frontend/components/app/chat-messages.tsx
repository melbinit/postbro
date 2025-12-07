"use client"

import { useState, useEffect, useRef } from "react"
import { chatApi, ChatMessage } from "@/lib/api"
import { ChatMessage as ChatMessageComponent } from "./chat-message"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { AlertCircle, Sparkles } from "lucide-react"
import { Spinner } from "@/components/ui/spinner"
import { toast } from "sonner"

interface ChatMessagesProps {
  postAnalysisId: string
  onMessagesLoaded?: (messages: ChatMessage[]) => void
  scrollContainerRef?: React.RefObject<HTMLDivElement>
}

export function ChatMessages({ postAnalysisId, onMessagesLoaded, scrollContainerRef }: ChatMessagesProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [streamingMessage, setStreamingMessage] = useState<ChatMessage | undefined>(undefined)
  const [userHasSentMessage, setUserHasSentMessage] = useState(false) // Track if user has sent a message
  
  // Refs for scroll management
  const streamingMessageRef = useRef<HTMLDivElement>(null)
  const thinkingLoaderRef = useRef<HTMLDivElement>(null)
  const latestUserMessageRef = useRef<HTMLDivElement>(null) // Track latest user message for scrolling
  
  // Use parent scroll container or create fallback
  const messagesContainerRef = scrollContainerRef || useRef<HTMLDivElement>(null)

  // Scroll latest user message to top of viewport (ChatGPT style)
  const scrollLatestMessageToTop = () => {
    const container = messagesContainerRef.current
    const messageElement = latestUserMessageRef.current
    
    if (!container || !messageElement) {
      console.warn('⚠️ [ChatMessages] Refs not available', {
        container: !!container,
        message: !!messageElement
      })
      return
    }
    
    // Calculate the message's position within the scrollable container
    // We need to scroll the container so the message appears at the VERY TOP
    // This will hide everything above it (PostCard, Analysis, etc.)
    const containerRect = container.getBoundingClientRect()
    const messageRect = messageElement.getBoundingClientRect()
    
    // How far is the message from the container's current top edge?
    const messageOffsetFromContainerTop = messageRect.top - containerRect.top
    
    // Scroll the container by that amount to bring message to the VERY TOP
    // Add a small offset (24px) for padding from the top edge
    const targetScrollTop = container.scrollTop + messageOffsetFromContainerTop - 24
    
    // Check max scroll before attempting
    const maxScroll = container.scrollHeight - container.clientHeight
    const clampedTargetScroll = Math.min(Math.max(0, targetScrollTop), maxScroll)
    
    console.log('📜 [ChatMessages] Scroll calculation:', {
      containerTop: containerRect.top.toFixed(2),
      messageTop: messageRect.top.toFixed(2),
      offset: messageOffsetFromContainerTop.toFixed(2),
      currentScroll: container.scrollTop.toFixed(2),
      targetScroll: targetScrollTop.toFixed(2),
      maxScroll: maxScroll.toFixed(2),
      clampedTarget: clampedTargetScroll.toFixed(2),
      scrollHeight: container.scrollHeight,
      clientHeight: container.clientHeight,
      willExceedMax: targetScrollTop > maxScroll
    })
    
    // Force scroll directly
    container.scrollTop = clampedTargetScroll
    
    // Force scroll again after a delay to override any interference
    setTimeout(() => {
      if (container && messageElement) {
        const newContainerRect = container.getBoundingClientRect()
        const newMessageRect = messageElement.getBoundingClientRect()
        const newOffset = newMessageRect.top - newContainerRect.top
        const newTargetScroll = container.scrollTop + newOffset - 24
        
        container.scrollTop = Math.max(0, newTargetScroll)
        
        console.log('✅ [ChatMessages] Forced scroll again:', {
          targetScroll: newTargetScroll.toFixed(2),
          actualScroll: container.scrollTop.toFixed(2),
          messageOffsetFromTop: newOffset.toFixed(2)
        })
      }
    }, 100)
  }


  // Load messages ONLY on initial mount or when postAnalysisId changes
  useEffect(() => {
    let mounted = true
    
    const loadMessages = async () => {
      try {
        if (messages.length === 0) {
          setIsLoading(true)
        }
        setError(null)
        
        console.log('📥 [ChatMessages] Loading messages for postAnalysisId:', postAnalysisId)
        const existingSessions = await chatApi.listChatSessions(postAnalysisId)
        
        if (existingSessions.sessions.length > 0) {
          const existingSession = existingSessions.sessions[0]
          const sessionData = await chatApi.getChatSession(existingSession.id)
          
          if (mounted) {
            console.log('✅ [ChatMessages] Loaded', sessionData.session.messages.length, 'messages')
            // Mark all loaded messages as complete
            const messagesWithStatus = sessionData.session.messages.map(msg => ({
              ...msg,
              status: 'complete' as const
            }))
            setMessages(messagesWithStatus)
            onMessagesLoaded?.(messagesWithStatus)
            // NO scroll on initial load - let user see where they left off
          }
        } else {
          if (mounted) {
            console.log('📭 [ChatMessages] No existing messages')
            setMessages([])
            onMessagesLoaded?.([])
          }
        }
      } catch (err: any) {
        console.error('❌ [ChatMessages] Failed to load messages:', err)
        if (mounted) {
          // Don't show error for 500 errors - might be transient DB issue
          // Just show empty state and let user try again
          if (err.status === 500) {
            console.warn('⚠️ [ChatMessages] Server error (500) - likely transient, showing empty state')
            setMessages([])
            onMessagesLoaded?.([])
          } else {
            setError(err.message || "Failed to load chat messages")
          }
        }
      } finally {
        if (mounted) {
          setIsLoading(false)
        }
      }
    }
    
    loadMessages()

    // Listen for optimistic message sending (triggers streaming)
    const handleMessageSending = async (event: CustomEvent) => {
      if (event.detail.postAnalysisId !== postAnalysisId) return
      
      const { userMessage, sessionId } = event.detail
      console.log('💬 [ChatMessages] User message received:', userMessage.substring(0, 50) + '...')
      
      // Mark that user has sent a message (enables bottom padding for scroll)
      setUserHasSentMessage(true)
      
      // Step 1: Add user message to messages array immediately (like ChatGPT)
      const newUserMessage: ChatMessage = {
        id: `user-${Date.now()}`,
        role: 'user',
        content: userMessage,
        created_at: new Date().toISOString(),
        status: 'complete' // User messages are always complete
      }
      setMessages(prev => [...prev, newUserMessage])
      
      // Scroll latest user message to top of viewport (ChatGPT style)
      // This makes only the latest user message + AI response visible
      // Older messages are above (hidden unless you scroll up)
      // Wait for DOM to update before scrolling - use longer delay
      setTimeout(() => {
        scrollLatestMessageToTop()
      }, 300)
      
      // Step 2: Initialize streaming message
      setStreamingMessage({
        id: `streaming-${Date.now()}`,
        role: 'assistant',
        content: '',
        created_at: new Date().toISOString(),
        status: 'streaming'
      })
      
      // Start streaming
      try {
        console.log('🚀 [ChatMessages] Starting stream for session:', sessionId)
        let chunkCount = 0
        let accumulatedContent = '' // Track accumulated content
        
        for await (const chunk of chatApi.streamMessage(
          sessionId,
          userMessage,
          // onChunk callback - update streaming message in real-time
          (chunk) => {
            chunkCount++
            console.log(`📥 [ChatMessages] Chunk #${chunkCount} received, length:`, chunk.length)
            accumulatedContent += chunk
            
            // Update streaming message content
            setStreamingMessage(prev => {
              if (!prev) return prev
              return {
                ...prev,
                content: accumulatedContent,
                status: 'streaming' as const
              }
            })
            // NO auto-scroll during streaming - user controls scrolling
          },
          // onDone callback - streaming complete
          (data) => {
            console.log('✅ [ChatMessages] Streaming complete, message_id:', data.message_id)
            
            // Step 3: Convert streaming message to complete message and add to messages array
            const completedMessage: ChatMessage = {
              id: data.message_id || `assistant-${Date.now()}`,
              role: 'assistant',
              content: accumulatedContent,
              created_at: new Date().toISOString(),
              tokens_used: data.tokens_used || null,
              status: 'complete'
            }
            
            // Add to messages array (don't fetch from DB)
            setMessages(prev => {
              const updated = [...prev, completedMessage]
              console.log('✅ [ChatMessages] Added assistant message to state, total:', updated.length)
              return updated
            })
            
            // Clear streaming message
            setStreamingMessage(undefined)
          },
          // onError callback (for SSE stream errors during streaming)
          (error) => {
            console.error('❌ [ChatMessages] Streaming error:', error)
            setStreamingMessage(undefined)
            setError(error)
            
            // Show toast with clean backend error message
            toast.error(error || 'Failed to send message')
          }
        )) {
          // Chunks are handled by onChunk callback above
          console.log('📦 [ChatMessages] Processing chunk in loop')
        }
        console.log('🏁 [ChatMessages] Stream loop completed')
      } catch (err: any) {
        console.error('❌ [ChatMessages] Stream error:', err)
        setStreamingMessage(undefined)
        
        // Extract backend error message (remove "Stream failed: 429" prefix if present)
        let errorMessage = err.message || 'Failed to stream message'
        if (errorMessage.includes('Stream failed:')) {
          // Extract the actual error message after "Stream failed: 429 "
          const match = errorMessage.match(/Stream failed: \d+ (.+)/)
          if (match && match[1]) {
            errorMessage = match[1]
          }
        }
        
        setError(errorMessage)
        // Note: Toast is shown in onError callback with clean message, no need to show here
      }
    }

    // Listen for new messages (after streaming completes)
    // NOTE: We don't fetch from DB after streaming - we keep the message in state
    // Only fetch from DB on initial load or page refresh
    const handleMessageSent = async (event: CustomEvent) => {
      if (event.detail?.postAnalysisId !== postAnalysisId) return
      
      // This event is triggered by chat-input, but we don't need to fetch from DB
      // The streaming message is already added to state in onDone callback
      console.log('📨 [ChatMessages] handleMessageSent called (no DB fetch needed)')
    }

    // Listen for errors
    const handleMessageError = () => {
      console.log('⚠️ [ChatMessages] Message error event received')
      setStreamingMessage(undefined)
    }

    window.addEventListener('chat-message-sending', handleMessageSending as unknown as EventListener)
    window.addEventListener('chat-message-sent', handleMessageSent as unknown as EventListener)
    window.addEventListener('chat-message-error', handleMessageError)
    
    return () => {
      mounted = false
      window.removeEventListener('chat-message-sending', handleMessageSending as unknown as EventListener)
      window.removeEventListener('chat-message-sent', handleMessageSent as unknown as EventListener)
      window.removeEventListener('chat-message-error', handleMessageError)
    }
  }, [postAnalysisId])

  if (error && messages.length === 0) {
    return (
      <div className="px-4 py-2">
        <Alert variant="destructive" className="py-2">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription className="text-sm">{error}</AlertDescription>
        </Alert>
      </div>
    )
  }

  if (isLoading && messages.length === 0) {
    return (
      <div className="flex items-center justify-center py-8">
        <Spinner className="h-4 w-4 mr-2" />
        <span className="text-sm text-muted-foreground">Loading chats...</span>
      </div>
    )
  }

  // Derive isWaitingForResponse from streamingMessage status
  const isWaitingForResponse = streamingMessage?.status === 'streaming'

  if (messages.length === 0 && !streamingMessage && !isWaitingForResponse) {
    return null
  }

  // Find the latest user message index
  const latestUserMessageIndex = (() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === 'user') {
        return i
      }
    }
    return -1
  })()

  return (
    <div className={`space-y-4 md:space-y-6 mt-6 ${userHasSentMessage ? 'pb-[30vh]' : ''}`}>
      {/* Existing messages */}
      {messages.map((message, index) => {
        // Attach ref to the latest user message for scrolling
        const isLatestUserMessage = index === latestUserMessageIndex
        return (
          <div
            key={message.id}
            ref={isLatestUserMessage ? latestUserMessageRef : null}
          >
            <ChatMessageComponent message={message} />
          </div>
        )
      })}
      
      {/* AI thinking indicator - only show if no streaming content yet */}
      {isWaitingForResponse && (!streamingMessage || !streamingMessage.content) && (
        <div ref={thinkingLoaderRef} className="flex gap-3 md:gap-4 w-full">
          <div className="flex-shrink-0 mt-0.5">
            <div className="size-7 md:size-8 rounded-full bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center ring-2 ring-background">
              <Sparkles className="size-3.5 md:size-4 text-white" />
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
      
      {/* Streaming AI response - show while streaming */}
      {streamingMessage && streamingMessage.content && (
        <div ref={streamingMessageRef}>
          <ChatMessageComponent 
            key={streamingMessage.id}
            message={streamingMessage}
            streaming={streamingMessage.status === 'streaming'}
          />
        </div>
      )}
    </div>
  )
}
