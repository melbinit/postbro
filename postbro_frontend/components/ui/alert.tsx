import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const alertVariants = cva(
  "relative w-full rounded-xl border px-4 py-3.5 text-sm grid has-[>svg]:grid-cols-[calc(var(--spacing)*4)_1fr] grid-cols-[0_1fr] has-[>svg]:gap-x-3 gap-y-1 items-start [&>svg]:size-4 [&>svg]:translate-y-0.5 [&>svg]:text-current transition-colors",
  {
    variants: {
      variant: {
        default: "bg-muted/50 border-border/50 text-foreground [&>svg]:text-muted-foreground",
        destructive:
          "bg-rose-50 dark:bg-rose-950/20 border-rose-200/50 dark:border-rose-900/30 text-rose-900 dark:text-rose-200 [&>svg]:text-rose-500 dark:[&>svg]:text-rose-400",
        warning:
          "bg-amber-50 dark:bg-amber-950/20 border-amber-200/50 dark:border-amber-900/30 text-amber-900 dark:text-amber-200 [&>svg]:text-amber-500 dark:[&>svg]:text-amber-400",
        success:
          "bg-emerald-50 dark:bg-emerald-950/20 border-emerald-200/50 dark:border-emerald-900/30 text-emerald-900 dark:text-emerald-200 [&>svg]:text-emerald-500 dark:[&>svg]:text-emerald-400",
        info:
          "bg-blue-50 dark:bg-blue-950/20 border-blue-200/50 dark:border-blue-900/30 text-blue-900 dark:text-blue-200 [&>svg]:text-blue-500 dark:[&>svg]:text-blue-400",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

function Alert({
  className,
  variant,
  ...props
}: React.ComponentProps<"div"> & VariantProps<typeof alertVariants>) {
  return (
    <div
      data-slot="alert"
      role="alert"
      className={cn(alertVariants({ variant }), className)}
      {...props}
    />
  )
}

function AlertTitle({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="alert-title"
      className={cn(
        "col-start-2 line-clamp-1 min-h-4 font-medium tracking-tight",
        className
      )}
      {...props}
    />
  )
}

function AlertDescription({
  className,
  ...props
}: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="alert-description"
      className={cn(
        "col-start-2 grid justify-items-start gap-1 text-sm [&_p]:leading-relaxed opacity-90",
        className
      )}
      {...props}
    />
  )
}

export { Alert, AlertTitle, AlertDescription }
