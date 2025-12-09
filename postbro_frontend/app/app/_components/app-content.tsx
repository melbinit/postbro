"use client"

import { useEffect, useState } from "react"
import { usePathname } from "next/navigation"
import { useAuth } from "@clerk/nextjs"
import { useRealtimeStatus } from "@/hooks/use-realtime-status"
import { Loader2 } from "lucide-react"

// Hooks
import { useAnalysisState } from "./hooks/use-analysis-state"
import { useScrollBehavior } from "./hooks/use-scroll-behavior"
import { useAnalysisLoader } from "./hooks/use-analysis-loader"
import { useAnalysisEvents } from "./hooks/use-analysis-events"

// UI Components
import { WelcomeMessage } from "./ui/welcome-message"
import { AnalysisStatus } from "./ui/analysis-status"
import { InputArea } from "./ui/input-area"
import { LoadingScreen } from "./ui/loading-screen"
import { NotesDrawer } from "@/components/app/notes-drawer"
import { NotesButton } from "@/components/app/notes-button"

/**
 * Main content area for analysis display
 * Orchestrates state, data loading, scroll behavior, and UI rendering
 * 
 * Refactored from 1042 lines to ~150 lines for better maintainability
 */
export function AppContent() {
  const pathname = usePathname()
  const { isSignedIn, isLoaded, getToken } = useAuth()
  const [isMounted, setIsMounted] = useState(false)
  const [isNotesDrawerOpen, setIsNotesDrawerOpen] = useState(false)
  
  // Extract analysis ID from URL path (e.g., /app/123-456-789)
  const analysisId = pathname?.startsWith('/app/') && pathname !== '/app' 
    ? pathname.split('/app/')[1]?.split('/')[0] 
    : null
  
  // Centralized state management
  const state = useAnalysisState()
  
  // Realtime status updates
  const { statusHistory, isConnected, latestStatus } = useRealtimeStatus(
    state.currentRequest?.id || null
  )
  
  // Scroll behavior management
  useScrollBehavior({
    currentRequest: state.currentRequest,
    messagesContainerRef: state.messagesContainerRef as React.RefObject<HTMLDivElement>,
    hasScrolledToBottomRef: state.hasScrolledToBottomRef,
    userHasInteractedRef: state.userHasInteractedRef,
    wasCompletedOnLoadRef: state.wasCompletedOnLoadRef,
    isTypingActiveRef: state.isTypingActiveRef,
    latestStatus,
    isLoadingAnalysis: state.isLoadingAnalysis,
    isLoadingPosts: state.isLoadingPosts,
    postAnalysisId: state.postAnalysisId,
    posts: state.posts,
    messagesLoaded: state.messagesLoaded,
    setIsTypingActive: state.setIsTypingActive,
    setIsTypingComplete: state.setIsTypingComplete,
  })
  
  // Data loading management
  useAnalysisLoader({
    analysisId,
    isLoaded: isLoaded || false,
    isSignedIn: isSignedIn || false,
    getToken,
    latestStatus,
    state,
  })
  
  // Event handling (sidebar updates, navigation)
  useAnalysisEvents({
    currentRequest: state.currentRequest,
    latestStatus,
    isLoaded: isLoaded || false,
    isSignedIn: isSignedIn || false,
  })
  
  // Mark as mounted on client (prevents hydration mismatch)
  useEffect(() => {
    console.log('🟢 [AppContent] Setting isMounted to true')
    setIsMounted(true)
  }, [])
  
  // Loading states
  if (!isMounted) {
    return <LoadingScreen message="Loading..." />
  }
  
  if (!isLoaded) {
    return <LoadingScreen message="Checking authentication..." />
  }
  
  if (!isSignedIn) {
    return null // Redirect handled in useAnalysisEvents
  }
  
  return (
    <main className="flex-1 flex flex-col min-w-0 relative bg-background overflow-hidden h-full">
      {/* Gradient background */}
      <div 
        className="absolute inset-0 pointer-events-none flex items-center justify-center"
        style={{ 
          background: 'radial-gradient(ellipse 80% 60% at 50% 50%, rgba(37, 99, 235, 0.06) 0%, rgba(139, 92, 246, 0.04) 30%, rgba(139, 92, 246, 0.015) 60%, transparent 100%)'
        }} 
      />

      {/* Chat-like interface */}
      <div className="flex-1 flex flex-col min-h-0 relative z-10">
        {/* Messages area */}
        <div 
          ref={state.messagesContainerRef}
          data-scroll-container
          className="flex-1 min-h-0 overflow-y-auto px-4 md:px-8 py-8"
          style={{ 
            position: 'relative',
            zIndex: isNotesDrawerOpen ? 45 : 'auto' // Higher than backdrop (40) but lower than modal (50)
          }}
        >
          <div className="max-w-3xl mx-auto space-y-6">
            {/* Welcome message */}
            {!state.currentRequest && !state.isLoadingAnalysis && <WelcomeMessage />}
            
            {/* Loading indicator */}
            {state.isLoadingAnalysis && (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="h-6 w-6 animate-spin text-primary mr-3" />
                <span className="text-sm text-muted-foreground">Loading analysis...</span>
              </div>
            )}
            
            {/* Analysis status, posts, and chat */}
            {state.currentRequest && !state.isLoadingAnalysis && (
              <AnalysisStatus
                currentRequest={state.currentRequest}
                posts={state.posts}
                isLoadingPosts={state.isLoadingPosts}
                latestStatus={latestStatus}
                postAnalysisId={state.postAnalysisId}
                messagesContainerRef={state.messagesContainerRef as React.RefObject<HTMLDivElement>}
                messagesLoaded={state.messagesLoaded}
                setMessagesLoaded={state.setMessagesLoaded}
                hasScrolledToBottomRef={state.hasScrolledToBottomRef}
                userHasInteractedRef={state.userHasInteractedRef}
                wasCompletedOnLoadRef={state.wasCompletedOnLoadRef}
              />
            )}
          </div>
        </div>
        
        {/* Input area */}
        <InputArea
          currentRequest={state.currentRequest}
          latestStatus={latestStatus}
          postAnalysisId={state.postAnalysisId}
          posts={state.posts}
          messagesLoaded={state.messagesLoaded}
          isFormMinimized={state.isFormMinimized}
          setIsFormMinimized={state.setIsFormMinimized}
        />

        {/* Floating Notes Button - only show when analysis is completed and has postAnalysisId */}
        {state.currentRequest?.status === 'completed' && state.postAnalysisId && (
          <div className="fixed bottom-24 right-6 z-30">
            <NotesButton onClick={() => setIsNotesDrawerOpen(true)} />
          </div>
        )}
      </div>

      {/* Notes Drawer - positioned absolutely, doesn't affect main layout */}
      <NotesDrawer
        isOpen={isNotesDrawerOpen}
        onClose={() => setIsNotesDrawerOpen(false)}
        postAnalysisId={state.postAnalysisId}
        postUsername={state.posts.length > 0 ? state.posts[0].username : null}
        onNoteSaved={() => {
          // Could trigger a refresh of notes list in sidebar if needed
        }}
      />
    </main>
  )
}
