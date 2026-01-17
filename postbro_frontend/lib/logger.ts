/**
 * Logger utility for production-safe logging
 * 
 * - Errors and warnings: Always logged (important for production debugging)
 * - Debug/Info logs: Only in development mode
 */

const isDev = process.env.NODE_ENV === 'development'

export const logger = {
  /**
   * Debug logs - only in development
   */
  debug: (...args: any[]) => {
    if (isDev) {
      console.log(...args)
    }
  },

  /**
   * Info logs - only in development
   */
  info: (...args: any[]) => {
    if (isDev) {
      console.log(...args)
    }
  },

  /**
   * Warnings - always logged (important for production)
   */
  warn: (...args: any[]) => {
    console.warn(...args)
  },

  /**
   * Errors - always logged (critical for production debugging)
   */
  error: (...args: any[]) => {
    console.error(...args)
  },

  /**
   * Log - alias for debug (for backward compatibility)
   */
  log: (...args: any[]) => {
    if (isDev) {
      console.log(...args)
    }
  },
}



