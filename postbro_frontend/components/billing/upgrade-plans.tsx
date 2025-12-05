"use client"

import { useState, useEffect } from "react"
import { PlanSelector } from "./plan-selector"
import { plansApi, type Subscription } from "@/lib/api"
import { Skeleton } from "@/components/ui/skeleton"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { AlertCircle } from "lucide-react"

export function UpgradePlans() {
  const [currentSubscription, setCurrentSubscription] = useState<Subscription | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

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
      setCurrentSubscription(data)
    } catch (err) {
      // Ignore errors, subscription might not exist yet
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-64 w-full" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {currentSubscription && (
        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            You are currently on the <strong>{currentSubscription.plan.name}</strong> plan.
            {currentSubscription.status === 'trial' && ' Your subscription will be activated after payment.'}
          </AlertDescription>
        </Alert>
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
          showCurrentPlan={true}
          compact={false}
        />
      </div>
    </div>
  )
}

