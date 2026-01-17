import { type AnalysisRequest, type Post } from "@/lib/api"
import { AnalysisForm } from "@/components/app/analysis-form"
import { ChatInput } from "@/components/app/chat-input"

interface InputAreaProps {
  currentRequest: AnalysisRequest | null
  latestStatus: any
  postAnalysisId: string | null
  posts: Post[]
  messagesLoaded: boolean
  isFormMinimized: boolean
  setIsFormMinimized: (minimized: boolean) => void
}

/**
 * Manages the input area at the bottom of the screen
 * Shows either ChatInput (for completed analyses) or AnalysisForm (for new/failed analyses)
 */
export function InputArea({
  currentRequest,
  latestStatus,
  postAnalysisId,
  posts,
  messagesLoaded,
  isFormMinimized,
  setIsFormMinimized,
}: InputAreaProps) {
  return (
    <div className="flex-shrink-0 px-4 lg:px-6 xl:px-8 py-4 relative z-10">
      {(() => {
        // 1. Show ChatInput if analysis completed and messages loaded
        if (
          currentRequest &&
          (latestStatus?.stage === 'analysis_complete' || currentRequest.status === 'completed') &&
          !latestStatus?.is_error &&
          postAnalysisId &&
          posts.length > 0 &&
          messagesLoaded
        ) {
          return (
            <div className="w-full max-w-2xl xl:max-w-3xl mx-auto">
              <ChatInput 
                postAnalysisId={postAnalysisId}
                onMessageSent={() => {
                  if (typeof window !== 'undefined') {
                    window.dispatchEvent(new CustomEvent('chat-message-sent'))
                  }
                }}
              />
            </div>
          )
        }
        
        // 2. Show form with pre-filled URL if analysis failed
        // Error message is already shown in the chat area, no need for redundant message
        if (
          currentRequest &&
          (currentRequest.status === 'failed' || latestStatus?.is_error)
        ) {
          return (
            <div className="w-full max-w-2xl xl:max-w-3xl mx-auto">
              <AnalysisForm 
                key={`analysis-form-retry-${currentRequest.id}`}
                currentRequest={currentRequest}
                initialValues={{
                  platform: currentRequest.platform,
                  post_urls: currentRequest.post_urls,
                }}
                onMinimizeChange={setIsFormMinimized}
                defaultMinimized={false}
              />
            </div>
          )
        }
        
        // 3. Hide form when processing
        if (
          currentRequest &&
          (currentRequest.status === 'processing' || currentRequest.status === 'pending')
        ) {
          return null
        }
        
        // 4. Hide form when completed but messages not loaded yet
        if (
          currentRequest &&
          (latestStatus?.stage === 'analysis_complete' || currentRequest.status === 'completed') &&
          !latestStatus?.is_error &&
          postAnalysisId &&
          posts.length > 0 &&
          !messagesLoaded
        ) {
          return null
        }
        
        // 5. Show form for new analyses
        if (!currentRequest) {
          return (
            <AnalysisForm 
              key="new-analysis-form"
              initialValues={undefined}
              onMinimizeChange={setIsFormMinimized}
              defaultMinimized={isFormMinimized}
            />
          )
        }
        
        // 6. Fallback
        return (
          <AnalysisForm 
            key={`analysis-form-${currentRequest.id}`}
            initialValues={undefined}
            onMinimizeChange={setIsFormMinimized}
            defaultMinimized={isFormMinimized}
          />
        )
      })()}
    </div>
  )
}


