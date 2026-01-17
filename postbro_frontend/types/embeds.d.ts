/**
 * Global type definitions for third-party embed scripts
 */

// Instagram Embed
declare global {
  interface Window {
    instgrm?: {
      Embeds: {
        process: () => void
      }
    }
  }
}

// Twitter/X Embed
declare global {
  interface Window {
    twttr?: {
      widgets: {
        load: (element?: HTMLElement) => Promise<void>
      }
    }
  }
}

export {}
