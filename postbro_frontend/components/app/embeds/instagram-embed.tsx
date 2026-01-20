"use client"

import { useEffect, useRef, useState } from "react"

interface InstagramEmbedProps {
  url: string  // Full Instagram URL (e.g., https://www.instagram.com/reel/ABC123/)
  onError?: () => void
}

export function InstagramEmbed({ url, onError }: InstagramEmbedProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [embedFailed, setEmbedFailed] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const hasCalledErrorRef = useRef(false)
  const timeoutRef = useRef<NodeJS.Timeout>()
  const iframeCheckIntervalRef = useRef<NodeJS.Timeout>()

  useEffect(() => {
    let mounted = true
    
    // Clean URL - ensure proper format
    const cleanUrl = url.replace(/\?.*$/, '').replace(/\/$/, '') + '/'
    
    const handleError = () => {
      if (!mounted || hasCalledErrorRef.current) return
      
      console.log('[InstagramEmbed] Embed failed, triggering fallback')
      hasCalledErrorRef.current = true
      setEmbedFailed(true)
      setIsLoading(false)
      
      // Clear all timers
      if (timeoutRef.current) clearTimeout(timeoutRef.current)
      if (iframeCheckIntervalRef.current) clearInterval(iframeCheckIntervalRef.current)
      
      // Notify parent to use fallback
      onError?.()
    }

    // Set aggressive timeout - 5 seconds max
    timeoutRef.current = setTimeout(() => {
      if (mounted && !hasCalledErrorRef.current) {
        console.log('[InstagramEmbed] Timeout reached, falling back')
        handleError()
      }
    }, 5000)

    // Check for iframe creation every 500ms
    let iframeCheckCount = 0
    iframeCheckIntervalRef.current = setInterval(() => {
      iframeCheckCount++
      
      // If no iframe after 3 seconds (6 checks), fail
      if (iframeCheckCount > 6) {
        if (containerRef.current && !containerRef.current.querySelector('iframe')) {
          console.log('[InstagramEmbed] No iframe created, falling back')
          handleError()
        }
        if (iframeCheckIntervalRef.current) {
          clearInterval(iframeCheckIntervalRef.current)
        }
      }
      
      // Success - iframe was created
      if (containerRef.current?.querySelector('iframe')) {
        console.log('[InstagramEmbed] Iframe detected, embed successful')
        setIsLoading(false)
        if (timeoutRef.current) clearTimeout(timeoutRef.current)
        if (iframeCheckIntervalRef.current) clearInterval(iframeCheckIntervalRef.current)
      }
    }, 500)

    const loadInstagramScript = () => {
      if (!mounted) return

      // Check if script already exists and is loaded
      if (window.instgrm) {
        processEmbed()
        return
      }

      // Check if script tag exists
      const existingScript = document.querySelector('script[src="https://www.instagram.com/embed.js"]')
      if (existingScript) {
        // Already loading, wait for it
        const checkInstgrm = setInterval(() => {
          if (window.instgrm && mounted) {
            clearInterval(checkInstgrm)
            processEmbed()
          }
        }, 100)
        
        // If not loaded after 3 seconds, fail
        setTimeout(() => {
          clearInterval(checkInstgrm)
          if (!window.instgrm && mounted) {
            console.log('[InstagramEmbed] Script loaded but instgrm not available')
            handleError()
          }
        }, 3000)
        return
      }

      // Load the script
      const script = document.createElement('script')
      script.src = 'https://www.instagram.com/embed.js'
      script.async = true
      
      script.onload = () => {
        if (mounted) processEmbed()
      }
      
      script.onerror = () => {
        console.log('[InstagramEmbed] Script failed to load')
        if (mounted) handleError()
      }
      
      document.body.appendChild(script)
    }

    const processEmbed = () => {
      if (!mounted || !window.instgrm) {
        handleError()
        return
      }

      try {
        // Clear any existing iframe to prevent conflicts
        if (containerRef.current) {
          const existingIframe = containerRef.current.querySelector('iframe')
          if (existingIframe) {
            existingIframe.remove()
          }
        }
        
        // Process the embed
        window.instgrm.Embeds.process()
      } catch (error) {
        console.error('[InstagramEmbed] Process error:', error)
        handleError()
      }
    }

    loadInstagramScript()

    return () => {
      mounted = false
      if (timeoutRef.current) clearTimeout(timeoutRef.current)
      if (iframeCheckIntervalRef.current) clearInterval(iframeCheckIntervalRef.current)
    }
  }, [url, onError])

  // If embed failed, return null immediately to trigger fallback
  if (embedFailed) {
    return null
  }

  return (
    <div className="relative w-full flex justify-center items-start">
      {isLoading && (
        <div className="flex items-center justify-center min-h-[300px]">
          <div className="text-center">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary mx-auto mb-2" />
            <p className="text-xs text-muted-foreground">Loading Instagram post...</p>
          </div>
        </div>
      )}
      <div ref={containerRef} className="w-full max-w-[400px]">
        <blockquote
          className="instagram-media"
          data-instgrm-permalink={url.replace(/\?.*$/, '').replace(/\/$/, '') + '/'}
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

// Type definition for Instagram embed
declare global {
  interface Window {
    instgrm?: {
      Embeds: {
        process: () => void
      }
    }
  }
}
