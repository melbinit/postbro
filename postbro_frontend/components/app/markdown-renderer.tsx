"use client"

import React from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeRaw from 'rehype-raw'
import rehypeHighlight from 'rehype-highlight'
// Use a theme that works with both light and dark mode
import 'highlight.js/styles/github.css'

interface MarkdownRendererProps {
  content: string
  className?: string
}

export function MarkdownRenderer({ content, className }: MarkdownRendererProps) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      rehypePlugins={[rehypeRaw, rehypeHighlight]}
      className={className}
      components={{
        // Paragraphs - clean spacing
        // Note: Prevents invalid nesting by checking for code blocks
        p: ({ children, node }: any) => {
          // Check if paragraph contains a pre/code block
          const hasCodeBlock = node?.children?.some((child: any) => 
            child.tagName === 'pre' || child.tagName === 'code'
          )
          
          // If it contains a code block, render as div to avoid invalid HTML
          if (hasCodeBlock) {
            return <div className="leading-[1.7] text-foreground/90 [&:not(:last-child)]:mb-3">{children}</div>
          }
          
          return <p className="leading-[1.7] text-foreground/90 [&:not(:last-child)]:mb-3">{children}</p>
        },
        
        // Bold text
        strong: ({ children }) => <strong className="font-semibold text-foreground">{children}</strong>,
        
        // Italic text
        em: ({ children }) => <em className="italic text-foreground/80">{children}</em>,
        
        // Headings - clean hierarchy
        h1: ({ children }) => <h1 className="text-lg font-semibold text-foreground mt-5 mb-2 first:mt-0">{children}</h1>,
        h2: ({ children }) => <h2 className="text-base font-semibold text-foreground mt-4 mb-2 first:mt-0">{children}</h2>,
        h3: ({ children }) => <h3 className="text-[15px] font-medium text-foreground mt-3 mb-1.5 first:mt-0">{children}</h3>,
        
        // Lists - cleaner styling
        ul: ({ children }) => <ul className="my-3 space-y-1.5 [&>li]:relative [&>li]:pl-5 [&>li]:before:content-['•'] [&>li]:before:absolute [&>li]:before:left-1 [&>li]:before:text-muted-foreground/50">{children}</ul>,
        ol: ({ children }) => <ol className="my-3 space-y-1.5 list-decimal pl-5 marker:text-muted-foreground/60">{children}</ol>,
        li: ({ children }) => <li className="leading-relaxed text-foreground/90">{children}</li>,
        
        // Pre wrapper for code blocks - prevents nesting issues
        pre: ({ children }) => (
          <pre className="bg-muted/60 rounded-xl p-4 my-4 overflow-x-auto text-sm">
            {children}
          </pre>
        ),
        
        // Code - handles both inline and block
        code({ node, inline, className, children, ...props }: any) {
          // For inline code (e.g., `main`)
          if (inline) {
            return (
              <code className="bg-muted/70 px-1.5 py-0.5 rounded-md text-[13px] font-mono text-foreground" {...props}>
                {children}
              </code>
            )
          }
          
          // For code blocks - just return the code element
          // The <pre> wrapper is handled by the pre component above
          return (
            <code className={`${className} font-mono block`} {...props}>
              {children}
            </code>
          )
        },
        
        // Blockquotes - subtle styling
        blockquote: ({ children }) => (
          <blockquote className="border-l-2 border-primary/40 pl-4 my-4 text-foreground/70 italic">
            {children}
          </blockquote>
        ),
        
        // Links
        a: ({ href, children }) => (
          <a 
            href={href} 
            target="_blank" 
            rel="noopener noreferrer"
            className="text-primary hover:text-primary/80 underline underline-offset-2 decoration-primary/30 hover:decoration-primary/60 transition-colors"
          >
            {children}
          </a>
        ),
        
        // Horizontal rule
        hr: () => <hr className="my-6 border-border/50" />,
        
        // Tables - cleaner design
        table: ({ children }) => (
          <div className="my-4 overflow-x-auto rounded-lg border border-border/50">
            <table className="min-w-full text-sm">
              {children}
            </table>
          </div>
        ),
        thead: ({ children }) => <thead className="bg-muted/50 border-b border-border/50">{children}</thead>,
        tbody: ({ children }) => <tbody className="divide-y divide-border/30">{children}</tbody>,
        tr: ({ children }) => <tr>{children}</tr>,
        th: ({ children }) => (
          <th className="px-3 py-2.5 text-left font-medium text-foreground">
            {children}
          </th>
        ),
        td: ({ children }) => (
          <td className="px-3 py-2.5 text-foreground/80">
            {children}
          </td>
        ),
      }}
    >
      {content}
    </ReactMarkdown>
  )
}

