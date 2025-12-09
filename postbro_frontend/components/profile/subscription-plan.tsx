"use client"

import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Check, Zap } from "lucide-react"
import Link from "next/link"
import { useEffect, useState } from "react"
import { plansApi, type Subscription } from "@/lib/api"
import { Skeleton } from "@/components/ui/skeleton"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { AlertCircle } from "lucide-react"
import { logger } from "@/lib/logger"

interface SubscriptionPlanProps {
  compact?: boolean
}

export function SubscriptionPlan({ compact }: SubscriptionPlanProps) {
  const [subscription, setSubscription] = useState<Subscription | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchSubscription = async () => {
      try {
        setIsLoading(true)
        setError(null)
        const data = await plansApi.getCurrentSubscription()
        setSubscription(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load subscription')
        logger.error('[SubscriptionPlan] Failed to fetch subscription:', err)
      } finally {
        setIsLoading(false)
      }
    }

    fetchSubscription()
  }, [])

  if (isLoading) {
    return (
      <div className="bg-background rounded-xl border border-border shadow-sm overflow-hidden h-full">
        <div className="p-6 border-b border-border">
          <Skeleton className="h-5 w-32 mb-4" />
          <Skeleton className="h-8 w-24" />
        </div>
        <div className="p-6">
          <Skeleton className="h-4 w-full mb-3" />
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-4 w-full" />
            ))}
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    // Check if it's a 404 (no subscription) vs other error
    const isNoSubscription = error.includes('No active subscription') || error.includes('404')
    
    if (isNoSubscription) {
      return (
        <div className="bg-background rounded-xl border border-border shadow-sm overflow-hidden h-full">
          <div className="p-6">
            <Alert>
              <AlertCircle className="h-4 w-4" />
              <AlertDescription className="space-y-2">
                <p>No active subscription found.</p>
                <Button asChild className="mt-2">
                  <Link href="/#pricing">Choose a Plan</Link>
                </Button>
              </AlertDescription>
            </Alert>
          </div>
        </div>
      )
    }
    
    return (
      <div className="bg-background rounded-xl border border-border shadow-sm overflow-hidden h-full">
        <div className="p-6">
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        </div>
      </div>
    )
  }

  if (!subscription) {
    return (
      <div className="bg-background rounded-xl border border-border shadow-sm overflow-hidden h-full">
        <div className="p-6">
          <Alert>
            <AlertCircle className="h-4 w-4" />
            <AlertDescription className="space-y-2">
              <p>No subscription found.</p>
              <Button asChild className="mt-2">
                <Link href="/#pricing">Choose a Plan</Link>
              </Button>
            </AlertDescription>
          </Alert>
        </div>
      </div>
    )
  }

  const plan = subscription.plan
  // Backend treats both 'active' and 'trial' as valid subscriptions
  const isActive = subscription.status === 'active' || subscription.status === 'trial'
  const isScheduledDowngrade = subscription.status === 'canceling' && subscription.downgrade_to_plan
  const price = parseFloat(plan.price).toFixed(0)

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
    <div className="bg-background rounded-xl border border-border shadow-sm overflow-hidden h-full">
      {/* Scheduled Downgrade Alert */}
      {isScheduledDowngrade && subscription.downgrade_to_plan && (
        <div className="p-3 border-b border-border bg-muted/30">
          <Alert className="py-1.5 px-2">
            <AlertCircle className="h-3 w-3 text-muted-foreground" />
            <AlertDescription className="text-xs text-muted-foreground py-0">
              Downgrading to <strong className="text-foreground">{subscription.downgrade_to_plan.name}</strong> on{' '}
              <strong className="text-foreground">{formatDate(subscription.end_date)}</strong>
            </AlertDescription>
          </Alert>
        </div>
      )}

      <div className="p-6 border-b border-border bg-gradient-to-br from-primary/5 via-transparent to-transparent">
        <div className="flex items-center gap-2 mb-4">
          <div className="p-2 bg-primary/10 rounded-lg text-primary">
            <Zap className="size-4" />
          </div>
          <h2 className="font-semibold">Current Plan</h2>
        </div>

        <div className="space-y-2">
          <div>
            <h3 className="text-2xl font-bold">{plan.name}</h3>
            <div className="flex items-baseline gap-1 mt-1">
              <span className="text-3xl font-bold">${price}</span>
              <span className="text-muted-foreground text-sm">/month</span>
            </div>
          </div>

          {isScheduledDowngrade && subscription.downgrade_to_plan && (
            <Badge variant="outline" className="text-orange-600 dark:text-orange-400 border-orange-300 dark:border-orange-700">
              Downgrading to {subscription.downgrade_to_plan.name}
            </Badge>
          )}

          {!isActive && !isScheduledDowngrade && (
            <Badge variant="outline" className="text-amber-600 dark:text-amber-400 border-amber-300 dark:border-amber-700">
              {subscription.status === 'cancelled' ? 'Cancelled' : subscription.status === 'expired' ? 'Expired' : subscription.status}
            </Badge>
          )}

          {isActive && plan.name !== 'Pro' && (
            <div className="pt-2">
              <Link 
                href="/#pricing" 
                className="text-sm text-primary hover:underline font-medium"
              >
                Upgrade Plan →
              </Link>
            </div>
          )}
          
          {!isActive && (
            <div className="pt-2">
              <Link 
                href="/#pricing" 
                className="text-sm text-primary hover:underline font-medium"
              >
                Choose a Plan →
              </Link>
            </div>
          )}
        </div>
      </div>

      <div className="p-6">
        <p className="text-sm font-medium mb-4">Included in your plan:</p>
        <ul className="space-y-3">
          <li className="flex items-center gap-2 text-sm text-muted-foreground">
            <Check className="size-4 text-green-500 shrink-0" />
            <span>{plan.max_urls} posts per day</span>
          </li>
          <li className="flex items-center gap-2 text-sm text-muted-foreground">
            <Check className="size-4 text-green-500 shrink-0" />
            <span>{plan.max_questions_per_day || 0} chats per day</span>
          </li>
        </ul>
      </div>
    </div>
  )
}
