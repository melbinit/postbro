"use client"

import { useEffect, useState, useCallback, Suspense } from "react"
import { useSearchParams, useRouter } from "next/navigation"
import { useAuth } from "@clerk/nextjs"
import { CheckCircle, Loader2, XCircle, Clock, RefreshCw, AlertCircle, ArrowRight, Sparkles } from "lucide-react"
import { Button } from "@/components/ui/button"
import Link from "next/link"
import { billingApi } from "@/lib/api"

type PaymentStatus = 'initializing' | 'checking' | 'success' | 'pending' | 'failed' | 'error'

function BillingCallbackContent() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const { isLoaded, isSignedIn, getToken } = useAuth()
  
  const [status, setStatus] = useState<PaymentStatus>('initializing')
  const [message, setMessage] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [retryCount, setRetryCount] = useState(0)
  const maxRetries = 5
  const retryDelay = 3000

  const checkoutId = searchParams.get('checkout_id')
  const subscriptionId = searchParams.get('subscription_id')
  const dodoStatus = searchParams.get('status')

  const checkPaymentStatus = useCallback(async () => {
    if (!isLoaded || !isSignedIn) {
      setError('Authentication required. Please sign in to check your payment status.')
      setStatus('error')
      return
    }

    let token: string | null = null
    try {
      token = await getToken()
      if (!token) {
        setError('Unable to get authentication token. Please sign in again.')
        setStatus('error')
        return
      }
    } catch (tokenError) {
      console.error('Error getting token:', tokenError)
      setError('Authentication failed. Please sign in again.')
      setStatus('error')
      return
    }

    if (!checkoutId && !subscriptionId) {
      setError('Missing payment information. Please contact support if this issue persists.')
      setStatus('error')
      return
    }

    setStatus('checking')
    setError(null)

    try {
      const result = await billingApi.checkSubscriptionSuccess({
        checkoutId: checkoutId || undefined,
        subscriptionId: subscriptionId || undefined,
      }, token)

      if (result.success) {
        setStatus('success')
        setMessage(result.message || 'Your subscription has been activated!')
        setTimeout(() => {
          router.push('/app')
        }, 3000)
      } else if (result.pending) {
        setStatus('pending')
        setMessage(result.message || 'Payment is being processed. This may take a few moments...')
      } else if (result.failed) {
        setStatus('failed')
        setMessage(result.message || 'Payment failed. Please try again or contact support if the issue persists.')
      } else {
        setStatus('error')
        setMessage(result.message || 'Unable to verify payment status. Please check your subscription in settings.')
      }
    } catch (error: any) {
      console.error('Error checking payment status:', error)
      
      if (error?.message?.includes('403') || error?.message?.includes('Forbidden')) {
        setError('Authentication failed. Please sign in and try again.')
        setStatus('error')
      } else if (error?.message?.includes('404') || error?.message?.includes('Not Found')) {
        setError('Payment information not found. Please contact support with your checkout ID.')
        setStatus('error')
      } else {
        setError('Unable to verify payment status. Please try again or contact support.')
        setStatus('error')
      }
    }
  }, [checkoutId, subscriptionId, router, isLoaded, isSignedIn, getToken])

  useEffect(() => {
    if (!isLoaded) {
      setStatus('initializing')
      return
    }

    if (!isSignedIn) {
      const returnUrl = `/billing/callback?${searchParams.toString()}`
      router.push(`/login?redirect=${encodeURIComponent(returnUrl)}`)
      return
    }

    if (dodoStatus === 'failed') {
      setStatus('failed')
      setMessage('Payment failed. Please try again or contact support if the issue persists.')
      return
    } else if (dodoStatus === 'active' || dodoStatus === 'succeeded' || dodoStatus === 'success') {
      setStatus('checking')
    } else if (dodoStatus === 'pending') {
      setStatus('pending')
    }

    const verifyAndCheck = async () => {
      try {
        const token = await getToken()
        if (!token) {
          setError('Unable to get authentication token. Please sign in again.')
          setStatus('error')
          return
        }
        
        if (typeof window !== 'undefined') {
          (window as any).__clerkGetToken = getToken
        }
        
        if (dodoStatus === 'failed') {
          return
        }
        
        setTimeout(() => {
          checkPaymentStatus()
        }, 2000)
      } catch (error) {
        console.error('Error getting token:', error)
        setError('Authentication failed. Please sign in again.')
        setStatus('error')
      }
    }

    verifyAndCheck()
  }, [isLoaded, isSignedIn, checkPaymentStatus, router, searchParams, getToken, dodoStatus])

  useEffect(() => {
    if (status === 'pending' && retryCount < maxRetries && isLoaded && isSignedIn) {
      const retryTimer = setTimeout(() => {
        setRetryCount(prev => prev + 1)
        checkPaymentStatus()
      }, retryDelay)

      return () => clearTimeout(retryTimer)
    }
  }, [status, retryCount, checkPaymentStatus, isLoaded, isSignedIn])

  const handleManualRetry = async () => {
    if (!isLoaded || !isSignedIn) {
      router.push('/login')
      return
    }
    
    try {
      const token = await getToken()
      if (!token) {
        setError('Unable to get authentication token. Please sign in again.')
        setStatus('error')
        return
      }
    } catch (error) {
      console.error('Error getting token for retry:', error)
      setError('Authentication failed. Please sign in again.')
      setStatus('error')
      return
    }
    
    setStatus('checking')
    setRetryCount(0)
    setError(null)
    checkPaymentStatus()
  }

  // Render functions for different states
  const getStatusConfig = () => {
    switch (status) {
      case 'initializing':
      case 'checking':
        return {
          icon: <Loader2 className="h-6 w-6 animate-spin text-primary" />,
          iconBg: "bg-primary/10",
          title: status === 'initializing' ? 'Setting things up...' : 'Verifying your payment',
          subtitle: status === 'initializing' 
            ? 'Please wait a moment'
            : 'This should only take a few seconds',
        }
      case 'success':
        return {
          icon: <CheckCircle className="h-6 w-6 text-emerald-500" />,
          iconBg: "bg-emerald-500/10",
          title: "You're all set!",
          subtitle: message,
        }
      case 'pending':
        return {
          icon: <Clock className="h-6 w-6 text-amber-500" />,
          iconBg: "bg-amber-500/10",
          title: 'Processing payment',
          subtitle: message,
        }
      case 'failed':
        return {
          icon: <XCircle className="h-6 w-6 text-rose-500" />,
          iconBg: "bg-rose-500/10",
          title: 'Payment unsuccessful',
          subtitle: message,
        }
      case 'error':
        return {
          icon: <AlertCircle className="h-6 w-6 text-muted-foreground" />,
          iconBg: "bg-muted",
          title: 'Something went wrong',
          subtitle: message || 'Please check your subscription in settings or contact support.',
        }
    }
  }

  const config = getStatusConfig()

  // Show minimal loading while auth initializes
  if (!isLoaded) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-b from-background to-muted/30 p-4">
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-primary/10 mb-4">
            <Loader2 className="h-5 w-5 animate-spin text-primary" />
          </div>
          <p className="text-sm text-muted-foreground">Loading...</p>
        </div>
      </div>
    )
  }

  // Redirect notice
  if (!isSignedIn) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-b from-background to-muted/30 p-4">
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-amber-500/10 mb-4">
            <AlertCircle className="h-5 w-5 text-amber-500" />
          </div>
          <p className="text-sm text-muted-foreground">Redirecting to login...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-b from-background to-muted/30 p-4">
      {/* Decorative background elements */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-primary/5 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-purple-500/5 rounded-full blur-3xl" />
      </div>

      <div className="relative w-full max-w-md">
        {/* Main Card */}
        <div className="bg-card/80 backdrop-blur-sm border border-border/50 rounded-2xl shadow-xl overflow-hidden">
          {/* Header with icon */}
          <div className="px-8 pt-10 pb-6 text-center">
            <div className={`inline-flex items-center justify-center w-14 h-14 rounded-2xl ${config.iconBg} mb-5`}>
              {config.icon}
            </div>
            <h1 className="text-xl font-semibold text-foreground mb-2">
              {config.title}
            </h1>
            <p className="text-sm text-muted-foreground leading-relaxed max-w-xs mx-auto">
              {config.subtitle}
            </p>
          </div>

          {/* Content area */}
          <div className="px-8 pb-8 space-y-4">
            {/* Error message */}
            {error && (
              <div className="p-3.5 bg-rose-50 dark:bg-rose-950/30 border border-rose-200/50 dark:border-rose-800/30 rounded-xl">
                <div className="flex items-start gap-2.5">
                  <AlertCircle className="h-4 w-4 text-rose-500 flex-shrink-0 mt-0.5" />
                  <p className="text-sm text-rose-700 dark:text-rose-300">{error}</p>
                </div>
              </div>
            )}

            {/* Status-specific actions */}
            {(status === 'initializing' || status === 'checking') && (
              <div className="flex items-center justify-center gap-2 py-3">
                <div className="flex gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce [animation-delay:0ms]" />
                  <span className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce [animation-delay:150ms]" />
                  <span className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce [animation-delay:300ms]" />
                </div>
              </div>
            )}

            {status === 'success' && (
              <div className="space-y-3">
                <div className="flex items-center justify-center gap-2 py-2 text-sm text-muted-foreground">
                  <Sparkles className="h-4 w-4 text-primary" />
                  <span>Redirecting to app...</span>
                </div>
                <Button asChild className="w-full h-11 rounded-xl">
                  <Link href="/app">
                    Go to App
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Link>
                </Button>
              </div>
            )}

            {status === 'pending' && (
              <div className="space-y-3">
                <div className="flex items-center justify-center gap-2 py-2">
                  <Loader2 className="h-4 w-4 animate-spin text-amber-500" />
                  <span className="text-sm text-muted-foreground">
                    Checking again... ({retryCount}/{maxRetries})
                  </span>
                </div>
                <Button variant="outline" className="w-full h-11 rounded-xl" onClick={handleManualRetry}>
                  <RefreshCw className="mr-2 h-4 w-4" />
                  Refresh Status
                </Button>
                <Button asChild variant="ghost" className="w-full h-10 rounded-xl text-muted-foreground">
                  <Link href="/app">Continue to App</Link>
                </Button>
              </div>
            )}

            {status === 'failed' && (
              <div className="space-y-3">
                <Button asChild className="w-full h-11 rounded-xl">
                  <Link href="/app?settings=subscription">
                    Try Again
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Link>
                </Button>
                <Button asChild variant="ghost" className="w-full h-10 rounded-xl text-muted-foreground">
                  <Link href="/app">Go to App</Link>
                </Button>
              </div>
            )}

            {status === 'error' && (
              <div className="space-y-3">
                <Button variant="outline" className="w-full h-11 rounded-xl" onClick={handleManualRetry}>
                  <RefreshCw className="mr-2 h-4 w-4" />
                  Try Again
                </Button>
                <Button asChild className="w-full h-11 rounded-xl">
                  <Link href="/app?settings=subscription">
                    Check Subscription
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Link>
                </Button>
              </div>
            )}
          </div>
        </div>

        {/* Help text */}
        <p className="text-center text-xs text-muted-foreground/60 mt-6">
          Having issues?{' '}
          <a href="mailto:support@postbro.app" className="text-primary hover:underline">
            Contact support
          </a>
        </p>
      </div>
    </div>
  )
}

export default function BillingCallbackPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-b from-background to-muted/30 p-4">
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-primary/10 mb-4">
            <Loader2 className="h-5 w-5 animate-spin text-primary" />
          </div>
          <p className="text-sm text-muted-foreground">Loading...</p>
        </div>
      </div>
    }>
      <BillingCallbackContent />
    </Suspense>
  )
}
