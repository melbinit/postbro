"use client"

import { Progress } from "@/components/ui/progress"
import { useEffect, useState } from "react"
import { usageApi, type UsageStats as UsageStatsType } from "@/lib/api"
import { Skeleton } from "@/components/ui/skeleton"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { AlertCircle, BarChart3, CreditCard, Sparkles } from "lucide-react"
import { DateRange } from "react-day-picker"
import { format } from "date-fns"
import { DateRangePicker } from "@/components/ui/date-range-picker"
import { Button } from "@/components/ui/button"
import { logger } from "@/lib/logger"

interface UsageStatsProps {
  compact?: boolean
  onNavigateToSubscription?: () => void
}

interface AggregatedUsage {
  url_lookups: { used: number; limit: number; remaining: number }
  questions_asked: { used: number; limit: number; remaining: number }
}

export function UsageStats({ compact, onNavigateToSubscription }: UsageStatsProps) {
  const [usage, setUsage] = useState<UsageStatsType | null>(null)
  const [aggregatedUsage, setAggregatedUsage] = useState<AggregatedUsage | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [dateRange, setDateRange] = useState<DateRange | undefined>(undefined)
  const [isToday, setIsToday] = useState(true)
  const [isMounted, setIsMounted] = useState(false)
  const [shouldFetch, setShouldFetch] = useState(false)

  // Initialize date range on client only to avoid hydration mismatch
  useEffect(() => {
    setIsMounted(true)
    const today = new Date()
    setDateRange({
      from: today,
      to: today,
    })
    setShouldFetch(true) // Auto-fetch on initial load
  }, [])

  const handleFetch = async () => {
    if (!dateRange?.from || !dateRange?.to) {
      return
    }

    try {
      setIsLoading(true)
      setError(null)

      // Check if BOTH dates are today
      const today = new Date()
      today.setHours(0, 0, 0, 0)
      const fromDate = new Date(dateRange.from)
      const toDate = new Date(dateRange.to)
      fromDate.setHours(0, 0, 0, 0)
      toDate.setHours(0, 0, 0, 0)
      
      const bothDatesToday = 
        fromDate.getTime() === today.getTime() &&
        toDate.getTime() === today.getTime()
      
      setIsToday(bothDatesToday)

      if (bothDatesToday) {
        // Fetch today's usage stats (shows remaining counts)
        const data = await usageApi.getUsageStats()
        
        // Handle case where API returns platforms object instead of flat structure
        if (data.usage && 'platforms' in data.usage && !('url_lookups' in data.usage)) {
          // Aggregate across all platforms
          const platforms = (data.usage as any).platforms || {}
          let totalUrlLookups = 0
          
          Object.values(platforms).forEach((platformUsage: any) => {
            totalUrlLookups += platformUsage.url_lookups || 0
          })
          
          // Transform to expected format - only posts and chats
          const normalizedData = {
            ...data,
            usage: {
              platform: 'all',
              date: data.usage.date || new Date().toISOString().split('T')[0],
              url_lookups: {
                used: totalUrlLookups,
                limit: data.plan?.max_urls || 0,
                remaining: Math.max(0, (data.plan?.max_urls || 0) - totalUrlLookups)
              },
              questions_asked: data.usage.questions_asked || {
                used: 0,
                limit: data.plan?.max_questions_per_day || 0,
                remaining: data.plan?.max_questions_per_day || 0
              }
            }
          }
          setUsage(normalizedData)
        } else if (data.usage && (data.usage.url_lookups || data.usage.questions_asked)) {
          // Already in the correct format, ensure questions_asked is included
          const normalizedData = {
            ...data,
            usage: {
              ...data.usage,
              questions_asked: data.usage.questions_asked || {
                used: 0,
                limit: data.plan?.max_questions_per_day || 0,
                remaining: data.plan?.max_questions_per_day || 0
              }
            }
          }
          setUsage(normalizedData)
        } else {
          // Fallback: create default structure with plan limits
          const normalizedData = {
            ...data,
            usage: {
              platform: 'all',
              date: data.usage?.date || new Date().toISOString().split('T')[0],
              url_lookups: {
                used: 0,
                limit: data.plan?.max_urls || 0,
                remaining: data.plan?.max_urls || 0
              },
              questions_asked: {
                used: 0,
                limit: data.plan?.max_questions_per_day || 0,
                remaining: data.plan?.max_questions_per_day || 0
              }
            }
          }
          setUsage(normalizedData)
        }
        setAggregatedUsage(null)
      } else {
        // Fetch usage history for date range (no remaining counts)
        const startDate = format(dateRange.from, 'yyyy-MM-dd')
        const endDate = format(dateRange.to, 'yyyy-MM-dd')
        const history = await usageApi.getUsageHistory(startDate, endDate)
        
        // Aggregate the data - only track usage, no limits for date ranges
        const aggregated: AggregatedUsage = {
          url_lookups: { used: 0, limit: 0, remaining: 0 },
          questions_asked: { used: 0, limit: 0, remaining: 0 },
        }

        // Get plan info for display
        const currentUsage = await usageApi.getUsageStats()
        setUsage(currentUsage)

        // Aggregate usage across all days in range
        if (history.usage_history.length > 0) {
          // Group by date to handle questions_asked properly (user-level, not platform-specific)
          const usageByDate = new Map<string, { url_lookups: number; questions_asked: number }>()
          
          history.usage_history.forEach((entry) => {
            const dateKey = entry.date
            
            if (!usageByDate.has(dateKey)) {
              usageByDate.set(dateKey, { url_lookups: 0, questions_asked: 0 })
            }
            
            const dayUsage = usageByDate.get(dateKey)!
            dayUsage.url_lookups += entry.url_lookups
            // For questions, take max per day since it's user-level (all platforms have same value)
            dayUsage.questions_asked = Math.max(dayUsage.questions_asked, entry.questions_asked || 0)
          })
          
          // Sum across all days
          usageByDate.forEach((dayUsage) => {
            aggregated.url_lookups.used += dayUsage.url_lookups
            aggregated.questions_asked.used += dayUsage.questions_asked
          })
        }

        setAggregatedUsage(aggregated)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load usage statistics')
      logger.error('[UsageStats] Failed to fetch usage stats:', err)
    } finally {
      setIsLoading(false)
      setShouldFetch(false)
    }
  }

  useEffect(() => {
    if (!isMounted || !shouldFetch) {
      return
    }
    handleFetch()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [shouldFetch, isMounted])

  // Don't render anything until mounted to avoid hydration mismatch
  if (!isMounted) {
    return (
      <div className="bg-background rounded-xl border border-border shadow-sm overflow-hidden h-full">
        <div className="p-6 border-b border-border">
          <Skeleton className="h-5 w-32 mb-2" />
          <Skeleton className="h-4 w-48" />
        </div>
        <div className="p-6 space-y-6">
          {[1, 2].map((i) => (
            <div key={i} className="space-y-2">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-2 w-full" />
            </div>
          ))}
        </div>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="bg-background rounded-xl border border-border shadow-sm overflow-hidden h-full">
        <div className="p-6 border-b border-border">
          <Skeleton className="h-5 w-32 mb-2" />
          <Skeleton className="h-4 w-48" />
        </div>
        <div className="p-6 space-y-6">
          {[1, 2].map((i) => (
            <div key={i} className="space-y-2">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-2 w-full" />
            </div>
          ))}
        </div>
      </div>
    )
  }

  if (error) {
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

  if (!usage) {
    return (
      <div className="bg-background rounded-xl border border-border shadow-sm overflow-hidden h-full">
        <div className="p-6">
          <Alert>
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>No usage data available</AlertDescription>
          </Alert>
        </div>
      </div>
    )
  }

  // Use aggregated usage for date ranges, or today's usage
  const displayUsage = isToday && usage.usage 
    ? usage.usage 
    : aggregatedUsage && dateRange?.from
    ? {
        url_lookups: aggregatedUsage.url_lookups,
        questions_asked: aggregatedUsage.questions_asked,
        date: dateRange?.from && dateRange?.to
          ? `${format(dateRange.from, 'MMM dd, yyyy')} - ${format(dateRange.to, 'MMM dd, yyyy')}`
          : format(dateRange.from, 'MMM dd, yyyy'),
      }
    : null

  if (!displayUsage) {
    return (
      <div className="bg-background rounded-xl border border-border shadow-sm overflow-hidden h-full">
        <div className="p-6">
          <Alert>
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>No usage data available</AlertDescription>
          </Alert>
        </div>
      </div>
    )
  }

  const postsPerDay = displayUsage.url_lookups || { used: 0, limit: 0, remaining: 0 }
  const chatsPerDay = displayUsage.questions_asked || { used: 0, limit: 0, remaining: 0 }

  // Only show progress bars and percentages for today
  const postsPercent = isToday && postsPerDay.limit > 0 ? (postsPerDay.used / postsPerDay.limit) * 100 : 0
  const chatsPercent = isToday && chatsPerDay.limit > 0 ? (chatsPerDay.used / chatsPerDay.limit) * 100 : 0

  return (
    <div className="bg-card rounded-2xl border border-border/50 overflow-hidden h-full">
      {/* Header */}
      <div className="p-6 border-b border-border/50 bg-gradient-to-r from-primary/5 via-transparent to-transparent space-y-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-primary/10">
            <BarChart3 className="size-5 text-primary" />
          </div>
          <div>
            <h2 className="font-semibold">Usage Statistics</h2>
            <p className="text-sm text-muted-foreground">
              {isToday ? 'Your activity for today' : 'Activity for selected period'}
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <DateRangePicker
            dateRange={dateRange}
            onDateRangeChange={setDateRange}
            className="flex-1"
          />
          <Button 
            onClick={() => setShouldFetch(true)}
            disabled={!dateRange?.from || !dateRange?.to || isLoading}
            className="shrink-0 rounded-xl"
          >
            {isLoading ? 'Loading...' : 'Apply'}
          </Button>
        </div>
      </div>

      <div className="p-6 space-y-6">
        {/* Posts Usage */}
        <div className="space-y-3">
          <div className="flex justify-between items-center">
            <div className="flex items-center gap-2">
              <div className="p-1.5 rounded-lg bg-blue-500/10">
                <div className="w-2 h-2 rounded-full bg-blue-500" />
              </div>
              <span className="text-sm font-medium">Posts Analyzed</span>
            </div>
            <span className="text-sm font-semibold">
              {isToday ? (
                <span>
                  <span className="text-foreground">{postsPerDay.used}</span>
                  <span className="text-muted-foreground"> / {postsPerDay.limit}</span>
                </span>
              ) : (
                <span>{postsPerDay.used} used</span>
              )}
            </span>
          </div>
          {isToday && (
            <>
              <Progress 
                value={postsPercent} 
                className={`h-2.5 rounded-full ${postsPercent >= 100 ? 'bg-muted [&>div]:bg-amber-500' : '[&>div]:bg-blue-500'}`} 
              />
              {postsPercent >= 100 && (
                <p className="text-xs text-amber-500 font-medium flex items-center gap-1">
                  <AlertCircle className="size-3" />
                  Daily limit reached
                </p>
              )}
            </>
          )}
        </div>

        {/* Chats Usage */}
        <div className="space-y-3">
          <div className="flex justify-between items-center">
            <div className="flex items-center gap-2">
              <div className="p-1.5 rounded-lg bg-purple-500/10">
                <div className="w-2 h-2 rounded-full bg-purple-500" />
              </div>
              <span className="text-sm font-medium">Chat Messages</span>
            </div>
            <span className="text-sm font-semibold">
              {isToday ? (
                <span>
                  <span className="text-foreground">{chatsPerDay.used}</span>
                  <span className="text-muted-foreground"> / {chatsPerDay.limit}</span>
                </span>
              ) : (
                <span>{chatsPerDay.used} used</span>
              )}
            </span>
          </div>
          {isToday && (
            <>
              <Progress 
                value={chatsPercent} 
                className={`h-2.5 rounded-full ${chatsPercent >= 100 ? 'bg-muted [&>div]:bg-amber-500' : '[&>div]:bg-purple-500'}`} 
              />
              {chatsPercent >= 100 && (
                <p className="text-xs text-amber-500 font-medium flex items-center gap-1">
                  <AlertCircle className="size-3" />
                  Daily limit reached
                </p>
              )}
            </>
          )}
        </div>

        {!compact && (
          <div className="pt-4 space-y-4 border-t border-border/30">
            {/* Current Plan Card */}
            <div className="p-4 bg-gradient-to-br from-muted/50 to-muted/30 rounded-xl border border-border/50">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-xs text-muted-foreground uppercase tracking-wider font-medium mb-1">Current Plan</div>
                  <div className="text-xl font-bold">{usage.plan?.name || 'Free'}</div>
                </div>
                <div className="p-3 rounded-xl bg-background/80">
                  <CreditCard className="size-5 text-primary" />
                </div>
              </div>
            </div>
            
            {/* Upgrade CTA */}
            {usage.plan && usage.plan.name !== 'Pro' && onNavigateToSubscription && (
              <div className="relative p-5 bg-gradient-to-br from-primary/10 via-primary/5 to-transparent rounded-xl border border-primary/20 overflow-hidden">
                {/* Decorative element */}
                <div className="absolute -right-4 -top-4 w-24 h-24 bg-primary/10 rounded-full blur-2xl" />
                
                <div className="relative">
                  <div className="flex items-center gap-2 mb-2">
                    <Sparkles className="size-4 text-primary" />
                    <p className="text-sm font-semibold">Unlock More</p>
                  </div>
                  <p className="text-xs text-muted-foreground mb-4 leading-relaxed">
                    Get more posts and chats per day by upgrading your plan.
                  </p>
                  <Button
                    onClick={onNavigateToSubscription}
                    size="sm"
                    className="w-full rounded-xl shadow-md shadow-primary/20"
                  >
                    View Plans & Upgrade
                  </Button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
