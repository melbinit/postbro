import { type AnalysisRequest, type Post } from "@/lib/api"
import { Loader2, AlertCircle, Sparkles } from "lucide-react"
import { PostCard } from "@/components/app/post-card"
import { ChatMessages } from "@/components/app/chat-messages"
import { sanitizeErrorMessage } from "../utils/error-utils"

interface AnalysisStatusProps {
  currentRequest: AnalysisRequest
  posts: Post[]
  isLoadingPosts: boolean
  latestStatus: any
  postAnalysisId: string | null
  messagesContainerRef: React.RefObject<HTMLDivElement>
  messagesLoaded: boolean
  setMessagesLoaded: (loaded: boolean) => void
  hasScrolledToBottomRef: React.MutableRefObject<Set<string>>
  userHasInteractedRef: React.MutableRefObject<boolean>
  wasCompletedOnLoadRef: React.MutableRefObject<Set<string>>
}

/**
 * Displays analysis status, posts, and chat messages
 */
export function AnalysisStatus({
  currentRequest,
  posts,
  isLoadingPosts,
  latestStatus,
  postAnalysisId,
  messagesContainerRef,
  messagesLoaded,
  setMessagesLoaded,
  hasScrolledToBottomRef,
  userHasInteractedRef,
  wasCompletedOnLoadRef,
}: AnalysisStatusProps) {
  return (
    <div className="space-y-4">
      {/* User message */}
      <div className="flex gap-4 justify-end">
        <div className="flex-1 max-w-[80%]">
          <div className="bg-primary/10 border border-primary/20 rounded-2xl rounded-tr-sm p-4">
            <p className="text-sm font-medium mb-1">
              Analyzing {currentRequest?.platform?.toUpperCase() || 'POST'} post
            </p>
            {currentRequest?.post_urls?.[0] && (
              <p className="text-xs text-muted-foreground truncate">
                {currentRequest.post_urls[0]}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Display posts when available */}
      {isLoadingPosts ? (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          <span className="ml-2 text-sm text-muted-foreground">Loading posts...</span>
        </div>
      ) : posts.length > 0 ? (
        <div className="space-y-6">
          {posts.map((post) => (
            <PostCard 
              key={`${currentRequest.id}-${post.id}`} 
              post={post} 
            />
          ))}
        </div>
      ) : currentRequest && (latestStatus?.stage === 'analysis_complete' || latestStatus?.stage === 'social_data_fetched') ? (
        <div className="text-center py-8 text-muted-foreground text-sm">
          <p>No posts found for this analysis</p>
        </div>
      ) : null}

      {/* Chat Messages */}
      {postAnalysisId && (latestStatus?.stage === 'analysis_complete' || currentRequest.status === 'completed') && (
        <ChatMessages 
          postAnalysisId={postAnalysisId}
          scrollContainerRef={messagesContainerRef as React.RefObject<HTMLDivElement>}
          onMessagesLoaded={(msgs) => {
            console.log('📬 [AnalysisStatus] Messages loaded:', msgs.length)
            setMessagesLoaded(true)
            // Scroll is now handled by use-scroll-behavior hook
            // Just dispatch the event for other listeners
            if (typeof window !== 'undefined') {
              window.dispatchEvent(new CustomEvent('chat-messages-loaded', {
                detail: { postAnalysisId, hasMessages: msgs.length > 0, messageCount: msgs.length }
              }))
            }
          }}
        />
      )}

      {/* PostBro status card - Show during processing */}
      {latestStatus && latestStatus.stage !== 'analysis_complete' && !latestStatus.is_error && (
        <div className="flex gap-3 md:gap-4 mt-6">
          <div className="flex-shrink-0 mt-0.5">
            <div className="size-7 md:size-8 rounded-full bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center ring-2 ring-background">
              <Sparkles className="size-3.5 md:size-4 text-white" />
            </div>
          </div>
          <div className="flex-1 min-w-0 pt-0.5">
            <div className="flex items-center gap-2">
              <Loader2 className="h-3.5 w-3.5 animate-spin text-primary flex-shrink-0" />
              <p className="text-sm text-foreground/90 flex-1">
                {latestStatus.message}
              </p>
              {latestStatus.progress_percentage > 0 && (
                <span className="text-xs text-muted-foreground ml-2 flex-shrink-0 tabular-nums">
                  {latestStatus.progress_percentage}%
                </span>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Error status card - Modern, subtle styling */}
      {latestStatus?.is_error && (
        <div className="flex gap-3 md:gap-4 mt-6">
          <div className="flex-shrink-0 mt-0.5">
            <div className="size-7 md:size-8 rounded-full bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center ring-2 ring-background">
              <Sparkles className="size-3.5 md:size-4 text-white" />
            </div>
          </div>
          <div className="flex-1 min-w-0">
            <div className="bg-amber-50 dark:bg-amber-950/30 border border-amber-200/60 dark:border-amber-800/40 rounded-xl p-3.5">
              <div className="flex items-start gap-2.5">
                <AlertCircle className="h-4 w-4 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-amber-900 dark:text-amber-200 mb-0.5">
                    Something went wrong
                  </p>
                  <p className="text-sm text-amber-800/80 dark:text-amber-300/80">
                    {latestStatus.actionable_message || sanitizeErrorMessage(latestStatus.message)}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
