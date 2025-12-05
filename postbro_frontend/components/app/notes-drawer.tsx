"use client"

import { useState, useEffect } from "react"
import { X, Save, Trash2, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog"
import { notesApi, type AnalysisNote } from "@/lib/api"
import { format } from "date-fns"

interface NotesDrawerProps {
  isOpen: boolean
  onClose: () => void
  postAnalysisId: string | null
  postUsername?: string | null
  onNoteSaved?: () => void
}

/**
 * Notes drawer that slides in from the right
 * Doesn't block the main view - user can still see and copy from chat
 */
export function NotesDrawer({
  isOpen,
  onClose,
  postAnalysisId,
  postUsername,
  onNoteSaved,
}: NotesDrawerProps) {
  const [title, setTitle] = useState("")
  const [content, setContent] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)
  const [existingNote, setExistingNote] = useState<AnalysisNote | null>(null)

  // Load existing note when drawer opens or postAnalysisId changes
  useEffect(() => {
    if (isOpen && postAnalysisId) {
      loadExistingNote()
    } else {
      // Reset when drawer closes
      setTitle("")
      setContent("")
      setExistingNote(null)
    }
  }, [isOpen, postAnalysisId])

  const loadExistingNote = async () => {
    if (!postAnalysisId) return

    setIsLoading(true)
    try {
      const note = await notesApi.getNote(postAnalysisId)
      if (note) {
        setExistingNote(note)
        // Only use note title if it's not empty, otherwise use default
        if (note.title && note.title.trim()) {
          setTitle(note.title)
        } else {
          // Note exists but title is empty - set default
          const currentDate = format(new Date(), "MMM d, yyyy")
          const defaultTitle = postUsername 
            ? `${postUsername} - ${currentDate}`
            : currentDate
          setTitle(defaultTitle)
        }
        setContent(note.content || "")
      } else {
        // No note exists - set default title
        setExistingNote(null)
        const currentDate = format(new Date(), "MMM d, yyyy")
        const defaultTitle = postUsername 
          ? `${postUsername} - ${currentDate}`
          : currentDate
        setTitle(defaultTitle)
        setContent("")
      }
    } catch (error) {
      console.error("Failed to load note:", error)
      setExistingNote(null)
      // Set default title on error (treat as no note)
      const currentDate = format(new Date(), "MMM d, yyyy")
      const defaultTitle = postUsername 
        ? `${postUsername} - ${currentDate}`
        : currentDate
      setTitle(defaultTitle)
      setContent("")
    } finally {
      setIsLoading(false)
    }
  }

  const handleSave = async () => {
    if (!postAnalysisId || !title.trim()) {
      return
    }

    setIsSaving(true)
    try {
      if (existingNote) {
        await notesApi.updateNote(postAnalysisId, title.trim(), content)
      } else {
        await notesApi.saveNote(postAnalysisId, title.trim(), content)
      }
      // Notify parent to refresh notes list, then close modal
      onNoteSaved?.()
      onClose()
    } catch (error) {
      console.error("Failed to save note:", error)
      alert("Failed to save note. Please try again.")
    } finally {
      setIsSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!existingNote) return

    if (!confirm("Are you sure you want to delete this note?")) {
      return
    }

    setIsDeleting(true)
    try {
      await notesApi.deleteNote(existingNote.id)
      setExistingNote(null)
      setTitle("")
      setContent("")
      onNoteSaved?.()
    } catch (error) {
      console.error("Failed to delete note:", error)
      alert("Failed to delete note. Please try again.")
    } finally {
      setIsDeleting(false)
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl w-full max-h-[85vh] p-0 gap-0 overflow-hidden flex flex-col" showCloseButton={false}>
        {/* Header - compact */}
        <div className="flex items-center justify-between px-4 sm:px-6 py-3 sm:py-4 border-b border-border flex-shrink-0">
          <DialogTitle className="text-base sm:text-lg font-semibold">Notes</DialogTitle>
          <Button
            variant="ghost"
            size="icon"
            onClick={onClose}
            className="h-7 w-7 sm:h-8 sm:w-8"
          >
            <X className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
          </Button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-3 sm:space-y-4">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : (
            <>
              <div className="space-y-1.5">
                <label htmlFor="note-title" className="text-xs font-medium text-muted-foreground">
                  Title
                </label>
                <Input
                  id="note-title"
                  placeholder="Enter note title..."
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="w-full h-9 sm:h-10 text-sm"
                />
              </div>

              <div className="space-y-1.5">
                <label htmlFor="note-content" className="text-xs font-medium text-muted-foreground">
                  Content
                </label>
                <Textarea
                  id="note-content"
                  placeholder="Save ideas, strategies, insights from AI responses..."
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  className="w-full min-h-[300px] sm:min-h-[350px] resize-none text-sm"
                />
              </div>
            </>
          )}
        </div>

        {/* Footer - compact */}
        <div className="px-4 sm:px-6 py-2.5 sm:py-3 border-t border-border flex items-center justify-between gap-2 flex-shrink-0">
          {existingNote && (
            <Button
              variant="destructive"
              size="sm"
              onClick={handleDelete}
              disabled={isDeleting || isSaving}
              className="h-8 text-xs"
            >
              {isDeleting ? (
                <Loader2 className="h-3 w-3 animate-spin mr-1.5" />
              ) : (
                <Trash2 className="h-3 w-3 mr-1.5" />
              )}
              Delete
            </Button>
          )}
          <div className="flex gap-2 ml-auto">
            <Button 
              variant="outline" 
              onClick={onClose} 
              disabled={isSaving || isDeleting}
              size="sm"
              className="h-8 text-xs px-3"
            >
              Cancel
            </Button>
            <Button
              onClick={handleSave}
              disabled={!title.trim() || isSaving || isDeleting || !postAnalysisId}
              size="sm"
              className="h-8 text-xs px-3"
            >
              {isSaving ? (
                <>
                  <Loader2 className="h-3 w-3 animate-spin mr-1.5" />
                  Saving...
                </>
              ) : (
                <>
                  <Save className="h-3 w-3 mr-1.5" />
                  {existingNote ? "Update" : "Save"}
                </>
              )}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}

