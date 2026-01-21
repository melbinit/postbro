"use client"

import { Button } from "@/components/ui/button"
import Link from "next/link"
import { ArrowRight, Sparkles, ShieldCheck, Gift } from "lucide-react"
import { motion, useInView } from "framer-motion"
import { useRef } from "react"

// Reusable animation components for performance
export function FadeInUp({ 
  children, 
  delay = 0,
  duration = 0.6
}: { 
  children: React.ReactNode
  delay?: number
  duration?: number
}) {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: "-50px" })

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 30 }}
      animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 30 }}
      transition={{ 
        duration, 
        ease: [0.16, 1, 0.3, 1],
        delay
      }}
    >
      {children}
    </motion.div>
  )
}

function FadeIn({ 
  children, 
  delay = 0,
  duration = 0.8
}: { 
  children: React.ReactNode
  delay?: number
  duration?: number
}) {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: "-50px" })

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0 }}
      animate={isInView ? { opacity: 1 } : { opacity: 0 }}
      transition={{ 
        duration, 
        ease: [0.16, 1, 0.3, 1],
        delay
      }}
    >
      {children}
    </motion.div>
  )
}

export function HeroSection() {
  return (
    <section className="relative pt-24 pb-12 md:pt-36 md:pb-20 overflow-hidden bg-hero-gradient">
      {/* Subtle background elements */}
      <div className="absolute inset-0 pointer-events-none">
        {/* Subtle grid pattern */}
        <div className="absolute inset-0 bg-[linear-gradient(to_right,transparent_0%,transparent_49%,var(--border)_50%,transparent_51%,transparent_100%),linear-gradient(to_bottom,transparent_0%,transparent_49%,var(--border)_50%,transparent_51%,transparent_100%)] bg-[size:80px_80px] opacity-[0.02]" />
      </div>

      <div className="container px-4 mx-auto relative z-10">
        <div className="text-center max-w-4xl mx-auto mb-8 md:mb-16">
          <FadeInUp delay={0.1} duration={0.7}>
            <h1 className="font-display text-3xl sm:text-4xl md:text-5xl lg:text-6xl font-bold tracking-tight mb-5 sm:mb-6 text-foreground px-2 sm:px-0">
              Decode Viral Posts
              <br className="sm:hidden" />
              <span className="hidden sm:inline"> — </span>
              <span className="sm:hidden block mt-1" />
              <span className="bg-gradient-to-r from-primary to-emerald-600 dark:to-emerald-400 bg-clip-text text-transparent">
                Create Viral Content
              </span>
            </h1>
          </FadeInUp>

          <FadeInUp delay={0.2} duration={0.7}>
            <p className="text-base sm:text-lg md:text-xl text-muted-foreground mb-8 sm:mb-10 max-w-2xl mx-auto leading-relaxed px-2 sm:px-0">
              Analyze any Instagram, X, or YouTube post.{" "}
              <span className="font-medium text-foreground">AI</span> discovers why it went viral and generates similar post ideas.
            </p>
          </FadeInUp>

          <FadeInUp delay={0.3}>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-3 sm:gap-4 px-4 sm:px-0">
              <Button
                size="lg"
                className="w-full sm:w-auto h-11 sm:h-12 px-6 sm:px-8 text-sm sm:text-base font-semibold bg-primary text-primary-foreground hover:bg-primary/90 rounded-md shadow-lg hover:shadow-xl transition-all duration-300 hover:-translate-y-0.5"
                asChild
              >
                <Link href="/signup">
                  Get Started Free
                  <ArrowRight className="ml-2 size-4" />
                </Link>
              </Button>
              <Button
                size="lg"
                variant="outline"
                className="w-full sm:w-auto h-11 sm:h-12 px-6 sm:px-8 text-sm sm:text-base font-medium bg-transparent border-border hover:bg-muted/50 rounded-md transition-all duration-300"
                asChild
              >
                <Link href="#features">See How It Works</Link>
              </Button>
            </div>
          </FadeInUp>
          
          {/* Trust indicators - Mobile optimized */}
          <FadeInUp delay={0.4}>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-3 sm:gap-6 mt-8 sm:mt-10 text-sm text-muted-foreground">
              <div className="flex items-center gap-2">
                <Sparkles className="size-4 text-primary" />
                <span>AI-Powered</span>
              </div>
              <div className="hidden sm:block w-1 h-1 rounded-full bg-border" />
              <div className="flex items-center gap-2">
                <ShieldCheck className="size-4 text-primary" />
                <span>No account connection</span>
              </div>
              <div className="hidden sm:block w-1 h-1 rounded-full bg-border" />
              <div className="flex items-center gap-2">
                <Gift className="size-4 text-primary" />
                <span>Free tier available</span>
              </div>
            </div>
          </FadeInUp>
        </div>
      </div>
    </section>
  )
}

