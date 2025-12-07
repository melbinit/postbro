"use client"

import { memo } from "react"
import { ChatMessage as ChatMessageType } from "@/lib/api"
import { cn } from "@/lib/utils"
import { MarkdownRenderer } from "./markdown-renderer"
import { StreamingMarkdown } from "./streaming-markdown"
import { Sparkles } from "lucide-react"

interface ChatMessageProps {
  message: ChatMessageType
  streaming?: boolean // If true, animate character-by-character
}

export const ChatMessage = memo(function ChatMessage({ message, streaming = false }: ChatMessageProps) {
  const isUser = message.role === 'user'
  
  return (
    <div className={cn(
      "w-full group",
      isUser ? "flex justify-end" : ""
    )}>
      {isUser ? (
        // User message - bubble style aligned right
        <div className="max-w-[85%] md:max-w-[75%]">
          <div className="bg-primary text-primary-foreground rounded-2xl rounded-br-md px-4 py-2.5 md:px-5 md:py-3">
            <p className="whitespace-pre-wrap break-words text-[15px] leading-relaxed">{message.content}</p>
          </div>
        </div>
      ) : (
        // AI message - clean, no background, properly spaced
        <div className="flex gap-3 md:gap-4">
          {/* Avatar */}
          <div className="flex-shrink-0 mt-0.5">
            <div className="size-7 md:size-8 rounded-full bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center ring-2 ring-background">
              <Sparkles className="size-3.5 md:size-4 text-white" />
            </div>
          </div>
          
          {/* Content - no background, clean typography */}
          <div className="flex-1 min-w-0 pt-0.5">
            <div className="text-[15px] leading-relaxed text-foreground prose-headings:text-foreground prose-p:text-foreground/90 prose-strong:text-foreground prose-code:text-foreground">
              {streaming ? (
                <StreamingMarkdown content={message.content} speed={25} />
              ) : (
                <MarkdownRenderer content={message.content} />
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
})

