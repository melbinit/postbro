/**
 * Utility functions for error handling and user-friendly messages
 */

/**
 * Sanitize error messages to never show raw Python exceptions to users
 */
export function sanitizeErrorMessage(message: string): string {
  if (!message) return 'An error occurred. Please try again.'
  
  // Never show raw Python exceptions
  if (message.includes("'NoneType' object has no attribute")) {
    return 'Failed to process media. Please try again.'
  }
  if (message.includes('AttributeError')) {
    return 'An error occurred while processing your request. Please try again.'
  }
  if (message.includes('Unexpected error:')) {
    // Extract the part after "Unexpected error:" and sanitize it
    const parts = message.split('Unexpected error:')
    if (parts.length > 1) {
      const errorPart = parts[1].trim()
      // If it looks like a Python exception, replace it
      if (errorPart.includes("'") || errorPart.includes('object has no attribute')) {
        return 'An unexpected error occurred. Please try again or contact support if this persists.'
      }
    }
  }
  
  // If message already looks user-friendly, return as-is
  return message
}

/**
 * Get user-friendly failure message based on analysis stage
 */
export function getFailureMessage(stage: string | undefined): { message: string; stage: string } {
  if (!stage) {
    return { message: 'Analysis failed. Please try again.', stage: 'unknown' }
  }
  
  const stageLower = stage.toLowerCase()
  
  // Post fetching failures
  if (stageLower.includes('fetching_posts') || stageLower.includes('fetching_social') || stageLower === 'fetching_posts') {
    return { 
      message: 'Failed to fetch post data from the platform. Please check the URL and try again.', 
      stage: 'post_fetch' 
    }
  }
  
  // Media processing failures
  if (stageLower.includes('collecting_media') || stageLower.includes('media') || stageLower === 'collecting_media') {
    return { 
      message: 'Failed to process media (images/videos). Please try again.', 
      stage: 'media_processing' 
    }
  }
  
  // Transcription failures
  if (stageLower.includes('transcribing') || stageLower === 'transcribing') {
    return { 
      message: 'Failed to transcribe audio. The analysis will continue without transcript.', 
      stage: 'transcription' 
    }
  }
  
  // Gemini/AI analysis failures
  if (stageLower.includes('analysing') || stageLower.includes('analysis') || stageLower === 'analysing') {
    return { 
      message: 'Failed to analyze with AI. Please try again.', 
      stage: 'ai_analysis' 
    }
  }
  
  // Generic failure
  return { 
    message: 'Analysis failed. Please try again.', 
    stage: 'unknown' 
  }
}


