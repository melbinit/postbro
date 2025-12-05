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
    <section id="features" className="pt-16 pb-24 md:py-24 bg-muted/30">
      <div className="container px-4 mx-auto">
        <div className="text-center max-w-2xl mx-auto mb-16">
          <h2 className="text-3xl md:text-4xl font-bold mb-4">
            Analyze Viral Posts, Get <span className="text-primary">Similar Content Ideas</span>
          </h2>
          <p className="text-muted-foreground text-xl">
            Paste any post URL and get AI-powered insights plus similar post ideas with captions and recommendations. Works with your posts or any viral content.
          </p>
        </div>

        {/* Core Features */}
        <div className="mb-16">
          <h3 className="text-2xl font-bold mb-8 text-center">What PostBro Does</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {features.map((feature, index) => (
              <FadeInUp key={index} delay={index * 0.1} duration={0.7}>
                <div
                  className="group p-6 bg-background rounded-2xl border border-border shadow-sm hover:shadow-md transition-all duration-300 hover:-translate-y-1"
                >
                <div
                  className={`size-12 rounded-xl bg-background border border-border flex items-center justify-center mb-4 group-hover:scale-110 transition-transform duration-300 shadow-sm ${feature.color}`}
                >
                  <feature.icon className="size-6" />
                </div>
                <h3 className="text-xl font-semibold mb-3">{feature.title}</h3>
                <p className="text-muted-foreground leading-relaxed text-base">{feature.description}</p>
                </div>
              </FadeInUp>
            ))}
          </div>
        </div>

        {/* Use Cases */}
        <div>
          <h3 className="text-2xl font-bold mb-8 text-center">Who It's For</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {useCases.map((useCase, index) => (
              <FadeInUp key={index} delay={index * 0.1} duration={0.7}>
                <div
                  className="group p-6 bg-background rounded-2xl border border-border shadow-sm hover:shadow-md transition-all duration-300 hover:-translate-y-1 text-center"
                >
                <div
                  className={`size-12 rounded-xl bg-background border border-border flex items-center justify-center mb-4 group-hover:scale-110 transition-transform duration-300 shadow-sm mx-auto ${useCase.color}`}
                >
                  <useCase.icon className="size-6" />
                </div>
                <h3 className="text-lg font-semibold mb-3">{useCase.title}</h3>
                <p className="text-muted-foreground leading-relaxed text-base">{useCase.description}</p>
                </div>
              </FadeInUp>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
