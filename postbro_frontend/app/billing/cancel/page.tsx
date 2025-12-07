"use client"

import { XCircle, ArrowRight, CreditCard } from "lucide-react"
import { Button } from "@/components/ui/button"
import Link from "next/link"

export default function BillingCancelPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-b from-background to-muted/30 p-4">
      {/* Decorative background elements */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-amber-500/5 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-orange-500/5 rounded-full blur-3xl" />
      </div>

      <div className="relative w-full max-w-md">
        {/* Main Card */}
        <div className="bg-card/80 backdrop-blur-sm border border-border/50 rounded-2xl shadow-xl overflow-hidden">
          {/* Header with icon */}
          <div className="px-8 pt-10 pb-6 text-center">
            <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-amber-500/10 mb-5">
              <XCircle className="h-6 w-6 text-amber-500" />
            </div>
            <h1 className="text-xl font-semibold text-foreground mb-2">
              Payment cancelled
            </h1>
            <p className="text-sm text-muted-foreground leading-relaxed max-w-xs mx-auto">
              No worries! Your payment was cancelled and no charges were made. You can upgrade anytime.
            </p>
          </div>

          {/* Content area */}
          <div className="px-8 pb-8 space-y-3">
            <Button asChild variant="outline" className="w-full h-11 rounded-xl">
              <Link href="/#pricing">
                <CreditCard className="mr-2 h-4 w-4" />
                View Plans
              </Link>
            </Button>
            <Button asChild className="w-full h-11 rounded-xl">
              <Link href="/app">
                Continue to App
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
          </div>
        </div>

        {/* Help text */}
        <p className="text-center text-xs text-muted-foreground/60 mt-6">
          Changed your mind?{' '}
          <Link href="/#pricing" className="text-primary hover:underline">
            Compare plans
          </Link>
        </p>
      </div>
    </div>
  )
}
