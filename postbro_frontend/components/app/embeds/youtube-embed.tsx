"use client"

import { useState } from "react"
import { AlertCircle } from "lucide-react"

interface YouTubeEmbedProps {
  videoId: string
  onError?: () => void
}

export function YouTubeEmbed({ videoId, onError }: YouTubeEmbedProps) {
  const [embedError, setEmbedError] = useState(false)

  const handleError = () => {
    setEmbedError(true)
    onError?.()
  }

  // If embed fails, return null to trigger fallback
  if (embedError) {
    return null
  }

  return (
    <div className="relative w-full bg-black" style={{ aspectRatio: '16/9', maxHeight: '400px' }}>
      <iframe
        src={`https://www.youtube.com/embed/${videoId}`}
        title="YouTube video player"
        className="absolute top-0 left-0 w-full h-full"
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
        allowFullScreen
        onError={handleError}
        style={{ border: 0 }}
      />
    </div>
  )
}

// Fallback component when embed fails
export function YouTubeEmbedFallback() {
  return (
    <div className="relative w-full aspect-video bg-muted flex items-center justify-center">
      <div className="text-center p-6">
        <AlertCircle className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
        <p className="text-sm text-muted-foreground">
          YouTube embed unavailable
        </p>
      </div>
    </div>
  )
}
