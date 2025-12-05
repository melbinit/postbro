"use client"

import { useState, useEffect, useCallback } from "react"
import { TypingEffect } from "@/components/app/typing-effect"

interface ContentObservationProps {
  observation: {
    caption_observation?: string
    visual_observation?: string
    engagement_context?: string
    platform_signals?: string
  }
  enableTypingEffect?: boolean
  typingDelay?: number
  onComplete?: () => void
}

export function ContentObservation({ 
  observation, 
  enableTypingEffect = true,
  typingDelay = 0,
  onComplete
}: ContentObservationProps) {
  const [currentSubSectionIndex, setCurrentSubSectionIndex] = useState(0)
  
  // Build ordered list of sub-sections with data
  const subSections = []
  
  if (observation.caption_observation?.trim()) {
    subSections.push({
      id: 'caption',
      title: 'Caption',
      content: observation.caption_observation
    })
  }
  
  if (observation.visual_observation?.trim()) {
    subSections.push({
      id: 'visual',
      title: 'Visual Content',
      content: observation.visual_observation
    })
  }
  
  if (observation.engagement_context?.trim()) {
    subSections.push({
      id: 'engagement',
      title: 'Engagement',
      content: observation.engagement_context
    })
  }
  
  if (observation.platform_signals?.trim()) {
    subSections.push({
      id: 'platform',
      title: 'Platform Signals',
      content: observation.platform_signals
    })
  }
  
  // Only render if we have at least one sub-section
  if (subSections.length === 0) {
    return null
  }
  
  // Initialize on mount
  useEffect(() => {
    if (!enableTypingEffect) {
      // Show all immediately if no typing effect
      setCurrentSubSectionIndex(subSections.length)
    } else {
      // Start with first sub-section
      setCurrentSubSectionIndex(0)
    }
  }, [enableTypingEffect, subSections.length])
  
  // Handle sub-section completion
  const handleSubSectionComplete = useCallback((idx: number) => {
    if (idx < subSections.length - 1) {
      // Show next sub-section after brief delay
      setTimeout(() => {
        setCurrentSubSectionIndex(idx + 1)
      }, 50) // Faster transition between sub-sections
    } else {
      // All sub-sections complete - notify parent
      onComplete?.()
    }
  }, [subSections.length, onComplete])
  
  // Track if header has been typed
  const [headerTyped, setHeaderTyped] = useState(!enableTypingEffect)
  
  return (
    <div className="space-y-6">
      {/* Main header */}
      <h2 className="text-xl font-semibold">
        {enableTypingEffect && !headerTyped ? (
          <TypingEffect 
            text="What PostBro Analyzed"
            speed={1}
            delay={0}
            typeByLine={true}
            onComplete={() => {
              // Header done, show first sub-section
              setHeaderTyped(true)
              setTimeout(() => setCurrentSubSectionIndex(0), 100)
            }}
          />
        ) : (
          "What PostBro Analyzed"
        )}
      </h2>
      
      {/* Sub-sections - only show after header is typed */}
      {headerTyped && subSections.map((section, idx) => {
        // Only render if this sub-section or earlier are visible
        if (idx > currentSubSectionIndex) {
          return null
        }
        
        const isCurrentSection = idx === currentSubSectionIndex
        const shouldType = enableTypingEffect && isCurrentSection
        
        return (
          <div key={section.id}>
            <h3 className="font-medium mb-2">
              {shouldType ? (
                <TypingEffect 
                  text={section.title}
                  speed={1}
                  delay={0}
                  typeByLine={true}
                  onProgress={() => {
                    if (typeof window !== 'undefined') {
                      window.dispatchEvent(new CustomEvent('analysis-typing-progress'))
                    }
                  }}
                />
              ) : (
                section.title
              )}
            </h3>
            <p className="leading-relaxed text-muted-foreground">
              {shouldType ? (
                <TypingEffect 
                  text={section.content}
                  speed={1}
                  delay={0}
                  typeByLine={true}
                  onProgress={() => {
                    if (typeof window !== 'undefined') {
                      window.dispatchEvent(new CustomEvent('analysis-typing-progress'))
                    }
                  }}
                  onComplete={() => handleSubSectionComplete(idx)}
                />
              ) : (
                section.content
              )}
            </p>
          </div>
        )
      })}
    </div>
  )
}
