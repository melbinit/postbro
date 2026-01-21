"use client"

import { Instagram, Twitter } from "lucide-react"
import { motion, useInView } from "framer-motion"
import { useRef } from "react"

// Reusable animation components
function FadeInUp({ 
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

export function SupportedPlatformsSection() {
  return (
    <section className="py-14 sm:py-20 md:py-28 relative">
      <div className="container px-4 mx-auto">
        <motion.div
          className="relative max-w-5xl mx-auto"
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
                <h3 className="font-display text-base sm:text-xl md:text-2xl font-semibold text-foreground">
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
