"use client"

import { useState, useEffect } from "react"
import { ExternalLink, Maximize2, Minimize2, X } from "lucide-react"
import type { Post } from "@/lib/api"
import { YouTubeEmbed, XEmbed, InstagramEmbed } from "./embeds"
import { cn } from "@/lib/utils"

interface PostPanelProps {
  post: Post | null
  isLoading?: boolean
  onClose?: () => void
}

/**
 * Right panel component that displays the embedded post
 * Designed for the 3-column layout on desktop
 */
export function PostPanel({ post, isLoading, onClose }: PostPanelProps) {
  const [useEmbedFallback, setUseEmbedFallback] = useState(false)
  const [isExpanded, setIsExpanded] = useState(false)

  // Reset fallback state when post changes
  useEffect(() => {
    setUseEmbedFallback(false)
  }, [post?.id])

  const handleEmbedError = () => {
    console.log(`[PostPanel] Embed failed, falling back to thumbnail`)
    setUseEmbedFallback(true)
  }

  if (!post && !isLoading) {
    return (
      <div className="h-full flex flex-col">
        {/* Empty state with subtle design */}
        <div className="flex-1 flex items-center justify-center p-6">
          <div className="text-center max-w-[240px]">
            <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-primary/10 to-violet-500/10 flex items-center justify-center">
              <svg 
                className="w-8 h-8 text-primary/40" 
                fill="none" 
                viewBox="0 0 24 24" 
                stroke="currentColor"
              >
                <path 
                  strokeLinecap="round" 
                  strokeLinejoin="round" 
                  strokeWidth={1.5} 
                  d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" 
                />
              </svg>
            </div>
            <p className="text-sm font-medium text-foreground/70 mb-1">No post selected</p>
            <p className="text-xs text-muted-foreground">
              Enter a URL to analyze a post
            </p>
          </div>
        </div>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="h-full flex flex-col">
        {/* Loading state */}
        <div className="flex-1 flex items-center justify-center p-6">
          <div className="text-center">
            <div className="w-12 h-12 mx-auto mb-3 rounded-xl bg-gradient-to-br from-primary/20 to-violet-500/20 flex items-center justify-center animate-pulse">
              <div className="w-6 h-6 border-2 border-primary/40 border-t-primary rounded-full animate-spin" />
            </div>
            <p className="text-sm text-muted-foreground">Loading post...</p>
          </div>
        </div>
      </div>
    )
  }

  const isYouTube = post?.platform === 'youtube'
  const isTwitter = post?.platform === 'twitter' || post?.platform === 'x'
  const isInstagram = post?.platform === 'instagram'

  return (
    <div className={cn(
      "h-full flex flex-col",
      isExpanded && "fixed inset-0 z-50 bg-background"
    )}>
      {/* Panel header */}
      <div className="flex-shrink-0 px-4 py-3 border-b border-border/40 bg-background/80 backdrop-blur-sm">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 min-w-0">
            {/* Platform icon */}
            {isYouTube && (
              <svg className="h-4 w-4 text-red-500 flex-shrink-0" viewBox="0 0 24 24" fill="currentColor">
                <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
              </svg>
            )}
            {isInstagram && (
              <svg className="h-4 w-4 text-pink-500 flex-shrink-0" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z"/>
              </svg>
            )}
            {isTwitter && (
              <svg className="h-4 w-4 text-foreground flex-shrink-0" viewBox="0 0 24 24" fill="currentColor">
                <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
              </svg>
            )}
            <span className="text-sm font-medium truncate">
              {post?.username ? `@${post.username}` : 'Post Preview'}
            </span>
          </div>
          <div className="flex items-center gap-1">
            {/* Open in new tab */}
            {post?.url && (
              <a
                href={post.url}
                target="_blank"
                rel="noopener noreferrer"
                className="p-1.5 rounded-md hover:bg-muted transition-colors"
                title="Open original post"
              >
                <ExternalLink className="h-4 w-4 text-muted-foreground" />
              </a>
            )}
            {/* Expand/Collapse */}
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="p-1.5 rounded-md hover:bg-muted transition-colors"
              title={isExpanded ? "Collapse" : "Expand"}
            >
              {isExpanded ? (
                <Minimize2 className="h-4 w-4 text-muted-foreground" />
              ) : (
                <Maximize2 className="h-4 w-4 text-muted-foreground" />
              )}
            </button>
            {/* Close button (expanded mode only) */}
            {isExpanded && (
              <button
                onClick={() => setIsExpanded(false)}
                className="p-1.5 rounded-md hover:bg-muted transition-colors"
              >
                <X className="h-4 w-4 text-muted-foreground" />
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Embed container */}
      <div className="flex-1 overflow-y-auto">
        <div className={cn(
          "p-4",
          isExpanded && "max-w-3xl mx-auto"
        )}>
          {!useEmbedFallback ? (
            <>
              {isYouTube && post.platform_post_id && (
                <div className="rounded-xl overflow-hidden shadow-sm border border-border/30">
                  <YouTubeEmbed 
                    videoId={post.platform_post_id} 
                    onError={handleEmbedError}
                  />
                </div>
              )}
              {isTwitter && post.platform_post_id && (
                <XEmbed 
                  tweetId={post.platform_post_id}
                  username={post.username}
                  onError={handleEmbedError}
                />
              )}
              {isInstagram && post.url && (
                <InstagramEmbed 
                  url={post.url}
                  onError={handleEmbedError}
                />
              )}
            </>
          ) : (
            // Fallback: Show thumbnail with link
            <div className="rounded-xl overflow-hidden border border-border/30 bg-muted">
              {post?.thumbnail ? (
                <a href={post.url} target="_blank" rel="noopener noreferrer" className="block">
                  <img 
                    src={post.thumbnail} 
                    alt={post.content || 'Post thumbnail'}
                    className="w-full h-auto object-cover"
                  />
                </a>
              ) : (
                <div className="aspect-video flex items-center justify-center">
                  <a 
                    href={post?.url} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="text-sm text-primary hover:underline flex items-center gap-2"
                  >
                    <ExternalLink className="h-4 w-4" />
                    View on {post?.platform}
                  </a>
                </div>
              )}
            </div>
          )}

          {/* Post metadata (only for YouTube or fallback) */}
          {(isYouTube || useEmbedFallback) && post && (
            <div className="mt-4 space-y-3">
              {/* Title (YouTube) */}
              {isYouTube && post.metrics?.title && (
                <h3 className="text-sm font-medium line-clamp-2">{post.metrics.title}</h3>
              )}
              
              {/* Metrics */}
              <div className="flex items-center gap-4 text-xs text-muted-foreground">
                {post.metrics?.views && (
                  <span>{post.metrics.views.toLocaleString()} views</span>
                )}
                {post.metrics?.likes && (
                  <span>{post.metrics.likes.toLocaleString()} likes</span>
                )}
                {post.metrics?.comments && (
                  <span>{post.metrics.comments.toLocaleString()} comments</span>
                )}
              </div>

              {/* Description */}
              {post.content && (
                <p className="text-xs text-muted-foreground line-clamp-4">
                  {post.content}
                </p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
