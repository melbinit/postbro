"use client"

import { useState } from "react"
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { 
  User, 
  CreditCard, 
  BarChart3, 
  Settings as SettingsIcon, 
  Receipt,
  X
} from "lucide-react"
import { ProfileForm } from "@/components/profile/profile-form"
import { SubscriptionPlan } from "@/components/profile/subscription-plan"
import { UsageStats } from "@/components/profile/usage-stats"
import { BillingHistory } from "@/components/profile/billing-history"
import { UpgradePlans } from "@/components/billing/upgrade-plans"
import { cn } from "@/lib/utils"

interface SettingsModalProps {
  isOpen: boolean
  onClose: () => void
  defaultTab?: string
}

type TabId = "general" | "subscription" | "usage" | "billing" | "settings"

const tabs: { id: TabId; label: string; icon: typeof User }[] = [
  { id: "general", label: "General", icon: User },
  { id: "subscription", label: "Subscription", icon: CreditCard },
  { id: "usage", label: "Usage", icon: BarChart3 },
  { id: "billing", label: "Billing", icon: Receipt },
  { id: "settings", label: "Settings", icon: SettingsIcon },
]

export function SettingsModal({ isOpen, onClose, defaultTab = "general" }: SettingsModalProps) {
  const [activeTab, setActiveTab] = useState<TabId>(defaultTab as TabId)

  const renderContent = () => {
    switch (activeTab) {
      case "general":
        return <ProfileForm />
      case "subscription":
        return (
          <div className="space-y-6">
            <SubscriptionPlan />
            <div className="mt-8">
              <UpgradePlans />
            </div>
          </div>
        )
      case "usage":
        return <UsageStats />
      case "billing":
        return <BillingHistory />
      case "settings":
        return (
          <div className="bg-background rounded-xl border border-border p-6 text-center text-muted-foreground min-h-[400px] flex items-center justify-center">
            <div>
              <SettingsIcon className="size-12 mx-auto mb-4 opacity-50" />
              <p className="text-lg font-medium mb-2">Additional Settings</p>
              <p className="text-sm">Coming soon</p>
            </div>
          </div>
        )
      default:
        return <ProfileForm />
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-[95vw] sm:max-w-[90vw] lg:max-w-7xl xl:max-w-[90vw] w-full h-[95vh] sm:h-[90vh] max-h-[900px] p-0 gap-0 overflow-hidden flex flex-col" showCloseButton={false}>
        {/* Header */}
        <div className="flex items-center justify-between px-4 sm:px-6 py-3 sm:py-4 border-b border-border flex-shrink-0 bg-background">
          <DialogTitle className="text-lg sm:text-xl font-semibold">Settings</DialogTitle>
          <Button
            variant="ghost"
            size="icon"
            onClick={onClose}
            className="h-8 w-8"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>

        {/* Main Content */}
        <div className="flex flex-col lg:flex-row flex-1 min-h-0 overflow-hidden">
          {/* Sidebar - Horizontal on mobile, vertical on desktop */}
          <div className="w-full lg:w-72 xl:w-80 border-b lg:border-b-0 lg:border-r border-border bg-muted/20 flex-shrink-0 overflow-x-auto lg:overflow-y-auto">
            <nav className="flex lg:flex-col p-2 sm:p-3 space-x-1 lg:space-x-0 lg:space-y-1">
              {tabs.map((tab) => {
                const Icon = tab.icon
                const isActive = activeTab === tab.id
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={cn(
                      "flex items-center gap-2 lg:gap-3 px-3 py-2 lg:py-2.5 rounded-lg text-sm font-medium transition-all duration-200 whitespace-nowrap lg:w-full",
                      isActive
                        ? "bg-primary text-primary-foreground shadow-sm"
                        : "text-muted-foreground hover:bg-muted/50 hover:text-foreground"
                    )}
                  >
                    <Icon className="size-4 shrink-0" />
                    <span>{tab.label}</span>
                  </button>
                )
              })}
            </nav>
          </div>

          {/* Content Area */}
          <div className="flex-1 overflow-y-auto bg-background">
            <div className="p-4 sm:p-6">
              <div className="max-w-5xl xl:max-w-6xl mx-auto">
                {renderContent()}
              </div>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}

