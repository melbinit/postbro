"use client"

import { useState, useEffect } from "react"
import { PlanSelector } from "./plan-selector"
import { plansApi, type Subscription } from "@/lib/api"
import { Skeleton } from "@/components/ui/skeleton"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { AlertCircle } from "lucide-react"
import { useToast } from "@/hooks/use-toast"
import { logger } from "@/lib/logger"

export function UpgradePlans() {
  const [currentSubscription, setCurrentSubscription] = useState<Subscription | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const { toast } = useToast()

  useEffect(() => {
    const fetchSubscription = async () => {
      try {
        setIsLoading(true)
        setError(null)
        const data = await plansApi.getCurrentSubscription()
        setCurrentSubscription(data)
      } catch (err: any) {
        // 404 or null response is expected if no subscription exists
        if (err?.status === 404 || !err) {
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
      setCurrentSubscription(data)
    } catch (err) {
      logger.error('[UpgradePlans] Failed to refresh subscription:', err)
      // Ignore errors, subscription might not exist yet
    }
  }

  const handleSuccessMessage = (message: string) => {
    // Show success message via toast
    toast({
      title: "Success",
      description: message,
    })
  }

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-64 w-full" />
      </div>
    )
  }

  // Format date for display
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

  const isScheduledDowngrade = currentSubscription?.status === 'canceling' && currentSubscription?.downgrade_to_plan

  return (
    <div className="space-y-6">
      {currentSubscription && (
        <>
          {isScheduledDowngrade ? (
            <Alert>
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                You are currently on the <strong>{currentSubscription.plan.name}</strong> plan.
                {' '}Your plan will be downgraded to <strong>{currentSubscription.downgrade_to_plan.name}</strong> on{' '}
                <strong>{formatDate(currentSubscription.end_date)}</strong>.
                {' '}You will continue to have access to {currentSubscription.plan.name} features until then.
              </AlertDescription>
            </Alert>
          ) : (
            <Alert>
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                You are currently on the <strong>{currentSubscription.plan.name}</strong> plan.
                {currentSubscription.status === 'trial' && ' Your subscription will be activated after payment.'}
                {currentSubscription.status === 'pending' && ' Your subscription is pending payment confirmation.'}
                {currentSubscription.status === 'failed' && ' Your last payment failed. Please update your payment method.'}
              </AlertDescription>
            </Alert>
          )}
        </>
      )}

      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div>
        <h3 className="text-lg font-semibold mb-4">Available Plans</h3>
        <PlanSelector 
          currentPlanId={currentSubscription?.plan.id}
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

