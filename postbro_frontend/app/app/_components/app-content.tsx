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
    <div className="flex-1 flex flex-col min-w-0 relative overflow-hidden h-full">
      {/* Subtle gradient background */}
      <div 
        className="absolute inset-0 pointer-events-none"
        style={{ 
          background: 'radial-gradient(ellipse 100% 80% at 50% 0%, rgba(37, 99, 235, 0.04) 0%, rgba(139, 92, 246, 0.02) 40%, transparent 100%)'
        }} 
      />
      
      {/* Grid pattern overlay for modern SaaS feel */}
      <div 
        className="absolute inset-0 pointer-events-none opacity-[0.02]"
        style={{
          backgroundImage: 'linear-gradient(rgba(0,0,0,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(0,0,0,0.1) 1px, transparent 1px)',
          backgroundSize: '32px 32px'
        }}
      />

      {/* Chat-like interface */}
      <div className="flex-1 flex flex-col min-h-0 relative z-10">
        {/* Messages area */}
        <div 
          ref={state.messagesContainerRef}
          data-scroll-container
          className="flex-1 min-h-0 overflow-y-auto px-4 lg:px-6 xl:px-8 py-6"
          style={{ 
            position: 'relative',
            zIndex: isNotesDrawerOpen ? 45 : 'auto'
          }}
        >
          <div className="max-w-2xl xl:max-w-3xl mx-auto space-y-6">
            {/* Welcome message */}
            {!state.currentRequest && !state.isLoadingAnalysis && <WelcomeMessage />}
            
            {/* Loading indicator */}
            {state.isLoadingAnalysis && (
              <div className="flex flex-col items-center justify-center py-16">
                <div className="relative">
                  <div className="size-12 rounded-xl bg-gradient-to-br from-primary/20 to-violet-500/20 flex items-center justify-center animate-pulse">
                    <Loader2 className="h-6 w-6 animate-spin text-primary" />
                  </div>
                </div>
                <span className="text-sm text-muted-foreground mt-4">Loading analysis...</span>
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
        
        {/* Input area with modern styling */}
        <div className="border-t border-border/40 bg-background/80 backdrop-blur-sm">
          <InputArea
            currentRequest={state.currentRequest}
            latestStatus={latestStatus}
            postAnalysisId={state.postAnalysisId}
            posts={state.posts}
            messagesLoaded={state.messagesLoaded}
            isFormMinimized={state.isFormMinimized}
            setIsFormMinimized={state.setIsFormMinimized}
          />
        </div>

        {/* Floating Notes Button - only show when analysis is completed and has postAnalysisId */}
        {/* On xl+ screens, position it differently to not overlap with right panel */}
        {state.currentRequest?.status === 'completed' && state.postAnalysisId && (
          <div className="fixed bottom-24 right-6 xl:right-[420px] 2xl:right-[460px] z-30 transition-all">
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
    </div>
  )
}
