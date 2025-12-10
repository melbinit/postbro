/**
 * Welcome message shown when no analysis is loaded
 */
export function WelcomeMessage() {
  return (
    <div className="flex gap-4">
      <div className="flex-shrink-0">
        <div className="size-8 rounded-full bg-gradient-to-br from-primary to-purple-600 flex items-center justify-center">
          <span className="text-white text-sm font-bold">PB</span>
        </div>
      </div>
      <div className="flex-1 space-y-2">
        <div className="bg-card/60 backdrop-blur-sm rounded-2xl rounded-tl-sm p-4 border border-border/30">
          <p className="text-sm text-foreground">
            Hey! I'm PostBro. I can analyze any Instagram, X, or YouTube post to help you understand what makes content go viral.
          </p>
          <p className="text-sm text-muted-foreground mt-2">
            Share a post URL to get started.
          </p>
        </div>
      </div>
    </div>
  )
}



