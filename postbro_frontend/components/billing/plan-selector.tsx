"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Check, Loader2, AlertCircle } from "lucide-react"
import { plansApi, type Plan } from "@/lib/api"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Skeleton } from "@/components/ui/skeleton"
import { useRouter } from "next/navigation"
import { useAuth, useUser } from "@clerk/nextjs"

interface PlanSelectorProps {
  currentPlanId?: string
  onPlanSelected?: (planId: string) => void
  showCurrentPlan?: boolean
  compact?: boolean
}

export function PlanSelector({ 
  currentPlanId, 
  onPlanSelected,
  showCurrentPlan = true,
  compact = false 
}: PlanSelectorProps) {
  const [plans, setPlans] = useState<Plan[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [subscribingPlanId, setSubscribingPlanId] = useState<string | null>(null)
  const router = useRouter()
  const { isSignedIn, isLoaded, getToken } = useAuth()
  const { user } = useUser()

  useEffect(() => {
    const fetchPlans = async () => {
      try {
        setIsLoading(true)
        setError(null)
        const response = await plansApi.getAllPlans()
        console.log('📋 [PlanSelector] Plans API response:', response)
        console.log('📋 [PlanSelector] First plan data:', response.plans[0])
        const filteredPlans = response.plans.filter(plan => plan.is_active)
        console.log('📋 [PlanSelector] Filtered plans:', filteredPlans)
        filteredPlans.forEach(plan => {
          console.log(`📋 [PlanSelector] Plan ${plan.name}: max_questions_per_day =`, plan.max_questions_per_day)
        })
        setPlans(filteredPlans)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load plans')
        console.error('Failed to fetch plans:', err)
      } finally {
        setIsLoading(false)
      }
    }

    fetchPlans()
  }, [])

  const handleSubscribe = async (plan: Plan) => {
    // Wait for Clerk to load
    if (!isLoaded) {
      console.log('⏳ [PlanSelector] Waiting for Clerk to load...')
      return
    }
    
    // If user is not signed in, redirect to signup
    if (!isSignedIn) {
      console.log('🔒 [PlanSelector] User not signed in, redirecting to signup')
      router.push(`/signup?plan=${plan.id}`)
      return
    }
    
    console.log('✅ [PlanSelector] User is signed in, proceeding with subscription')
    
    // Get token before making API call
    let authToken: string | null = null
    try {
      authToken = await getToken()
      if (!authToken) {
        console.warn('⚠️ [PlanSelector] No token available, redirecting to login')
        router.push(`/login?redirect=/&plan=${plan.id}`)
        return
      }
      console.log('✅ [PlanSelector] Token available, length:', authToken.length)
    } catch (tokenError) {
      console.error('❌ [PlanSelector] Failed to get token:', tokenError)
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
        console.error('Failed to subscribe:', err)
        alert(err instanceof Error ? err.message : 'Failed to subscribe to plan')
      } finally {
        setSubscribingPlanId(null)
      }
      return
    }

    // For paid plans, create checkout session
    try {
      setSubscribingPlanId(plan.id)
      const response = await plansApi.subscribeToPlan(plan.id, authToken)
      
      // Check if we got a checkout URL (paid plan)
      if (response.checkout_url) {
        // Redirect to Dodo checkout
        window.location.href = response.checkout_url
      } else if (response.subscription) {
        // Free plan or already subscribed
        if (onPlanSelected) {
          onPlanSelected(plan.id)
        } else {
          window.location.reload()
        }
      }
    } catch (err: any) {
      console.error('Failed to create subscription:', err)
      
      // Handle authentication errors - redirect to login
      if (err?.status === 401 || err?.status === 403) {
        console.log('🔒 [PlanSelector] Authentication required, redirecting to login')
        router.push(`/login?redirect=/&plan=${plan.id}`)
        return
      }
      
      const errorMessage = err?.data?.message || err?.data?.detail || err?.message || 'Failed to create subscription'
      alert(errorMessage)
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

  return (
    <div className={`grid grid-cols-1 ${compact ? 'md:grid-cols-2' : 'md:grid-cols-3'} gap-6`}>
      {sortedPlans.map((plan) => {
        const isCurrentPlan = currentPlanId === plan.id
        const isSubscribing = subscribingPlanId === plan.id
        const price = parseFloat(plan.price)
        const isFree = price === 0
        const isPopular = plan.name === 'Starter' || plan.name === 'Basic' // Adjust based on your plans

        return (
          <div
            key={plan.id}
            className={`relative bg-background rounded-xl border ${
              isPopular ? 'border-primary shadow-lg shadow-primary/10' : 'border-border'
            } p-6 flex flex-col transition-all duration-300 hover:shadow-md ${
              isCurrentPlan ? 'ring-2 ring-primary' : ''
            }`}
          >
            {isPopular && (
              <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-primary text-primary-foreground text-xs font-medium px-3 py-1 rounded-full shadow-sm">
                Most Popular
              </div>
            )}

            {isCurrentPlan && showCurrentPlan && (
              <div className="absolute -top-3 right-4">
                <Badge variant="default" className="text-xs">
                  Current Plan
                </Badge>
              </div>
            )}

            <div className="mb-6">
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
                <span>{plan.max_urls} post analysis per day</span>
              </div>
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Check className="size-4 text-green-500 shrink-0" />
                <span>
                  {(() => {
                    const chatCount = plan.max_questions_per_day ?? 0;
                    if (chatCount === 0 || chatCount === undefined || chatCount === null) {
                      console.warn(`⚠️ [PlanSelector] Plan ${plan.name} has invalid max_questions_per_day:`, plan.max_questions_per_day, 'Full plan object:', plan);
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
              disabled={isSubscribing || isCurrentPlan}
            >
              {isSubscribing ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Processing...
                </>
              ) : isCurrentPlan ? (
                'Current Plan'
              ) : isFree ? (
                'Get Started Free'
              ) : (
                `Subscribe to ${plan.name}`
              )}
            </Button>
          </div>
        )
      })}
    </div>
  )
}

