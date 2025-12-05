"use client"

import { memo } from "react"
import { ChatMessage as ChatMessageType } from "@/lib/api"
import { cn } from "@/lib/utils"
import { MarkdownRenderer } from "./markdown-renderer"
import { StreamingMarkdown } from "./streaming-markdown"

interface ChatMessageProps {
  message: ChatMessageType
  streaming?: boolean // If true, animate character-by-character
}

export const ChatMessage = memo(function ChatMessage({ message, streaming = false }: ChatMessageProps) {
  const isUser = message.role === 'user'
  
  return (
    <div className="flex gap-3 md:gap-4 w-full group">
      {/* Avatar - only for AI messages, matching PostBro style */}
      {!isUser && (
        <div className="flex-shrink-0">
          <div className="size-7 md:size-8 rounded-full bg-gradient-to-br from-primary to-purple-600 flex items-center justify-center shadow-sm">
            <span className="text-white text-xs md:text-sm font-bold">PB</span>
          </div>
        </div>
      )}
      
      {/* Message content */}
      <div className={cn(
        "flex-1 min-w-0",
        isUser && "ml-7 md:ml-12" // Indent user messages to align with AI messages (responsive)
      )}>
        <div
          className={cn(
            "rounded-2xl px-4 py-3 md:px-5 md:py-3.5 text-base leading-relaxed shadow-sm transition-shadow",
            isUser
              ? "bg-primary/10 border border-primary/20 rounded-tr-sm hover:shadow-md"
              : "bg-card/80 dark:bg-transparent backdrop-blur-sm border border-border/40 dark:border-transparent rounded-tl-sm shadow-sm dark:shadow-none hover:shadow-md dark:hover:shadow-none"
          )}
        >
          {isUser ? (
            // User messages: plain text (no markdown)
            <p className="whitespace-pre-wrap break-words text-foreground">{message.content}</p>
          ) : streaming ? (
            // AI messages: streaming with character-by-character animation
            <StreamingMarkdown content={message.content} speed={25} />
          ) : (
            // AI messages: static markdown rendering
            <MarkdownRenderer content={message.content} />
          )}
        </div>
      </div>
    </div>
  )
})

