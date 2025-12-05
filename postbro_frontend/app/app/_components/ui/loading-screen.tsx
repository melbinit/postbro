/**
 * Loading screen shown during initial mount and auth checks
 */
export function LoadingScreen({ message = "Loading..." }: { message?: string }) {
  return (
    <main className="flex-1 flex flex-col min-w-0 relative bg-background overflow-hidden h-full">
      <div className="flex items-center justify-center h-full">
        <div className="animate-pulse text-muted-foreground">{message}</div>
      </div>
    </main>
  )
}



