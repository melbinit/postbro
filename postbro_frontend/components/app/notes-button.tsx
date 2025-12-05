"use client"

import { Plus } from "lucide-react"
import { Button } from "@/components/ui/button"

interface NotesButtonProps {
  onClick: () => void
  className?: string
}

/**
 * Floating + button to open notes drawer
 */
export function NotesButton({ onClick, className }: NotesButtonProps) {
  return (
    <Button
      onClick={onClick}
      size="icon"
      className={`rounded-full shadow-lg hover:shadow-xl transition-shadow ${className || ""}`}
      aria-label="Open notes"
    >
      <Plus className="h-5 w-5" />
    </Button>
  )
}



