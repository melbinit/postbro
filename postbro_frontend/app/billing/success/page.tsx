"use client"

import { useEffect, useState } from "react"
import { useSearchParams, useRouter } from "next/navigation"
import { CheckCircle, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import Link from "next/link"

export default function BillingSuccessPage() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const [isLoading, setIsLoading] = useState(true)
  const checkoutId = searchParams.get('checkout_id')

  useEffect(() => {
    // Give webhook a moment to process, then redirect
    const timer = setTimeout(() => {
      setIsLoading(false)
      // Redirect to app after 3 seconds
      setTimeout(() => {
        router.push('/app')
      }, 3000)
    }, 2000)

    return () => clearTimeout(timer)
  }, [router])

  return (
    <div className="min-h-screen flex items-center justify-center bg-muted/30 p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-green-100 dark:bg-green-900">
            <CheckCircle className="h-8 w-8 text-green-600 dark:text-green-400" />
          </div>
          <CardTitle className="text-2xl">Payment Successful!</CardTitle>
          <CardDescription>
            Your subscription has been activated. You can now access all features of your plan.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {isLoading ? (
            <div className="flex items-center justify-center py-4">
              <Loader2 className="h-6 w-6 animate-spin text-primary" />
              <span className="ml-2 text-sm text-muted-foreground">Activating your subscription...</span>
            </div>
          ) : (
            <>
              <p className="text-center text-sm text-muted-foreground">
                Redirecting you to the app...
              </p>
              <Button asChild className="w-full">
                <Link href="/app">Go to App</Link>
              </Button>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

