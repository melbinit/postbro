"use client"

import { HeroSection } from "@/components/landing/hero-section"
import { FeaturesSection } from "@/components/landing/features-section"
import { HowItWorksSection } from "@/components/landing/how-it-works-section"
import { PricingSection } from "@/components/landing/pricing-section"
import { SocialProofSection } from "@/components/landing/social-proof-section"
import { FAQSection } from "@/components/landing/faq-section"
import { LandingHeader } from "@/components/layout/landing-header"
import { Footer } from "@/components/layout/footer"
import { useEffect } from "react"

export default function LandingPage() {
  useEffect(() => {
    // Handle hash scrolling after page load
    const handleHashScroll = () => {
      if (typeof window !== "undefined" && window.location.hash) {
        const hash = window.location.hash.substring(1)
        const element = document.getElementById(hash)
        if (element) {
          // Small delay to ensure page is fully rendered
          setTimeout(() => {
            element.scrollIntoView({ behavior: "smooth", block: "start" })
          }, 100)
        }
      }
    }

    // Run on mount and after a short delay to ensure DOM is ready
    handleHashScroll()
    const timeout = setTimeout(handleHashScroll, 300)

    return () => clearTimeout(timeout)
  }, [])

  return (
    <div className="flex min-h-screen flex-col">
      <LandingHeader />
      <main className="flex-1">
        <HeroSection />
        <FeaturesSection />
        <HowItWorksSection />
        <SocialProofSection />
        <PricingSection />
        <FAQSection />
      </main>
      <Footer />
    </div>
  )
}
