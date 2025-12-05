"use client"

import { useEffect, useState } from "react"
import { billingApi, type Subscription } from "@/lib/api"
import { Skeleton } from "@/components/ui/skeleton"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { AlertCircle, Calendar, CheckCircle2, XCircle, Clock } from "lucide-react"
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
      <div className="bg-background rounded-xl border border-border shadow-sm overflow-hidden">
        <div className="p-6 border-b border-border">
          <Skeleton className="h-6 w-48 mb-2" />
          <Skeleton className="h-4 w-64" />
        </div>
        <div className="p-6 space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="space-y-2">
              <Skeleton className="h-20 w-full" />
            </div>
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-background rounded-xl border border-border shadow-sm overflow-hidden">
        <div className="p-6">
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        </div>
      </div>
    )
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'active':
      case 'trial':
        return <CheckCircle2 className="size-4 text-green-600 dark:text-green-400" />
      case 'cancelled':
      case 'expired':
        return <XCircle className="size-4 text-red-600 dark:text-red-400" />
      default:
        return <Clock className="size-4 text-amber-600 dark:text-amber-400" />
    }
  }

  const getStatusBadgeVariant = (status: string) => {
    switch (status) {
      case 'active':
      case 'trial':
        return 'default'
      case 'cancelled':
        return 'destructive'
      case 'expired':
        return 'secondary'
      default:
        return 'outline'
    }
  }

  return (
    <div className="bg-background rounded-xl border border-border shadow-sm overflow-hidden">
      <div className="p-6 border-b border-border">
        <h2 className="text-xl font-semibold mb-2">Billing History</h2>
        <p className="text-sm text-muted-foreground">
          View your subscription history and payment records
        </p>
      </div>

      <div className="p-6">
        {subscriptions.length === 0 ? (
          <div className="text-center py-12">
            <AlertCircle className="size-12 text-muted-foreground mx-auto mb-4 opacity-50" />
            <p className="text-muted-foreground">No subscription history found</p>
          </div>
        ) : (
          <div className="space-y-4">
            {subscriptions.map((subscription) => (
              <div
                key={subscription.id}
                className="border border-border rounded-lg p-4 hover:bg-muted/30 transition-colors"
              >
                <div className="flex flex-col gap-4">
                  <div className="flex-1 space-y-2">
                    <div className="flex items-center gap-3">
                      {getStatusIcon(subscription.status)}
                      <h3 className="font-semibold text-lg">{subscription.plan.name}</h3>
                      <Badge variant={getStatusBadgeVariant(subscription.status)}>
                        {subscription.status === 'trial' ? 'Trial' : subscription.status}
                      </Badge>
                    </div>
                    <div className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
                      <div className="flex items-center gap-2">
                        <Calendar className="size-4" />
                        <span>
                          Started: {format(new Date(subscription.start_date), 'MMM dd, yyyy')}
                        </span>
                      </div>
                      {subscription.end_date && (
                        <div className="flex items-center gap-2">
                          <Calendar className="size-4" />
                          <span>
                            Ended: {format(new Date(subscription.end_date), 'MMM dd, yyyy')}
                          </span>
                        </div>
                      )}
                    </div>
                    <div className="flex items-center gap-2 text-sm">
                      <span className="text-muted-foreground">Price:</span>
                      <span className="font-semibold">${subscription.plan.price}/month</span>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

