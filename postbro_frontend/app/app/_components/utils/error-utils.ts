/**
 * Utility functions for error handling and user-friendly messages
 */

/**
 * Sanitize error messages to never show raw Python exceptions to users
 */
export function sanitizeErrorMessage(message: string): string {
  if (!message) return 'Something went wrong. Please try again.'
  
  // Never show raw Python exceptions
  if (message.includes("'NoneType' object has no attribute")) {
    return 'We had trouble processing the media. Please try again.'
  }
  if (message.includes('AttributeError')) {
    return 'Something went wrong on our end. Please try again.'
  }
  if (message.includes('Unexpected error:')) {
    // Extract the part after "Unexpected error:" and sanitize it
    const parts = message.split('Unexpected error:')
    if (parts.length > 1) {
      const errorPart = parts[1].trim()
      // If it looks like a Python exception, replace it
      if (errorPart.includes("'") || errorPart.includes('object has no attribute')) {
        return 'Something unexpected happened. Please try again.'
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
    return { message: "We couldn't complete the analysis", stage: 'unknown' }
  }
  
  const stageLower = stage.toLowerCase()
  
  // Post fetching failures
  if (stageLower.includes('fetching_posts') || stageLower.includes('fetching_social') || stageLower === 'fetching_posts') {
    return { 
      message: "Couldn't fetch the post. Please check the URL is correct and the post is public.", 
      stage: 'post_fetch' 
    }
  }
  
  // Media processing failures
  if (stageLower.includes('collecting_media') || stageLower.includes('media') || stageLower === 'collecting_media') {
    return { 
      message: "Had trouble processing the media. This sometimes happens with certain formats.", 
      stage: 'media_processing' 
    }
  }
  
  // Transcription failures
  if (stageLower.includes('transcribing') || stageLower === 'transcribing') {
    return { 
      message: "Couldn't transcribe the audio, but the analysis can continue without it.", 
      stage: 'transcription' 
    }
  }
  
  // Gemini/AI analysis failures
  if (stageLower.includes('analysing') || stageLower.includes('analysis') || stageLower === 'analysing') {
    return { 
      message: "Our AI had trouble analyzing this post. This is usually temporary.", 
      stage: 'ai_analysis' 
    }
  }
  
  // Generic failure
  return { 
    message: "We couldn't complete the analysis", 
    stage: 'unknown' 
  }
}

