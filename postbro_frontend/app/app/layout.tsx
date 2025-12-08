"use client"

import { AppSidebar } from "@/components/app/app-sidebar"
import { AppHeader } from "@/components/layout/app-header"
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from "@/components/ui/sheet"
import { AppProvider } from "@/contexts/app-context"
import { useState, Suspense } from "react"
import { Skeleton } from "@/components/ui/skeleton"

// Layout that wraps both /app and /app/[id] routes
// This ensures the sidebar persists and doesn't remount when navigating
export default function AppLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)

  // Skeleton loader for sidebar while Suspense resolves
  const SidebarSkeleton = () => (
    <div className="w-full h-full flex flex-col">
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

  return (
    <AppProvider>
      <div className="flex h-screen flex-col overflow-hidden">
        <AppHeader onMenuClick={() => setIsSidebarOpen(true)} />
        <div className="flex flex-1 pt-16 h-[calc(100vh-4rem)] overflow-hidden">
          {/* Desktop Sidebar - Wrapped in Suspense for useSearchParams */}
          <aside className="hidden md:flex w-64 bg-background/80 backdrop-blur-sm flex-col h-full border-r border-border/50 shadow-sm">
            <Suspense fallback={<SidebarSkeleton />}>
              <AppSidebar />
            </Suspense>
          </aside>

          {/* Mobile Sidebar - Also wrapped in Suspense */}
          <Sheet open={isSidebarOpen} onOpenChange={setIsSidebarOpen}>
            <SheetContent side="left" className="w-64 p-0 pt-6">
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

          {/* Main Content - Only this part changes when navigating */}
          {children}
        </div>
      </div>
    </AppProvider>
  )
}

