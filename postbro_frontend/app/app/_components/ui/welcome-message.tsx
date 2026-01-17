import { Sparkles, Instagram, Youtube, Twitter } from "lucide-react"

/**
 * Welcome message shown when no analysis is loaded
 * Modern SaaS-style centered design for 3-column layout
 */
export function WelcomeMessage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[50vh] text-center px-4">
      {/* Logo/Icon */}
      <div className="relative mb-6">
        <div className="size-16 rounded-2xl bg-gradient-to-br from-primary via-violet-500 to-purple-600 flex items-center justify-center shadow-lg shadow-primary/20">
          <Sparkles className="size-8 text-white" />
        </div>
        <div className="absolute -bottom-1 -right-1 size-6 rounded-full bg-emerald-500 border-2 border-background flex items-center justify-center">
          <span className="text-white text-xs">✓</span>
        </div>
      </div>
      
      {/* Heading */}
      <h1 className="text-2xl font-semibold text-foreground mb-2">
        Welcome to PostBro
      </h1>
      
      {/* Description */}
      <p className="text-muted-foreground max-w-md mb-8">
        I analyze social media posts to help you understand what makes content go viral. 
        Just paste a URL and I'll break down the magic.
      </p>
      
      {/* Platform badges */}
      <div className="flex items-center gap-3 mb-8">
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-gradient-to-r from-pink-500/10 to-purple-500/10 border border-pink-500/20">
          <Instagram className="size-4 text-pink-500" />
          <span className="text-xs font-medium text-pink-600 dark:text-pink-400">Instagram</span>
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-gradient-to-r from-red-500/10 to-orange-500/10 border border-red-500/20">
          <Youtube className="size-4 text-red-500" />
          <span className="text-xs font-medium text-red-600 dark:text-red-400">YouTube</span>
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-muted border border-border/50">
          <Twitter className="size-4 text-foreground" />
          <span className="text-xs font-medium">X / Twitter</span>
        </div>
      </div>
      
      {/* CTA hint */}
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <div className="size-2 rounded-full bg-primary animate-pulse" />
        <span>Paste a post URL below to get started</span>
      </div>
    </div>
  )
}



