"use client"

import { useEffect, useRef, useState } from "react"
import { AlertCircle } from "lucide-react"

interface XEmbedProps {
  tweetId: string
  username?: string
  onError?: () => void
}

export function XEmbed({ tweetId, username, onError }: XEmbedProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [embedError, setEmbedError] = useState(false)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    // Load Twitter widget script if not already loaded
    const loadTwitterScript = () => {
      if (window.twttr) {
        // Script already loaded, process this embed
        renderEmbed()
        return
      }

      // Check if script is already being loaded
      const existingScript = document.querySelector('script[src="https://platform.twitter.com/widgets.js"]')
      if (existingScript) {
        // Wait for it to load
        existingScript.addEventListener('load', renderEmbed)
        return
      }

      // Load script
      const script = document.createElement('script')
      script.src = 'https://platform.twitter.com/widgets.js'
      script.async = true
      script.charset = 'utf-8'
      script.onload = renderEmbed
      script.onerror = handleError
      document.body.appendChild(script)
    }

    const renderEmbed = () => {
      if (!window.twttr || !containerRef.current) {
        handleError()
        return
      }

      // Clear container
      containerRef.current.innerHTML = ''

      // Create tweet blockquote
      const blockquote = document.createElement('blockquote')
      blockquote.className = 'twitter-tweet'
      blockquote.setAttribute('data-theme', 'light')
      blockquote.setAttribute('data-dnt', 'true') // Do not track
      
      const link = document.createElement('a')
      link.href = `https://twitter.com/${username || 'i'}/status/${tweetId}`
      link.textContent = 'Loading tweet...'
      blockquote.appendChild(link)
      
      containerRef.current.appendChild(blockquote)

      // Render the embed
      try {
        window.twttr.widgets.load(containerRef.current).then(() => {
          setIsLoading(false)
        }).catch(() => {
          handleError()
        })
      } catch (error) {
        handleError()
      }
    }

    const handleError = () => {
      setEmbedError(true)
      setIsLoading(false)
      onError?.()
    }

    loadTwitterScript()
  }, [tweetId, username, onError])

  // If embed fails, return null to trigger fallback
  if (embedError) {
    return null
  }

  return (
    <div className="relative w-full flex justify-center items-start">
      {isLoading && (
        <div className="absolute inset-0 flex items-center justify-center bg-muted rounded-xl min-h-[200px]">
          <div className="text-center">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary mx-auto mb-2" />
            <p className="text-xs text-muted-foreground">Loading tweet...</p>
          </div>
        </div>
      )}
      <div ref={containerRef} className="w-full max-w-[400px]" />
    </div>
  )
}

// Fallback component when embed fails
export function XEmbedFallback() {
  return (
    <div className="relative w-full aspect-square bg-muted flex items-center justify-center">
      <div className="text-center p-6">
        <AlertCircle className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
        <p className="text-sm text-muted-foreground">
          Tweet embed unavailable
        </p>
      </div>
    </div>
  )
}

// Add type definition for Twitter embed
declare global {
  interface Window {
    twttr?: {
      widgets: {
        load: (element?: HTMLElement) => Promise<void>
      }
    }
  }
}
