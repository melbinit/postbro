"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { Header } from "@/components/layout/header"
import { Footer } from "@/components/layout/footer"
import { useAuth } from "@clerk/nextjs"
import { analysisApi, type AnalysisRequest } from "@/lib/api"
import { useRealtimeStatus } from "@/hooks/use-realtime-status"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Progress } from "@/components/ui/progress"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Loader2, CheckCircle2, XCircle, AlertCircle, Sparkles } from "lucide-react"
import { toast } from "sonner"

export default function AnalyzePage() {
  const router = useRouter()
  const { isLoaded, isSignedIn } = useAuth()
  
  const [urls, setUrls] = useState<string>("")
  const [platform, setPlatform] = useState<"instagram" | "x" | "youtube">("instagram")
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [currentRequest, setCurrentRequest] = useState<AnalysisRequest | null>(null)
  
  const { statusHistory, isConnected, latestStatus } = useRealtimeStatus(
    currentRequest?.id || null
  )

  // Show loading state while Clerk is loading
  if (!isLoaded) {
    return (
      <div className="flex min-h-screen flex-col">
        <Header />
        <main className="flex-1 bg-muted/30 py-12 flex items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </main>
        <Footer />
      </div>
    )
  }

  // Redirect to login if not signed in
  if (!isSignedIn) {
    router.replace('/login')
    return null
  }

  const handleSubmit = async (e?: React.MouseEvent) => {
    // Prevent ANY default behavior
    if (e) {
      e.preventDefault()
      e.stopPropagation()
    }
    
    if (!urls.trim()) {
      toast.error("Please enter at least one URL")
      return false
    }

    setIsSubmitting(true)
    
    try {
      // Parse URLs (split by newline or comma)
      const urlList = urls
        .split(/[\n,]+/)
        .map((url) => url.trim())
        .filter((url) => url.length > 0)

      if (urlList.length === 0) {
        toast.error("Please enter at least one valid URL")
        setIsSubmitting(false)
        return false
      }

      const response = await analysisApi.createAnalysis({
        platform,
        post_urls: urlList,
      })

      // Set request immediately to show realtime UI
      setCurrentRequest(response)
      
      // Clear form
      setUrls("")
      
      return false
    } catch (error: any) {
      toast.error(error.message || "Failed to start analysis")
      console.error("Analysis error:", error)
      setIsSubmitting(false)
      return false
    }
  }

  const getStatusIcon = (stage: string, isError: boolean) => {
    if (isError) return <AlertCircle className="h-4 w-4 text-amber-500" />
    if (stage === "analysis_complete") return <CheckCircle2 className="h-4 w-4 text-emerald-500" />
    return <Loader2 className="h-4 w-4 animate-spin text-primary" />
  }

  const getStatusColor = (stage: string, isError: boolean) => {
    if (isError) return "text-amber-700 dark:text-amber-400"
    if (stage === "analysis_complete") return "text-emerald-600 dark:text-emerald-400"
    return "text-foreground"
  }

  return (
    <div className="flex min-h-screen flex-col">
      <Header />
      <main className="flex-1 bg-muted/30 py-12">
        <div className="container px-4 mx-auto max-w-4xl">
          <div className="mb-8">
            <h1 className="text-3xl font-bold mb-2">Analyze Posts</h1>
            <p className="text-muted-foreground">
              Paste URLs from Instagram, X (Twitter), or YouTube to get AI-powered insights
            </p>
          </div>

          {!currentRequest ? (
            <Card>
              <CardHeader>
                <CardTitle>Start Analysis</CardTitle>
                <CardDescription>
                  Enter one or more post URLs (separated by commas or new lines)
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-6">
                  <div className="space-y-2">
                    <Label htmlFor="platform">Platform</Label>
                    <Select
                      value={platform}
                      onValueChange={(value) => setPlatform(value as any)}
                      disabled={isSubmitting}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="instagram">Instagram</SelectItem>
                        <SelectItem value="x">X (Twitter)</SelectItem>
                        <SelectItem value="youtube">YouTube</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="urls">Post URLs</Label>
                    <textarea
                      id="urls"
                      value={urls}
                      onChange={(e) => setUrls(e.target.value)}
                      placeholder="https://instagram.com/p/...&#10;https://x.com/username/status/...&#10;https://youtube.com/watch?v=..."
                      className="min-h-[120px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                      disabled={isSubmitting}
                    />
                    <p className="text-xs text-muted-foreground">
                      Enter multiple URLs separated by commas or new lines
                    </p>
                  </div>

                  <button
                    type="button"
                    onClick={(e) => {
                      e.preventDefault()
                      e.stopPropagation()
                      handleSubmit(e)
                    }}
                    disabled={isSubmitting || !urls.trim()} 
                    className="w-full inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4 py-2"
                  >
                    {isSubmitting ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Starting Analysis...
                      </>
                    ) : (
                      <>
                        <Sparkles className="mr-2 h-4 w-4" />
                        Analyze Posts
                      </>
                    )}
                  </button>
                </div>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-6">
              <Card>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle>Analysis in Progress</CardTitle>
                      <CardDescription>
                        Request ID: {currentRequest.id.slice(0, 8)}...
                      </CardDescription>
                    </div>
                    <div className="flex items-center gap-2">
                      <div
                        className={`h-2 w-2 rounded-full ${
                          isConnected ? "bg-green-500" : "bg-gray-400"
                        }`}
                      />
                      <span className="text-xs text-muted-foreground">
                        {isConnected ? "Connected" : "Connecting..."}
                      </span>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  {latestStatus && (
                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-sm">
                        <span className="font-medium">Progress</span>
                        <span>{latestStatus.progress_percentage}%</span>
                      </div>
                      <Progress value={latestStatus.progress_percentage} />
                    </div>
                  )}

                  <div className="space-y-3">
                    {statusHistory.length === 0 ? (
                      <div className="text-center py-8 text-muted-foreground">
                        <Loader2 className="h-8 w-8 mx-auto mb-2 animate-spin" />
                        <p className="font-medium mb-1">Getting started...</p>
                        <p className="text-sm">Turning on my server... Waiting for real-time updates...</p>
                        {!isConnected && (
                          <p className="text-xs mt-2 text-yellow-500">Connecting to real-time feed...</p>
                        )}
                      </div>
                    ) : (
                      statusHistory.map((status) => (
                        <div
                          key={status.id}
                          className={`flex items-start gap-3 p-3.5 rounded-xl border transition-colors ${
                            status.is_error
                              ? "border-amber-200/60 dark:border-amber-800/40 bg-amber-50/50 dark:bg-amber-950/20"
                              : status.stage === "analysis_complete"
                              ? "border-emerald-200/60 dark:border-emerald-800/40 bg-emerald-50/50 dark:bg-emerald-950/20"
                              : "border-border/50 bg-muted/30"
                          }`}
                        >
                          <div className="mt-0.5">
                            {getStatusIcon(status.stage, status.is_error)}
                          </div>
                          <div className="flex-1 space-y-1 min-w-0">
                            <div className="flex items-center justify-between gap-2">
                              <p
                                className={`text-sm font-medium ${getStatusColor(
                                  status.stage,
                                  status.is_error
                                )}`}
                              >
                                {status.message}
                              </p>
                              {status.progress_percentage > 0 && (
                                <span className="text-xs text-muted-foreground tabular-nums flex-shrink-0">
                                  {status.progress_percentage}%
                                </span>
                              )}
                            </div>
                            {status.actionable_message && (
                              <p className="text-xs text-muted-foreground/80">
                                {status.actionable_message}
                              </p>
                            )}
                            <p className="text-[10px] text-muted-foreground/60">
                              {new Date(status.created_at).toLocaleTimeString()}
                            </p>
                          </div>
                        </div>
                      ))
                    )}
                  </div>

                  {latestStatus?.stage === "analysis_complete" && (
                    <Alert variant="success">
                      <CheckCircle2 className="h-4 w-4" />
                      <AlertDescription>
                        Analysis complete! Results are ready to view.
                      </AlertDescription>
                    </Alert>
                  )}

                  {latestStatus?.is_error && (
                    <Alert variant="destructive">
                      <AlertCircle className="h-4 w-4" />
                      <AlertDescription>
                        {latestStatus.actionable_message || latestStatus.message}
                      </AlertDescription>
                    </Alert>
                  )}

                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      onClick={() => {
                        setCurrentRequest(null)
                        setUrls("")
                      }}
                    >
                      New Analysis
                    </Button>
                    {latestStatus?.stage === "analysis_complete" && (
                      <Button onClick={() => router.push(`/analysis/${currentRequest.id}`)}>
                        View Results
                      </Button>
                    )}
                  </div>
                </CardContent>
              </Card>
            </div>
          )}
        </div>
      </main>
      <Footer />
    </div>
  )
}

