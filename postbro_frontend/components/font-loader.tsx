"use client"

import { useEffect } from "react"

export function FontLoader() {
  useEffect(() => {
    // Check if links already exist
    const existingPreconnect1 = document.querySelector('link[href="https://fonts.googleapis.com"]')
    const existingPreconnect2 = document.querySelector('link[href="https://fonts.gstatic.com"]')
    const existingInter = document.querySelector('link[href*="family=Inter"]')
    const existingPoppins = document.querySelector('link[href*="family=Poppins"]')

    if (!existingPreconnect1) {
      const link1 = document.createElement('link')
      link1.rel = 'preconnect'
      link1.href = 'https://fonts.googleapis.com'
      document.head.appendChild(link1)
    }

    if (!existingPreconnect2) {
      const link2 = document.createElement('link')
      link2.rel = 'preconnect'
      link2.href = 'https://fonts.gstatic.com'
      link2.crossOrigin = 'anonymous'
      document.head.appendChild(link2)
    }

    // Load Inter for body text & UI
    if (!existingInter) {
      const linkInter = document.createElement('link')
      linkInter.href = 'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap'
      linkInter.rel = 'stylesheet'
      document.head.appendChild(linkInter)
    }

    // Load Poppins for headings & marketing
    if (!existingPoppins) {
      const linkPoppins = document.createElement('link')
      linkPoppins.href = 'https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&display=swap'
      linkPoppins.rel = 'stylesheet'
      document.head.appendChild(linkPoppins)
    }
  }, [])

  return null
}






