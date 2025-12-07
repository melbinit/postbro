"use client"

import { useRef } from "react"
import { motion, useInView } from "framer-motion"

// Animation component
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

export function HowItWorksSection() {
  return (
    <section id="how-it-works" className="py-14 sm:py-20 md:py-28 relative overflow-hidden">
      <div className="container px-4 mx-auto">
        <div className="text-center max-w-2xl mx-auto mb-10 sm:mb-16">
          <FadeInUp>
            <p className="text-[10px] sm:text-xs font-semibold text-primary uppercase tracking-wider mb-3 sm:mb-4">How It Works</p>
          </FadeInUp>
          <FadeInUp delay={0.1}>
            <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold mb-4 sm:mb-5 px-2 sm:px-0">
              From Post to Insights in <span className="text-primary">Seconds</span>
            </h2>
          </FadeInUp>
          <FadeInUp delay={0.2}>
            <p className="text-muted-foreground text-base sm:text-lg leading-relaxed px-2 sm:px-0">
              Copy a viral post link, paste it in PostBro, and get instant AI analysis.
            </p>
          </FadeInUp>
        </div>

        <div className="relative max-w-4xl mx-auto">
          {/* Connecting Line - Desktop */}
          <div className="hidden md:block absolute top-[52px] left-[16.67%] right-[16.67%] h-px">
            <div className="w-full h-full bg-gradient-to-r from-primary/20 via-primary/40 to-primary/20" />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 sm:gap-8 md:gap-6 relative">
            {/* Step 1 */}
            <FadeInUp delay={0.1} duration={0.8}>
              <div className="relative flex flex-col items-center text-center group">
                <div className="relative mb-4 sm:mb-6">
                  <div className="size-20 sm:size-[104px] rounded-xl sm:rounded-2xl bg-gradient-to-br from-primary/10 to-primary/5 flex items-center justify-center">
                    <div className="size-10 sm:size-14 rounded-lg sm:rounded-xl bg-card border border-border/50 flex items-center justify-center shadow-sm">
                      <span className="text-lg sm:text-xl font-bold text-primary">1</span>
                    </div>
                  </div>
                </div>
                <h3 className="text-base sm:text-lg font-semibold mb-2 sm:mb-3">Copy the Link</h3>
                <p className="text-muted-foreground text-xs sm:text-sm leading-relaxed max-w-[280px] mx-auto">
                  See a viral post? Copy the Instagram, X, or YouTube URL. No sign-ins needed.
                </p>
              </div>
            </FadeInUp>

            {/* Step 2 */}
            <FadeInUp delay={0.2} duration={0.8}>
              <div className="relative flex flex-col items-center text-center group">
                <div className="relative mb-4 sm:mb-6">
                  <div className="size-20 sm:size-[104px] rounded-xl sm:rounded-2xl bg-gradient-to-br from-primary/10 to-primary/5 flex items-center justify-center">
                    <div className="size-10 sm:size-14 rounded-lg sm:rounded-xl bg-card border border-border/50 flex items-center justify-center shadow-sm">
                      <span className="text-lg sm:text-xl font-bold text-primary">2</span>
                    </div>
                  </div>
                </div>
                <h3 className="text-base sm:text-lg font-semibold mb-2 sm:mb-3">AI Analyzes</h3>
                <p className="text-muted-foreground text-xs sm:text-sm leading-relaxed max-w-[280px] mx-auto">
                  Our AI analyzes images, captions, and engagement patterns to understand virality.
                </p>
              </div>
            </FadeInUp>

            {/* Step 3 */}
            <FadeInUp delay={0.3} duration={0.8}>
              <div className="relative flex flex-col items-center text-center group">
                <div className="relative mb-4 sm:mb-6">
                  <div className="size-20 sm:size-[104px] rounded-xl sm:rounded-2xl bg-gradient-to-br from-primary/10 to-primary/5 flex items-center justify-center">
                    <div className="size-10 sm:size-14 rounded-lg sm:rounded-xl bg-card border border-border/50 flex items-center justify-center shadow-sm">
                      <span className="text-lg sm:text-xl font-bold text-primary">3</span>
                    </div>
                  </div>
                </div>
                <h3 className="text-base sm:text-lg font-semibold mb-2 sm:mb-3">Get Insights</h3>
                <p className="text-muted-foreground text-xs sm:text-sm leading-relaxed max-w-[280px] mx-auto">
                  Understand why it went viral and get similar content ideas with captions.
                </p>
              </div>
            </FadeInUp>
          </div>
        </div>
      </div>
    </section>
  )
}
