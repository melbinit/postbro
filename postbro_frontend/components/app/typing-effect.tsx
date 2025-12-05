"use client"

import { useEffect, useState, useRef } from "react"

interface TypingEffectProps {
  text: string
  speed?: number // Lines per interval (for line-by-line typing)
  delay?: number // Initial delay in ms
  onComplete?: () => void
  onProgress?: () => void // Callback for each line typed (for auto-scroll)
  className?: string
  typeByLine?: boolean // Whether to type line by line or character by character
}

export function TypingEffect({ 
  text, 
  speed = 1, // 1 line per interval for line-by-line typing
  delay = 0,
  onComplete,
  onProgress,
  className = "",
  typeByLine = true
}: TypingEffectProps) {
  const [displayedText, setDisplayedText] = useState("")
  const [isComplete, setIsComplete] = useState(false)
  const progressCallbackRef = useRef(onProgress)

  // Update ref when callback changes
  useEffect(() => {
    progressCallbackRef.current = onProgress
  }, [onProgress])

  useEffect(() => {
    // Don't show typing effect for empty or whitespace-only text
    if (!text || !text.trim()) {
      setIsComplete(true)
      onComplete?.()
      return
    }

    setDisplayedText("")
    setIsComplete(false)

    // Initial delay
    const timeoutId = setTimeout(() => {
      if (typeByLine) {
        // Type line by line (or word by word if no newlines)
        const lines = text.split('\n')
        let currentLineIndex = 0
        
        // If no newlines, split by sentences or words for better effect
        const hasNewlines = lines.length > 1
        
        const typeLine = () => {
          if (currentLineIndex < lines.length) {
            const currentLine = lines[currentLineIndex]
            
            if (hasNewlines) {
              // Has newlines - type line by line
              const linesToShow = lines.slice(0, currentLineIndex + 1)
              setDisplayedText(linesToShow.join('\n'))
              currentLineIndex++
              
              // Trigger progress callback for auto-scroll
              if (progressCallbackRef.current) {
                progressCallbackRef.current()
              }
              
                  // Continue to next line after delay
                  if (currentLineIndex < lines.length) {
                    setTimeout(typeLine, 100) // 100ms delay between lines (faster)
              } else {
                setIsComplete(true)
                onComplete?.()
              }
            } else {
              // No newlines - type word by word for smooth effect
              const words = currentLine.split(' ')
              let wordIndex = 0
              
              const typeWord = () => {
                if (wordIndex < words.length) {
                  const wordsToShow = words.slice(0, wordIndex + 1)
                  setDisplayedText(wordsToShow.join(' '))
                  wordIndex++
                  
                  // Trigger progress callback frequently for smooth scroll
                  if (progressCallbackRef.current && wordIndex % 3 === 0) {
                    progressCallbackRef.current()
                  }
                  
                  // Continue to next word
                  if (wordIndex < words.length) {
                    setTimeout(typeWord, 30) // 30ms delay between words (faster)
                  } else {
                    setIsComplete(true)
                    onComplete?.()
                  }
                }
              }
              
              typeWord()
              currentLineIndex = lines.length // Mark as complete
            }
          }
        }
        
        // Start typing first line
        typeLine()
      } else {
        // Original character-by-character typing
        let currentIndex = 0
        
        const intervalId = setInterval(() => {
          if (currentIndex < text.length) {
            // Add multiple characters at once for faster typing
            const nextIndex = Math.min(currentIndex + speed, text.length)
            setDisplayedText(text.slice(0, nextIndex))
            currentIndex = nextIndex
            
            // Trigger progress callback periodically
            if (progressCallbackRef.current && currentIndex % 10 === 0) {
              progressCallbackRef.current()
            }
          } else {
            clearInterval(intervalId)
            setIsComplete(true)
            onComplete?.()
          }
        }, 20) // Update every 20ms for faster effect

        return () => clearInterval(intervalId)
      }
    }, delay)

    return () => clearTimeout(timeoutId)
  }, [text, speed, delay, onComplete, typeByLine])

  return (
    <span className={className}>
      {displayedText}
      {!isComplete && (
        <span className="animate-pulse">▊</span>
      )}
    </span>
  )
}

