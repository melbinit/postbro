/**
 * Utility functions for error handling and user-friendly messages
 */

/**
 * Sanitize error messages to never show raw Python exceptions, stack traces, or backend internals to users
 */
export function sanitizeErrorMessage(message: string | null | undefined): string {
  if (!message) return 'Something went wrong. Please try again.'
  
  const msg = String(message)
  
  // Never show stack traces
  if (msg.includes('at ') && (msg.includes('.py:') || msg.includes('File "'))) {
    return 'Something went wrong on our end. Please try again.'
  }
  
  // Never show raw Python exceptions
  const pythonExceptions = [
    "'NoneType' object has no attribute",
    "AttributeError",
    "TypeError",
    "KeyError",
    "ValueError",
    "IndexError",
    "ImportError",
    "ModuleNotFoundError",
    "object has no attribute",
    "Traceback (most recent call last)",
    "File \"/",
    "File \"C:\\",
    "Exception:",
    "Error:",
    "raise ",
  ]
  
  for (const pattern of pythonExceptions) {
    if (msg.includes(pattern)) {
      return 'Something went wrong on our end. Please try again.'
    }
  }
  
  // Never show internal file paths
  if (msg.includes('/app/') || msg.includes('/usr/') || msg.includes('\\app\\') || msg.includes('postbro_backend/')) {
    return 'Something went wrong on our end. Please try again.'
  }
  
  // Never show database errors
  if (msg.includes('psycopg2') || msg.includes('PostgreSQL') || msg.includes('database') || msg.includes('SQL')) {
    return 'Something went wrong on our end. Please try again.'
  }
  
  // Never show API keys or tokens (even partial)
  if (msg.match(/[a-zA-Z0-9_-]{20,}/) && (msg.includes('key') || msg.includes('token') || msg.includes('secret'))) {
    return 'Something went wrong on our end. Please try again.'
  }
  
  // Never show Django/backend framework errors
  if (msg.includes('Django') || msg.includes('settings.') || msg.includes('models.') || msg.includes('views.')) {
    return 'Something went wrong on our end. Please try again.'
  }
  
  // Never show internal error codes or IDs
  if (msg.match(/error_code:\s*\d+/i) || msg.match(/error_id:\s*[a-f0-9-]{20,}/i)) {
    return 'Something went wrong on our end. Please try again.'
  }
  
  // Never show Gemini/AI technical errors or content policy details
  if (msg.includes('Gemini') || msg.includes('safety filters') || msg.includes('content policy') || 
      msg.includes('finish_reason') || msg.includes('SAFETY') || msg.includes('blocked by') ||
      msg.includes('candidates_tokens') || msg.includes('prompt_tokens') || msg.includes('response.text')) {
    return 'Unable to analyze this post. Please try again.'
  }
  
  // Check for "Unexpected error:" prefix and sanitize the rest
  if (msg.includes('Unexpected error:')) {
    const parts = msg.split('Unexpected error:')
    if (parts.length > 1) {
      const errorPart = parts[1].trim()
      // If it looks like a technical error, replace it
      if (errorPart.includes("'") || errorPart.includes('object has no attribute') || errorPart.includes('at ')) {
        return 'Something unexpected happened. Please try again.'
      }
    }
  }
  
  // If message already looks user-friendly, return as-is
  return msg
}

/**
 * Extract safe error message from error object
 * Never exposes backend internals, stack traces, or technical details
 */
export function getSafeErrorMessage(error: any): string {
  // Handle different error formats
  let message: string | null = null
  
  // Try to get user-friendly message from API response
  if (error?.response?.data?.message) {
    message = error.response.data.message
  } else if (error?.response?.data?.error) {
    message = error.response.data.error
  } else if (error?.data?.message) {
    message = error.data.message
  } else if (error?.data?.error) {
    message = error.data.error
  } else if (error?.message) {
    message = error.message
  }
  
  // Always sanitize before returning
  return sanitizeErrorMessage(message)
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
      message: "Our AI had trouble analyzing this post. Please try again.", 
      stage: 'ai_analysis' 
    }
  }
  
  // Generic failure
  return { 
    message: "We couldn't complete the analysis", 
    stage: 'unknown' 
  }
}

