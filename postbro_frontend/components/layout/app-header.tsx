"use client"

import * as React from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { ModeToggle } from "@/components/mode-toggle"
import { LogOut, BarChart2, Menu } from "lucide-react"
import { useClerk } from "@clerk/nextjs"
import { toast } from "sonner"

interface AppHeaderProps {
  onMenuClick?: () => void
}

export function AppHeader({ onMenuClick }: AppHeaderProps) {
  const router = useRouter()
  const { signOut } = useClerk()
  const [isScrolled, setIsScrolled] = React.useState(false)

  React.useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 20)
    }
    window.addEventListener("scroll", handleScroll)
    return () => window.removeEventListener("scroll", handleScroll)
  }, [])

  const handleLogout = async () => {
    try {
      // Clear all caches before signing out
      const { userCache } = await import('@/lib/storage')
      userCache.clear()
      
      // Clear any localStorage data
      if (typeof window !== 'undefined') {
        localStorage.removeItem('postbro_cache_user')
      }
      
      await signOut()
      router.push("/")
    } catch (error) {
      // Silent fail - user will see they're still logged in
    }
  }

  return (
    <header
      className={`fixed top-0 w-full z-50 transition-all duration-300 border-b ${
        isScrolled
          ? "bg-background/80 backdrop-blur-md border-border/50 supports-[backdrop-filter]:bg-background/60"
          : "bg-background/50 backdrop-blur-sm border-border/30"
      }`}
    >
      <div className="h-16 flex items-center px-4 relative">
        {/* Mobile: Hamburger on left */}
        {onMenuClick && (
          <Button
            variant="ghost"
            size="icon"
            onClick={onMenuClick}
            className="md:hidden -ml-2"
          >
            <Menu className="size-5" />
          </Button>
        )}

        {/* Desktop: Logo on left */}
        <Link href="/app" className="hidden md:flex items-center gap-2 group">
          <div className="size-8 rounded-lg bg-primary flex items-center justify-center group-hover:bg-primary/90 transition-colors">
            <BarChart2 className="size-5 text-primary-foreground" />
          </div>
          <span className="font-semibold text-xl tracking-tight">PostBro</span>
        </Link>

        {/* Mobile: Centered Logo */}
        <Link href="/app" className="md:hidden absolute left-1/2 -translate-x-1/2 flex items-center gap-2 group">
          <div className="size-8 rounded-lg bg-primary flex items-center justify-center group-hover:bg-primary/90 transition-colors">
            <BarChart2 className="size-5 text-primary-foreground" />
          </div>
          <span className="font-semibold text-xl tracking-tight">PostBro</span>
        </Link>

        {/* Right side - Controls */}
        <div className="flex items-center gap-2 md:gap-4 ml-auto">
          <ModeToggle />
          <div className="h-6 w-px bg-border" />
          <Button
            variant="ghost"
            size="icon"
            onClick={handleLogout}
            className="text-muted-foreground hover:text-foreground md:size-auto md:px-0"
          >
            <LogOut className="size-4 md:mr-2" />
            <span className="hidden md:inline">Logout</span>
          </Button>
        </div>
      </div>
    </header>
  )
}

