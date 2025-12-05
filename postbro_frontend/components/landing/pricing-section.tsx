"use client"

import { PlanSelector } from "@/components/billing/plan-selector"

export function PricingSection() {
  return (
    <section id="pricing" className="py-24 bg-muted/30">
      <div className="container px-4 mx-auto">
        <div className="text-center max-w-2xl mx-auto mb-16">
          <h2 className="text-3xl md:text-4xl font-bold mb-4">
            Simple, transparent <span className="text-primary">pricing</span>
          </h2>
          <p className="text-muted-foreground text-xl">
            Choose the plan that fits your needs. No hidden fees. Cancel anytime.
          </p>
        </div>

        <div className="max-w-6xl mx-auto">
          <PlanSelector showCurrentPlan={false} />
        </div>

        <div className="text-center mt-12">
          <p className="text-muted-foreground">
            Need higher limits?{" "}
            <a href="mailto:support@postbro.app" className="text-primary hover:underline font-medium">
              Contact us
            </a>{" "}
            for custom plans.
          </p>
        </div>
      </div>
    </section>
  )
}
