"use client"

import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Mail, ArrowLeft, CheckCircle2 } from "lucide-react"
import { useSearchParams } from "next/navigation"
import { useEffect, useState, Suspense } from "react"

function VerifyEmailContent() {
  const searchParams = useSearchParams()
  const [isVerified, setIsVerified] = useState(false)
  const email = searchParams.get('email')

  useEffect(() => {
    // Check if user came from signup with verification token
    const token = searchParams.get('token')
    if (token) {
      // In a real app, you'd verify the token with the backend
      // For now, we'll just show the verification page
      setIsVerified(false)
    }
  }, [searchParams])

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-6">
      <div className="w-full max-w-md space-y-8 text-center">
        <div className="space-y-4">
          {isVerified ? (
            <>
              <div className="mx-auto size-16 rounded-full bg-green-100 dark:bg-green-900/30 flex items-center justify-center">
                <CheckCircle2 className="size-8 text-green-600 dark:text-green-400" />
              </div>
              <h1 className="text-2xl md:text-3xl font-bold">Email Verified!</h1>
              <p className="text-muted-foreground">
                Your email has been successfully verified. You can now access all features.
              </p>
              <Button asChild className="w-full">
                <Link href="/profile">Go to Profile</Link>
              </Button>
            </>
          ) : (
            <>
              <div className="mx-auto size-16 rounded-full bg-primary/10 flex items-center justify-center">
                <Mail className="size-8 text-primary" />
              </div>
              <h1 className="text-2xl md:text-3xl font-bold">Check your email</h1>
              <p className="text-muted-foreground">
                {email
                  ? `We've sent a verification link to ${email}`
                  : "We've sent a verification link to your email address"}
              </p>
              <p className="text-sm text-muted-foreground">
                Please click the link in the email to verify your account. The link will expire in 24 hours.
              </p>
              <div className="space-y-4 pt-4">
                <div className="bg-muted/30 rounded-lg p-4 text-left space-y-2">
                  <p className="text-sm font-medium">Didn't receive the email?</p>
                  <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
                    <li>Check your spam or junk folder</li>
                    <li>Make sure you entered the correct email address</li>
                    <li>Wait a few minutes and try again</li>
                  </ul>
                </div>
                <div className="flex flex-col sm:flex-row gap-3">
                  <Button variant="outline" asChild className="flex-1">
                    <Link href="/login">
                      <ArrowLeft className="mr-2 size-4" />
                      Back to Login
                    </Link>
                  </Button>
                  <Button asChild className="flex-1">
                    <Link href="/signup">Create New Account</Link>
                  </Button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-background p-6">
        <div className="w-full max-w-md space-y-8 text-center">
          <div className="mx-auto size-16 rounded-full bg-primary/10 flex items-center justify-center">
            <Mail className="size-8 text-primary animate-pulse" />
          </div>
          <h1 className="text-2xl md:text-3xl font-bold">Loading...</h1>
        </div>
      </div>
    }>
      <VerifyEmailContent />
    </Suspense>
  )
}

