import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Strip markdown formatting from text
 * Removes **bold**, *italic*, `code`, # headers, etc.
 */
export function stripMarkdown(text: string): string {
  if (!text) return text
  
  return text
    // Remove bold markers (handle multiple instances)
    .replace(/\*\*([^*]+)\*\*/g, '$1')  // **bold**
    .replace(/\*\*([^*]*)\*\*/g, '$1')  // **bold** (fallback for empty)
    // Remove italic markers
    .replace(/\*([^*]+)\*/g, '$1')      // *italic* (but not **bold**)
    .replace(/__([^_]+)__/g, '$1')      // __bold__
    .replace(/_([^_]+)_/g, '$1')        // _italic_
    // Remove code blocks
    .replace(/```[\s\S]*?```/g, '')     // ```code blocks```
    .replace(/`([^`]+)`/g, '$1')        // `inline code`
    // Remove headers
    .replace(/^#{1,6}\s+(.+)$/gm, '$1') // # Header
    // Remove links but keep text
    .replace(/\[([^\]]+)\]\([^\)]+\)/g, '$1') // [text](url)
    // Remove images
    .replace(/!\[([^\]]*)\]\([^\)]+\)/g, '') // ![alt](url)
    // Clean up any remaining markdown artifacts
    .replace(/\*\*/g, '')  // Remove any leftover **
    .replace(/\*/g, '')    // Remove any leftover *
    // Clean up extra whitespace
    .replace(/\n{3,}/g, '\n\n')
    .trim()
}
