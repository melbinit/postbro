"use client"

import { useState, useEffect, useCallback } from "react"
import { TypingEffect } from "@/components/app/typing-effect"

interface SuggestionItemProps {
  suggestion: {
    hook?: string
    outline?: string
    why_it_works?: string
    engagement_potential?: 'high' | 'medium' | 'low'
  }
  enableTypingEffect?: boolean
  onComplete?: () => void
}

export function SuggestionItem({ suggestion, enableTypingEffect = true, onComplete }: SuggestionItemProps) {
  const hasHook = suggestion.hook?.trim()
  const hasOutline = suggestion.outline?.trim()
  const hasWhyItWorks = suggestion.why_it_works?.trim()
  
  // Track which part is currently typing
  const [currentPart, setCurrentPart] = useState<'hook' | 'outline' | 'why_it_works' | 'done'>('hook')
  
  // Initialize typing state
  useEffect(() => {
    if (!enableTypingEffect) {
      setCurrentPart('done')
      return
    }
    
    // Determine starting part
    if (hasHook) {
      setCurrentPart('hook')
    } else if (hasOutline) {
      setCurrentPart('outline')
    } else if (hasWhyItWorks) {
      setCurrentPart('why_it_works')
    } else {
      setCurrentPart('done')
      onComplete?.()
    }
  }, [enableTypingEffect, hasHook, hasOutline, hasWhyItWorks, onComplete])
  
  // Handle completion of each part
  const handleHookComplete = useCallback(() => {
    if (hasOutline) {
      setTimeout(() => setCurrentPart('outline'), 25) // Faster transition
    } else if (hasWhyItWorks) {
      setTimeout(() => setCurrentPart('why_it_works'), 25) // Faster transition
    } else {
      setCurrentPart('done')
      onComplete?.()
    }
  }, [hasOutline, hasWhyItWorks, onComplete])
  
  const handleOutlineComplete = useCallback(() => {
    if (hasWhyItWorks) {
      setTimeout(() => setCurrentPart('why_it_works'), 25) // Faster transition
    } else {
      setCurrentPart('done')
      onComplete?.()
    }
  }, [hasWhyItWorks, onComplete])
  
  const handleWhyItWorksComplete = useCallback(() => {
    setCurrentPart('done')
    onComplete?.()
  }, [onComplete])
  
  const shouldTypeHook = enableTypingEffect && currentPart === 'hook'
  const shouldTypeOutline = enableTypingEffect && currentPart === 'outline'
  const shouldTypeWhyItWorks = enableTypingEffect && currentPart === 'why_it_works'
  
  const hookCompleted = currentPart !== 'hook' || !enableTypingEffect
  const outlineCompleted = (currentPart !== 'outline' && currentPart !== 'hook') || !enableTypingEffect
  const whyItWorksCompleted = currentPart === 'done' || !enableTypingEffect
  
  return (
    <div className="space-y-2">
      {hasHook && (
        <div className="flex items-start gap-2">
          <h3 className="font-medium flex-1">
            {shouldTypeHook ? (
              <TypingEffect 
                text={suggestion.hook}
                speed={1}
                delay={0}
                typeByLine={true}
                onComplete={handleHookComplete}
              />
            ) : hookCompleted ? (
              suggestion.hook
            ) : null}
          </h3>
          {suggestion.engagement_potential && hookCompleted && (
            <span className={`text-xs px-2 py-1 rounded ${
              suggestion.engagement_potential === 'high' 
                ? 'bg-green-500/20 text-green-500' 
                : suggestion.engagement_potential === 'medium'
                ? 'bg-yellow-500/20 text-yellow-500'
                : 'bg-gray-500/20 text-gray-500'
            }`}>
              {suggestion.engagement_potential}
            </span>
          )}
        </div>
      )}
      {hasOutline && hookCompleted && (
        <p className="leading-relaxed text-muted-foreground">
          {shouldTypeOutline ? (
            <TypingEffect 
              text={suggestion.outline}
              speed={1}
              delay={0}
              typeByLine={true}
              onProgress={() => {
                if (typeof window !== 'undefined') {
                  window.dispatchEvent(new CustomEvent('analysis-typing-progress'))
                }
              }}
              onComplete={handleOutlineComplete}
            />
          ) : outlineCompleted ? (
            suggestion.outline
          ) : null}
        </p>
      )}
      {hasWhyItWorks && outlineCompleted && (
        <p className="text-sm text-muted-foreground italic">
          Why it works: {shouldTypeWhyItWorks ? (
            <TypingEffect 
              text={suggestion.why_it_works}
              speed={1}
              delay={0}
              typeByLine={true}
              onProgress={() => {
                if (typeof window !== 'undefined') {
                  window.dispatchEvent(new CustomEvent('analysis-typing-progress'))
                }
              }}
              onComplete={handleWhyItWorksComplete}
            />
          ) : whyItWorksCompleted ? (
            suggestion.why_it_works
          ) : null}
        </p>
      )}
    </div>
  )
}


