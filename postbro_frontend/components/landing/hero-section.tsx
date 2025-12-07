"use client"

import { Button } from "@/components/ui/button"
import Link from "next/link"
import { ArrowRight, Sparkles, Instagram, Twitter } from "lucide-react"
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

// Card animation component
function CardAnimation({ 
  children, 
  direction 
}: { 
  children: React.ReactNode
  direction: "left" | "right" 
}) {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: "-100px" })

  return (
    <motion.div
      ref={ref}
      initial={{ 
        opacity: 0, 
        x: direction === "left" ? -100 : 100,
        y: 50
      }}
      animate={isInView ? { 
        opacity: 1, 
        x: 0,
        y: 0
      } : { 
        opacity: 0, 
        x: direction === "left" ? -100 : 100,
        y: 50
      }}
      transition={{ 
        duration: 1, 
        ease: [0.16, 1, 0.3, 1],
        delay: direction === "left" ? 0.1 : 0.2
      }}
    >
      {children}
    </motion.div>
  )
}

export function HeroSection() {
  return (
    <section className="relative pt-24 pb-12 md:pt-36 md:pb-20 overflow-hidden">
      {/* Subtle background elements */}
      <div className="absolute inset-0 pointer-events-none">
        {/* Very subtle gradient orbs */}
        <div className="absolute top-20 left-1/4 w-[500px] h-[500px] bg-primary/[0.03] rounded-full blur-[120px]" />
        <div className="absolute top-40 right-1/4 w-[400px] h-[400px] bg-purple-500/[0.02] rounded-full blur-[100px]" />
        
        {/* Subtle grid pattern */}
        <div className="absolute inset-0 bg-[linear-gradient(to_right,transparent_0%,transparent_49%,var(--border)_50%,transparent_51%,transparent_100%),linear-gradient(to_bottom,transparent_0%,transparent_49%,var(--border)_50%,transparent_51%,transparent_100%)] bg-[size:80px_80px] opacity-[0.03]" />
      </div>

      <div className="container px-4 mx-auto relative z-10">
        <div className="text-center max-w-4xl mx-auto mb-8 md:mb-16">
          <FadeInUp delay={0.1}>
            <div className="inline-flex items-center gap-2 px-3 py-1.5 sm:px-4 sm:py-2 rounded-full border border-border/50 bg-card/50 backdrop-blur-sm mb-6 sm:mb-8 text-xs sm:text-sm font-medium text-muted-foreground shadow-sm">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
              </span>
              Analyze social posts instantly
            </div>
          </FadeInUp>

          <FadeInUp delay={0.2} duration={0.7}>
            <h1 className="text-3xl sm:text-4xl md:text-5xl lg:text-6xl font-bold tracking-tight mb-5 sm:mb-6 text-foreground px-2 sm:px-0">
              Decode Viral Posts
              <br className="sm:hidden" />
              <span className="hidden sm:inline"> — </span>
              <span className="sm:hidden block mt-1" />
              <span className="bg-gradient-to-r from-primary to-primary/70 bg-clip-text text-transparent">
                Create Viral Content
              </span>
            </h1>
          </FadeInUp>

          <FadeInUp delay={0.3} duration={0.7}>
            <p className="text-base sm:text-lg md:text-xl text-muted-foreground mb-8 sm:mb-10 max-w-2xl mx-auto leading-relaxed px-2 sm:px-0">
              Analyze any Instagram, X, or YouTube post.{" "}
              <span className="font-medium text-foreground">AI</span> discovers why it went viral and generates similar post ideas.
            </p>
          </FadeInUp>

          <FadeInUp delay={0.4}>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-3 sm:gap-4 px-4 sm:px-0">
              <Button
                size="lg"
                className="w-full sm:w-auto h-11 sm:h-12 px-6 sm:px-8 text-sm sm:text-base font-medium bg-foreground text-background hover:bg-foreground/90 rounded-xl shadow-lg hover:shadow-xl transition-all duration-300 hover:-translate-y-0.5"
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
                className="w-full sm:w-auto h-11 sm:h-12 px-6 sm:px-8 text-sm sm:text-base font-medium bg-transparent border-border/60 hover:bg-muted/50 rounded-xl transition-all duration-300"
                asChild
              >
                <Link href="#features">See How It Works</Link>
              </Button>
            </div>
          </FadeInUp>
          
          {/* Trust indicators - Mobile optimized */}
          <FadeInUp delay={0.5}>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-3 sm:gap-6 mt-8 sm:mt-10 text-sm text-muted-foreground">
              <div className="flex items-center gap-2">
                <Sparkles className="size-4 text-primary" />
                <span>AI-Powered</span>
              </div>
              <div className="hidden sm:block w-1 h-1 rounded-full bg-border" />
              <span className="text-center">No account connection</span>
              <div className="hidden sm:block w-1 h-1 rounded-full bg-border" />
              <span>Free tier available</span>
            </div>
          </FadeInUp>
        </div>

        {/* Hero Visual - Refined & Mobile Optimized */}
        <motion.div
          className="relative max-w-5xl mx-auto mt-4 sm:mt-0"
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.3 }}
        >
          {/* Subtle background for cards area */}
          <div className="absolute inset-0 bg-gradient-to-b from-muted/30 via-muted/20 to-transparent rounded-2xl sm:rounded-3xl -z-10" />
          
          <div className="relative rounded-xl sm:rounded-2xl p-4 sm:p-6 md:p-10">
            {/* Section heading */}
            <div className="text-center mb-6 sm:mb-10">
              <FadeInUp delay={0.1} duration={0.8}>
                <p className="text-[10px] sm:text-xs font-semibold text-primary uppercase tracking-wider mb-2 sm:mb-3">What You Can Analyze</p>
                <h3 className="text-base sm:text-xl md:text-2xl font-semibold text-foreground">
                  <span className="hidden sm:inline">Captions • Images • Videos • Comments</span>
                  <span className="sm:hidden">Captions, Images, Videos & Comments</span>
                </h3>
              </FadeInUp>
            </div>

            {/* Analysis Results Cards - Mobile Optimized */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6 lg:gap-8 pointer-events-none select-none">
              {/* Instagram Card */}
              <CardAnimation direction="left">
                <div className="bg-card rounded-xl sm:rounded-2xl p-4 sm:p-5 border border-border/40 shadow-lg shadow-black/[0.03] dark:shadow-black/20 sm:rotate-[-1deg] sm:hover:rotate-0 transition-all duration-500">
                  <div className="flex items-center gap-2.5 sm:gap-3 mb-3 sm:mb-4">
                    <div className="size-7 sm:size-8 rounded-full bg-gradient-to-tr from-amber-400 via-rose-500 to-purple-600 p-[2px]">
                      <div className="size-full rounded-full bg-card flex items-center justify-center">
                        <Instagram className="size-3 sm:size-4" />
                      </div>
                    </div>
                    <div>
                      <p className="text-xs sm:text-sm font-semibold">@gymshark</p>
                      <p className="text-[10px] sm:text-xs text-muted-foreground">Instagram Reel</p>
                    </div>
                  </div>
                  <div className="relative aspect-[4/3] sm:aspect-[4/5] bg-muted/30 rounded-lg sm:rounded-xl mb-3 sm:mb-4 overflow-hidden">
                    <img 
                      src="/gymshark_insta_2.jpg" 
                      alt="Gymshark Instagram post" 
                      className="w-full h-full object-cover object-top"
                    />
                    <div className="absolute top-2 sm:top-3 right-2 sm:right-3 bg-black/70 text-white text-[9px] sm:text-[10px] font-medium px-2 py-0.5 sm:px-2.5 sm:py-1 rounded-full backdrop-blur-sm">
                      REEL
                    </div>
                  </div>
                  <div className="space-y-2 sm:space-y-3">
                    <p className="text-xs sm:text-sm text-muted-foreground line-clamp-1 sm:line-clamp-2">Don't give up 💪 #gymshark</p>
                    <div className="flex items-center gap-3 sm:gap-4 text-[10px] sm:text-xs">
                      <span className="font-semibold text-foreground">1.1M views</span>
                      <span className="text-muted-foreground">45K likes</span>
                      <span className="text-muted-foreground hidden sm:inline">2.3K comments</span>
                    </div>
                  </div>
                </div>
              </CardAnimation>

              {/* Twitter/X Card */}
              <CardAnimation direction="right">
                <div className="bg-card rounded-xl sm:rounded-2xl p-4 sm:p-5 border border-border/40 shadow-lg shadow-black/[0.03] dark:shadow-black/20 sm:rotate-[1deg] sm:hover:rotate-0 transition-all duration-500 md:mt-8">
                  <div className="flex items-center gap-2.5 sm:gap-3 mb-3 sm:mb-4">
                    <div className="size-7 sm:size-8 rounded-full bg-foreground flex items-center justify-center">
                      <Twitter className="size-3 sm:size-4 text-background" />
                    </div>
                    <div>
                      <p className="text-xs sm:text-sm font-semibold">Tanya <span className="font-normal text-muted-foreground text-[10px] sm:text-xs">@Tanya_Sabrinaaa</span></p>
                      <p className="text-[10px] sm:text-xs text-muted-foreground">Nov 19</p>
                    </div>
                  </div>
                  <div className="relative aspect-[16/10] sm:aspect-video bg-muted/30 rounded-lg sm:rounded-xl mb-3 sm:mb-4 overflow-hidden">
                    <img 
                      src="/tanya_x.jpeg" 
                      alt="Tanya's tweet" 
                      className="w-full h-full object-cover object-top"
                    />
                  </div>
                  <div className="space-y-2 sm:space-y-3">
                    <p className="text-xs sm:text-sm leading-relaxed line-clamp-2">
                      wearing shoes that are way too big for you is the male equivalent of stuffing your bra
                    </p>
                    <div className="flex items-center gap-3 sm:gap-4 text-[10px] sm:text-xs">
                      <span className="font-semibold text-foreground">3.7M views</span>
                      <span className="text-muted-foreground">124K ♥</span>
                      <span className="text-muted-foreground">18K ↻</span>
                    </div>
                  </div>
                </div>
              </CardAnimation>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  )
}

