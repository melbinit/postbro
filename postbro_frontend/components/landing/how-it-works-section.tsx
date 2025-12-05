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
    <section id="how-it-works" className="py-24 relative overflow-hidden">
      <div className="container px-4 mx-auto">
        <div className="text-center max-w-2xl mx-auto mb-20">
          <div className="inline-flex items-center justify-center px-4 py-1.5 rounded-full bg-primary/10 text-primary text-sm font-medium mb-6">
            Simple Process
          </div>
          <h2 className="text-3xl md:text-4xl font-bold mb-4">
            From Post to Insights in <span className="text-primary">Seconds</span>
          </h2>
          <p className="text-muted-foreground text-xl">
            You saw a post go viral and want to know why. Simply copy the link and let PostBro do the work. We'll analyze why it went viral, read the comments to understand what people are saying, explain why people are liking it, and give you similar content ideas.
          </p>
        </div>

        <div className="relative">
          {/* Connecting Line */}
          <div className="hidden md:block absolute top-1/2 left-0 w-full h-0.5 bg-gradient-to-r from-transparent via-border to-transparent -translate-y-1/2" />

          <div className="grid grid-cols-1 md:grid-cols-3 gap-12 relative">
            {/* Step 1 */}
            <FadeInUp delay={0.1} duration={0.8}>
              <div className="relative flex flex-col items-center text-center group">
                <div className="size-16 rounded-2xl bg-background border-2 border-primary/20 flex items-center justify-center mb-6 shadow-lg z-10 group-hover:border-primary transition-colors">
                  <span className="text-2xl font-bold text-primary">1</span>
                </div>
                <h3 className="text-xl font-bold mb-3">Copy the Link</h3>
                <p className="text-muted-foreground text-base">
                  You see a post that's getting tons of engagement. Copy the Instagram, X, or YouTube post URL and paste it into PostBro. That's it - no sign-ins or account connections needed.
                </p>
              </div>
            </FadeInUp>

            {/* Step 2 */}
            <FadeInUp delay={0.2} duration={0.8}>
              <div className="relative flex flex-col items-center text-center group">
                <div className="size-16 rounded-2xl bg-background border-2 border-primary/20 flex items-center justify-center mb-6 shadow-lg z-10 group-hover:border-primary transition-colors">
                  <span className="text-2xl font-bold text-primary">2</span>
                </div>
                <h3 className="text-xl font-bold mb-3">PostBro Analyzes</h3>
                <p className="text-muted-foreground text-base">
                  Our AI reads through comments, analyzes the images and captions, and studies the engagement patterns. It figures out why people are engaging and what made this post go viral.
                </p>
              </div>
            </FadeInUp>

            {/* Step 3 */}
            <FadeInUp delay={0.3} duration={0.8}>
              <div className="relative flex flex-col items-center text-center group">
                <div className="size-16 rounded-2xl bg-background border-2 border-primary/20 flex items-center justify-center mb-6 shadow-lg z-10 group-hover:border-primary transition-colors">
                  <span className="text-2xl font-bold text-primary">3</span>
                </div>
                <h3 className="text-xl font-bold mb-3">Get Why It Went Viral + Ideas</h3>
                <p className="text-muted-foreground text-base">
                  You get a clear explanation of why the post went viral, what people are saying in the comments, and why they're liking it. Plus, we give you similar content ideas with captions and recommendations you can use.
                </p>
              </div>
            </FadeInUp>
          </div>
        </div>
      </div>
    </section>
  )
}
