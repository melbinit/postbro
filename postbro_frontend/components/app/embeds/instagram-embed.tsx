"use client"

import { useEffect, useRef, useState } from "react"
import { AlertCircle } from "lucide-react"

interface InstagramEmbedProps {
  url: string  // Full Instagram URL (e.g., https://www.instagram.com/reel/ABC123/)
  onError?: () => void
}

export function InstagramEmbed({ url, onError }: InstagramEmbedProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [embedError, setEmbedError] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const timeoutRef = useRef<NodeJS.Timeout>()

  useEffect(() => {
    // Set a timeout to detect if embed fails to load
    timeoutRef.current = setTimeout(() => {
      // If still loading after 10 seconds, consider it failed
      if (isLoading) {
        handleError()
      }
    }, 10000)

    // Load Instagram embed script if not already loaded
    const loadInstagramScript = () => {
      if (window.instgrm) {
        // Script already loaded, process this embed
        processEmbed()
        return
      }

      // Check if script is already being loaded
      const existingScript = document.querySelector('script[src="https://www.instagram.com/embed.js"]')
      if (existingScript) {
        // Wait for it to load
        existingScript.addEventListener('load', processEmbed)
        return
      }

      // Load script
      const script = document.createElement('script')
      script.src = 'https://www.instagram.com/embed.js'
      script.async = true
      script.onload = processEmbed
      script.onerror = handleError
      document.body.appendChild(script)
    }

    const processEmbed = () => {
      if (!window.instgrm) {
        handleError()
        return
      }

      try {
        // Process all Instagram embeds on the page
        window.instgrm.Embeds.process()
        
        // Mark as loaded after processing
        setTimeout(() => {
          setIsLoading(false)
          if (timeoutRef.current) {
            clearTimeout(timeoutRef.current)
          }
        }, 1000)
      } catch (error) {
        console.error('Instagram embed error:', error)
        handleError()
      }
    }

    const handleError = () => {
      setEmbedError(true)
      setIsLoading(false)
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
      }
      onError?.()
    }

    loadInstagramScript()

    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
      }
    }
  }, [url, onError, isLoading])

  // If embed fails, return null to trigger fallback
  if (embedError) {
    return null
  }

  return (
    <div className="relative w-full flex justify-center items-start">
      {isLoading && (
        <div className="absolute inset-0 flex items-center justify-center bg-muted rounded-xl min-h-[300px]">
          <div className="text-center">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary mx-auto mb-2" />
            <p className="text-xs text-muted-foreground">Loading post...</p>
          </div>
        </div>
      )}
      <div ref={containerRef} className="w-full max-w-[400px]">
        <blockquote
          className="instagram-media"
          data-instgrm-permalink={url}
          data-instgrm-version="14"
          style={{
            background: '#FFF',
            border: 0,
            borderRadius: '12px',
            boxShadow: '0 0 1px 0 rgba(0,0,0,0.5),0 1px 10px 0 rgba(0,0,0,0.15)',
            margin: 0,
            maxWidth: '400px',
            minWidth: '280px',
            padding: 0,
            width: '100%',
          }}
        >
          <a 
            href={url} 
            target="_blank" 
            rel="noopener noreferrer"
            style={{
              background: '#FFFFFF',
              lineHeight: 0,
              padding: '16px 0',
              textAlign: 'center',
              textDecoration: 'none',
              width: '100%',
              display: 'block',
              fontSize: '12px',
            }}
          >
            View on Instagram
          </a>
        </blockquote>
      </div>
    </div>
  )
}

// Fallback component when embed fails
export function InstagramEmbedFallback() {
  return (
    <div className="relative w-full aspect-square bg-muted flex items-center justify-center">
      <div className="text-center p-6">
        <AlertCircle className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
        <p className="text-sm text-muted-foreground">
          Instagram embed unavailable
        </p>
      </div>
    </div>
  )
}

// Add type definition for Instagram embed
declare global {
  interface Window {
    instgrm?: {
      Embeds: {
        process: () => void
      }
    }
  }
}
