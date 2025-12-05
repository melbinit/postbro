import { useEffect } from "react"
import { useRouter } from "next/navigation"
import { type AnalysisRequest } from "@/lib/api"

interface UseAnalysisEventsProps {
  currentRequest: AnalysisRequest | null
  latestStatus: any
  isLoaded: boolean
  isSignedIn: boolean
}

/**
 * Manages event dispatching and listening for analysis component
 * Handles sidebar updates, username updates, and navigation events
 */
export function useAnalysisEvents({
  currentRequest,
  latestStatus,
  isLoaded,
  isSignedIn,
}: UseAnalysisEventsProps) {
  const router = useRouter()
  
  // Dispatch status updates to sidebar
  useEffect(() => {
    if (!currentRequest?.id) return
    
    if (typeof window !== 'undefined' && currentRequest.status) {
      const timeoutId = setTimeout(() => {
        window.dispatchEvent(new CustomEvent('analysis-status-updated', {
          detail: {
            analysis_request_id: currentRequest.id,
            status: currentRequest.status
          }
        }))
      }, 0)
      
      return () => clearTimeout(timeoutId)
    }
  }, [currentRequest?.id, currentRequest?.status])
  
  // Dispatch username updates when social data is fetched
  useEffect(() => {
    if (!currentRequest?.id || !latestStatus) return
    
    if (latestStatus.stage === 'social_data_fetched' && latestStatus.metadata?.username) {
      const username = latestStatus.metadata.username
      
      if (typeof window !== 'undefined') {
        const timeoutId = setTimeout(() => {
          window.dispatchEvent(new CustomEvent('analysis-username-updated', {
            detail: {
              analysis_request_id: currentRequest.id,
              username: username
            }
          }))
        }, 0)
        
        return () => clearTimeout(timeoutId)
      }
    }
  }, [latestStatus?.stage, latestStatus?.metadata?.username, currentRequest?.id])
  
  // Listen for new analysis created and navigate
  useEffect(() => {
    if (!isLoaded) return
    
    if (!isSignedIn) {
      router.replace('/login')
      return
    }
    
    const handleAnalysisCreated = (event: Event) => {
      const customEvent = event as CustomEvent<AnalysisRequest>
      router.push(`/app/${customEvent.detail.id}`)
    }
    
    window.addEventListener('analysis-created', handleAnalysisCreated)
    
    return () => {
      window.removeEventListener('analysis-created', handleAnalysisCreated as EventListener)
    }
  }, [router, isLoaded, isSignedIn])
}




