"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Instagram, Send, Hash, ChevronDown, ChevronUp } from "lucide-react"
import { analysisApi, type AnalysisRequest } from "@/lib/api"
import { toast } from "sonner"

interface AnalysisFormProps {
  initialValues?: {
    platform?: 'instagram' | 'x' | 'youtube'
    post_urls?: string[]
  }
  onMinimizeChange?: (minimized: boolean) => void
  defaultMinimized?: boolean
}

export function AnalysisForm({ initialValues, onMinimizeChange, defaultMinimized = false }: AnalysisFormProps = {}) {
  const [platform, setPlatform] = useState<'instagram' | 'x' | 'youtube'>(
    initialValues?.platform || 'x'
  )
  const [url, setUrl] = useState(
    initialValues?.post_urls?.[0] || ''
  )
  const [isLoading, setIsLoading] = useState(false)
  const [isMinimized, setIsMinimized] = useState(defaultMinimized)

  // Update minimized state when prop changes
  useEffect(() => {
    setIsMinimized(defaultMinimized)
  }, [defaultMinimized])

  // Notify parent when minimized state changes
  const handleMinimizeToggle = (minimized: boolean) => {
    setIsMinimized(minimized)
    onMinimizeChange?.(minimized)
  }

  // Update form when initialValues change (for prefilling failed analyses)
  useEffect(() => {
    if (initialValues) {
      if (initialValues.platform) setPlatform(initialValues.platform)
      if (initialValues.post_urls && initialValues.post_urls.length > 0) {
        setUrl(initialValues.post_urls[0])
      }
      
      // Don't minimize if prefilled (failed analysis - user should see what they tried)
      if (initialValues.post_urls && initialValues.post_urls.length > 0) {
        setIsMinimized(false)
      }
    }
  }, [initialValues])

  const validateSocialMediaUrl = (url: string, platform: 'instagram' | 'x' | 'youtube'): { valid: boolean; error?: string } => {
    const trimmedUrl = url.trim()
    if (!trimmedUrl) {
      return { valid: false, error: 'Please enter a URL' }
    }

    // Add https:// if missing
    let fullUrl = trimmedUrl
    if (!trimmedUrl.startsWith('http://') && !trimmedUrl.startsWith('https://')) {
      fullUrl = 'https://' + trimmedUrl
    }

    try {
      const urlObj = new URL(fullUrl.toLowerCase())
      let hostname = urlObj.hostname

      // Remove www. and m. prefixes
      if (hostname.startsWith('www.')) {
        hostname = hostname.substring(4)
      }
      if (hostname.startsWith('m.')) {
        hostname = hostname.substring(2)
      }

      // Define allowed domains for each platform
      const allowedDomains: Record<string, string[]> = {
        instagram: ['instagram.com', 'instagr.am'],
        x: ['x.com', 'twitter.com', 't.co'],
        youtube: ['youtube.com', 'youtu.be'],
      }

      const platformDomains = allowedDomains[platform] || []
      const isValid = platformDomains.some(domain => hostname.includes(domain))

      if (!isValid) {
        const platformNames: Record<string, string> = {
          instagram: 'Instagram',
          x: 'X (Twitter)',
          youtube: 'YouTube'
        }
        return {
          valid: false,
          error: `URL must be from ${platformNames[platform]}. Please provide a valid ${platformNames[platform]} post URL.`
        }
      }

      return { valid: true }
    } catch (error) {
      return { valid: false, error: 'Invalid URL format. Please enter a valid URL.' }
    }
  }

  const handleSubmit = async (e?: React.MouseEvent | React.KeyboardEvent) => {
    if (e) {
      e.preventDefault()
      e.stopPropagation()
    }
    
    const trimmedUrl = url.trim()
    
    // Validate URL format and platform match
    const validation = validateSocialMediaUrl(trimmedUrl, platform)
    if (!validation.valid) {
      toast.error(validation.error || 'Invalid URL')
      return
    }

    try {
      setIsLoading(true)

      const data = {
        platform,
        post_urls: [trimmedUrl]  // Single URL in array
      }

      const analysisRequest = await analysisApi.createAnalysis(data)
      
      setUrl('')
      
      // Auto-minimize after successful submission
      handleMinimizeToggle(true)
      
      // Notify parent component about the new analysis
      if (typeof window !== 'undefined') {
        window.dispatchEvent(new CustomEvent('analysis-created', { detail: analysisRequest }))
      }
    } catch (error: any) {
      // Handle API errors with proper messages
      if (error?.status === 403 || error?.response?.status === 403) {
        // Usage limit reached
        const errorData = error?.response?.data || error?.data || {}
        const message = errorData.message || errorData.error || 'Usage limit reached'
        toast.error(message, {
          duration: 5000, // Show for 5 seconds
        })
      } else if (error?.status === 400 || error?.response?.status === 400) {
        // Validation error
        const errorData = error?.response?.data || error?.data || {}
        const message = errorData.error || errorData.details || 'Invalid input data'
        toast.error(message, {
          duration: 5000,
        })
      } else {
        // Generic error
        const message = error?.message || error?.response?.data?.error || 'Failed to create analysis'
        toast.error(message, {
          duration: 5000,
        })
      }
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="w-full max-w-3xl mx-auto">
      {/* Floating card */}
      <div className="relative border border-border/50 dark:border-border/40 rounded-2xl bg-card/90 backdrop-blur-md shadow-lg hover:shadow-xl transition-shadow duration-300">
        {/* Minimize button */}
        <button
          type="button"
          onClick={() => handleMinimizeToggle(!isMinimized)}
          className="absolute top-4 right-4 p-1.5 rounded-md hover:bg-muted/50 transition-colors z-10"
        >
          {isMinimized ? (
            <ChevronUp className="size-4 text-muted-foreground" />
          ) : (
            <ChevronDown className="size-4 text-muted-foreground" />
          )}
        </button>

        <div className="relative">
          {/* Minimized state - show message */}
          <div className={`transition-all duration-700 ease-in-out overflow-hidden ${
            isMinimized 
              ? 'max-h-[80px] opacity-100' 
              : 'max-h-0 opacity-0'
          }`}>
            <button
              type="button"
              onClick={() => handleMinimizeToggle(false)}
              className="w-full p-6 flex items-center justify-center hover:bg-muted/30 transition-colors rounded-lg"
            >
              <p className="text-sm text-muted-foreground hover:text-foreground transition-colors">
                Click to start analyzing posts
              </p>
            </button>
          </div>

          {/* Expanded state - show form */}
          <div className={`transition-all duration-700 ease-in-out overflow-hidden ${
            isMinimized 
              ? 'max-h-0 opacity-0' 
              : 'max-h-[600px] opacity-100'
          }`}>
            <div className="space-y-4 p-6">
              {/* Minimal platform and type selection - segmented control style */}
              <div className="flex flex-col md:flex-row items-start md:items-center gap-3">
                {/* Platform selection */}
                <div className="inline-flex items-center gap-0.5 p-0.5 rounded-lg bg-muted/30 border border-border/40">
                  <button
                    type="button"
                    onClick={() => setPlatform('x')}
                    className={`flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                      platform === 'x'
                        ? 'bg-gradient-to-br from-primary/10 via-primary/8 to-purple-500/8 text-foreground shadow-sm border border-primary/30 dark:border-transparent dark:from-primary/20 dark:via-primary/15 dark:to-purple-500/15'
                        : 'text-muted-foreground hover:text-foreground hover:bg-muted/50 active:bg-muted/70'
                    }`}
                  >
                    <Hash className="size-3" />
                    <span>X</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setPlatform('instagram')}
                    className={`flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                      platform === 'instagram'
                        ? 'bg-gradient-to-br from-primary/10 via-primary/8 to-purple-500/8 text-foreground shadow-sm border border-primary/30 dark:border-transparent dark:from-primary/20 dark:via-primary/15 dark:to-purple-500/15'
                        : 'text-muted-foreground hover:text-foreground hover:bg-muted/50 active:bg-muted/70'
                    }`}
                  >
                    <Instagram className="size-3" />
                    <span>Instagram</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setPlatform('youtube')}
                    className={`flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                      platform === 'youtube'
                        ? 'bg-gradient-to-br from-primary/10 via-primary/8 to-purple-500/8 text-foreground shadow-sm border border-primary/30 dark:border-transparent dark:from-primary/20 dark:via-primary/15 dark:to-purple-500/15'
                        : 'text-muted-foreground hover:text-foreground hover:bg-muted/50 active:bg-muted/70'
                    }`}
                  >
                    <svg className="size-3" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
                    </svg>
                    <span>YouTube</span>
                  </button>
                </div>

              </div>

              {/* Input field */}
              <div className="relative">
                <Input
                  placeholder={
                    platform === 'x' 
                      ? 'https://x.com/username/status/123456789'
                      : platform === 'instagram'
                      ? 'https://www.instagram.com/p/ABC123/'
                      : 'https://www.youtube.com/watch?v=VIDEO_ID'
                  }
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      handleSubmit(e)
                    }
                  }}
                  disabled={isLoading}
                  className="h-12 text-base bg-card/70 backdrop-blur-sm border-border/40 focus:border-primary/50 pr-12"
                />
                
                <button
                  type="button"
                  onClick={handleSubmit}
                  disabled={isLoading || !url.trim()}
                  className="absolute right-2 top-1/2 -translate-y-1/2 h-8 w-8 rounded-lg bg-primary hover:bg-primary/90 shadow-lg flex items-center justify-center disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 hover:scale-105 active:scale-95 hover:shadow-xl"
                >
                  <Send className="size-4 text-primary-foreground" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
