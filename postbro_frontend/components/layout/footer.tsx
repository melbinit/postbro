import Link from "next/link"
import { BarChart2, Twitter, Instagram, Github } from "lucide-react"

export function Footer() {
  return (
    <footer className="border-t border-border/50">
      <div className="container mx-auto px-4 py-10 sm:py-12 md:py-16">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6 sm:gap-8 lg:gap-12">
          {/* Brand */}
          <div className="col-span-2 md:col-span-1 space-y-4">
            <Link href="/" className="flex items-center gap-2 group w-fit">
              <div className="size-8 rounded-lg bg-foreground flex items-center justify-center">
                <BarChart2 className="size-4 text-background" />
              </div>
              <span className="font-semibold text-lg">PostBro</span>
            </Link>
            <p className="text-sm text-muted-foreground max-w-[200px] leading-relaxed">
              AI-powered social media analytics and content ideas.
            </p>
            <div className="flex items-center gap-2">
              <Link
                href="https://twitter.com"
                className="text-muted-foreground hover:text-foreground transition-colors p-2 rounded-lg hover:bg-muted"
              >
                <Twitter className="size-4" />
                <span className="sr-only">Twitter</span>
              </Link>
              <Link
                href="https://instagram.com"
                className="text-muted-foreground hover:text-foreground transition-colors p-2 rounded-lg hover:bg-muted"
              >
                <Instagram className="size-4" />
                <span className="sr-only">Instagram</span>
              </Link>
              <Link
                href="https://github.com"
                className="text-muted-foreground hover:text-foreground transition-colors p-2 rounded-lg hover:bg-muted"
              >
                <Github className="size-4" />
                <span className="sr-only">GitHub</span>
              </Link>
            </div>
          </div>

          {/* Product */}
          <div>
            <h3 className="text-[10px] sm:text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3 sm:mb-4">Product</h3>
            <ul className="space-y-2 sm:space-y-3">
              <li>
                <Link href="#features" className="text-xs sm:text-sm text-foreground/80 hover:text-foreground transition-colors">
                  Features
                </Link>
              </li>
              <li>
                <Link href="#pricing" className="text-xs sm:text-sm text-foreground/80 hover:text-foreground transition-colors">
                  Pricing
                </Link>
              </li>
              <li>
                <Link href="/docs" className="text-xs sm:text-sm text-foreground/80 hover:text-foreground transition-colors">
                  Documentation
                </Link>
              </li>
              <li>
                <Link href="/changelog" className="text-xs sm:text-sm text-foreground/80 hover:text-foreground transition-colors">
                  Changelog
                </Link>
              </li>
            </ul>
          </div>

          {/* Company */}
          <div>
            <h3 className="text-[10px] sm:text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3 sm:mb-4">Company</h3>
            <ul className="space-y-2 sm:space-y-3">
              <li>
                <Link href="/about" className="text-xs sm:text-sm text-foreground/80 hover:text-foreground transition-colors">
                  About
                </Link>
              </li>
              <li>
                <Link href="/blog" className="text-xs sm:text-sm text-foreground/80 hover:text-foreground transition-colors">
                  Blog
                </Link>
              </li>
              <li>
                <Link href="/careers" className="text-xs sm:text-sm text-foreground/80 hover:text-foreground transition-colors">
                  Careers
                </Link>
              </li>
              <li>
                <Link href="/contact" className="text-xs sm:text-sm text-foreground/80 hover:text-foreground transition-colors">
                  Contact
                </Link>
              </li>
            </ul>
          </div>

          {/* Legal */}
          <div>
            <h3 className="text-[10px] sm:text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3 sm:mb-4">Legal</h3>
            <ul className="space-y-2 sm:space-y-3">
              <li>
                <Link href="/privacy" className="text-xs sm:text-sm text-foreground/80 hover:text-foreground transition-colors">
                  Privacy
                </Link>
              </li>
              <li>
                <Link href="/terms" className="text-xs sm:text-sm text-foreground/80 hover:text-foreground transition-colors">
                  Terms
                </Link>
              </li>
              <li>
                <Link href="/cookies" className="text-xs sm:text-sm text-foreground/80 hover:text-foreground transition-colors">
                  Cookies
                </Link>
              </li>
            </ul>
          </div>
        </div>

        <div className="mt-8 sm:mt-10 pt-5 sm:pt-6 border-t border-border/50 flex flex-col sm:flex-row items-center justify-between gap-3 sm:gap-4">
          <p className="text-[10px] sm:text-xs text-muted-foreground">© {new Date().getFullYear()} PostBro. All rights reserved.</p>
          <div className="flex items-center gap-1.5 text-[10px] sm:text-xs text-muted-foreground">
            <span className="size-1.5 rounded-full bg-emerald-500" />
            <span>All systems operational</span>
          </div>
        </div>
      </div>
    </footer>
  )
}
