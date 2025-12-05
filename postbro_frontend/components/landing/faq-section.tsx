"use client"

import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion"
import { FadeInUp } from "./hero-section"

const faqs = [
  {
    question: "How does PostBro analyze posts? Do I need to connect my social media accounts?",
    answer:
      "No account connections needed! PostBro works differently - just paste any public Instagram, X, or YouTube post URL and we'll analyze it. You can analyze your own posts, any public post you see, or study what works for others by simply pasting their post URL. No OAuth, no sign-ins to social platforms required. It's that simple.",
  },
  {
    question: "What payment methods do you accept? Can I cancel anytime?",
    answer:
      "We accept all major credit cards and debit cards through secure payment processing. Yes, you can cancel your subscription anytime with no cancellation fees. Your access continues until the end of your current billing period, and you can reactivate anytime.",
  },
  {
    question: "What makes PostBro different from other social media analytics tools?",
    answer:
      "PostBro focuses on competitive intelligence and content ideas, not just your own analytics. Unlike other tools that require connecting accounts, you can analyze any public post instantly. Plus, we provide AI-generated similar post ideas with captions and recommendations - turning insights into actionable content you can use immediately.",
  },
  {
    question: "Which social media platforms does PostBro support?",
    answer:
      "Currently, PostBro supports Instagram, X (Twitter), and YouTube with full analysis capabilities. We're working on adding TikTok and Facebook support soon. You can analyze posts from any public account on supported platforms - no need to own or manage those accounts.",
  },
  {
    question: "How accurate is the AI analysis? What data do you use?",
    answer:
      "Our AI analyzes real engagement metrics, comments, visual composition, captions, and posting patterns from the actual post data. We use state-of-the-art AI models to understand why content performs well. The analysis includes engagement rates, reach, comment sentiment, and visual elements that drove the post's success. All data comes from publicly available information.",
  },
]

export function FAQSection() {
  return (
    <section id="faq" className="py-24 bg-background">
      <div className="container px-4 mx-auto">
        <FadeInUp delay={0.1}>
          <div className="text-center max-w-2xl mx-auto mb-16">
            <h2 className="text-3xl md:text-4xl font-bold mb-4">
              Frequently Asked <span className="text-primary">Questions</span>
            </h2>
            <p className="text-muted-foreground text-lg">
              Everything you need to know about PostBro, payments, and how it works.
            </p>
          </div>
        </FadeInUp>

        <div className="max-w-3xl mx-auto">
          <Accordion type="single" collapsible className="w-full space-y-4">
            {faqs.map((faq, index) => (
              <FadeInUp key={index} delay={0.1 + index * 0.1} duration={0.6}>
                <AccordionItem
                  value={`item-${index}`}
                  className="border-0 rounded-lg px-6 bg-background/50 hover:bg-background transition-colors"
                >
                  <AccordionTrigger className="text-left font-semibold hover:no-underline py-6">
                    {faq.question}
                  </AccordionTrigger>
                  <AccordionContent className="text-muted-foreground leading-relaxed pb-6">
                    {faq.answer}
                  </AccordionContent>
                </AccordionItem>
              </FadeInUp>
            ))}
          </Accordion>
        </div>
      </div>
    </section>
  )
}

