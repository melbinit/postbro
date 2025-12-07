"use client"

import { useState, useEffect } from "react"
import { X, Save, Trash2, Loader2, FileText, Sparkles } from "lucide-react"
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
      <DialogContent className="max-w-2xl w-full max-h-[85vh] p-0 gap-0 overflow-hidden flex flex-col rounded-2xl border-border/50" showCloseButton={false}>
        {/* Header - with gradient accent */}
        <div className="relative flex items-center justify-between px-5 sm:px-6 py-4 sm:py-5 border-b border-border/50 flex-shrink-0 bg-gradient-to-r from-primary/5 via-transparent to-transparent">
          {/* Decorative icon */}
          <div className="absolute -left-2 top-1/2 -translate-y-1/2 w-1 h-8 bg-gradient-to-b from-primary to-primary/50 rounded-full" />
          
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-primary/10 text-primary">
              <FileText className="h-4 w-4 sm:h-5 sm:w-5" />
            </div>
            <div>
              <DialogTitle className="text-base sm:text-lg font-semibold">
                {existingNote ? "Edit Note" : "New Note"}
              </DialogTitle>
              <p className="text-xs text-muted-foreground mt-0.5">
                {existingNote 
                  ? `Last updated ${format(new Date(existingNote.updated_at), "MMM d, yyyy")}`
                  : "Save your insights and ideas"
                }
              </p>
            </div>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={onClose}
            className="h-8 w-8 rounded-xl hover:bg-muted/80 transition-colors"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-5 sm:p-6 space-y-5 bg-gradient-to-b from-transparent to-muted/20">
          {isLoading ? (
            <div className="flex flex-col items-center justify-center py-16 gap-3">
              <div className="p-3 rounded-full bg-primary/10">
                <Loader2 className="h-6 w-6 animate-spin text-primary" />
              </div>
              <p className="text-sm text-muted-foreground">Loading note...</p>
            </div>
          ) : (
            <>
              <div className="space-y-2">
                <label htmlFor="note-title" className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  Title
                </label>
                <Input
                  id="note-title"
                  placeholder="Give your note a memorable title..."
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="w-full h-11 text-base font-medium bg-background border-border/60 focus:border-primary/50 rounded-xl"
                />
              </div>

              <div className="space-y-2">
                <label htmlFor="note-content" className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  Content
                </label>
                <div className="relative">
                  <Textarea
                    id="note-content"
                    placeholder="Capture your insights, strategies, and ideas from the AI analysis...

• What stood out about this post?
• Key takeaways for your content
• Ideas to try in your own posts"
                    value={content}
                    onChange={(e) => setContent(e.target.value)}
                    className="w-full min-h-[280px] sm:min-h-[320px] resize-none text-sm leading-relaxed bg-background border-border/60 focus:border-primary/50 rounded-xl p-4"
                  />
                  {/* Character count */}
                  <div className="absolute bottom-3 right-3 text-xs text-muted-foreground/60">
                    {content.length} characters
                  </div>
                </div>
              </div>

              {/* Tip card */}
              {!existingNote && (
                <div className="flex items-start gap-3 p-4 rounded-xl bg-primary/5 border border-primary/10">
                  <Sparkles className="h-4 w-4 text-primary mt-0.5 shrink-0" />
                  <div>
                    <p className="text-xs font-medium text-foreground">Pro tip</p>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Copy insights from the AI chat and paste them here to build your content library.
                    </p>
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer - polished with gradient */}
        <div className="px-5 sm:px-6 py-4 border-t border-border/50 flex items-center justify-between gap-3 flex-shrink-0 bg-muted/30">
          {existingNote && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleDelete}
              disabled={isDeleting || isSaving}
              className="h-9 text-destructive hover:text-destructive hover:bg-destructive/10 rounded-xl transition-colors"
            >
              {isDeleting ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <Trash2 className="h-4 w-4 mr-2" />
              )}
              Delete
            </Button>
          )}
          <div className="flex gap-2.5 ml-auto">
            <Button 
              variant="outline" 
              onClick={onClose} 
              disabled={isSaving || isDeleting}
              size="sm"
              className="h-9 px-4 rounded-xl border-border/60 hover:bg-muted/60"
            >
              Cancel
            </Button>
            <Button
              onClick={handleSave}
              disabled={!title.trim() || isSaving || isDeleting || !postAnalysisId}
              size="sm"
              className="h-9 px-5 rounded-xl bg-primary hover:bg-primary/90 shadow-md shadow-primary/20 hover:shadow-lg hover:shadow-primary/25 transition-all"
            >
              {isSaving ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  Saving...
                </>
              ) : (
                <>
                  <Save className="h-4 w-4 mr-2" />
                  {existingNote ? "Update Note" : "Save Note"}
                </>
              )}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}

