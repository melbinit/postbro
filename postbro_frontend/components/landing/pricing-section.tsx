"use client"

import { PlanSelector } from "@/components/billing/plan-selector"

export function PricingSection() {
  return (
    <section id="pricing" className="py-20 md:py-28 relative">
      {/* Subtle background */}
      <div className="absolute inset-0 bg-gradient-to-b from-muted/30 via-muted/20 to-transparent pointer-events-none" />
      
      <div className="container px-4 mx-auto relative">
        <div className="text-center max-w-2xl mx-auto mb-12">
          <p className="text-xs font-semibold text-primary uppercase tracking-wider mb-4">Pricing</p>
          <h2 className="text-3xl md:text-4xl font-bold mb-4">
            Simple, transparent pricing
          </h2>
          <p className="text-muted-foreground text-lg">
            Choose the plan that fits your needs. No hidden fees. Cancel anytime.
          </p>
        </div>

        <div className="max-w-5xl mx-auto">
          <PlanSelector showCurrentPlan={false} />
        </div>

        <div className="text-center mt-10">
          <p className="text-sm text-muted-foreground">
            Need higher limits?{" "}
            <a href="mailto:mail.postbro@gmail.com" className="text-foreground hover:text-primary transition-colors font-medium">
              Contact us
            </a>{" "}
            for custom plans.
          </p>
        </div>
      </div>
    </section>
  )
}
