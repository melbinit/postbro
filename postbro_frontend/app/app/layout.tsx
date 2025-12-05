"use client"

import { AppSidebar } from "@/components/app/app-sidebar"
import { AppHeader } from "@/components/layout/app-header"
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from "@/components/ui/sheet"
import { AppProvider } from "@/contexts/app-context"
import { useState } from "react"

// Layout that wraps both /app and /app/[id] routes
// This ensures the sidebar persists and doesn't remount when navigating
export default function AppLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)

  return (
    <AppProvider>
      <div className="flex h-screen flex-col overflow-hidden">
        <AppHeader onMenuClick={() => setIsSidebarOpen(true)} />
        <div className="flex flex-1 pt-16 h-[calc(100vh-4rem)] overflow-hidden">
          {/* Desktop Sidebar - Persists across route changes */}
          <aside className="hidden md:flex w-64 bg-background/50 backdrop-blur-sm flex-col h-full border-r border-border/30">
            <AppSidebar />
          </aside>

          {/* Mobile Sidebar */}
          <Sheet open={isSidebarOpen} onOpenChange={setIsSidebarOpen}>
            <SheetContent side="left" className="w-64 p-0 pt-6">
              <SheetHeader className="sr-only">
                <SheetTitle>Navigation Menu</SheetTitle>
                <SheetDescription>
                  Main navigation menu for PostBro application
                </SheetDescription>
              </SheetHeader>
              <AppSidebar onNavigate={() => setIsSidebarOpen(false)} />
            </SheetContent>
          </Sheet>

          {/* Main Content - Only this part changes when navigating */}
          {children}
        </div>
      </div>
    </AppProvider>
  )
}

