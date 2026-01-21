/**
 * Welcome message shown when no analysis is loaded
 * Professional, clean design for 3-column layout
 */
export function WelcomeMessage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[50vh] text-center px-4">
      {/* Heading */}
      <h1 className="font-display text-3xl font-semibold text-foreground mb-3">
        Analyze Viral Content
      </h1>
      
      {/* Description */}
      <p className="text-muted-foreground max-w-lg text-base leading-relaxed mb-8">
        Get AI-powered insights on engagement patterns, content strategies, and what makes posts go viral.
      </p>
      
      {/* CTA hint */}
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <div className="size-2 rounded-full bg-primary" />
        <span>Enter a post URL below to begin analysis</span>
      </div>
    </div>
  )
}



