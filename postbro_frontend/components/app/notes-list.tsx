"use client"

import { useState, useEffect } from "react"
import { FileText, Loader2, Trash2, Sparkles } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { notesApi, type AnalysisNote } from "@/lib/api"
import { format } from "date-fns"
import { NotesDrawer } from "./notes-drawer"

interface NotesListProps {
  onNoteClick?: (note: AnalysisNote) => void
  onNavigate?: () => void
}

/**
 * Notes list component for sidebar
 * Shows all user notes, newest first
 */
export function NotesList({ onNoteClick, onNavigate }: NotesListProps) {
  const [notes, setNotes] = useState<AnalysisNote[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [selectedNote, setSelectedNote] = useState<AnalysisNote | null>(null)
  const [isDrawerOpen, setIsDrawerOpen] = useState(false)

  useEffect(() => {
    loadNotes()
  }, [])

  const loadNotes = async () => {
    setIsLoading(true)
    try {
      const response = await notesApi.listNotes()
      setNotes(response.notes)
    } catch (error) {
      console.error("Failed to load notes:", error)
      setNotes([])
    } finally {
      setIsLoading(false)
    }
  }

  const handleNoteClick = (note: AnalysisNote) => {
    setSelectedNote(note)
    setIsDrawerOpen(true)
    onNoteClick?.(note)
  }

  const handleNoteSaved = () => {
    loadNotes() // Refresh list
    // Note: Modal closing is handled by NotesDrawer itself after save
  }

  if (isLoading) {
    return (
      <div className="space-y-2 p-2">
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-20 w-full rounded-xl" />
        ))}
      </div>
    )
  }

  if (notes.length === 0) {
    return (
      <div className="p-6 text-center">
        <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-br from-primary/10 to-primary/5 mb-4">
          <FileText className="h-6 w-6 text-primary/70" />
        </div>
        <p className="text-sm font-medium text-foreground mb-1">No notes yet</p>
        <p className="text-xs text-muted-foreground leading-relaxed">
          Save insights from your analyses by clicking the notes button
        </p>
      </div>
    )
  }

  return (
    <>
      <div className="space-y-1.5 p-2">
        {notes.map((note, index) => (
          <button
            key={note.id}
            onClick={() => handleNoteClick(note)}
            className="w-full text-left p-3.5 rounded-xl hover:bg-muted/60 hover:shadow-sm transition-all duration-200 group border border-transparent hover:border-border/40"
          >
            <div className="flex items-start gap-3">
              <div className={`p-2 rounded-lg transition-colors shrink-0 ${
                index === 0 
                  ? 'bg-primary/10 text-primary' 
                  : 'bg-muted/50 text-muted-foreground group-hover:bg-muted group-hover:text-foreground'
              }`}>
                <FileText className="size-4" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate group-hover:text-foreground transition-colors">
                  {note.title}
                </p>
                <p className="text-xs text-muted-foreground mt-1.5 line-clamp-2 leading-relaxed">
                  {note.content || "No content"}
                </p>
                <div className="flex items-center gap-2 mt-2">
                  <span className="text-[10px] text-muted-foreground/70 font-medium uppercase tracking-wider">
                    {format(new Date(note.updated_at), "MMM dd, yyyy")}
                  </span>
                  {index === 0 && (
                    <span className="inline-flex items-center gap-1 text-[10px] text-primary font-medium uppercase tracking-wider">
                      <Sparkles className="size-2.5" />
                      Latest
                    </span>
                  )}
                </div>
              </div>
            </div>
          </button>
        ))}
      </div>

      {/* Notes Drawer for viewing/editing */}
      {selectedNote && (
        <NotesDrawer
          isOpen={isDrawerOpen}
          onClose={() => {
            setIsDrawerOpen(false)
            setSelectedNote(null)
          }}
          postAnalysisId={selectedNote.post_analysis_id}
          onNoteSaved={handleNoteSaved}
        />
      )}
    </>
  )
}

