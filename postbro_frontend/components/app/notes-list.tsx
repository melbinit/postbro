"use client"

import { useState, useEffect } from "react"
import { FileText, Loader2, Trash2 } from "lucide-react"
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
          <Skeleton key={i} className="h-16 w-full" />
        ))}
      </div>
    )
  }

  if (notes.length === 0) {
    return (
      <div className="p-4 text-center">
        <FileText className="h-8 w-8 mx-auto text-muted-foreground mb-2" />
        <p className="text-sm text-muted-foreground">No notes yet</p>
        <p className="text-xs text-muted-foreground mt-1">
          Click the + button to save notes
        </p>
      </div>
    )
  }

  return (
    <>
      <div className="space-y-1 p-2">
        {notes.map((note) => (
          <button
            key={note.id}
            onClick={() => handleNoteClick(note)}
            className="w-full text-left p-3 rounded-md hover:bg-muted/50 transition-colors group"
          >
            <div className="flex items-start gap-2">
              <FileText className="size-4 text-muted-foreground mt-0.5 flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{note.title}</p>
                <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                  {note.content || "No content"}
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  {format(new Date(note.updated_at), "MMM dd, yyyy")}
                </p>
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

