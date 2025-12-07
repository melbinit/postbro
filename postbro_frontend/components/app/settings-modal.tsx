"use client"

import { useState, useEffect } from "react"
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { 
  User, 
  CreditCard, 
  BarChart3, 
  Settings as SettingsIcon, 
  Receipt,
  X,
  ChevronLeft
} from "lucide-react"
import { ProfileForm } from "@/components/profile/profile-form"
import { SubscriptionView } from "@/components/profile/subscription-view"
import { UsageStats } from "@/components/profile/usage-stats"
import { BillingHistory } from "@/components/profile/billing-history"
import { cn } from "@/lib/utils"

interface SettingsModalProps {
  isOpen: boolean
  onClose: () => void
  defaultTab?: string
}

type TabId = "general" | "subscription" | "usage" | "billing" | "settings"

const tabs: { id: TabId; label: string; description: string; icon: typeof User }[] = [
  { id: "general", label: "General", description: "Profile & account", icon: User },
  { id: "subscription", label: "Subscription", description: "Plans & pricing", icon: CreditCard },
  { id: "usage", label: "Usage", description: "Analytics & limits", icon: BarChart3 },
  { id: "billing", label: "Billing", description: "History & invoices", icon: Receipt },
  { id: "settings", label: "Settings", description: "Preferences", icon: SettingsIcon },
]

export function SettingsModal({ isOpen, onClose, defaultTab = "general" }: SettingsModalProps) {
  const [activeTab, setActiveTab] = useState<TabId>(defaultTab as TabId)
  // Mobile: show menu first, then content
  const [showMobileContent, setShowMobileContent] = useState(false)

  // Update active tab when defaultTab prop changes
  useEffect(() => {
    if (isOpen && defaultTab) {
      setActiveTab(defaultTab as TabId)
      // If opening with a specific tab, go directly to content on mobile
      if (defaultTab !== "general") {
        setShowMobileContent(true)
      }
    }
  }, [isOpen, defaultTab])

  // Reset mobile view when modal closes
  useEffect(() => {
    if (!isOpen) {
      setShowMobileContent(false)
    }
  }, [isOpen])

  const activeTabData = tabs.find(t => t.id === activeTab)

  const handleTabClick = (tabId: TabId) => {
    setActiveTab(tabId)
    setShowMobileContent(true)
  }

  const handleMobileBack = () => {
    setShowMobileContent(false)
  }

  const renderContent = () => {
    switch (activeTab) {
      case "general":
        return <ProfileForm />
      case "subscription":
        return <SubscriptionView />
      case "usage":
        return <UsageStats onNavigateToSubscription={() => setActiveTab("subscription")} />
      case "billing":
        return <BillingHistory />
      case "settings":
        return (
          <div className="bg-card rounded-xl sm:rounded-2xl border border-border/50 p-6 sm:p-8 text-center min-h-[300px] sm:min-h-[400px] flex items-center justify-center">
            <div>
              <div className="inline-flex items-center justify-center w-14 h-14 sm:w-16 sm:h-16 rounded-xl sm:rounded-2xl bg-gradient-to-br from-muted to-muted/50 mb-4 sm:mb-5">
                <SettingsIcon className="size-6 sm:size-7 text-muted-foreground" />
              </div>
              <p className="text-base sm:text-lg font-semibold mb-1.5 sm:mb-2">Additional Settings</p>
              <p className="text-xs sm:text-sm text-muted-foreground">Coming soon</p>
            </div>
          </div>
        )
      default:
        return <ProfileForm />
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent 
        className="max-w-[100vw] sm:max-w-[90vw] lg:max-w-6xl w-full h-[100dvh] sm:h-[90vh] sm:max-h-[850px] p-0 gap-0 overflow-hidden flex flex-col sm:rounded-2xl rounded-none border-0 sm:border border-border/50" 
        showCloseButton={false}
      >
        {/* Mobile Header - Shows back button when in content view */}
        <div className="flex sm:hidden items-center justify-between px-4 py-3 border-b border-border/50 bg-background flex-shrink-0">
          {showMobileContent ? (
            <button 
              onClick={handleMobileBack}
              className="flex items-center gap-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
            >
              <ChevronLeft className="size-5" />
              <span>Settings</span>
            </button>
          ) : (
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-lg bg-primary/10 text-primary">
                <SettingsIcon className="h-4 w-4" />
              </div>
              <DialogTitle className="text-base font-semibold">Settings</DialogTitle>
            </div>
          )}
          <Button
            variant="ghost"
            size="icon"
            onClick={onClose}
            className="h-8 w-8 rounded-lg hover:bg-muted/80"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>

        {/* Desktop Header */}
        <div className="hidden sm:flex relative items-center justify-between px-6 py-5 border-b border-border/50 flex-shrink-0 bg-gradient-to-r from-primary/5 via-transparent to-transparent">
          <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-10 bg-gradient-to-b from-primary to-primary/50 rounded-r-full" />
          
          <div className="flex items-center gap-3 pl-3">
            <div className="p-2.5 rounded-xl bg-primary/10 text-primary">
              <SettingsIcon className="h-5 w-5" />
            </div>
            <div>
              <DialogTitle className="text-xl font-semibold">Settings</DialogTitle>
              <p className="text-xs text-muted-foreground mt-0.5">
                Manage your account and preferences
              </p>
            </div>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={onClose}
            className="h-9 w-9 rounded-xl hover:bg-muted/80"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>

        {/* Main Content */}
        <div className="flex flex-col lg:flex-row flex-1 min-h-0 overflow-hidden">
          {/* Mobile Menu View */}
          <div className={cn(
            "sm:hidden flex-1 overflow-y-auto bg-background",
            showMobileContent ? "hidden" : "block"
          )}>
            <nav className="p-3 space-y-1">
              {tabs.map((tab) => {
                const Icon = tab.icon
                const isActive = activeTab === tab.id
                return (
                  <button
                    key={tab.id}
                    onClick={() => handleTabClick(tab.id)}
                    className={cn(
                      "flex items-center gap-3 w-full px-4 py-3.5 rounded-xl text-left transition-all",
                      isActive
                        ? "bg-primary/10 text-primary"
                        : "text-foreground hover:bg-muted/60 active:bg-muted"
                    )}
                  >
                    <div className={cn(
                      "p-2 rounded-lg",
                      isActive ? "bg-primary/15" : "bg-muted/60"
                    )}>
                      <Icon className="size-4" />
                    </div>
                    <div className="flex-1">
                      <div className="font-medium text-sm">{tab.label}</div>
                      <div className="text-xs text-muted-foreground mt-0.5">{tab.description}</div>
                    </div>
                    <ChevronLeft className="size-4 text-muted-foreground rotate-180" />
                  </button>
                )
              })}
            </nav>
          </div>

          {/* Mobile Content View */}
          <div className={cn(
            "sm:hidden flex-1 overflow-y-auto bg-background",
            showMobileContent ? "block" : "hidden"
          )}>
            {/* Mobile Content Header */}
            <div className="px-4 py-4 border-b border-border/30 bg-muted/30">
              <div className="flex items-center gap-2.5">
                {activeTabData && (
                  <>
                    <div className="p-1.5 rounded-lg bg-primary/10 text-primary">
                      <activeTabData.icon className="size-4" />
                    </div>
                    <div>
                      <h2 className="text-base font-semibold">{activeTabData.label}</h2>
                      <p className="text-xs text-muted-foreground">{activeTabData.description}</p>
                    </div>
                  </>
                )}
              </div>
            </div>
            
            {/* Mobile Content Body */}
            <div className="p-4">
              {renderContent()}
            </div>
          </div>

          {/* Desktop Sidebar */}
          <div className="hidden sm:block w-full lg:w-64 xl:w-72 border-b lg:border-b-0 lg:border-r border-border/50 bg-muted/30 flex-shrink-0 overflow-x-auto lg:overflow-y-auto">
            <nav className="flex lg:flex-col p-3 gap-1.5">
              {tabs.map((tab) => {
                const Icon = tab.icon
                const isActive = activeTab === tab.id
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={cn(
                      "flex items-center gap-2.5 px-3 py-2.5 lg:py-3 rounded-xl text-sm font-medium transition-all duration-200 whitespace-nowrap lg:w-full group",
                      isActive
                        ? "bg-gradient-to-r from-primary to-primary/85 text-primary-foreground shadow-lg shadow-primary/25"
                        : "text-muted-foreground hover:bg-background hover:text-foreground hover:shadow-sm"
                    )}
                  >
                    <div className={cn(
                      "p-1.5 lg:p-2 rounded-lg transition-colors",
                      isActive 
                        ? "bg-white/20" 
                        : "bg-muted/50 group-hover:bg-muted"
                    )}>
                      <Icon className="size-4" />
                    </div>
                    <div className="flex-1 text-left hidden lg:block">
                      <div className="font-medium">{tab.label}</div>
                      <div className={cn(
                        "text-xs mt-0.5 transition-colors",
                        isActive ? "text-primary-foreground/70" : "text-muted-foreground"
                      )}>
                        {tab.description}
                      </div>
                    </div>
                    <span className="lg:hidden text-sm">{tab.label}</span>
                  </button>
                )
              })}
            </nav>
          </div>

          {/* Desktop Content Area */}
          <div className="hidden sm:flex flex-1 flex-col overflow-hidden bg-gradient-to-b from-background to-muted/20">
            {/* Content Header */}
            <div className="px-6 lg:px-8 pt-5 pb-4 border-b border-border/30 flex-shrink-0">
              <div className="flex items-center gap-3">
                {activeTabData && (
                  <>
                    <div className="p-2 rounded-lg bg-primary/10 text-primary">
                      <activeTabData.icon className="size-4" />
                    </div>
                    <div>
                      <h2 className="text-lg font-semibold">{activeTabData.label}</h2>
                      <p className="text-sm text-muted-foreground">{activeTabData.description}</p>
                    </div>
                  </>
                )}
              </div>
            </div>
            
            {/* Content Body */}
            <div className="flex-1 overflow-y-auto p-6 lg:p-8">
              <div className="max-w-4xl">
                {renderContent()}
              </div>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
