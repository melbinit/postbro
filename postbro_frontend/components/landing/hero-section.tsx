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
    <section className="relative pt-24 pb-12 md:pt-40 md:pb-24 overflow-hidden">
      {/* Background gradients */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[1000px] h-[600px] opacity-30 pointer-events-none">
        <div className="absolute inset-0 bg-gradient-to-r from-blue-500/30 to-purple-500/30 blur-[100px] rounded-full mix-blend-multiply dark:mix-blend-screen animate-blob" />
      </div>

      <div className="container px-4 mx-auto relative z-10">
        <div className="text-center max-w-4xl mx-auto mb-8 md:mb-12">
          <FadeInUp delay={0.1}>
            <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-border bg-background/50 backdrop-blur-sm mb-6 text-sm font-medium text-muted-foreground shadow-sm hover:border-primary/50 transition-colors cursor-default">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
              </span>
              Analyze social posts instantly
            </div>
          </FadeInUp>

          <FadeInUp delay={0.2} duration={0.7}>
            <h1 className="text-4xl md:text-6xl lg:text-7xl font-semibold tracking-tight mb-6 bg-clip-text text-transparent bg-gradient-to-b from-foreground to-foreground/70 pb-2">
              Decode Viral Posts — Create <span className="text-primary">Viral Content</span>
            </h1>
          </FadeInUp>

          <FadeInUp delay={0.3} duration={0.7}>
            <p className="text-lg md:text-xl text-muted-foreground mb-8 max-w-2xl mx-auto leading-relaxed">
              Analyze any Instagram, X, or YouTube post by URL or username. <span className="font-medium text-foreground">AI</span> discovers why it went viral, shows detailed metrics, and generates similar post ideas to create your own winning content. Works with images, videos, and all content types.
            </p>
          </FadeInUp>

          <FadeInUp delay={0.4}>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Button
                size="lg"
                className="h-12 px-8 text-base bg-primary hover:bg-primary/90 shadow-lg shadow-primary/25 rounded-full"
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
                className="h-12 px-8 text-base bg-background/50 backdrop-blur-sm border-border hover:bg-accent/50 rounded-full"
                asChild
              >
                <Link href="#features">View Demo</Link>
              </Button>
            </div>
          </FadeInUp>
        </div>

        {/* Hero Visual */}
        <motion.div
          className="relative max-w-6xl mx-auto mt-8 md:mt-20 mb-8 md:mb-0"
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.2 }}
        >
          <div className="relative rounded-xl overflow-hidden min-h-[400px] md:min-h-[700px]">
            {/* Centered gradient blob */}
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[500px] opacity-20 pointer-events-none">
              <div className="absolute inset-0 bg-gradient-to-r from-primary/30 to-primary/10 blur-[100px] rounded-full mix-blend-multiply dark:mix-blend-screen" />
            </div>

            {/* Analysis Results Cards */}
            <div className="p-6 md:p-8 py-12 md:py-16 h-full flex flex-col items-center justify-center">
              <div className="w-full max-w-4xl">
                {/* Heading */}
                <div className="text-center mb-12 md:mb-16">
                  <FadeInUp delay={0.1} duration={0.8}>
                    <h3 className="text-2xl md:text-3xl lg:text-4xl font-semibold text-foreground mb-4 leading-tight">
                      Analyze <span className="text-primary">Captions</span>, <span className="text-primary">Images</span>, <span className="text-primary">Videos</span> & <span className="text-primary">Comments</span>
                    </h3>
                  </FadeInUp>
                  <FadeInUp delay={0.2} duration={0.8}>
                    <p className="text-base md:text-lg text-muted-foreground max-w-2xl mx-auto leading-relaxed">
                      Get engagement metrics, likes, comments count, and insights on why content performs
                    </p>
                  </FadeInUp>
                </div>

                {/* Analysis Results Cards */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 opacity-95 pointer-events-none select-none">
                  {/* Instagram Card - Entered via Username */}
                  <CardAnimation direction="left">
                    <div className="bg-background rounded-xl p-4 border border-border shadow-lg rotate-[-2deg] hover:rotate-0 transition-transform duration-300">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <div className="size-6 rounded-full bg-gradient-to-tr from-yellow-400 via-red-500 to-purple-500 p-[1.5px]">
                          <div className="size-full rounded-full bg-background flex items-center justify-center">
                            <Instagram className="size-3" />
                          </div>
                        </div>
                        <span className="text-xs text-muted-foreground">Analyzed via: @gymshark</span>
                      </div>
                    </div>
                    <div className="relative h-64 bg-muted/20 rounded-lg mb-3 overflow-hidden">
                      <img 
                        src="/gymshark_insta_2.jpg" 
                        alt="Gymshark Instagram post" 
                        className="w-full h-full object-cover object-top"
                      />
                      <div className="absolute top-2 right-2 bg-black/60 text-white text-[10px] px-2 py-1 rounded-full">
                        REEL
                      </div>
                    </div>
                    <div className="space-y-2 mb-3">
                      <div className="flex items-center gap-3 text-xs">
                        <span className="font-semibold">@gymshark</span>
                        <span className="text-muted-foreground">Don't give up #gymshark</span>
                      </div>
                      <div className="flex items-center gap-4 text-xs text-muted-foreground">
                        <span className="font-medium">1.1M views</span>
                        <span>45K likes</span>
                        <span>2.3K comments</span>
                      </div>
                    </div>
                    </div>
                  </CardAnimation>

                  {/* Twitter/X Card - Entered via URL */}
                  <CardAnimation direction="right">
                    <div className="bg-background rounded-xl p-4 border border-border shadow-lg rotate-[2deg] hover:rotate-0 transition-transform duration-300 mt-8 md:mt-0">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <div className="size-6 rounded-full bg-foreground text-background flex items-center justify-center">
                          <Twitter className="size-3" />
                        </div>
                        <span className="text-xs text-muted-foreground">Analyzed via: URL</span>
                      </div>
                    </div>
                    <div className="relative h-56 bg-muted/20 rounded-lg mb-3 overflow-hidden">
                      <img 
                        src="/tanya_x.jpeg" 
                        alt="Tanya's tweet" 
                        className="w-full h-full object-cover object-top"
                      />
                    </div>
                    <div className="space-y-2 mb-3">
                      <div className="flex items-center gap-2 text-xs">
                        <span className="font-semibold">Tanya</span>
                        <span className="text-muted-foreground">@Tanya_Sabrinaaa</span>
                        <span className="text-muted-foreground">· Nov 19</span>
                      </div>
                      <p className="text-base leading-relaxed">
                        wearing shoes that are way too big for you is the male equivalent of stuffing your bra
                      </p>
                      <div className="flex items-center gap-4 text-xs text-muted-foreground">
                        <span>3.7M views</span>
                        <span>124K</span>
                        <span>18K</span>
                        <span>2.1K</span>
                      </div>
                    </div>
                    </div>
                  </CardAnimation>
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  )
}

