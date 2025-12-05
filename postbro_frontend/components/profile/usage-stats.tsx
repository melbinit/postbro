"use client"

import { Progress } from "@/components/ui/progress"
import { useEffect, useState } from "react"
import { usageApi, type UsageStats as UsageStatsType } from "@/lib/api"
import { Skeleton } from "@/components/ui/skeleton"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { AlertCircle } from "lucide-react"
import { DateRange } from "react-day-picker"
import { format } from "date-fns"
import { DateRangePicker } from "@/components/ui/date-range-picker"
import { Button } from "@/components/ui/button"

interface UsageStatsProps {
  compact?: boolean
}

interface AggregatedUsage {
  handle_analyses: { used: number; limit: number; remaining: number }
  url_lookups: { used: number; limit: number; remaining: number }
  post_suggestions: { used: number; limit: number; remaining: number }
}

export function UsageStats({ compact }: UsageStatsProps) {
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
        if (data.usage && 'platforms' in data.usage && !('handle_analyses' in data.usage)) {
          // Aggregate across all platforms
          const platforms = (data.usage as any).platforms || {}
          let totalHandleAnalyses = 0
          let totalUrlLookups = 0
          let totalPostSuggestions = 0
          
          Object.values(platforms).forEach((platformUsage: any) => {
            totalHandleAnalyses += platformUsage.handle_analyses || 0
            totalUrlLookups += platformUsage.url_lookups || 0
            totalPostSuggestions += platformUsage.post_suggestions || 0
          })
          
          // Transform to expected format
          const normalizedData = {
            ...data,
            usage: {
              platform: 'all',
              date: data.usage.date || new Date().toISOString().split('T')[0],
              handle_analyses: {
                used: totalHandleAnalyses,
                limit: data.plan?.max_handles || 0,
                remaining: Math.max(0, (data.plan?.max_handles || 0) - totalHandleAnalyses)
              },
              url_lookups: {
                used: totalUrlLookups,
                limit: data.plan?.max_urls || 0,
                remaining: Math.max(0, (data.plan?.max_urls || 0) - totalUrlLookups)
              },
              post_suggestions: {
                used: totalPostSuggestions,
                limit: data.plan?.max_analyses_per_day || 0,
                remaining: Math.max(0, (data.plan?.max_analyses_per_day || 0) - totalPostSuggestions)
              }
            }
          }
          setUsage(normalizedData)
        } else if (data.usage && data.usage.handle_analyses) {
          // Already in the correct format
          setUsage(data)
        } else {
          // Fallback: create default structure with plan limits
          const normalizedData = {
            ...data,
            usage: {
              platform: 'all',
              date: data.usage?.date || new Date().toISOString().split('T')[0],
              handle_analyses: {
                used: 0,
                limit: data.plan?.max_handles || 0,
                remaining: data.plan?.max_handles || 0
              },
              url_lookups: {
                used: 0,
                limit: data.plan?.max_urls || 0,
                remaining: data.plan?.max_urls || 0
              },
              post_suggestions: {
                used: 0,
                limit: data.plan?.max_analyses_per_day || 0,
                remaining: data.plan?.max_analyses_per_day || 0
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
          handle_analyses: { used: 0, limit: 0, remaining: 0 },
          url_lookups: { used: 0, limit: 0, remaining: 0 },
          post_suggestions: { used: 0, limit: 0, remaining: 0 },
        }

        // Get plan info for display
        const currentUsage = await usageApi.getUsageStats()
        setUsage(currentUsage)

        // Aggregate usage across all days in range
        if (history.usage_history.length > 0) {
          history.usage_history.forEach((entry) => {
            aggregated.handle_analyses.used += entry.handle_analyses
            aggregated.url_lookups.used += entry.url_lookups
            aggregated.post_suggestions.used += entry.post_suggestions
          })
        }

        setAggregatedUsage(aggregated)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load usage statistics')
      console.error('Failed to fetch usage stats:', err)
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
          {[1, 2, 3].map((i) => (
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
          {[1, 2, 3].map((i) => (
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
        handle_analyses: aggregatedUsage.handle_analyses,
        url_lookups: aggregatedUsage.url_lookups,
        post_suggestions: aggregatedUsage.post_suggestions,
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

  const handleAnalyses = displayUsage.handle_analyses || { used: 0, limit: 0, remaining: 0 }
  const urlLookups = displayUsage.url_lookups || { used: 0, limit: 0, remaining: 0 }
  const postSuggestions = displayUsage.post_suggestions || { used: 0, limit: 0, remaining: 0 }

  // Only show progress bars and percentages for today
  const handleAnalysesPercent = isToday && handleAnalyses.limit > 0 ? (handleAnalyses.used / handleAnalyses.limit) * 100 : 0
  const urlLookupsPercent = isToday && urlLookups.limit > 0 ? (urlLookups.used / urlLookups.limit) * 100 : 0
  const postSuggestionsPercent = isToday && postSuggestions.limit > 0 ? (postSuggestions.used / postSuggestions.limit) * 100 : 0

  return (
    <div className="bg-background rounded-xl border border-border shadow-sm overflow-hidden h-full">
      <div className="p-6 border-b border-border space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold">Usage Statistics</h2>
        </div>
        <div className="space-y-3">
          <div className="flex gap-2">
            <DateRangePicker
              dateRange={dateRange}
              onDateRangeChange={setDateRange}
              className="flex-1"
            />
            <Button 
              onClick={() => setShouldFetch(true)}
              disabled={!dateRange?.from || !dateRange?.to || isLoading}
              className="shrink-0"
            >
              {isLoading ? 'Loading...' : 'Apply'}
            </Button>
          </div>
          <p className="text-sm text-muted-foreground">
            {isToday ? 'Your activity for today' : 'Your activity for the selected period'}
          </p>
        </div>
      </div>

      <div className="p-6 space-y-6">
        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span className="font-medium">Handle Analyses</span>
            <span className="text-muted-foreground">
              {isToday ? (
                <>
                  {handleAnalyses.used} / {handleAnalyses.limit} today
                </>
              ) : (
                <>{handleAnalyses.used} used</>
              )}
            </span>
          </div>
          {isToday && (
            <>
              <Progress 
                value={handleAnalysesPercent} 
                className={`h-2 ${handleAnalysesPercent >= 100 ? 'bg-muted [&>div]:bg-amber-500' : ''}`} 
              />
              {handleAnalysesPercent >= 100 && (
                <p className="text-xs text-amber-500 font-medium">Limit reached</p>
              )}
            </>
          )}
        </div>

        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span className="font-medium">URL Lookups</span>
            <span className="text-muted-foreground">
              {isToday ? (
                <>
                  {urlLookups.used} / {urlLookups.limit} today
                </>
              ) : (
                <>{urlLookups.used} used</>
              )}
            </span>
          </div>
          {isToday && (
            <>
              <Progress 
                value={urlLookupsPercent} 
                className={`h-2 ${urlLookupsPercent >= 100 ? 'bg-muted [&>div]:bg-amber-500' : ''}`} 
              />
              {urlLookupsPercent >= 100 && (
                <p className="text-xs text-amber-500 font-medium">Limit reached</p>
              )}
            </>
          )}
        </div>

        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span className="font-medium">Post Suggestions</span>
            <span className="text-muted-foreground">
              {isToday ? (
                <>
                  {postSuggestions.used} / {postSuggestions.limit} today
                </>
              ) : (
                <>{postSuggestions.used} used</>
              )}
            </span>
          </div>
          {isToday && (
            <>
              <Progress 
                value={postSuggestionsPercent} 
                className={`h-2 ${postSuggestionsPercent >= 100 ? 'bg-muted [&>div]:bg-amber-500' : ''}`} 
              />
              {postSuggestionsPercent >= 100 && (
                <p className="text-xs text-amber-500 font-medium">Limit reached</p>
              )}
            </>
          )}
        </div>

        {!compact && (
          <div className={`pt-4 grid gap-4 ${isToday ? 'grid-cols-2' : 'grid-cols-1'}`}>
            {isToday && (
              <div className="p-4 bg-muted/30 rounded-lg border border-border">
                <div className="text-2xl font-bold mb-1">
                  {handleAnalyses.remaining + urlLookups.remaining + postSuggestions.remaining}
                </div>
                <div className="text-xs text-muted-foreground uppercase tracking-wider font-medium">
                  Remaining Today
                </div>
              </div>
            )}
            <div className="p-4 bg-muted/30 rounded-lg border border-border">
              <div className="text-2xl font-bold mb-1">{usage.plan?.name || 'Free'}</div>
              <div className="text-xs text-muted-foreground uppercase tracking-wider font-medium">Current Plan</div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
