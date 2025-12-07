"use client"

import { useState, useEffect } from "react"
import { PlanSelector } from "@/components/billing/plan-selector"
import { plansApi, type Subscription, type Plan } from "@/lib/api"
import { Skeleton } from "@/components/ui/skeleton"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { AlertCircle, Check, Zap, Crown, Sparkles, X } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"

export function SubscriptionView() {
  const [currentSubscription, setCurrentSubscription] = useState<Subscription | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  useEffect(() => {
    const fetchSubscription = async () => {
      try {
        setIsLoading(true)
        setError(null)
        const data = await plansApi.getCurrentSubscription()
        setCurrentSubscription(data)
      } catch (err: any) {
        // 404 is expected if no subscription exists
        if (err?.status === 404) {
          setCurrentSubscription(null)
        } else {
          setError(err instanceof Error ? err.message : 'Failed to load subscription')
        }
      } finally {
        setIsLoading(false)
      }
    }

    fetchSubscription()
  }, [])

  const handlePlanSelected = async (planId: string) => {
    // Refresh subscription after plan change
    try {
      const data = await plansApi.getCurrentSubscription()
      console.log('🔄 [SubscriptionView] Refreshed subscription after plan change:', data)
      console.log('🔄 [SubscriptionView] Downgrade info:', {
        status: data?.status,
        downgrade_to_plan: data?.downgrade_to_plan,
        hasDowngrade: data?.status === 'canceling' && data?.downgrade_to_plan
      })
      setCurrentSubscription(data)
    } catch (err) {
      console.error('❌ [SubscriptionView] Failed to refresh subscription:', err)
      // Ignore errors, subscription might not exist yet
    }
  }

  const handleSuccessMessage = (message: string) => {
    setSuccessMessage(message)
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-40 w-full rounded-2xl" />
        <Skeleton className="h-64 w-full rounded-2xl" />
      </div>
    )
  }

  const currentPlan = currentSubscription?.plan
  const isPro = currentPlan?.name === 'Pro'
  const isScheduledDowngrade = currentSubscription?.status === 'canceling' && currentSubscription?.downgrade_to_plan

  const formatDate = (dateString: string | null | undefined): string => {
    if (!dateString) return ''
    try {
      const date = new Date(dateString)
      return date.toLocaleDateString('en-US', { 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric' 
      })
    } catch {
      return dateString
    }
  }

  return (
    <div className="space-y-8">
      {/* Success message alert (closable) */}
      {successMessage && (
        <div className="inline-flex items-center gap-2 rounded-md border border-border bg-muted/50 px-3 py-1.5 text-sm text-muted-foreground">
          <Check className="h-3.5 w-3.5 shrink-0" />
          <span>{successMessage}</span>
          <Button
            variant="ghost"
            size="sm"
            className="h-4 w-4 p-0 hover:bg-transparent shrink-0 -mr-1"
            onClick={() => setSuccessMessage(null)}
          >
            <X className="h-3 w-3" />
          </Button>
        </div>
      )}

      {/* Scheduled Downgrade Alert */}
      {isScheduledDowngrade && currentSubscription.downgrade_to_plan && (
        <div className="flex items-start gap-2 text-sm text-muted-foreground">
          <AlertCircle className="h-3.5 w-3.5 mt-0.5 shrink-0" />
          <p>
            You are currently on the <strong className="text-foreground">{currentSubscription.plan.name}</strong> plan.
            {' '}Your plan will be downgraded to <strong className="text-foreground">{currentSubscription.downgrade_to_plan.name}</strong> on{' '}
            <strong className="text-foreground">{formatDate(currentSubscription.end_date)}</strong>.
            {' '}You will continue to have access to {currentSubscription.plan.name} features until then.
          </p>
        </div>
      )}

      {/* Error alert for critical errors when no subscription */}
      {error && !currentSubscription && (
        <Alert variant="destructive" className="rounded-xl">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Current Plan - Enhanced Card */}
      {currentPlan && (
        <div className="relative bg-card rounded-2xl border border-border/50 overflow-hidden">
          {/* Premium gradient background for Pro */}
          {isPro && (
            <div className="absolute inset-0 bg-gradient-to-br from-amber-500/10 via-transparent to-purple-500/10" />
          )}
          
          <div className="relative p-6 sm:p-8">
            <div className="flex flex-col md:flex-row gap-8">
              {/* Left Side: Plan Info */}
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-4">
                  <div className={`p-2.5 rounded-xl ${isPro ? 'bg-gradient-to-br from-amber-500/20 to-amber-500/10' : 'bg-primary/10'}`}>
                    {isPro ? <Crown className="size-5 text-amber-500" /> : <Zap className="size-5 text-primary" />}
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Current Plan</p>
                    <div className="flex items-center gap-2">
                      <h3 className="text-2xl font-bold">{currentPlan.name}</h3>
                      {currentSubscription.status === 'active' && (
                        <Badge className="bg-green-500/10 text-green-600 dark:text-green-400 border-green-500/20 hover:bg-green-500/10">
                          Active
                        </Badge>
                      )}
                      {currentSubscription.status === 'trial' && (
                        <Badge variant="outline" className="text-amber-600 dark:text-amber-400 border-amber-500/30">
                          Pending Payment
                        </Badge>
                      )}
                    </div>
                  </div>
                </div>
                
                <div className="flex items-baseline gap-1 mb-6">
                  <span className="text-5xl font-bold bg-gradient-to-r from-foreground to-foreground/70 bg-clip-text text-transparent">
                    ${parseFloat(currentPlan.price).toFixed(0)}
                  </span>
                  <span className="text-muted-foreground text-lg">/month</span>
                </div>

                {currentPlan.description && (
                  <p className="text-sm text-muted-foreground max-w-md">
                    {currentPlan.description}
                  </p>
                )}
              </div>

              {/* Right Side: Features */}
              <div className="flex-1 bg-muted/30 rounded-xl p-5">
                <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-4 flex items-center gap-2">
                  <Sparkles className="size-3.5" />
                  Included Features
                </p>
                <ul className="space-y-3">
                  <li className="flex items-center gap-3 text-sm">
                    <div className="p-1 rounded-full bg-green-500/10">
                      <Check className="size-3.5 text-green-500" />
                    </div>
                    <span>
                      {currentPlan.name === 'Free' && 'Basic post analysis'}
                      {currentPlan.name === 'Starter' && 'Detailed post analysis'}
                      {currentPlan.name === 'Pro' && 'In-depth post analysis'}
                      {!['Free', 'Starter', 'Pro'].includes(currentPlan.name) && 'Post analysis'}
                    </span>
                  </li>
                  <li className="flex items-center gap-3 text-sm">
                    <div className="p-1 rounded-full bg-green-500/10">
                      <Check className="size-3.5 text-green-500" />
                    </div>
                    <span><strong>{currentPlan.max_urls}</strong> posts per day</span>
                  </li>
                  <li className="flex items-center gap-3 text-sm">
                    <div className="p-1 rounded-full bg-green-500/10">
                      <Check className="size-3.5 text-green-500" />
                    </div>
                    <span><strong>{currentPlan.max_questions_per_day || 0}</strong> chats per day</span>
                  </li>
                  <li className="flex items-center gap-3 text-sm">
                    <div className="p-1 rounded-full bg-green-500/10">
                      <Check className="size-3.5 text-green-500" />
                    </div>
                    <span>Instagram, X & YouTube</span>
                  </li>
                  <li className="flex items-center gap-3 text-sm">
                    <div className="p-1 rounded-full bg-green-500/10">
                      <Check className="size-3.5 text-green-500" />
                    </div>
                    <span>Notes & idea saving</span>
                  </li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Error alert for other errors */}
      {error && currentPlan && (
        <Alert variant="destructive" className="rounded-xl">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* All Plans Grid */}
      <div>
        <div className="flex items-center gap-3 mb-5">
          <h3 className="text-lg font-semibold">Available Plans</h3>
          {currentPlan && currentPlan.name !== 'Pro' && (
            <Badge variant="outline" className="text-primary border-primary/30">
              Upgrade available
            </Badge>
          )}
        </div>
        <PlanSelector 
          currentPlanId={currentPlan?.id}
          onPlanSelected={handlePlanSelected}
          onSuccessMessage={handleSuccessMessage}
          showCurrentPlan={true}
          compact={false}
          currentSubscription={currentSubscription}
        />
      </div>
    </div>
  )
}

