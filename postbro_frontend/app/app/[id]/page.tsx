"use client"

import { AppContent } from "../_components/app-content"

// Analysis detail page - uses same component as main page (ChatGPT-like behavior)
// URL changes to /app/{id} but uses the same component, so no full page refresh
export default function AnalysisDetailPage() {
  return <AppContent />
}
