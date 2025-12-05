"use client"

import { Suspense } from "react"
import { AppHeader } from "@/components/layout/app-header"
import { Footer } from "@/components/layout/footer"
import { ProfileHeader } from "@/components/profile/profile-header"
import { ProfileContent } from "@/components/profile/profile-content"
import { useAuth } from "@clerk/nextjs"
import { useRouter, useSearchParams } from "next/navigation"
import { Button } from "@/components/ui/button"
import { ArrowLeft } from "lucide-react"

function ProfilePageContent() {
  const searchParams = useSearchParams()
  const defaultTab = searchParams.get('tab') || 'overview'

  return (
    <>
      <ProfileHeader />
      <ProfileContent defaultTab={defaultTab} />
    </>
  )
}

export default function ProfilePage() {
  const router = useRouter()
  const { isLoaded, isSignedIn } = useAuth()

  // Show loading state while Clerk is loading
  if (!isLoaded) {
    return (
      <div className="flex min-h-screen flex-col">
        <AppHeader />
        <main className="flex-1 bg-muted/30 py-24">
          <div className="container px-4 mx-auto max-w-5xl">
            <div className="animate-pulse space-y-4">
              <div className="h-8 w-48 bg-muted rounded"></div>
              <div className="h-64 bg-muted rounded"></div>
            </div>
          </div>
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

  return (
    <div className="flex min-h-screen flex-col">
      <AppHeader />
      <main className="flex-1 bg-muted/30 py-24">
        <div className="container px-4 mx-auto max-w-5xl">
          {/* Back Button */}
          <div className="mb-6">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => router.push('/app')}
              className="text-muted-foreground hover:text-foreground"
            >
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to App
            </Button>
          </div>
          <Suspense fallback={
            <div className="animate-pulse space-y-4">
              <div className="h-8 w-48 bg-muted rounded"></div>
              <div className="h-64 bg-muted rounded"></div>
            </div>
          }>
            <ProfilePageContent />
          </Suspense>
        </div>
      </main>
      <Footer />
    </div>
  )
}
