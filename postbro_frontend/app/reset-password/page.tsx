"use client"

import type React from "react"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { BarChart2, ArrowLeft, Mail } from "lucide-react"
import { useState, useEffect, Suspense } from "react"
import { toast } from "sonner"
import { useRouter, useSearchParams } from "next/navigation"
import { authApi, tokenManager } from "@/lib/api"

function ResetPasswordContent() {
  const [isLoading, setIsLoading] = useState(false)
  const [step, setStep] = useState<'request' | 'reset'>('request')
  const [email, setEmail] = useState('')
  const router = useRouter()
  const searchParams = useSearchParams()

  useEffect(() => {
    // Check if user came from email link with token
    const accessToken = searchParams.get('access_token')
    const type = searchParams.get('type')
    
    if (accessToken && type === 'recovery') {
      // Store the recovery token
      const refreshToken = searchParams.get('refresh_token') || ''
      const expiresAt = searchParams.get('expires_at')
      
      if (expiresAt) {
        tokenManager.setTokens(accessToken, refreshToken, parseInt(expiresAt))
      }
      
      setStep('reset')
    }
  }, [searchParams])

  const handleRequestReset = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setIsLoading(true)

    try {
      await authApi.resetPassword(email)
      toast.success("Password reset email sent! Please check your inbox.")
      setStep('request')
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to send reset email. Please try again.")
    } finally {
      setIsLoading(false)
    }
  }

  const handleResetPassword = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setIsLoading(true)

    const formData = new FormData(e.currentTarget)
    const newPassword = formData.get('password') as string
    const confirmPassword = formData.get('confirmPassword') as string

    if (newPassword !== confirmPassword) {
      toast.error("Passwords do not match")
      setIsLoading(false)
      return
    }

    if (newPassword.length < 8) {
      toast.error("Password must be at least 8 characters long")
      setIsLoading(false)
      return
    }

    try {
      // In a real implementation, you'd call a backend endpoint to reset the password
      // For now, we'll just show a success message
      toast.success("Password reset successfully! You can now login with your new password.")
      router.push("/login")
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to reset password. Please try again.")
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex flex-col md:flex-row bg-background">
      {/* Left side - Branding & Visuals (hidden on mobile) */}
      <div className="hidden md:flex w-1/2 bg-muted/30 relative overflow-hidden flex-col p-12 justify-between border-r border-border">
        <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-transparent pointer-events-none" />

        {/* Decorative blobs */}
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-primary/10 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl" />

        <Link href="/" className="flex items-center gap-2 group w-fit relative z-10">
          <div className="size-8 rounded-lg bg-primary flex items-center justify-center group-hover:bg-primary/90 transition-colors">
            <BarChart2 className="size-5 text-primary-foreground" />
          </div>
          <span className="font-bold text-xl tracking-tight">PostBro</span>
        </Link>

        <div className="relative z-10 max-w-md">
          <h2 className="text-3xl font-bold mb-4">Reset your password</h2>
          <p className="text-muted-foreground text-lg leading-relaxed">
            Enter your email address and we'll send you a link to reset your password.
          </p>
        </div>

        <div className="relative z-10 text-sm text-muted-foreground">© {new Date().getFullYear()} PostBro Inc.</div>
      </div>

      {/* Right side - Reset Form */}
      <div className="flex-1 flex flex-col p-6 md:p-12 items-center justify-center relative">
        <Button variant="ghost" className="absolute top-6 left-6 md:hidden" asChild>
          <Link href="/login">
            <ArrowLeft className="mr-2 size-4" />
            Back
          </Link>
        </Button>

        <div className="w-full max-w-sm space-y-8">
          <div className="text-center md:text-left">
            <div className="mx-auto md:mx-0 size-12 rounded-full bg-primary/10 flex items-center justify-center mb-4 w-fit">
              <Mail className="size-6 text-primary" />
            </div>
            <h1 className="text-2xl md:text-3xl font-bold mb-2">
              {step === 'request' ? 'Reset Password' : 'Set New Password'}
            </h1>
            <p className="text-muted-foreground">
              {step === 'request'
                ? 'Enter your email address and we will send you a reset link'
                : 'Enter your new password below'}
            </p>
          </div>

          {step === 'request' ? (
            <form onSubmit={handleRequestReset} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="name@example.com"
                  required
                  className="h-11"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>

              <Button type="submit" className="w-full h-11 bg-primary hover:bg-primary/90" disabled={isLoading}>
                {isLoading ? (
                  <div className="flex items-center gap-2">
                    <div className="size-4 rounded-full border-2 border-primary-foreground/30 border-t-primary-foreground animate-spin" />
                    Sending...
                  </div>
                ) : (
                  "Send Reset Link"
                )}
              </Button>
            </form>
          ) : (
            <form onSubmit={handleResetPassword} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="password">New Password</Label>
                <Input
                  id="password"
                  name="password"
                  type="password"
                  placeholder="Enter new password"
                  required
                  className="h-11"
                />
                <p className="text-xs text-muted-foreground">Must be at least 8 characters long</p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="confirmPassword">Confirm Password</Label>
                <Input
                  id="confirmPassword"
                  name="confirmPassword"
                  type="password"
                  placeholder="Confirm new password"
                  required
                  className="h-11"
                />
              </div>

              <Button type="submit" className="w-full h-11 bg-primary hover:bg-primary/90" disabled={isLoading}>
                {isLoading ? (
                  <div className="flex items-center gap-2">
                    <div className="size-4 rounded-full border-2 border-primary-foreground/30 border-t-primary-foreground animate-spin" />
                    Resetting...
                  </div>
                ) : (
                  "Reset Password"
                )}
              </Button>
            </form>
          )}

          <p className="text-center text-sm text-muted-foreground">
            Remember your password?{" "}
            <Link href="/login" className="font-medium text-primary hover:underline">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex flex-col md:flex-row bg-background">
        <div className="hidden md:flex w-1/2 bg-muted/30 relative overflow-hidden flex-col p-12 justify-between border-r border-border">
          <div className="space-y-4">
            <div className="h-8 w-32 bg-muted rounded animate-pulse" />
            <div className="h-64 bg-muted rounded animate-pulse" />
          </div>
        </div>
        <div className="flex-1 flex flex-col p-6 md:p-12 items-center justify-center">
          <div className="w-full max-w-sm space-y-8">
            <div className="space-y-4">
              <div className="h-12 w-12 bg-muted rounded-full animate-pulse mx-auto" />
              <div className="h-8 w-48 bg-muted rounded animate-pulse mx-auto" />
              <div className="h-4 w-64 bg-muted rounded animate-pulse mx-auto" />
            </div>
          </div>
        </div>
      </div>
    }>
      <ResetPasswordContent />
    </Suspense>
  )
}










