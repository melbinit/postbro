"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Check, Loader2, AlertCircle } from "lucide-react"
import { plansApi, type Plan, type Subscription } from "@/lib/api"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Skeleton } from "@/components/ui/skeleton"
import { useRouter } from "next/navigation"
import { useAuth, useUser } from "@clerk/nextjs"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { useToast } from "@/hooks/use-toast"
import { logger } from "@/lib/logger"

interface PlanSelectorProps {
  currentPlanId?: string
  onPlanSelected?: (planId: string) => void
  onSuccessMessage?: (message: string) => void
  showCurrentPlan?: boolean
  compact?: boolean
  currentSubscription?: Subscription | null
}

export function PlanSelector({ 
  currentPlanId, 
  onPlanSelected,
  onSuccessMessage,
  showCurrentPlan = true,
  compact = false,
  currentSubscription
}: PlanSelectorProps) {
  const [plans, setPlans] = useState<Plan[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [subscribingPlanId, setSubscribingPlanId] = useState<string | null>(null)
  const [showDowngradeDialog, setShowDowngradeDialog] = useState(false)
  const [pendingPlan, setPendingPlan] = useState<Plan | null>(null)
  const router = useRouter()
  const { isSignedIn, isLoaded, getToken } = useAuth()
  const { user } = useUser()
  const { toast } = useToast()

  useEffect(() => {
    const fetchPlans = async () => {
      try {
        setIsLoading(true)
        setError(null)
        const response = await plansApi.getAllPlans()
        const filteredPlans = response.plans.filter(plan => plan.is_active)
        setPlans(filteredPlans)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load plans')
        logger.error('[PlanSelector] Failed to fetch plans:', err)
      } finally {
        setIsLoading(false)
      }
    }

    fetchPlans()
  }, [])

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

  const handleSubscribe = async (plan: Plan) => {
    // Wait for Clerk to load
    if (!isLoaded) {
      return
    }
    
    // If user is not signed in, redirect to signup
    if (!isSignedIn) {
      router.push(`/signup?plan=${plan.id}`)
      return
    }
    
    // Check if this is a downgrade - show confirmation dialog
    if (currentSubscription && currentSubscription.plan && parseFloat(plan.price) < parseFloat(currentSubscription.plan.price)) {
      setPendingPlan(plan)
      setShowDowngradeDialog(true)
        return
    }
    
    // Proceed with subscription (upgrade or new)
    await proceedWithSubscription(plan)
  }

  const proceedWithSubscription = async (plan: Plan) => {
    // Get token before making API call
    let authToken: string | null = null
    try {
      authToken = await getToken()
      if (!authToken) {
        logger.warn('[PlanSelector] No token available, redirecting to login')
        router.push(`/login?redirect=/&plan=${plan.id}`)
        return
      }
    } catch (tokenError) {
      logger.error('[PlanSelector] Failed to get token:', tokenError)
      router.push(`/login?redirect=/&plan=${plan.id}`)
      return
    }

    // If it's the free plan, subscribe directly
    if (parseFloat(plan.price) === 0) {
      try {
        setSubscribingPlanId(plan.id)
        const response = await plansApi.subscribeToPlan(plan.id, authToken)
        
        if (onPlanSelected) {
          onPlanSelected(plan.id)
        } else {
          // Refresh the page or show success message
          window.location.reload()
        }
      } catch (err) {
        logger.error('[PlanSelector] Failed to subscribe:', err)
        toast({
          variant: "destructive",
          title: "Subscription Failed",
          description: err instanceof Error ? err.message : 'Failed to subscribe to plan',
        })
      } finally {
        setSubscribingPlanId(null)
      }
      return
    }

    // For paid plans, create checkout session
    try {
      setSubscribingPlanId(plan.id)
      const response = await plansApi.subscribeToPlan(plan.id, authToken)
      
      // Check if we got a checkout URL (paid plan - upgrade or new subscription)
      if (response.checkout_url) {
        logger.debug('[PlanSelector] Redirecting to checkout')
        // Redirect to Dodo checkout
        window.location.href = response.checkout_url
        // Don't reset subscribingPlanId here - let redirect happen
        return
      } 
      
      // Handle downgrade response (has downgrade flag)
      if (response.downgrade && response.subscription) {
        logger.debug('[PlanSelector] Downgrade scheduled')
        
        // Show success message via toast
        const message = response.message || 'Downgrade scheduled successfully'
        toast({
          title: "Downgrade Scheduled",
          description: message,
        })
        
        // Also call callback if provided
        if (onSuccessMessage) {
          onSuccessMessage(message)
        }
        
        // Refresh subscription if callback exists
        if (onPlanSelected) {
          await onPlanSelected(plan.id)  // Make it async and await
        } else {
          window.location.reload()
        }
        setSubscribingPlanId(null) // Reset loading state
        return
      }
      
      // Handle subscription response (free plan or already subscribed)
      if (response.subscription) {
        if (onPlanSelected) {
          onPlanSelected(plan.id)
        } else {
          window.location.reload()
        }
        setSubscribingPlanId(null) // Reset loading state
        return
      }
      
      // No valid response - show error
      logger.error('[PlanSelector] Invalid response:', response)
      toast({
        variant: "destructive",
        title: "Subscription Failed",
        description: response.message || 'Failed to process subscription. Please try again.',
      })
      setSubscribingPlanId(null)
      
    } catch (err: any) {
      logger.error('[PlanSelector] Failed to create subscription:', err)
      
      // Handle authentication errors - redirect to login
      if (err?.status === 401 || err?.status === 403) {
        router.push(`/login?redirect=/&plan=${plan.id}`)
        setSubscribingPlanId(null)
        return
      }
      
      const errorMessage = err?.data?.message || err?.data?.detail || err?.message || 'Failed to create subscription'
      toast({
        variant: "destructive",
        title: "Subscription Failed",
        description: errorMessage,
      })
      setSubscribingPlanId(null)
    }
  }

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {[1, 2, 3].map((i) => (
          <div key={i} className="bg-background rounded-xl border border-border p-6">
            <Skeleton className="h-8 w-24 mb-4" />
            <Skeleton className="h-12 w-32 mb-4" />
            <Skeleton className="h-4 w-full mb-2" />
            <Skeleton className="h-4 w-full mb-2" />
            <Skeleton className="h-10 w-full mt-6" />
          </div>
        ))}
      </div>
    )
  }

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    )
  }

  if (plans.length === 0) {
    return (
      <Alert>
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>No plans available at the moment.</AlertDescription>
      </Alert>
    )
  }

  // Sort plans by price
  const sortedPlans = [...plans].sort((a, b) => parseFloat(a.price) - parseFloat(b.price))

  // Calculate downgrade dialog content
  const downgradeDialogContent = pendingPlan && currentSubscription ? {
    currentPlan: currentSubscription.plan.name,
    newPlan: pendingPlan.name,
    endDate: currentSubscription.end_date 
      ? formatDate(currentSubscription.end_date)
      : 'the end of your billing period'
  } : null

  return (
    <>
      {/* Downgrade Confirmation Dialog */}
      <AlertDialog open={showDowngradeDialog} onOpenChange={setShowDowngradeDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Confirm Downgrade</AlertDialogTitle>
            <AlertDialogDescription>
              {downgradeDialogContent && (
                <>
                  This will schedule a downgrade from <strong>{downgradeDialogContent.currentPlan}</strong> to <strong>{downgradeDialogContent.newPlan}</strong>.
                  <br /><br />
                  You will be switched to {downgradeDialogContent.newPlan} on {downgradeDialogContent.endDate}.
                  <br /><br />
                  You will continue to have access to {downgradeDialogContent.currentPlan} features until then.
                </>
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => {
              setShowDowngradeDialog(false)
              setPendingPlan(null)
            }}>
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction onClick={async () => {
              setShowDowngradeDialog(false)
              if (pendingPlan) {
                await proceedWithSubscription(pendingPlan)
                setPendingPlan(null)
              }
            }}>
              Confirm Downgrade
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

    <div className={`grid grid-cols-1 ${compact ? 'md:grid-cols-2' : 'md:grid-cols-3'} gap-6`}>
      {sortedPlans.map((plan) => {
        const isCurrentPlan = currentPlanId === plan.id
        const isSubscribing = subscribingPlanId === plan.id
        const price = parseFloat(plan.price)
        const isFree = price === 0
        const isPopular = plan.name === 'Starter' || plan.name === 'Basic' // Adjust based on your plans
        const isScheduledDowngradeTarget = currentSubscription?.status === 'canceling' && 
          currentSubscription?.downgrade_to_plan?.id === plan.id
        const isDowngradeOption = currentSubscription && 
          currentSubscription.plan && 
          price < parseFloat(currentSubscription.plan.price)

        return (
          <div
            key={plan.id}
            className={`relative bg-card rounded-2xl border ${
              isPopular ? 'border-primary/50 shadow-xl shadow-primary/10' : 'border-border/60'
            } p-6 flex flex-col transition-all duration-300 hover:shadow-lg hover:-translate-y-0.5 ${
              isCurrentPlan ? 'ring-2 ring-primary ring-offset-2 ring-offset-background' : ''
            }`}
          >
            {/* Badges */}
            <div className="absolute -top-3 left-1/2 -translate-x-1/2 flex gap-2 z-10">
              {isPopular && (
                <div className="bg-primary text-primary-foreground text-xs font-medium px-3 py-1 rounded-full shadow-sm">
                  Most Popular
                </div>
              )}
            </div>

            <div className={`mb-6 ${isPopular ? 'pt-2' : ''}`}>
              <h3 className="text-xl font-bold mb-2">{plan.name}</h3>
              <div className="flex items-baseline gap-1">
                <span className="text-4xl font-bold">
                  ${price === 0 ? '0' : price.toFixed(0)}
                </span>
                <span className="text-muted-foreground text-sm">/month</span>
              </div>
              {plan.description && (
                <p className="text-muted-foreground mt-2 text-sm">{plan.description}</p>
              )}
            </div>

            <div className="flex-1 space-y-3 mb-6">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Check className="size-4 text-green-500 shrink-0" />
                <span>
                  {plan.name === 'Free' && 'Basic post analysis'}
                  {plan.name === 'Starter' && 'Detailed post analysis'}
                  {plan.name === 'Pro' && 'In-depth post analysis'}
                  {!['Free', 'Starter', 'Pro'].includes(plan.name) && 'Post analysis'}
                </span>
              </div>
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Check className="size-4 text-green-500 shrink-0" />
                <span>{plan.max_urls} posts per day</span>
              </div>
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Check className="size-4 text-green-500 shrink-0" />
                <span>
                  {(() => {
                    const chatCount = plan.max_questions_per_day ?? 0;
                    if (chatCount === 0 || chatCount === undefined || chatCount === null) {
                      logger.warn(`[PlanSelector] Plan ${plan.name} has invalid max_questions_per_day:`, plan.max_questions_per_day);
                    }
                    return `${chatCount} chats per day`;
                  })()}
                </span>
              </div>
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Check className="size-4 text-green-500 shrink-0" />
                <span>Instagram, X & YouTube support</span>
              </div>
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Check className="size-4 text-green-500 shrink-0" />
                <span>Notes & idea saving</span>
              </div>
            </div>

            <Button
              variant={isPopular ? "default" : "outline"}
              className={`w-full ${isPopular ? "bg-primary hover:bg-primary/90" : ""}`}
              onClick={() => handleSubscribe(plan)}
              disabled={isSubscribing || isCurrentPlan || isScheduledDowngradeTarget}
            >
              {isSubscribing ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Processing...
                </>
              ) : isCurrentPlan ? (
                'Current Plan'
              ) : isScheduledDowngradeTarget ? (
                'Downgrading To'
              ) : isFree ? (
                'Get Started Free'
              ) : isDowngradeOption ? (
                `Downgrade to ${plan.name}`
              ) : (
                `Subscribe to ${plan.name}`
              )}
            </Button>
          </div>
        )
      })}
    </div>
    </>
  )
}

