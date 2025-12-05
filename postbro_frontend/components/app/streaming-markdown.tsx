"use client"

import { useEffect, useState } from "react"
import { MarkdownRenderer } from "./markdown-renderer"

interface StreamingMarkdownProps {
  content: string
  speed?: number // milliseconds per character
}

export function StreamingMarkdown({ content, speed = 25 }: StreamingMarkdownProps) {
  const [visibleContent, setVisibleContent] = useState("")

  useEffect(() => {
    setVisibleContent("")
    if (!content) return

    let index = 0
    const interval = setInterval(() => {
      index += 1
      setVisibleContent(content.slice(0, index))
      if (index >= content.length) {
        clearInterval(interval)
      }
    }, speed)

    return () => clearInterval(interval)
  }, [content, speed])

  return <MarkdownRenderer content={visibleContent} />
}



