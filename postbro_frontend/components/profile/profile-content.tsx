"use client"

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ProfileForm } from "@/components/profile/profile-form"
import { SubscriptionPlan } from "@/components/profile/subscription-plan"
import { UsageStats } from "@/components/profile/usage-stats"
import { BillingHistory } from "@/components/profile/billing-history"
import { User, CreditCard, BarChart3, Settings, Receipt } from "lucide-react"

interface ProfileContentProps {
  defaultTab?: string
}

export function ProfileContent({ defaultTab = "overview" }: ProfileContentProps) {
  return (
    <Tabs defaultValue={defaultTab} className="space-y-6">
      <TabsList>
        <TabsTrigger value="overview">
          <User className="size-4" />
          General
        </TabsTrigger>
        <TabsTrigger value="subscription">
          <CreditCard className="size-4" />
          Subscription
        </TabsTrigger>
        <TabsTrigger value="usage">
          <BarChart3 className="size-4" />
          Usage
        </TabsTrigger>
        <TabsTrigger value="billing">
          <Receipt className="size-4" />
          Billing
        </TabsTrigger>
        <TabsTrigger value="settings">
          <Settings className="size-4" />
          Settings
        </TabsTrigger>
      </TabsList>

      <TabsContent value="overview" className="space-y-6">
        <ProfileForm />
      </TabsContent>

      <TabsContent value="subscription">
        <SubscriptionPlan />
      </TabsContent>

      <TabsContent value="usage">
        <UsageStats />
      </TabsContent>

      <TabsContent value="billing">
        <BillingHistory />
      </TabsContent>

      <TabsContent value="settings">
        <div className="bg-background rounded-xl border border-border p-6 text-center text-muted-foreground min-h-[400px] flex items-center justify-center">
          Additional settings coming soon
        </div>
      </TabsContent>
    </Tabs>
  )
}
