"use client"

import { AppSidebar } from "@/components/app/app-sidebar"
import { AppHeader } from "@/components/layout/app-header"
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from "@/components/ui/sheet"
import { AppProvider, useAppContext } from "@/contexts/app-context"
import { PostPanel } from "@/components/app/post-panel"
import { useState, Suspense } from "react"
import { Skeleton } from "@/components/ui/skeleton"

// Layout that wraps both /app and /app/[id] routes
// This ensures the sidebar persists and doesn't remount when navigating
export default function AppLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <AppProvider>
      <AppLayoutInner>{children}</AppLayoutInner>
    </AppProvider>
  )
}

// Inner layout component that can access AppContext
function AppLayoutInner({ children }: { children: React.ReactNode }) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)
  const { currentPost, isLoadingPosts } = useAppContext()

  // Skeleton loader for sidebar while Suspense resolves
  const SidebarSkeleton = () => (
    <div className="w-full h-full flex flex-col bg-background/50">
      <div className="p-4 space-y-4 border-b border-border/40">
        <div className="flex items-center gap-3">
          <Skeleton className="size-10 rounded-full" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-3 w-32" />
          </div>
        </div>
      </div>
      <div className="p-4 space-y-2">
        <Skeleton className="h-16 w-full rounded-md" />
        <Skeleton className="h-16 w-full rounded-md" />
        <Skeleton className="h-16 w-full rounded-md" />
      </div>
    </div>
  )

  // Post panel skeleton
  const PostPanelSkeleton = () => (
    <div className="w-full h-full flex flex-col bg-background/50">
      <div className="p-4 border-b border-border/40">
        <div className="flex items-center gap-2">
          <Skeleton className="h-4 w-4 rounded" />
          <Skeleton className="h-4 w-24" />
        </div>
      </div>
      <div className="flex-1 p-4">
        <Skeleton className="w-full aspect-square rounded-xl" />
      </div>
    </div>
  )

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-background">
      <AppHeader onMenuClick={() => setIsSidebarOpen(true)} />
      
      <div className="flex flex-1 pt-16 h-[calc(100vh-4rem)] overflow-hidden">
        {/* Left Sidebar - Settings & History */}
        <aside className="hidden md:flex w-[280px] xl:w-[300px] bg-gradient-to-b from-background to-muted/20 flex-col h-full border-r border-border/40 shadow-sm">
          <Suspense fallback={<SidebarSkeleton />}>
            <AppSidebar />
          </Suspense>
        </aside>

        {/* Mobile Sidebar - Sheet */}
        <Sheet open={isSidebarOpen} onOpenChange={setIsSidebarOpen}>
          <SheetContent side="left" className="w-[280px] p-0 pt-6">
            <SheetHeader className="sr-only">
              <SheetTitle>Navigation Menu</SheetTitle>
              <SheetDescription>
                Main navigation menu for PostBro application
              </SheetDescription>
            </SheetHeader>
            <Suspense fallback={<SidebarSkeleton />}>
              <AppSidebar onNavigate={() => setIsSidebarOpen(false)} />
            </Suspense>
          </SheetContent>
        </Sheet>

        {/* Center - Main Content (Chat/Analysis) */}
        <main className="flex-1 min-w-0 flex flex-col h-full overflow-hidden">
          {children}
        </main>

        {/* Right Panel - Post Preview (Desktop only, xl+) */}
        <aside className="hidden xl:flex w-[380px] 2xl:w-[420px] bg-gradient-to-b from-background to-muted/10 flex-col h-full border-l border-border/40">
          <Suspense fallback={<PostPanelSkeleton />}>
            <PostPanel 
              post={currentPost || null}
              isLoading={isLoadingPosts}
            />
          </Suspense>
        </aside>
      </div>
    </div>
  )
}

