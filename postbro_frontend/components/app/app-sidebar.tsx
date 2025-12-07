"use client"

import { useMemo, memo, useState, useEffect } from "react"
import Link from "next/link"
import { usePathname, useRouter, useSearchParams } from "next/navigation"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { 
  Settings, 
  History,
  Instagram,
  CheckCircle2,
  Clock,
  XCircle,
  Loader2,
  Hash,
  Plus,
  FileText
} from "lucide-react"
import { type AnalysisRequest } from "@/lib/api"
import { format } from "date-fns"
import { useAppContext } from "@/contexts/app-context"
import { NotesList } from "./notes-list"
import { SettingsModal } from "./settings-modal"

interface AppSidebarProps {
  onNavigate?: () => void
  selectedAnalysisId?: string | null
}

// Memoized Profile Section - never re-renders unnecessarily
const ProfileSection = memo(({ user, isLoading, router, onNavigate, onOpenSettings }: {
  user: ReturnType<typeof useAppContext>['user'] | null
  isLoading: boolean
  router: ReturnType<typeof useRouter>
  onNavigate?: () => void
  onOpenSettings: () => void
}) => {
  const initials = user?.full_name
    ?.split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase() || user?.email[0].toUpperCase() || 'U'

  return (
    <div className="p-4 border-b border-border/40 flex-shrink-0">
      {isLoading ? (
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <Skeleton className="size-10 rounded-full" />
            <div className="flex-1 space-y-2">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-3 w-32" />
            </div>
          </div>
        </div>
      ) : user ? (
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <Avatar className="size-10 ring-2 ring-primary/10 ring-offset-2 ring-offset-background">
              <AvatarImage src={user.profile_image || undefined} alt={user.full_name || user.email} />
              <AvatarFallback className="text-sm bg-gradient-to-br from-primary/20 to-primary/10 text-primary font-semibold">
                {initials}
              </AvatarFallback>
            </Avatar>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold truncate">{user.full_name || 'User'}</p>
              <p className="text-xs text-muted-foreground truncate">{user.email}</p>
            </div>
          </div>
          <div className="flex flex-col gap-1.5">
            <Button
              variant="default"
              size="sm"
              className="justify-start w-full bg-primary/10 text-primary hover:bg-primary/20 border-0 shadow-none"
              onClick={() => {
                router.push('/app')
                onNavigate?.()
              }}
            >
              <Plus className="mr-2 size-4" />
              New Analysis
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="justify-start w-full text-muted-foreground hover:text-foreground"
              onClick={() => {
                onOpenSettings()
                // Don't call onNavigate here - let the modal appear on top of the sidebar
                // The modal will handle closing itself and then user can close sidebar if needed
              }}
            >
              <Settings className="mr-2 size-4" />
              Settings
            </Button>
          </div>
        </div>
      ) : null}
    </div>
  )
})

ProfileSection.displayName = 'ProfileSection'

// Memoize the sidebar to prevent unnecessary re-renders when pathname changes
export const AppSidebar = memo(function AppSidebar({ onNavigate, selectedAnalysisId: externalSelectedId }: AppSidebarProps) {
  const pathname = usePathname()
  const router = useRouter()
  
  // Use cached data from context - no API calls on every render!
  const { 
    user, 
    analyses, 
    isLoadingUser, 
    isLoadingAnalyses,
    isLoadingMoreAnalyses,
    hasMoreAnalyses,
    loadMoreAnalyses
  } = useAppContext()
  
  // Extract analysis ID from URL path (e.g., /app/123-456-789)
  // Memoize to prevent unnecessary recalculations
  const urlAnalysisId = useMemo(() => {
    return pathname?.startsWith('/app/') && pathname !== '/app' 
      ? pathname.split('/app/')[1]?.split('/')[0] 
      : null
  }, [pathname])
  
  // Use external selected ID if provided, otherwise use URL-based ID
  const selectedAnalysisId = externalSelectedId !== undefined ? externalSelectedId : urlAnalysisId

  // Tab state for switching between Analyses and Notes
  const [activeTab, setActiveTab] = useState<'analyses' | 'notes'>('analyses')
  
  // Settings modal state
  const searchParams = useSearchParams()
  const [isSettingsModalOpen, setIsSettingsModalOpen] = useState(false)
  const [defaultSettingsTab, setDefaultSettingsTab] = useState<string>("general")
  
  // Check for settings query parameter on mount and when it changes
  useEffect(() => {
    const settingsParam = searchParams.get('settings')
    if (settingsParam) {
      setDefaultSettingsTab(settingsParam)
      setIsSettingsModalOpen(true)
      // Clean up URL by removing query parameter after opening modal
      const newUrl = new URL(window.location.href)
      newUrl.searchParams.delete('settings')
      router.replace(newUrl.pathname + (newUrl.search ? newUrl.search : ''))
    }
  }, [searchParams, router])


  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle2 className="size-3 text-green-600 dark:text-green-400" />
      case 'processing':
      case 'pending':
        return <Loader2 className="size-3 text-blue-600 dark:text-blue-400 animate-spin" />
      case 'failed':
        return <XCircle className="size-3 text-red-600 dark:text-red-400" />
      default:
        return <Clock className="size-3 text-muted-foreground" />
    }
  }

  const getPlatformIcon = (platform: string) => {
    if (platform === 'instagram') {
      return <Instagram className="size-4" />
    } else if (platform === 'youtube') {
      return (
        <svg className="size-4" viewBox="0 0 24 24" fill="currentColor">
          <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
        </svg>
      )
    } else {
      return <Hash className="size-4" />
    }
  }

  return (
    <>
      <div className="flex flex-col h-full overflow-hidden bg-gradient-subtle">
        {/* Profile Section - Memoized, never refreshes - Shows independently */}
        <ProfileSection 
          user={user} 
          isLoading={isLoadingUser} 
          router={router} 
          onNavigate={onNavigate}
          onOpenSettings={() => setIsSettingsModalOpen(true)}
        />

      {/* Tabs for Analyses and Notes */}
      <div className="flex-1 flex flex-col min-h-0">
        <div className="p-4 border-b border-border/40 flex-shrink-0">
          <div className="flex items-center gap-1 p-1 bg-muted/40 rounded-lg">
            <button
              onClick={() => setActiveTab('analyses')}
              className={`flex items-center gap-2 text-sm font-medium px-3 py-1.5 rounded-md transition-all duration-200 ${
                activeTab === 'analyses'
                  ? 'bg-background text-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground hover:bg-background/50'
              }`}
            >
              <History className="size-4" />
              Analyses
            </button>
            <button
              onClick={() => setActiveTab('notes')}
              className={`flex items-center gap-2 text-sm font-medium px-3 py-1.5 rounded-md transition-all duration-200 ${
                activeTab === 'notes'
                  ? 'bg-background text-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground hover:bg-background/50'
              }`}
            >
              <FileText className="size-4" />
              Notes
            </button>
          </div>
        </div>

        <div className="flex-1 min-h-0 overflow-y-auto scrollbar-visible">
          {activeTab === 'analyses' ? (
            <div className="p-2">
              {isLoadingAnalyses ? (
              <div className="space-y-2">
                {[1, 2, 3].map((i) => (
                  <Skeleton key={i} className="h-16 w-full rounded-md" />
                ))}
              </div>
            ) : analyses.length === 0 ? (
              <div className="p-4 text-center text-sm text-muted-foreground">
                <p>No analyses yet</p>
                <p className="text-xs mt-1">Create your first analysis!</p>
              </div>
            ) : (
              <>
                <div className="space-y-1.5">
                  {analyses.map((analysis) => {
                    const isSelected = selectedAnalysisId === analysis.id
                    return (
                      <button
                        key={analysis.id}
                        onClick={(e) => {
                          e.preventDefault()
                          e.stopPropagation()
                          onNavigate?.()
                          // Use Next.js router for client-side navigation (no full page refresh)
                          router.push(`/app/${analysis.id}`)
                        }}
                        className={`w-full text-left p-3 rounded-xl transition-all duration-200 group ${
                          isSelected
                            ? 'bg-gradient-to-r from-primary/12 to-primary/6 border border-primary/25 shadow-sm'
                            : 'hover:bg-muted/60 hover:shadow-sm border border-transparent'
                        }`}
                      >
                        <div className="flex items-start gap-3">
                          <div className={`mt-0.5 p-1.5 rounded-lg transition-colors ${
                            isSelected 
                              ? 'bg-primary/15 text-primary' 
                              : 'bg-muted/50 text-muted-foreground group-hover:bg-muted group-hover:text-foreground'
                          }`}>
                            {getPlatformIcon(analysis.platform)}
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              <p className={`text-sm font-medium truncate transition-colors ${
                                isSelected ? 'text-foreground' : 'group-hover:text-foreground'
                              }`}>
                                {analysis.display_name 
                                  ? analysis.display_name
                                  : analysis.username
                                  ? analysis.username
                                  : (analysis.status === 'pending' || analysis.status === 'processing')
                                    ? 'New Analysis'  // Only show "New Analysis" for new/processing analyses
                                    : (analysis.post_urls?.[0] 
                                        ? analysis.post_urls[0].split('/').pop()?.slice(0, 20) || 'Analysis'
                                        : 'Analysis')}
                              </p>
                              {getStatusIcon(analysis.status)}
                            </div>
                            <p className="text-xs text-muted-foreground">
                              {analysis.created_at ? format(new Date(analysis.created_at), 'MMM dd, yyyy') : 'Recent'}
                            </p>
                          </div>
                        </div>
                      </button>
                    )
                  })}
                </div>
                
                {/* Load More Button */}
                {hasMoreAnalyses && (
                  <div className="p-2 pt-4">
                    <button
                      onClick={(e) => {
                        e.preventDefault()
                        e.stopPropagation()
                        loadMoreAnalyses()
                      }}
                      disabled={isLoadingMoreAnalyses}
                      className="w-full text-xs text-muted-foreground hover:text-foreground transition-colors py-2 px-3 rounded-md hover:bg-muted/50 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {isLoadingMoreAnalyses ? (
                        <span className="flex items-center justify-center gap-2">
                          <Loader2 className="h-3 w-3 animate-spin" />
                          Loading...
                        </span>
                      ) : (
                        'Load more'
                      )}
                    </button>
                  </div>
                )}
              </>
            )}
            </div>
          ) : (
            <NotesList onNavigate={onNavigate} />
          )}
        </div>
      </div>
      </div>

      {/* Settings Modal */}
      <SettingsModal 
        isOpen={isSettingsModalOpen} 
        onClose={() => setIsSettingsModalOpen(false)}
        defaultTab={defaultSettingsTab}
      />
    </>
  )
})

