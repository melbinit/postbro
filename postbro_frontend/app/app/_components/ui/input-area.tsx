import { type AnalysisRequest, type Post } from "@/lib/api"
import { AnalysisForm } from "@/components/app/analysis-form"
import { ChatInput } from "@/components/app/chat-input"
import { XCircle } from "lucide-react"
import { getFailureMessage } from "../utils/error-utils"

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
    <div className="flex-shrink-0 p-4 md:p-6 relative z-10">
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
            <div className="w-full max-w-3xl mx-auto">
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
        if (
          currentRequest &&
          (currentRequest.status === 'failed' || latestStatus?.is_error)
        ) {
          const failureInfo = getFailureMessage(latestStatus?.stage)
          
          return (
            <div className="w-full max-w-3xl mx-auto">
              <div className="mb-4 p-4 bg-destructive/5 border border-destructive/50 rounded-lg">
                <div className="flex items-start gap-2">
                  <XCircle className="h-5 w-5 text-destructive flex-shrink-0 mt-0.5" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-destructive font-medium mb-1">
                      {failureInfo.message}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      You can retry the analysis below. The form is pre-filled with your previous input.
                    </p>
                  </div>
                </div>
              </div>
              <AnalysisForm 
                key={`analysis-form-retry-${currentRequest.id}`}
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


