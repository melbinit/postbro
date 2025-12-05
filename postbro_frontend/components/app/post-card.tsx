"use client"

import { useState, useEffect, useRef } from "react"
import { Instagram, Hash, Heart, MessageCircle, Eye, ChevronLeft, ChevronRight, Repeat2 } from "lucide-react"
import { formatDistanceToNow } from "date-fns"
import type { Post } from "@/lib/api"

interface PostCardProps {
  post: Post
}

export function PostCard({ post }: PostCardProps) {
  const cardRef = useRef<HTMLDivElement>(null)
  const [isSticky, setIsSticky] = useState(false)
  
  // Scroll detection for sticky card
  useEffect(() => {
    if (!cardRef.current) {
      return
    }

    // Find the scrollable container (could be window or a parent element)
    const findScrollContainer = (element: HTMLElement | null): Element | null => {
      if (!element) {
        return null
      }
      
      // Check if element has overflow scroll/auto
      const style = window.getComputedStyle(element)
      const hasOverflow = style.overflowY === 'auto' || style.overflowY === 'scroll' || 
                          style.overflow === 'auto' || style.overflow === 'scroll'
      
      if (hasOverflow) {
        return element
      }
      
      // Check parent
      return findScrollContainer(element.parentElement)
    }

    const scrollContainer = findScrollContainer(cardRef.current.parentElement)
    const isWindow = !scrollContainer || scrollContainer === window
    const finalScrollContainer = scrollContainer || window
    const scrollElement = isWindow ? window : finalScrollContainer as HTMLElement

    let lastScrollTop = isWindow ? window.scrollY : (scrollElement as HTMLElement).scrollTop
    const scrollDirectionRef = { current: 'none' as 'up' | 'down' | 'none' } // Track scroll direction

    const handleScroll = () => {
      const currentScrollTop = isWindow ? window.scrollY : (scrollElement as HTMLElement).scrollTop
      const scrollDelta = currentScrollTop - lastScrollTop
      
      // Update scroll direction
      if (Math.abs(scrollDelta) > 1) {
        scrollDirectionRef.current = scrollDelta > 0 ? 'down' : 'up'
      }
      
      lastScrollTop = currentScrollTop
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          // Always hide sticky when card becomes visible (works for both user scroll and auto-scroll)
          if (entry.isIntersecting) {
            setIsSticky(false)
            scrollDirectionRef.current = 'none' // Reset direction when visible
            return
          }

          // Show sticky when card is scrolled past
          // Check if we were scrolling down OR if card is above viewport (scrolled past)
          const isScrollingDown = scrollDirectionRef.current === 'down'
          const cardIsAboveViewport = entry.boundingClientRect.bottom < (entry.rootBounds?.top || 0)
          
          // Show sticky if:
          // 1. Card is not visible (scrolled past)
          // 2. Either scrolling down OR card is above viewport (definitely scrolled past)
          if (!entry.isIntersecting && (isScrollingDown || cardIsAboveViewport)) {
            setIsSticky(true)
          }
        })
      },
      {
        threshold: 0, // Trigger when any part leaves viewport
        root: isWindow ? null : finalScrollContainer, // Use scroll container as root
        rootMargin: '0px 0px 0px 0px'
      }
    )

    scrollElement.addEventListener('scroll', handleScroll, { passive: true })
    observer.observe(cardRef.current)

    return () => {
      scrollElement.removeEventListener('scroll', handleScroll)
      observer.disconnect()
    }
  }, [post.id])
  
  // Platform-specific rendering
  const isYouTube = post.platform === 'youtube'
  const isTwitter = post.platform === 'twitter' || post.platform === 'x'
  const isInstagram = post.platform === 'instagram'

  return (
    <>
      {/* Sticky minimized card - compact version */}
      {isSticky && (
        <div className="fixed top-20 z-50 w-full max-w-lg animate-in slide-in-from-top-2 fade-in duration-200 left-1/2 md:left-[calc(50vw+8rem)] -translate-x-1/2">
          <div 
            className="bg-card/95 backdrop-blur-sm border border-border/50 rounded-lg shadow-lg cursor-pointer hover:bg-card transition-all overflow-hidden px-3 py-2"
            onClick={() => {
              // Scroll back to the post
              cardRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
              setTimeout(() => setIsSticky(false), 100)
            }}
          >
            <div className="flex items-center gap-2">
              {/* Platform icon */}
              {isYouTube ? (
                <svg className="h-4 w-4 text-red-500 flex-shrink-0" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
                </svg>
              ) : isInstagram ? (
                <Instagram className="h-4 w-4 text-pink-500 flex-shrink-0" />
              ) : (
                <Hash className="h-4 w-4 text-blue-500 flex-shrink-0" />
              )}
              
              {/* Username */}
              <p className="text-xs font-semibold flex-shrink-0">{isTwitter ? `@${post.username}` : post.username}</p>
              
              {/* Content preview */}
              <p className="text-xs text-muted-foreground line-clamp-1 truncate flex-1 min-w-0">
                {post.metrics?.title || post.content || `${post.username}'s post`}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Full post card - shrinks when sticky appears */}
      <div 
        ref={cardRef} 
        className={`bg-card border border-border/30 rounded-2xl overflow-hidden max-w-lg mx-auto transition-all duration-300 ${
          isSticky ? 'opacity-0 scale-95' : 'opacity-100 scale-100'
        }`}
      >
        <PostCardContent post={post} isMinimized={false} />
      </div>
    </>
  )
}

// Extract card content to reusable component
function PostCardContent({ post, isMinimized }: { post: Post, isMinimized: boolean }) {
  // Platform-specific rendering
  const isYouTube = post.platform === 'youtube'
  
  // Include all displayable media: images, thumbnails, and video frames
  // For YouTube: only show thumbnail (preview_image), exclude video frames
  // For other platforms: show images, thumbnails, and video frames
  const displayMedia = post.media.filter(m => {
    if (isYouTube) {
      // YouTube: only show video_thumbnail, exclude video_frame
      return m.media_type === 'video_thumbnail'
    } else {
      // Other platforms: show images, thumbnails, and video frames
      return m.media_type === 'image' || 
             m.media_type === 'video_thumbnail' || 
             m.media_type === 'video_frame'
    }
  })
  const [currentMediaIndex, setCurrentMediaIndex] = useState(0)
  const [imageError, setImageError] = useState(false)
  const currentMedia = displayMedia[currentMediaIndex]
  // Prioritize Supabase URL to avoid CORS issues with Instagram CDN
  const mediaUrl = currentMedia?.supabase_url || currentMedia?.source_url || post.thumbnail
  
  // Reset error state when media changes
  useEffect(() => {
    setImageError(false)
  }, [currentMediaIndex])
  const isTwitter = post.platform === 'twitter' || post.platform === 'x'
  const isInstagram = post.platform === 'instagram'

  return (
    <>
      {/* Header - Platform specific */}
      {isYouTube ? (
        // YouTube style header
        <div className={`${isMinimized ? 'px-3 py-2' : 'px-4 py-3'} border-b border-border/30`}>
          <div className="flex items-center gap-2 mb-2">
            <svg className={`${isMinimized ? 'h-4 w-4' : 'h-5 w-5'} text-red-500`} viewBox="0 0 24 24" fill="currentColor">
              <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
            </svg>
            <p className={`${isMinimized ? 'text-xs' : 'text-sm'} font-semibold`}>{post.username}</p>
          </div>
          {post.metrics?.title && !isMinimized && (
            <p className="text-sm font-medium line-clamp-2">{post.metrics.title}</p>
          )}
          {isMinimized && (
            <p className="text-xs text-muted-foreground line-clamp-1 truncate">
              {post.metrics?.title || post.content || `${post.username}'s post`}
            </p>
          )}
        </div>
      ) : (
        // Instagram/Twitter style header
        <div className={`flex items-center gap-3 ${isMinimized ? 'px-3 py-2' : 'px-4 py-3'} border-b border-border/30`}>
          <div className={`${isMinimized ? 'size-6' : 'size-8'} rounded-full bg-gradient-to-br from-primary to-purple-600 flex items-center justify-center flex-shrink-0`}>
            <span className={`text-white ${isMinimized ? 'text-xs' : 'text-xs'} font-bold`}>
              {post.username.charAt(0).toUpperCase()}
            </span>
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <p className={`${isMinimized ? 'text-xs' : 'text-sm'} font-semibold`}>{isTwitter ? `@${post.username}` : post.username}</p>
              {isInstagram && (
                <Instagram className={`${isMinimized ? 'h-3 w-3' : 'h-3.5 w-3.5'} text-pink-500`} />
              )}
              {isTwitter && (
                <Hash className={`${isMinimized ? 'h-3 w-3' : 'h-3.5 w-3.5'} text-blue-500`} />
              )}
            </div>
            {isMinimized && (
              <p className="text-xs text-muted-foreground line-clamp-1 truncate mt-0.5">
                {post.metrics?.title || post.content || `${post.username}'s post`}
              </p>
            )}
          </div>
          {!isMinimized && (
            <p className="text-xs text-muted-foreground">
              {formatDistanceToNow(new Date(post.posted_at), { addSuffix: true })}
            </p>
          )}
        </div>
      )}

      {/* Media Carousel - Hidden when minimized */}
      {!isMinimized && mediaUrl && !imageError ? (
        <div className={`relative bg-muted ${isYouTube ? 'aspect-video' : 'aspect-square'}`}>
          <img
            src={mediaUrl}
            alt={post.content || post.username}
            className="w-full h-full object-cover"
            onError={() => {
              // If image fails (CORS or other), show placeholder
              setImageError(true)
            }}
          />
          
          {/* Carousel indicators */}
          {displayMedia.length > 1 && (
            <>
              {/* Dots */}
              <div className="absolute bottom-3 left-1/2 -translate-x-1/2 flex gap-1.5">
                {displayMedia.map((_, index) => (
                  <button
                    key={index}
                    onClick={() => setCurrentMediaIndex(index)}
                    className={`h-1.5 rounded-full transition-all ${
                      index === currentMediaIndex
                        ? 'w-6 bg-white'
                        : 'w-1.5 bg-white/50'
                    }`}
                  />
                ))}
              </div>
              
              {/* Navigation arrows */}
              {currentMediaIndex > 0 && (
                <button
                  onClick={() => setCurrentMediaIndex(currentMediaIndex - 1)}
                  className="absolute left-2 top-1/2 -translate-y-1/2 size-8 rounded-full bg-black/50 hover:bg-black/70 backdrop-blur-sm flex items-center justify-center text-white transition-all"
                >
                  <ChevronLeft className="h-4 w-4" />
                </button>
              )}
              {currentMediaIndex < displayMedia.length - 1 && (
                <button
                  onClick={() => setCurrentMediaIndex(currentMediaIndex + 1)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 size-8 rounded-full bg-black/50 hover:bg-black/70 backdrop-blur-sm flex items-center justify-center text-white transition-all"
                >
                  <ChevronRight className="h-4 w-4" />
                </button>
              )}
            </>
          )}
        </div>
      ) : !isMinimized ? (
        // Placeholder when image fails to load or not available
        <div className={`relative bg-muted flex items-center justify-center ${isYouTube ? 'aspect-video' : 'aspect-square'}`}>
          <div className="text-center p-8">
            <p className="text-sm text-muted-foreground mb-2">Image unavailable</p>
            <p className="text-xs text-muted-foreground">Failed to load image</p>
          </div>
        </div>
      ) : null}

      {/* Actions & Metrics - Platform specific */}
      <div className={`${isMinimized ? 'px-3 py-2' : 'px-4 py-3'} space-y-2`}>
        {isYouTube ? (
          // YouTube style metrics
          <>
            {post.metrics && (
              <div className={`flex items-center gap-4 ${isMinimized ? 'text-xs' : 'text-xs'} text-muted-foreground`}>
                {post.metrics.views && (
                  <span>{post.metrics.views.toLocaleString()} views</span>
                )}
                {post.metrics.likes && (
                  <span>{post.metrics.likes.toLocaleString()} likes</span>
                )}
                {post.metrics.comments && (
                  <span>{post.metrics.comments.toLocaleString()} comments</span>
                )}
                {!isMinimized && (
                  <span>{formatDistanceToNow(new Date(post.posted_at), { addSuffix: true })}</span>
                )}
              </div>
            )}
            {post.content && !isMinimized && (
              <div className="text-sm text-foreground line-clamp-3">
                {post.content}
              </div>
            )}
          </>
        ) : isTwitter ? (
          // Twitter style metrics
          <>
            {post.metrics && (
              <div className={`flex items-center gap-4 ${isMinimized ? 'text-xs' : 'text-sm'} text-muted-foreground`}>
                {post.metrics.views && (
                  <div className="flex items-center gap-1">
                    <Eye className={isMinimized ? 'h-3 w-3' : 'h-4 w-4'} />
                    <span>{post.metrics.views.toLocaleString()}</span>
                  </div>
                )}
                {post.metrics.retweets && (
                  <div className="flex items-center gap-1">
                    <Repeat2 className={isMinimized ? 'h-3 w-3' : 'h-4 w-4'} />
                    <span>{post.metrics.retweets.toLocaleString()}</span>
                  </div>
                )}
                {post.metrics.likes && (
                  <div className="flex items-center gap-1">
                    <Heart className={isMinimized ? 'h-3 w-3' : 'h-4 w-4'} />
                    <span>{post.metrics.likes.toLocaleString()}</span>
                  </div>
                )}
                {post.metrics.comments && (
                  <div className="flex items-center gap-1">
                    <MessageCircle className={isMinimized ? 'h-3 w-3' : 'h-4 w-4'} />
                    <span>{post.metrics.comments.toLocaleString()}</span>
                  </div>
                )}
              </div>
            )}
            {post.content && !isMinimized && (
              <div className="text-sm text-foreground">
                {post.content}
              </div>
            )}
          </>
        ) : (
          // Instagram style (default)
          <>
            {post.metrics && (
              <div className={`flex items-center gap-4 ${isMinimized ? 'text-xs' : 'text-sm'}`}>
                {post.metrics.likes && (
                  <div className={`flex items-center ${isMinimized ? 'gap-1' : 'gap-1.5'}`}>
                    <Heart className={isMinimized ? 'h-3.5 w-3.5' : 'h-5 w-5'} />
                    <span className={isMinimized ? 'text-xs font-medium' : 'font-semibold'}>{post.metrics.likes.toLocaleString()}</span>
                  </div>
                )}
                {post.metrics.comments && (
                  <div className={`flex items-center ${isMinimized ? 'gap-1' : 'gap-1.5'}`}>
                    <MessageCircle className={isMinimized ? 'h-3.5 w-3.5' : 'h-5 w-5'} />
                    <span className={isMinimized ? 'text-xs font-medium' : 'font-semibold'}>{post.metrics.comments.toLocaleString()}</span>
                  </div>
                )}
                {post.metrics.views && (
                  <div className={`flex items-center ${isMinimized ? 'gap-1' : 'gap-1.5'}`}>
                    <Eye className={isMinimized ? 'h-3.5 w-3.5' : 'h-5 w-5'} />
                    <span className={isMinimized ? 'text-xs font-medium' : 'font-semibold'}>{post.metrics.views.toLocaleString()}</span>
                  </div>
                )}
              </div>
            )}
            {post.content && !isMinimized && (
              <div className="text-sm">
                <span className="font-semibold mr-2">{post.username}</span>
                <span className="text-foreground">{post.content}</span>
              </div>
            )}
          </>
        )}
      </div>
    </>
  )
}
