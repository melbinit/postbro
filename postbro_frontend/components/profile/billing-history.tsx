"use client"

import { useEffect, useState } from "react"
import { billingApi, type Subscription } from "@/lib/api"
import { Skeleton } from "@/components/ui/skeleton"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { AlertCircle, Calendar, CheckCircle2, XCircle, Clock, Receipt, CreditCard } from "lucide-react"
import { format } from "date-fns"
import { Badge } from "@/components/ui/badge"

export function BillingHistory() {
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        setIsLoading(true)
        setError(null)
        const data = await billingApi.getSubscriptionHistory()
        setSubscriptions(data.subscriptions)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load billing history')
        console.error('Failed to fetch subscription history:', err)
      } finally {
        setIsLoading(false)
      }
    }

    fetchHistory()
  }, [])

  if (isLoading) {
    return (
      <div className="bg-card rounded-2xl border border-border/50 overflow-hidden">
        <div className="p-6 border-b border-border/50 bg-gradient-to-r from-primary/5 via-transparent to-transparent">
          <Skeleton className="h-6 w-48 mb-2" />
          <Skeleton className="h-4 w-64" />
        </div>
        <div className="p-6 space-y-4">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-24 w-full rounded-xl" />
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-card rounded-2xl border border-border/50 overflow-hidden">
        <div className="p-6">
          <Alert variant="destructive" className="rounded-xl">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        </div>
      </div>
    )
  }

  const getStatusConfig = (status: string) => {
    switch (status) {
      case 'active':
        return { 
          icon: CheckCircle2, 
          color: 'text-green-500',
          bg: 'bg-green-500/10',
          badge: 'bg-green-500/10 text-green-600 dark:text-green-400 border-green-500/20'
        }
      case 'trial':
        return { 
          icon: Clock, 
          color: 'text-amber-500',
          bg: 'bg-amber-500/10',
          badge: 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20'
        }
      case 'cancelled':
        return { 
          icon: XCircle, 
          color: 'text-red-500',
          bg: 'bg-red-500/10',
          badge: 'bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/20'
        }
      case 'expired':
        return { 
          icon: XCircle, 
          color: 'text-muted-foreground',
          bg: 'bg-muted',
          badge: 'bg-muted text-muted-foreground border-border'
        }
      default:
        return { 
          icon: Clock, 
          color: 'text-muted-foreground',
          bg: 'bg-muted',
          badge: 'bg-muted text-muted-foreground border-border'
        }
    }
  }

  return (
    <div className="bg-card rounded-2xl border border-border/50 overflow-hidden">
      {/* Header */}
      <div className="p-6 border-b border-border/50 bg-gradient-to-r from-primary/5 via-transparent to-transparent">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-primary/10">
            <Receipt className="size-5 text-primary" />
          </div>
          <div>
            <h2 className="text-lg font-semibold">Billing History</h2>
            <p className="text-sm text-muted-foreground">
              View your subscription history and payment records
            </p>
          </div>
        </div>
      </div>

      <div className="p-6">
        {subscriptions.length === 0 ? (
          <div className="text-center py-16">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-muted/50 mb-5">
              <CreditCard className="size-7 text-muted-foreground" />
            </div>
            <p className="text-base font-medium mb-1">No billing history</p>
            <p className="text-sm text-muted-foreground">Your subscription history will appear here</p>
          </div>
        ) : (
          <div className="space-y-3">
            {subscriptions.map((subscription, index) => {
              const statusConfig = getStatusConfig(subscription.status)
              const StatusIcon = statusConfig.icon
              const isFirst = index === 0
              
              return (
                <div
                  key={subscription.id}
                  className={`relative rounded-xl p-5 transition-all duration-200 border ${
                    isFirst 
                      ? 'bg-gradient-to-r from-primary/5 via-transparent to-transparent border-primary/20' 
                      : 'border-border/50 hover:bg-muted/30 hover:border-border/70'
                  }`}
                >
                  {/* Current indicator */}
                  {isFirst && subscription.status === 'active' && (
                    <div className="absolute -left-px top-4 bottom-4 w-1 bg-gradient-to-b from-primary to-primary/50 rounded-full" />
                  )}
                  
                  <div className="flex flex-col sm:flex-row sm:items-center gap-4">
                    {/* Plan info */}
                    <div className="flex items-center gap-3 flex-1">
                      <div className={`p-2 rounded-lg ${statusConfig.bg}`}>
                        <StatusIcon className={`size-4 ${statusConfig.color}`} />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <h3 className="font-semibold">{subscription.plan.name}</h3>
                          <Badge className={statusConfig.badge}>
                            {subscription.status === 'trial' ? 'Trial' : subscription.status}
                          </Badge>
                        </div>
                        <div className="flex items-center gap-3 text-xs text-muted-foreground mt-1">
                          <span className="flex items-center gap-1">
                            <Calendar className="size-3" />
                            {format(new Date(subscription.start_date), 'MMM dd, yyyy')}
                          </span>
                          {subscription.end_date && (
                            <>
                              <span>→</span>
                              <span>{format(new Date(subscription.end_date), 'MMM dd, yyyy')}</span>
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                    
                    {/* Price */}
                    <div className="text-right">
                      <span className="text-lg font-bold">${subscription.plan.price}</span>
                      <span className="text-sm text-muted-foreground">/mo</span>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

