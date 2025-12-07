"use client"

import Image from "next/image"
import { useRef } from "react"
import { motion, useInView } from "framer-motion"

// Reusable animation component (same as hero-section)
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

export function SocialProofSection() {
  return (
    <section className="py-10 sm:py-16 border-y border-border/30">
      <div className="container px-4 mx-auto">
        <FadeInUp delay={0.1}>
          <p className="text-center text-[10px] sm:text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-6 sm:mb-10">
            Supported Platforms
          </p>
        </FadeInUp>

        <div className="grid grid-cols-3 sm:flex sm:flex-wrap items-center justify-center gap-4 sm:gap-6 md:gap-10 max-w-4xl mx-auto">
          {/* Instagram - Active */}
          <FadeInUp delay={0.15}>
            <div className="flex flex-col items-center gap-2 sm:gap-3 group">
              <div className="relative size-14 sm:size-20 md:size-24 rounded-xl sm:rounded-2xl bg-card border border-border/50 p-2 sm:p-4 transition-all duration-300 group-hover:border-border group-hover:shadow-md">
                <Image
                  src="https://img.icons8.com/?size=100&id=32323&format=png&color=000000"
                  alt="Instagram"
                  fill
                  className="object-contain p-2 sm:p-3"
                />
              </div>
              <span className="text-xs sm:text-sm font-medium text-foreground">Instagram</span>
            </div>
          </FadeInUp>

          {/* Twitter/X - Active */}
          <FadeInUp delay={0.2}>
            <div className="flex flex-col items-center gap-2 sm:gap-3 group">
              <div className="relative size-14 sm:size-20 md:size-24 rounded-xl sm:rounded-2xl bg-card border border-border/50 p-2 sm:p-4 transition-all duration-300 group-hover:border-border group-hover:shadow-md">
                <Image
                  src="https://img.icons8.com/?size=100&id=phOKFKYpe00C&format=png&color=000000"
                  alt="Twitter"
                  fill
                  className="object-contain p-2 sm:p-3 dark:invert"
                />
              </div>
              <span className="text-xs sm:text-sm font-medium text-foreground">X / Twitter</span>
            </div>
          </FadeInUp>

          {/* YouTube - Active */}
          <FadeInUp delay={0.25}>
            <div className="flex flex-col items-center gap-2 sm:gap-3 group">
              <div className="relative size-14 sm:size-20 md:size-24 rounded-xl sm:rounded-2xl bg-card border border-border/50 p-2 sm:p-4 transition-all duration-300 group-hover:border-border group-hover:shadow-md">
                <Image
                  src="https://img.icons8.com/?size=100&id=19318&format=png&color=000000"
                  alt="YouTube"
                  fill
                  className="object-contain p-2 sm:p-3"
                />
              </div>
              <span className="text-xs sm:text-sm font-medium text-foreground">YouTube</span>
            </div>
          </FadeInUp>

          {/* TikTok - Coming Soon */}
          <FadeInUp delay={0.3}>
            <div className="flex flex-col items-center gap-2 sm:gap-3 group relative">
              <div className="relative size-14 sm:size-20 md:size-24 rounded-xl sm:rounded-2xl bg-muted/30 border border-border/30 p-2 sm:p-4 opacity-50">
                <Image
                  src="https://img.icons8.com/?size=100&id=118640&format=png&color=000000"
                  alt="TikTok"
                  fill
                  className="object-contain p-2 sm:p-3"
                />
              </div>
              <div className="flex flex-col items-center">
                <span className="text-xs sm:text-sm font-medium text-muted-foreground">TikTok</span>
                <span className="text-[8px] sm:text-[10px] text-primary font-medium uppercase tracking-wider">Soon</span>
              </div>
            </div>
          </FadeInUp>

          {/* Facebook - Coming Soon */}
          <FadeInUp delay={0.35}>
            <div className="flex flex-col items-center gap-2 sm:gap-3 group relative col-span-2 sm:col-span-1 justify-self-center">
              <div className="relative size-14 sm:size-20 md:size-24 rounded-xl sm:rounded-2xl bg-muted/30 border border-border/30 p-2 sm:p-4 opacity-50">
                <Image
                  src="https://img.icons8.com/?size=100&id=118497&format=png&color=000000"
                  alt="Facebook"
                  fill
                  className="object-contain p-2 sm:p-3"
                />
              </div>
              <div className="flex flex-col items-center">
                <span className="text-xs sm:text-sm font-medium text-muted-foreground">Facebook</span>
                <span className="text-[8px] sm:text-[10px] text-primary font-medium uppercase tracking-wider">Soon</span>
              </div>
            </div>
          </FadeInUp>
        </div>
      </div>
    </section>
  )
}
