"use client"

import type React from "react"

import Link from "next/link"
import { Button } from "@/components/ui/button"
import { BarChart2, ArrowLeft } from "lucide-react"
import { useEffect } from "react"
import { useRouter } from "next/navigation"
import { SignIn } from "@clerk/nextjs"
import { useAuth } from "@clerk/nextjs"

export default function LoginPage() {
  const router = useRouter()
  const { getToken, isSignedIn } = useAuth()

  // Set up token getter for API client
  useEffect(() => {
    if (typeof window !== 'undefined' && getToken) {
      (window as any).__clerkGetToken = getToken
    }
  }, [getToken])

  // Sync with backend and redirect when signed in
  useEffect(() => {
    const syncWithBackend = async () => {
      if (isSignedIn) {
        try {
          const token = await getToken()
          if (token) {
            const { authApi } = await import('@/lib/api')
            await authApi.loginWithToken(token)
          }
          router.push("/app")
        } catch (error) {
          console.warn('Backend sync failed, but Clerk login succeeded:', error)
          // Still redirect even if backend sync fails
          router.push("/app")
        }
      }
    }
    syncWithBackend()
  }, [isSignedIn, getToken, router])

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
          <h2 className="text-3xl font-bold mb-4">Welcome back to PostBro</h2>
          <p className="text-muted-foreground text-lg leading-relaxed mb-6">
            Decode why posts go viral and generate winning content ideas. Analyze any Instagram, X, or YouTube post by URL or username to understand what makes content successful.
          </p>
          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <div className="size-2 rounded-full bg-primary" />
              <span className="text-muted-foreground">AI-powered viral analysis</span>
            </div>
            <div className="flex items-center gap-3">
              <div className="size-2 rounded-full bg-primary" />
              <span className="text-muted-foreground">Similar post ideas</span>
            </div>
            <div className="flex items-center gap-3">
              <div className="size-2 rounded-full bg-primary" />
              <span className="text-muted-foreground">Works with images & videos</span>
            </div>
          </div>
        </div>

        <div className="relative z-10 text-sm text-muted-foreground">© {new Date().getFullYear()} PostBro Inc.</div>
      </div>

      {/* Right side - Clerk Sign In */}
      <div className="flex-1 flex flex-col p-6 md:p-12 items-center justify-center relative">
        <div className="absolute top-6 left-6 right-6 flex items-center justify-between md:hidden">
          <Button variant="ghost" asChild>
            <Link href="/">
              <ArrowLeft className="mr-2 size-4" />
              Back
            </Link>
          </Button>
          <Link href="/" className="flex items-center gap-2">
            <div className="size-7 rounded-lg bg-primary flex items-center justify-center">
              <BarChart2 className="size-4 text-primary-foreground" />
            </div>
            <span className="font-bold text-lg tracking-tight">PostBro</span>
          </Link>
        </div>

        <div className="w-full max-w-sm">
          <SignIn 
            routing="path"
            path="/login"
            signUpUrl="/signup"
            fallbackRedirectUrl="/app"
            appearance={{
              elements: {
                rootBox: "mx-auto",
                card: "shadow-none bg-transparent",
              },
            }}
          />
        </div>
      </div>
    </div>
  )
}



