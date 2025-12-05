"use client"

import { useState, useEffect, useRef, useCallback } from "react"
import { type PostAnalysis } from "@/lib/api"
import { TypingEffect } from "@/components/app/typing-effect"
import { ContentObservation } from "@/components/app/content-observation"
import { SuggestionItem } from "@/components/app/suggestion-item"

interface AnalysisDisplayProps {
  analysis: PostAnalysis
  enableTypingEffect?: boolean
}

export function AnalysisDisplay({ analysis, enableTypingEffect = true }: AnalysisDisplayProps) {
  const { 
    is_viral, 
    virality_reasoning, 
    quick_takeaways,
    content_observation, 
    replicable_elements,
    analysis_data, 
    improvements, 
    suggestions_for_future_posts,
    viral_formula
  } = analysis
  
  // Track which sections should be visible
  const [currentSectionIndex, setCurrentSectionIndex] = useState(-1) // Start at -1 (nothing visible)
  const [completedSections, setCompletedSections] = useState<Set<number>>(new Set())
  
  // Build ordered list of sections with data
  const sections = useRef<Array<{
    id: string
    type: 'header' | 'list' | 'text' | 'suggestions'
    title?: string
    content?: string | string[]
    data?: any
  }>>([])
  
  // Initialize sections on mount
  useEffect(() => {
    const sectionList: typeof sections.current = []
    
    // Quick Takeaways
    if (quick_takeaways?.length) {
      sectionList.push({
        id: 'quick_takeaways_header',
        type: 'header',
        title: 'Quick Takeaways'
      })
      quick_takeaways.forEach((takeaway, idx) => {
        sectionList.push({
          id: `quick_takeaway_${idx}`,
          type: 'list',
          content: takeaway
        })
      })
    }
    
    // Content Observation
    const hasContentObservation = content_observation && (
      content_observation.caption_observation || 
      content_observation.visual_observation || 
      content_observation.engagement_context || 
      content_observation.platform_signals
    )
    if (hasContentObservation) {
      sectionList.push({
        id: 'content_observation',
        type: 'text',
        title: 'What PostBro Analyzed',
        data: content_observation
      })
    }
    
    // Virality Assessment
    if (virality_reasoning) {
      sectionList.push({
        id: 'virality_header',
        type: 'header',
        title: is_viral ? 'Viral Post Analysis' : 'Performance Analysis'
      })
      sectionList.push({
        id: 'virality_reasoning',
        type: 'text',
        content: virality_reasoning
      })
    }
    
    // Replicable Elements
    if (replicable_elements?.length) {
      sectionList.push({
        id: 'replicable_header',
        type: 'header',
        title: 'Replicable Elements'
      })
      replicable_elements.forEach((element, idx) => {
        sectionList.push({
          id: `replicable_${idx}`,
          type: 'list',
          content: element
        })
      })
    }
    
    // Strengths
    if (analysis_data?.strengths?.length) {
      sectionList.push({
        id: 'strengths_header',
        type: 'header',
        title: 'Strengths'
      })
      analysis_data.strengths.forEach((strength, idx) => {
        sectionList.push({
          id: `strength_${idx}`,
          type: 'list',
          content: strength
        })
      })
    }
    
    // Weaknesses
    if (analysis_data?.weaknesses?.length) {
      sectionList.push({
        id: 'weaknesses_header',
        type: 'header',
        title: 'Areas for Improvement'
      })
      analysis_data.weaknesses.forEach((weakness, idx) => {
        sectionList.push({
          id: `weakness_${idx}`,
          type: 'list',
          content: weakness
        })
      })
    }
    
    // Improvements
    if (improvements?.length) {
      sectionList.push({
        id: 'improvements_header',
        type: 'header',
        title: 'Quick Improvements'
      })
      improvements.forEach((improvement, idx) => {
        sectionList.push({
          id: `improvement_${idx}`,
          type: 'list',
          content: improvement
        })
      })
    }
    
    // Future Content Ideas
    if (suggestions_for_future_posts?.length) {
      sectionList.push({
        id: 'suggestions_header',
        type: 'header',
        title: 'Future Content Ideas'
      })
      suggestions_for_future_posts.forEach((suggestion, idx) => {
        if (suggestion.hook || suggestion.outline || suggestion.why_it_works) {
          sectionList.push({
            id: `suggestion_${idx}`,
            type: 'suggestions',
            data: suggestion
          })
        }
      })
    }
    
    // Viral Formula
    if (viral_formula?.trim()) {
      sectionList.push({
        id: 'viral_formula_header',
        type: 'header',
        title: 'Viral Formula'
      })
      sectionList.push({
        id: 'viral_formula',
        type: 'text',
        content: viral_formula
      })
    }
    
    sections.current = sectionList
    
    // If typing effect disabled, show all sections immediately
    if (!enableTypingEffect) {
      setCurrentSectionIndex(sectionList.length - 1)
      setCompletedSections(new Set(sectionList.map((_, idx) => idx)))
    } else {
      // Start with first section after a brief moment
      setTimeout(() => {
        setCurrentSectionIndex(0)
        setCompletedSections(new Set())
      }, 50)
    }
  }, [
    quick_takeaways, content_observation, virality_reasoning, 
    replicable_elements, analysis_data, improvements, 
    suggestions_for_future_posts, viral_formula, is_viral, enableTypingEffect
  ])
  
  // Handle section completion - show next section
  const handleSectionComplete = useCallback((sectionIdx: number) => {
    console.log(`✅ [AnalysisDisplay] Section ${sectionIdx} complete:`, sections.current[sectionIdx]?.id)
    setCompletedSections(prev => new Set(prev).add(sectionIdx))
    
        // Show next section after a brief delay
        if (sectionIdx < sections.current.length - 1) {
          setTimeout(() => {
            console.log(`➡️ [AnalysisDisplay] Moving to section ${sectionIdx + 1}:`, sections.current[sectionIdx + 1]?.id)
            setCurrentSectionIndex(sectionIdx + 1)
            // No auto-scroll - let user control scrolling
          }, 50) // Brief pause between sections (faster)
        } else {
          console.log('🎉 [AnalysisDisplay] All sections complete!')
          // Notify that typing is complete (for status card display)
          if (typeof window !== 'undefined') {
            window.dispatchEvent(new CustomEvent('analysis-typing-complete'))
          }
        }
  }, [])
  
  // Render nothing if no data
  if (sections.current.length === 0) {
    return null
  }
  
  return (
    <div className="space-y-6">
      {sections.current.map((section, idx) => {
        // Only render if this section or earlier sections are visible
        if (idx > currentSectionIndex) {
          return null
        }
        
        const isCurrentSection = idx === currentSectionIndex
        const isCompleted = completedSections.has(idx)
        const shouldType = enableTypingEffect && isCurrentSection && !isCompleted
        
        // Header sections
        if (section.type === 'header') {
          return (
            <h2 key={section.id} className="text-xl font-semibold mb-3">
              {shouldType ? (
                <TypingEffect 
                  text={section.title || ''}
                  speed={1}
                  delay={0}
                  typeByLine={true}
                  onComplete={() => handleSectionComplete(idx)}
                />
              ) : (
                section.title
              )}
            </h2>
          )
        }
        
        // List items
        if (section.type === 'list') {
          return (
            <div key={section.id} className="leading-relaxed text-muted-foreground">
              • {shouldType ? (
                <TypingEffect 
                  text={section.content as string}
                  speed={1}
                  delay={0}
                  typeByLine={true}
                  onComplete={() => handleSectionComplete(idx)}
                />
              ) : (
                section.content
              )}
            </div>
          )
        }
        
        // Text content
        if (section.type === 'text') {
          // Special handling for content observation
          if (section.id === 'content_observation') {
            return (
              <ContentObservation 
                key={section.id}
                observation={section.data}
                enableTypingEffect={shouldType}
                typingDelay={0}
                onComplete={() => handleSectionComplete(idx)}
              />
            )
          }
          
          return (
            <p key={section.id} className="leading-relaxed text-muted-foreground">
              {shouldType ? (
                <TypingEffect 
                  text={section.content as string}
                  speed={1}
                  delay={0}
                  typeByLine={true}
                  onComplete={() => handleSectionComplete(idx)}
                />
              ) : (
                section.content
              )}
            </p>
          )
        }
        
        // Suggestion items - use dedicated component for sequential typing
        if (section.type === 'suggestions') {
          return (
            <SuggestionItem
              key={section.id}
              suggestion={section.data}
              enableTypingEffect={shouldType}
              onComplete={() => handleSectionComplete(idx)}
            />
          )
        }
        
        return null
      })}
    </div>
  )
}
