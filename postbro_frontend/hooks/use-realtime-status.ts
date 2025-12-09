/**
 * Hook for subscribing to real-time analysis status updates
 */

import { useEffect, useState, useRef } from 'react'
import { supabase } from '@/lib/supabase'
import type { RealtimeChannel } from '@supabase/supabase-js'
import { logger } from '@/lib/logger'

export interface AnalysisStatus {
  id: string
  analysis_request_id: string
  stage: string
  message: string
  metadata: Record<string, any>
  is_error: boolean
  error_code?: string
  retryable: boolean
  actionable_message?: string
  progress_percentage: number
  duration_seconds?: number
  api_calls_made: number
  cost_estimate?: number
  created_at: string
}

export function useRealtimeStatus(analysisRequestId: string | null) {
  const [statusHistory, setStatusHistory] = useState<AnalysisStatus[]>([])
  const [isConnected, setIsConnected] = useState(false)
  const channelRef = useRef<RealtimeChannel | null>(null)

  useEffect(() => {
    if (!analysisRequestId) {
      setStatusHistory([])
      return
    }

    // Load existing status history FIRST (before subscribing) to catch any statuses already created
    const loadHistory = async () => {
      try {
        const { data, error } = await supabase
          .from('analysis_analysisstatushistory')
          .select('*')
          .eq('analysis_request_id', analysisRequestId)
          .order('created_at', { ascending: true })

        if (error) {
          logger.error('[RealtimeStatus] Error loading history:', error)
          return
        }

        if (data) {
          logger.debug(`[RealtimeStatus] Loaded ${data.length} status entries`)
          setStatusHistory(data as AnalysisStatus[])
          
          // Check if social_data_fetched status exists in history and trigger username update
          const socialDataFetchedStatus = data.find((s: AnalysisStatus) => s.stage === 'social_data_fetched')
          if (socialDataFetchedStatus?.metadata?.username) {
            // Dispatch event to update sidebar (will be handled by app-content.tsx)
            if (typeof window !== 'undefined') {
              window.dispatchEvent(new CustomEvent('analysis-username-updated', {
                detail: {
                  analysis_request_id: analysisRequestId,
                  username: socialDataFetchedStatus.metadata.username
                }
              }))
            }
          }
        }
      } catch (error) {
        logger.error('[RealtimeStatus] Exception loading history:', error)
      }
    }

    // Load history immediately
    loadHistory()

    // Create channel with unique name
    const channelName = `analysis-status-${analysisRequestId}-${Date.now()}`
    
    const channel = supabase
      .channel(channelName)
      .on(
        'postgres_changes',
        {
          event: 'INSERT',
          schema: 'public',
          table: 'analysis_analysisstatushistory',
          filter: `analysis_request_id=eq.${analysisRequestId}`,
        },
        (payload) => {
          const newStatus = payload.new as AnalysisStatus
          logger.debug(`[RealtimeStatus] Status update: ${newStatus.stage}`)
          setStatusHistory((prev) => {
            // Avoid duplicates (can happen if status was created between history load and subscription)
            if (prev.some((s) => s.id === newStatus.id)) {
              // Silently skip - this is normal when status was already loaded from history
              return prev
            }
            const updated = [...prev, newStatus].sort(
              (a, b) =>
                new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
            )
            return updated
          })
        }
      )
      .subscribe((status, err) => {
        if (status === 'SUBSCRIBED') {
          setIsConnected(true)
          logger.debug(`[RealtimeStatus] Subscribed: ${analysisRequestId}`)
        } else if (status === 'CHANNEL_ERROR' || err) {
          setIsConnected(false)
          logger.error('[RealtimeStatus] Channel error:', err || status)
        } else if (status === 'TIMED_OUT') {
          setIsConnected(false)
          logger.error('[RealtimeStatus] Subscription timed out')
        } else {
          setIsConnected(false)
        }
      })

    channelRef.current = channel

    // Cleanup on unmount
    return () => {
      if (channelRef.current) {
        supabase.removeChannel(channelRef.current)
        channelRef.current = null
      }
      setIsConnected(false)
    }
  }, [analysisRequestId])

  return {
    statusHistory,
    isConnected,
    latestStatus: statusHistory[statusHistory.length - 1] || null,
  }
}

