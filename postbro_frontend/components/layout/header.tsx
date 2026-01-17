"use client"

import * as React from "react"
import Link from "next/link"
import { usePathname, useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { ModeToggle } from "@/components/mode-toggle"
import { cn } from "@/lib/utils"
import { Menu, BarChart2, LogOut, ChevronRight } from "lucide-react"
import { Sheet, SheetContent, SheetTrigger, SheetHeader, SheetTitle, SheetDescription } from "@/components/ui/sheet"
import { useAuth, useClerk } from "@clerk/nextjs"
import { toast } from "sonner"
import { Skeleton } from "@/components/ui/skeleton"

export function Header() {
  const pathname = usePathname()
  const router = useRouter()
  const { isLoaded, isSignedIn } = useAuth()
  const { signOut } = useClerk()
  const [isScrolled, setIsScrolled] = React.useState(false)
  const [isMenuOpen, setIsMenuOpen] = React.useState(false)
  const isAuthPage = pathname === "/login" || pathname === "/signup" || pathname === "/reset-password" || pathname === "/verify-email"

  // Derive isAuth from Clerk's isSignedIn
  const isAuth = isLoaded && isSignedIn

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

  React.useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 20)
    }
    window.addEventListener("scroll", handleScroll)
    return () => window.removeEventListener("scroll", handleScroll)
  }, [])

  const navLinks = [
    { name: "Features", href: "/#features" },
    { name: "How it Works", href: "/#how-it-works" },
    { name: "Pricing", href: "/#pricing" },
  ]

  if (isAuthPage) return null

  // Loading state - show skeleton to prevent flash
  if (!isLoaded) {
    return (
      <header
        className={cn(
          "fixed top-0 w-full z-50 transition-all duration-300 border-b border-transparent",
          isScrolled
            ? "bg-background/80 backdrop-blur-md border-border/50 supports-[backdrop-filter]:bg-background/60"
            : "bg-transparent",
        )}
      >
        <div className="container mx-auto px-4 h-16 flex items-center justify-between">
          {/* Logo - always visible */}
          <Link href="/" className="flex items-center gap-2 group">
            <div className="size-8 rounded-lg bg-primary flex items-center justify-center">
              <BarChart2 className="size-5 text-primary-foreground" />
            </div>
            <span className="font-bold text-xl tracking-tight">PostBro</span>
          </Link>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center gap-8">
            {navLinks.map((link) => (
              <Link
                key={link.name}
                href={link.href}
                className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
              >
                {link.name}
              </Link>
            ))}
          </nav>

          {/* Right side - Skeleton for auth buttons */}
          <div className="hidden md:flex items-center gap-4">
            <ModeToggle />
            <div className="h-6 w-px bg-border" />
            <Skeleton className="h-9 w-16 rounded-md" />
            <Skeleton className="h-9 w-24 rounded-md" />
          </div>

          {/* Mobile - just show mode toggle and skeleton */}
          <div className="flex items-center gap-4 md:hidden">
            <ModeToggle />
            <Skeleton className="h-9 w-9 rounded-md" />
          </div>
        </div>
      </header>
    )
  }

  return (
    <header
      className={cn(
        "fixed top-0 w-full z-50 transition-all duration-300 border-b border-transparent",
        isScrolled
          ? "bg-background/80 backdrop-blur-md border-border/50 supports-[backdrop-filter]:bg-background/60"
          : "bg-transparent",
      )}
    >
      <div className={cn(
        "h-16 flex items-center justify-between w-full",
        isAuth ? "px-4 md:pl-4" : "container mx-auto px-4"
      )}>
        <div className="flex items-center gap-2">
          <Link href={isAuth ? "/app" : "/"} className="flex items-center gap-2 group">
            <div className="size-8 rounded-lg bg-primary flex items-center justify-center group-hover:bg-primary/90 transition-colors">
              <BarChart2 className="size-5 text-primary-foreground" />
            </div>
            <span className="font-bold text-xl tracking-tight">PostBro</span>
          </Link>
        </div>

        {/* Desktop Navigation - Only show when not authenticated */}
        {!isAuth && (
          <nav className="hidden md:flex items-center gap-8">
            {navLinks.map((link) => (
              <Link
                key={link.name}
                href={link.href}
                className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
              >
                {link.name}
              </Link>
            ))}
          </nav>
        )}

        <div className="hidden md:flex items-center gap-4 animate-in fade-in duration-300">
          {isAuth ? (
            <>
              <ModeToggle />
              <div className="h-6 w-px bg-border" />
              <Button
                variant="ghost"
                onClick={handleLogout}
                className="text-muted-foreground hover:text-foreground"
              >
                <LogOut className="mr-2 size-4" />
                Logout
              </Button>
            </>
          ) : (
            <>
              <ModeToggle />
              <div className="h-6 w-px bg-border" />
              <Button variant="ghost" asChild className="text-muted-foreground hover:text-foreground">
                <Link href="/login">Log in</Link>
              </Button>
              <Button
                asChild
                className="bg-primary text-primary-foreground hover:bg-primary/90 shadow-sm hover:shadow transition-all"
              >
                <Link href="/signup">Get Started</Link>
              </Button>
            </>
          )}
        </div>

        {/* Mobile Navigation */}
        <div className="flex items-center gap-4 md:hidden">
          <ModeToggle />
          <Sheet open={isMenuOpen} onOpenChange={setIsMenuOpen}>
            <SheetTrigger asChild>
              <Button variant="ghost" size="icon" className="-mr-2">
                <Menu className="size-5" />
                <span className="sr-only">Toggle menu</span>
              </Button>
            </SheetTrigger>
            <SheetContent side="right" className="w-[85%] sm:w-[400px] p-0">
              <SheetHeader className="px-6 pt-6 pb-4 border-b border-border">
                <SheetTitle className="text-xl font-bold">PostBro</SheetTitle>
                <SheetDescription className="sr-only">
                  Navigation menu for PostBro
                </SheetDescription>
              </SheetHeader>
              <nav className="px-3 py-4">
                <div className="space-y-1">
                  {!isAuth && navLinks.map((link) => (
                    <Link
                      key={link.name}
                      href={link.href}
                      onClick={() => setIsMenuOpen(false)}
                      className="flex items-center justify-between px-3 py-2.5 text-sm font-medium text-foreground hover:bg-muted/50 rounded-md transition-colors"
                    >
                      <span>{link.name}</span>
                      <ChevronRight className="size-4 text-muted-foreground" />
                    </Link>
                  ))}
                  {isAuth ? (
                    <>
                      <Link
                        href="/profile"
                        onClick={() => setIsMenuOpen(false)}
                        className="flex items-center justify-between px-3 py-2.5 text-sm font-medium text-foreground hover:bg-muted/50 rounded-md transition-colors"
                      >
                        <span>Profile</span>
                        <ChevronRight className="size-4 text-muted-foreground" />
                      </Link>
                      <button
                        onClick={async () => {
                          setIsMenuOpen(false)
                          await handleLogout()
                        }}
                        className="w-full text-left flex items-center justify-between px-3 py-2.5 text-sm font-medium text-foreground hover:bg-muted/50 rounded-md transition-colors"
                      >
                        <span className="flex items-center">
                          <LogOut className="mr-2 size-4" />
                          Logout
                        </span>
                        <ChevronRight className="size-4 text-muted-foreground" />
                      </button>
                    </>
                  ) : (
                    <>
                      <Link
                        href="/login"
                        onClick={() => setIsMenuOpen(false)}
                        className="flex items-center justify-between px-3 py-2.5 text-sm font-medium text-foreground hover:bg-muted/50 rounded-md transition-colors"
                      >
                        <span>Log in</span>
                        <ChevronRight className="size-4 text-muted-foreground" />
                      </Link>
                      <Link
                        href="/signup"
                        onClick={() => setIsMenuOpen(false)}
                        className="flex items-center justify-between px-3 py-2.5 text-sm font-medium text-primary hover:bg-primary/10 rounded-md transition-colors"
                      >
                        <span>Get Started</span>
                        <ChevronRight className="size-4 text-primary/70" />
                      </Link>
                    </>
                  )}
                </div>
              </nav>
            </SheetContent>
          </Sheet>
        </div>
      </div>
    </header>
  )
}
