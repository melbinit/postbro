/**
 * Hook for subscribing to real-time updates for all processing analyses
 * Keeps subscriptions active even when not viewing them (better UX)
 */

import { useEffect, useRef } from 'react'
import { supabase } from '@/lib/supabase'
import type { RealtimeChannel } from '@supabase/supabase-js'
import type { AnalysisStatus } from './use-realtime-status'

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
      console.error(`❌ [RealtimeAnalyses] Error checking existing status for ${analysisId}:`, error)
      return
    }

    if (data && data.length > 0) {
      const status = data[0] as AnalysisStatus
      if (status.metadata?.username) {
        console.log(`👤 [RealtimeAnalyses] Found existing social_data_fetched status for ${analysisId} with username: ${status.metadata.username}`)
        onUsernameUpdate(analysisId, status.metadata.username)
      }
    }
  } catch (error) {
    console.error(`❌ [RealtimeAnalyses] Exception checking existing status for ${analysisId}:`, error)
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

    console.log(`📊 [RealtimeAnalyses] Processing analyses to subscribe:`, processingAnalyses.map(a => ({ id: a.id, status: a.status })))

    // Subscribe to each processing analysis
    processingAnalyses.forEach((analysis) => {
      // Skip if already subscribed
      if (channelsRef.current.has(analysis.id)) {
        console.log(`⏭️ [RealtimeAnalyses] Already subscribed to ${analysis.id}, skipping`)
        return
      }

      console.log(`🔌 [RealtimeAnalyses] Subscribing to ${analysis.id} (status: ${analysis.status})`)

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
            console.log(`🔄 [RealtimeAnalyses] Received status for ${analysis.id}: ${newStatus.stage}`, newStatus.metadata)

            // Update status if analysis completed or failed
            if (newStatus.stage === 'analysis_complete') {
              console.log(`✅ [RealtimeAnalyses] Updating status to completed for ${analysis.id}`)
              onStatusUpdate(analysis.id, 'completed')
            } else if (newStatus.is_error && !newStatus.retryable) {
              console.log(`❌ [RealtimeAnalyses] Updating status to failed for ${analysis.id}`)
              onStatusUpdate(analysis.id, 'failed')
            } else if (newStatus.stage === 'social_data_fetched') {
              console.log(`📦 [RealtimeAnalyses] social_data_fetched received for ${analysis.id}`, {
                hasUsername: !!newStatus.metadata?.username,
                username: newStatus.metadata?.username,
                metadata: newStatus.metadata
              })
              if (newStatus.metadata?.username) {
                // Update username when social data is fetched
                console.log(`👤 [RealtimeAnalyses] Calling onUsernameUpdate('${analysis.id}', '${newStatus.metadata.username}')`)
                onUsernameUpdate(analysis.id, newStatus.metadata.username)
                console.log(`✅ [RealtimeAnalyses] onUsernameUpdate called for ${analysis.id}`)
              } else {
                console.log(`⚠️ [RealtimeAnalyses] social_data_fetched but no username in metadata for ${analysis.id}`)
              }
            }
          }
        )
        .subscribe((status, err) => {
          if (status === 'SUBSCRIBED') {
            console.log(`✅ [RealtimeAnalyses] Subscribed to analysis ${analysis.id}`)
          } else if (status === 'CHANNEL_ERROR' || err) {
            console.error(`❌ [RealtimeAnalyses] Channel error for ${analysis.id}:`, err || status)
          }
        })

      channelsRef.current.set(analysis.id, channel)
    })

    // Cleanup: Remove subscriptions for analyses that are no longer processing
    const processingIds = new Set(processingAnalyses.map((a) => a.id))
    channelsRef.current.forEach((channel, analysisId) => {
      if (!processingIds.has(analysisId)) {
        console.log(`🧹 [RealtimeAnalyses] Cleaning up subscription for completed analysis ${analysisId}`)
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

