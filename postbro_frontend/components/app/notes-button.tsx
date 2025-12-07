"use client"

import { FileText } from "lucide-react"
import { Button } from "@/components/ui/button"

interface NotesButtonProps {
  onClick: () => void
  className?: string
}

/**
 * Floating button to open notes drawer
 * Modern design with gradient and glow effect
 */
export function NotesButton({ onClick, className }: NotesButtonProps) {
  return (
    <Button
      onClick={onClick}
      size="icon"
      className={`
        relative h-12 w-12 rounded-2xl 
        bg-gradient-to-br from-primary to-primary/80 
        shadow-lg shadow-primary/25 
        hover:shadow-xl hover:shadow-primary/30 
        hover:scale-105 active:scale-95
        transition-all duration-200 
        group
        ${className || ""}
      `}
      aria-label="Open notes"
    >
      {/* Glow effect */}
      <div className="absolute inset-0 rounded-2xl bg-primary/20 blur-xl opacity-0 group-hover:opacity-60 transition-opacity duration-300" />
      
      {/* Icon with subtle animation */}
      <FileText className="h-5 w-5 relative z-10 transition-transform group-hover:rotate-[-8deg]" />
      
      {/* Subtle ring on hover */}
      <div className="absolute inset-0 rounded-2xl ring-2 ring-white/20 opacity-0 group-hover:opacity-100 transition-opacity" />
    </Button>
  )
}




