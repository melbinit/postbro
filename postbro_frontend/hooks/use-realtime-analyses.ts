/**
 * Hook for subscribing to real-time updates for all processing analyses
 * Keeps subscriptions active even when not viewing them (better UX)
 */

import { useEffect, useRef } from 'react'
import { supabase } from '@/lib/supabase'
import type { RealtimeChannel } from '@supabase/supabase-js'
import type { AnalysisStatus } from './use-realtime-status'
import { logger } from '@/lib/logger'

// Helper to check existing statuses when subscribing
async function checkExistingStatus(
  analysisId: string,
  onUsernameUpdate: (analysisId: string, username: string) => void
) {
  try {
    const { data, error } = await supabase
      .from('analysis_analysisstatushistory')
      .select('*')
      .eq('analysis_request_id', analysisId)
      .eq('stage', 'social_data_fetched')
      .order('created_at', { ascending: false })
      .limit(1)

    if (error) {
      logger.error(`[RealtimeAnalyses] Error checking status for ${analysisId}:`, error)
      return
    }

    if (data && data.length > 0) {
      const status = data[0] as AnalysisStatus
      if (status.metadata?.username) {
        onUsernameUpdate(analysisId, status.metadata.username)
      }
    }
  } catch (error) {
    logger.error(`[RealtimeAnalyses] Exception checking status for ${analysisId}:`, error)
  }
}

interface ProcessingAnalysis {
  id: string
  status: 'pending' | 'processing'
}

export function useRealtimeAnalyses(
  analyses: ProcessingAnalysis[],
  onStatusUpdate: (analysisId: string, status: string) => void,
  onUsernameUpdate: (analysisId: string, username: string) => void
) {
  const channelsRef = useRef<Map<string, RealtimeChannel>>(new Map())
  const checkedStatusesRef = useRef<Set<string>>(new Set()) // Track which analyses we've already checked

  useEffect(() => {
    // Get all processing analyses (pending or processing)
    const processingAnalyses = analyses.filter(
      (a) => a.status === 'pending' || a.status === 'processing'
    )

    logger.debug(`[RealtimeAnalyses] Subscribing to ${processingAnalyses.length} analyses`)

    // Subscribe to each processing analysis
    processingAnalyses.forEach((analysis) => {
      // Skip if already subscribed
      if (channelsRef.current.has(analysis.id)) {
        return
      }

      // Check for existing social_data_fetched status ONCE (in case status was created before subscription)
      // Only check if we haven't checked this analysis before
      if (!checkedStatusesRef.current.has(analysis.id)) {
        checkedStatusesRef.current.add(analysis.id)
        checkExistingStatus(analysis.id, onUsernameUpdate)
      }

      // Create channel for this analysis
      const channelName = `analysis-status-global-${analysis.id}-${Date.now()}`
      const channel = supabase
        .channel(channelName)
        .on(
          'postgres_changes',
          {
            event: 'INSERT',
            schema: 'public',
            table: 'analysis_analysisstatushistory',
            filter: `analysis_request_id=eq.${analysis.id}`,
          },
          (payload) => {
            const newStatus = payload.new as AnalysisStatus
            logger.debug(`[RealtimeAnalyses] Status update: ${analysis.id} -> ${newStatus.stage}`)

            // Update status if analysis completed or failed
            if (newStatus.stage === 'analysis_complete') {
              onStatusUpdate(analysis.id, 'completed')
            } else if (newStatus.is_error && !newStatus.retryable) {
              onStatusUpdate(analysis.id, 'failed')
            } else if (newStatus.stage === 'social_data_fetched') {
              if (newStatus.metadata?.username) {
                // Update username when social data is fetched
                onUsernameUpdate(analysis.id, newStatus.metadata.username)
              }
            }
          }
        )
        .subscribe((status, err) => {
          if (status === 'SUBSCRIBED') {
            logger.debug(`[RealtimeAnalyses] Subscribed: ${analysis.id}`)
          } else if (status === 'CHANNEL_ERROR' || err) {
            logger.error(`[RealtimeAnalyses] Channel error for ${analysis.id}:`, err || status)
          }
        })

      channelsRef.current.set(analysis.id, channel)
    })

    // Cleanup: Remove subscriptions for analyses that are no longer processing
    const processingIds = new Set(processingAnalyses.map((a) => a.id))
    channelsRef.current.forEach((channel, analysisId) => {
      if (!processingIds.has(analysisId)) {
        logger.debug(`[RealtimeAnalyses] Cleaning up: ${analysisId}`)
        supabase.removeChannel(channel)
        channelsRef.current.delete(analysisId)
      }
    })

    // Cleanup on unmount
    return () => {
      channelsRef.current.forEach((channel) => {
        supabase.removeChannel(channel)
      })
      channelsRef.current.clear()
    }
  }, [analyses, onStatusUpdate, onUsernameUpdate])
}

