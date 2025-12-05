'use client'

import * as React from 'react'
import * as TabsPrimitive from '@radix-ui/react-tabs'

import { cn } from '@/lib/utils'

function Tabs({
  className,
  ...props
}: React.ComponentProps<typeof TabsPrimitive.Root>) {
  return (
    <TabsPrimitive.Root
      data-slot="tabs"
      className={cn('flex flex-col gap-2', className)}
      {...props}
    />
  )
}

function TabsList({
  className,
  ...props
}: React.ComponentProps<typeof TabsPrimitive.List>) {
  return (
    <div className="w-full overflow-x-auto scrollbar-hide -mx-0.5 px-0.5">
      <TabsPrimitive.List
        data-slot="tabs-list"
        className={cn(
          'bg-muted/50 dark:bg-muted text-muted-foreground inline-flex h-auto min-h-[2.5rem] w-auto items-center justify-start rounded-lg p-1.5 border border-border/50 gap-1',
          className,
        )}
        {...props}
      />
    </div>
  )
}

function TabsTrigger({
  className,
  ...props
}: React.ComponentProps<typeof TabsPrimitive.Trigger>) {
  const ref = React.useRef<HTMLButtonElement>(null)
  
  React.useEffect(() => {
    const element = ref.current
    if (!element) return

    // Observe data-state attribute changes
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        if (mutation.type === 'attributes' && mutation.attributeName === 'data-state') {
          const isActive = element.getAttribute('data-state') === 'active'
          if (isActive) {
            // Small delay to ensure layout is complete
            setTimeout(() => {
              element.scrollIntoView({
                behavior: 'smooth',
                block: 'nearest',
                inline: 'center'
              })
            }, 100)
          }
        }
      })
    })

    observer.observe(element, {
      attributes: true,
      attributeFilter: ['data-state']
    })

    // Scroll on mount if already active
    if (element.getAttribute('data-state') === 'active') {
      setTimeout(() => {
        element.scrollIntoView({
          behavior: 'smooth',
          block: 'nearest',
          inline: 'center'
        })
      }, 100)
    }

    return () => observer.disconnect()
  }, [])
  
  return (
    <TabsPrimitive.Trigger
      ref={ref}
      data-slot="tabs-trigger"
      className={cn(
        "text-muted-foreground data-[state=active]:text-foreground data-[state=active]:bg-background data-[state=active]:border-border data-[state=active]:shadow-md dark:data-[state=active]:bg-input/30 dark:data-[state=active]:border-input focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:outline-ring inline-flex shrink-0 h-full min-h-[2.25rem] items-center justify-center gap-1.5 rounded-md border border-transparent px-4 py-2 text-sm font-medium whitespace-nowrap transition-all duration-200 focus-visible:ring-[3px] focus-visible:outline-1 disabled:pointer-events-none disabled:opacity-50 data-[state=active]:font-semibold data-[state=active]:ring-1 data-[state=active]:ring-primary/10 dark:data-[state=active]:ring-primary/20 hover:text-foreground [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
        className,
      )}
      {...props}
    />
  )
}

function TabsContent({
  className,
  ...props
}: React.ComponentProps<typeof TabsPrimitive.Content>) {
  return (
    <TabsPrimitive.Content
      data-slot="tabs-content"
      className={cn('flex-1 outline-none', className)}
      {...props}
    />
  )
}

export { Tabs, TabsList, TabsTrigger, TabsContent }
