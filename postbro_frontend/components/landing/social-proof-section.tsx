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
    <section className="py-12 border-y border-border/50 bg-background/50">
      <div className="container px-4 mx-auto">
        <FadeInUp delay={0.1}>
          <h2 className="text-center text-3xl md:text-4xl font-bold text-foreground mb-10">Supported Platforms</h2>
        </FadeInUp>

        <div className="flex flex-wrap items-center justify-center gap-8 md:gap-12 max-w-5xl mx-auto">
          {/* Instagram - Active */}
          <FadeInUp delay={0.2}>
            <div className="flex flex-col items-center gap-3 group">
              <div className="relative size-24 md:size-28 rounded-xl bg-background border border-border p-4 shadow-sm hover:shadow-md transition-all hover:scale-105">
                <Image
                  src="https://img.icons8.com/?size=100&id=32323&format=png&color=000000"
                  alt="Instagram"
                  fill
                  className="object-contain p-2"
                />
              </div>
              <span className="text-sm font-medium text-foreground">Instagram</span>
            </div>
          </FadeInUp>

          {/* Twitter/X - Active */}
          <FadeInUp delay={0.3}>
            <div className="flex flex-col items-center gap-3 group">
              <div className="relative size-24 md:size-28 rounded-xl bg-background border border-border p-4 shadow-sm hover:shadow-md transition-all hover:scale-105">
                <Image
                  src="https://img.icons8.com/?size=100&id=phOKFKYpe00C&format=png&color=000000"
                  alt="Twitter"
                  fill
                  className="object-contain p-2 dark:invert"
                />
              </div>
              <span className="text-sm font-medium text-foreground">Twitter / X</span>
            </div>
          </FadeInUp>

          {/* YouTube - Active */}
          <FadeInUp delay={0.35}>
            <div className="flex flex-col items-center gap-3 group">
              <div className="relative size-24 md:size-28 rounded-xl bg-background border border-border p-4 shadow-sm hover:shadow-md transition-all hover:scale-105">
                <Image
                  src="https://img.icons8.com/?size=100&id=19318&format=png&color=000000"
                  alt="YouTube"
                  fill
                  className="object-contain p-2"
                />
              </div>
              <span className="text-sm font-medium text-foreground">YouTube</span>
            </div>
          </FadeInUp>

          {/* TikTok - Coming Soon */}
          <FadeInUp delay={0.45}>
            <div className="flex flex-col items-center gap-3 group relative">
              <div className="relative size-24 md:size-28 rounded-xl bg-background border border-border p-4 shadow-sm opacity-60">
                <Image
                  src="https://img.icons8.com/?size=100&id=118640&format=png&color=000000"
                  alt="TikTok"
                  fill
                  className="object-contain p-2"
                />
              </div>
              <div className="flex flex-col items-center gap-1">
                <span className="text-sm font-medium text-muted-foreground">TikTok</span>
                <span className="text-xs text-primary font-medium">Coming Soon</span>
              </div>
            </div>
          </FadeInUp>

          {/* Facebook - Coming Soon */}
          <FadeInUp delay={0.5}>
            <div className="flex flex-col items-center gap-3 group relative">
              <div className="relative size-24 md:size-28 rounded-xl bg-background border border-border p-4 shadow-sm opacity-60">
                <Image
                  src="https://img.icons8.com/?size=100&id=118497&format=png&color=000000"
                  alt="Facebook"
                  fill
                  className="object-contain p-2"
                />
              </div>
              <div className="flex flex-col items-center gap-1">
                <span className="text-sm font-medium text-muted-foreground">Facebook</span>
                <span className="text-xs text-primary font-medium">Coming Soon</span>
              </div>
            </div>
          </FadeInUp>
        </div>
      </div>
    </section>
  )
}
