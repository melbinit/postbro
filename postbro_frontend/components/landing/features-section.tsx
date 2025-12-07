"use client"

import { Sparkles, Lightbulb, TrendingUp, Search, Image, Calendar, Zap, Target, Users, Briefcase } from "lucide-react"
import { useRef } from "react"
import { motion, useInView } from "framer-motion"

const features = [
  {
    icon: Search,
    title: "Analyze Any Public Post",
    description:
      "No account connections needed. Simply paste any public post URL to analyze it instantly. Study what works for others, analyze your own posts, or explore any viral content. Works with Instagram, X (Twitter), and YouTube.",
    color: "text-blue-500",
  },
  {
    icon: Image,
    title: "Complete Visual Analysis",
    description:
      "Our AI analyzes everything - images, videos, captions, and context. Get insights on visual composition, colors, text placement, and what makes content visually engaging. Not just metrics - understand the why.",
    color: "text-purple-500",
  },
  {
    icon: TrendingUp,
    title: "Viral Content Intelligence",
    description:
      "Understand why posts go viral with AI-powered analysis. See detailed engagement metrics, reach, and get explanations of what drove the performance. Learn from top-performing content instantly.",
    color: "text-green-500",
  },
  {
    icon: Lightbulb,
    title: "AI-Generated Post Ideas",
    description:
      "Get actionable content ideas based on successful posts. Each suggestion includes captions, hashtags, and visual recommendations tailored to your niche. Turn insights into your next viral post.",
    color: "text-yellow-500",
  },
]

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

const useCases = [
  {
    icon: Target,
    title: "Content Creators",
    description: "Analyze what works in your niche. Get post ideas inspired by top performers. Understand why certain content resonates with your audience.",
    color: "text-pink-500",
  },
  {
    icon: Briefcase,
    title: "Marketing Agencies",
    description: "Analyze any public post by pasting its URL. Study what works for others in your industry, benchmark performance, and create data-backed content recommendations for your clients.",
    color: "text-blue-500",
  },
  {
    icon: Users,
    title: "Social Media Managers",
    description: "Paste any public post URL to analyze it instantly. Understand engagement patterns, identify trends, and generate content ideas in seconds—no complex tools needed.",
    color: "text-purple-500",
  },
  {
    icon: Zap,
    title: "Small Businesses",
    description: "Learn from successful brands in your industry. Get content inspiration and understand what drives engagement without expensive tools.",
    color: "text-orange-500",
  },
]

export function FeaturesSection() {
  return (
    <section id="features" className="py-14 sm:py-20 md:py-28 relative">
      {/* Subtle background */}
      <div className="absolute inset-0 bg-gradient-to-b from-muted/40 via-muted/20 to-transparent pointer-events-none" />
      
      <div className="container px-4 mx-auto relative">
        <div className="text-center max-w-2xl mx-auto mb-10 sm:mb-16">
          <FadeInUp>
            <p className="text-[10px] sm:text-xs font-semibold text-primary uppercase tracking-wider mb-3 sm:mb-4">Features</p>
          </FadeInUp>
          <FadeInUp delay={0.1}>
            <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold mb-4 sm:mb-5 px-2 sm:px-0">
              Analyze Viral Posts, Get{" "}
              <span className="text-primary">Content Ideas</span>
            </h2>
          </FadeInUp>
          <FadeInUp delay={0.2}>
            <p className="text-muted-foreground text-base sm:text-lg leading-relaxed px-2 sm:px-0">
              Paste any post URL and get AI-powered insights plus content ideas with captions.
            </p>
          </FadeInUp>
        </div>

        {/* Core Features - Bento-style grid */}
        <div className="mb-14 sm:mb-20">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-5">
            {features.map((feature, index) => (
              <FadeInUp key={index} delay={index * 0.1} duration={0.7}>
                <div className="group relative p-5 sm:p-6 md:p-8 bg-card rounded-xl sm:rounded-2xl border border-border/50 hover:border-border transition-all duration-300">
                  {/* Subtle gradient on hover */}
                  <div className="absolute inset-0 bg-gradient-to-br from-primary/[0.02] to-transparent opacity-0 group-hover:opacity-100 transition-opacity rounded-xl sm:rounded-2xl" />
                  
                  <div className="relative">
                    <div className={`size-10 sm:size-11 rounded-lg sm:rounded-xl flex items-center justify-center mb-4 sm:mb-5 ${feature.color} bg-current/10`}>
                      <feature.icon className="size-4 sm:size-5" />
                    </div>
                    <h3 className="text-base sm:text-lg font-semibold mb-2 sm:mb-3">{feature.title}</h3>
                    <p className="text-muted-foreground leading-relaxed text-sm sm:text-[15px]">{feature.description}</p>
                  </div>
                </div>
              </FadeInUp>
            ))}
          </div>
        </div>

        {/* Use Cases */}
        <div>
          <FadeInUp>
            <p className="text-[10px] sm:text-xs font-semibold text-primary uppercase tracking-wider mb-3 sm:mb-4 text-center">Who It's For</p>
          </FadeInUp>
          <FadeInUp delay={0.1}>
            <h3 className="text-xl sm:text-2xl font-bold mb-6 sm:mb-10 text-center">Built for creators and marketers</h3>
          </FadeInUp>
          
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
            {useCases.map((useCase, index) => (
              <FadeInUp key={index} delay={index * 0.08} duration={0.6}>
                <div className="group relative p-4 sm:p-5 bg-card rounded-lg sm:rounded-xl border border-border/50 hover:border-border transition-all duration-300 text-center h-full">
                  <div className={`size-8 sm:size-10 rounded-lg flex items-center justify-center mb-3 sm:mb-4 mx-auto ${useCase.color} bg-current/10`}>
                    <useCase.icon className="size-4 sm:size-5" />
                  </div>
                  <h4 className="text-sm sm:text-base font-semibold mb-1.5 sm:mb-2">{useCase.title}</h4>
                  <p className="text-muted-foreground text-xs sm:text-sm leading-relaxed line-clamp-4 sm:line-clamp-none">{useCase.description}</p>
                </div>
              </FadeInUp>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
