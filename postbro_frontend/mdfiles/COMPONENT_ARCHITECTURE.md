# Component Architecture Guide

Detailed guide to the component structure and relationships in the PostBro frontend.

## Component Hierarchy

### Root Layout
```
app/layout.tsx
├── ClerkProvider
├── ThemeProvider
├── FontLoader
├── Toaster
└── Analytics
```

### App Layout
```
app/app/layout.tsx
├── AppHeader
├── AppSidebar
└── {children} (AppContent)
```

### Main App Page
```
app/app/page.tsx
└── AppContent
```

### Analysis Page
```
app/app/[id]/page.tsx
└── AppContent (with analysisId from URL)
```

### AppContent Component
```
app/app/_components/app-content.tsx
├── useAnalysisState (hook)
├── useRealtimeStatus (hook)
├── useScrollBehavior (hook)
├── useAnalysisLoader (hook)
├── useAnalysisEvents (hook)
├── WelcomeMessage
├── AnalysisStatus
├── AnalysisDisplay
├── ChatInterface
├── InputArea
├── NotesButton
└── NotesDrawer
```

---

## Component Categories

### 1. Layout Components

**Location:** `components/layout/`

#### Header (`header.tsx`)
- Main navigation header
- User menu
- Theme toggle
- Used on: All pages

#### Landing Header (`landing-header.tsx`)
- Landing page specific header
- CTA buttons
- Used on: Landing page

#### App Header (`app-header.tsx`)
- App-specific header
- Analysis navigation
- Used on: App pages

#### Footer (`footer.tsx`)
- Site footer
- Links and copyright
- Used on: Landing page

---

### 2. App Components

**Location:** `components/app/`

#### Analysis Display (`analysis-display.tsx`)
- Main analysis results container
- Renders post cards and analysis
- Handles multiple posts
- **Children:**
  - PostCard (per post)
  - ContentObservation
  - SuggestionItem (per suggestion)

#### Post Card (`post-card.tsx`)
- Individual post display
- Media gallery
- Metrics display
- Transcript viewer
- **Props:**
  - `post: Post`
  - `analysis?: PostAnalysis`
  - `onSelect?: () => void`

#### Content Observation (`content-observation.tsx`)
- Displays AI content observations
- Structured sections:
  - Caption observation
  - Visual observation
  - Engagement context
  - Platform signals

#### Suggestion Item (`suggestion-item.tsx`)
- Future post suggestion card
- Hook, outline, why it works
- Engagement potential indicator

#### Analysis Form (`analysis-form.tsx`)
- URL input form
- Platform selection
- Validation
- Submit handler
- **State:**
  - Form values
  - Validation errors
  - Loading state

#### Chat Interface (`chat-interface.tsx`)
- Chat container
- Messages list
- Input area
- **Children:**
  - ChatMessages
  - ChatInput

#### Chat Messages (`chat-messages.tsx`)
- Messages container
- Scroll management
- **Children:**
  - ChatMessage (per message)

#### Chat Message (`chat-message.tsx`)
- Individual message display
- User/assistant styling
- Markdown rendering
- **Props:**
  - `message: ChatMessage`
  - `isStreaming?: boolean`

#### Chat Input (`chat-input.tsx`)
- Message input field
- Send button
- Streaming support
- **Props:**
  - `postAnalysisId: string`
  - `onMessageSent?: () => void`

#### Streaming Markdown (`streaming-markdown.tsx`)
- Real-time markdown rendering
- Typing effect
- Syntax highlighting
- **Props:**
  - `content: string`
  - `isStreaming: boolean`

#### Typing Effect (`typing-effect.tsx`)
- Animated typing indicator
- Character-by-character reveal
- **Props:**
  - `text: string`
  - `speed?: number`

#### Notes Drawer (`notes-drawer.tsx`)
- Side drawer for notes
- Note editor
- Notes list
- **State:**
  - `isOpen: boolean`
  - `currentNote?: AnalysisNote`

#### Notes Button (`notes-button.tsx`)
- Toggle button for notes drawer
- Badge with note count
- **Props:**
  - `postAnalysisId: string`
  - `onClick: () => void`

#### Notes List (`notes-list.tsx`)
- List of all notes
- Note preview
- Delete action
- **Props:**
  - `notes: AnalysisNote[]`
  - `onSelect: (note: AnalysisNote) => void`

#### Markdown Renderer (`markdown-renderer.tsx`)
- Markdown to HTML conversion
- Syntax highlighting
- GFM support
- **Props:**
  - `content: string`
  - `className?: string`

#### Settings Modal (`settings-modal.tsx`)
- Settings dialog
- Theme selection
- Account settings
- **State:**
  - `isOpen: boolean`

---

### 3. Profile Components

**Location:** `components/profile/`

#### Profile Content (`profile-content.tsx`)
- Main profile page container
- Tab navigation
- **Children:**
  - ProfileForm
  - SubscriptionView
  - UsageStats
  - BillingHistory

#### Profile Form (`profile-form.tsx`)
- Profile edit form
- Name, company fields
- Save handler
- **State:**
  - Form values
  - Loading state

#### Profile Header (`profile-header.tsx`)
- Profile header section
- Avatar
- User info
- **Props:**
  - `user: User`

#### Subscription View (`subscription-view.tsx`)
- Current subscription display
- Plan details
- Upgrade/downgrade options
- **Props:**
  - `subscription?: Subscription`

#### Subscription Plan (`subscription-plan.tsx`)
- Plan card component
- Features list
- Price display
- **Props:**
  - `plan: Plan`
  - `isCurrent?: boolean`
  - `onSelect?: () => void`

#### Usage Stats (`usage-stats.tsx`)
- Usage statistics display
- Progress bars
- Limits display
- **Props:**
  - `usage: UsageStats`

#### Billing History (`billing-history.tsx`)
- Payment history table
- Invoice links
- **Props:**
  - `subscriptions: Subscription[]`

---

### 4. Billing Components

**Location:** `components/billing/`

#### Plan Selector (`plan-selector.tsx`)
- Plan selection UI
- Comparison table
- **Props:**
  - `plans: Plan[]`
  - `currentPlan?: Plan`
  - `onSelect: (planId: string) => void`

#### Upgrade Plans (`upgrade-plans.tsx`)
- Upgrade flow UI
- Plan comparison
- **Props:**
  - `plans: Plan[]`
  - `currentPlan: Plan`

---

### 5. Landing Components

**Location:** `components/landing/`

#### Hero Section (`hero-section.tsx`)
- Main hero banner
- Headline, CTA
- **Props:**
  - `onGetStarted: () => void`

#### Features Section (`features-section.tsx`)
- Features grid
- Icons and descriptions
- **Props:**
  - `features: Feature[]`

#### Pricing Section (`pricing-section.tsx`)
- Pricing table
- Plan cards
- **Props:**
  - `plans: Plan[]`

#### How It Works (`how-it-works-section.tsx`)
- Step-by-step guide
- Process visualization

#### FAQ Section (`faq-section.tsx`)
- FAQ accordion
- **Props:**
  - `faqs: FAQ[]`

#### Social Proof (`social-proof-section.tsx`)
- Testimonials
- Social media links

---

### 6. UI Components (shadcn/ui)

**Location:** `components/ui/`

**Primitive Components:**
- `button.tsx` - Button with variants
- `input.tsx` - Text input
- `textarea.tsx` - Textarea
- `select.tsx` - Select dropdown
- `checkbox.tsx` - Checkbox
- `radio-group.tsx` - Radio buttons
- `switch.tsx` - Toggle switch
- `slider.tsx` - Range slider

**Layout Components:**
- `card.tsx` - Card container
- `separator.tsx` - Divider
- `scroll-area.tsx` - Scrollable area
- `resizable.tsx` - Resizable panels

**Overlay Components:**
- `dialog.tsx` - Modal dialog
- `drawer.tsx` - Side drawer
- `sheet.tsx` - Bottom sheet
- `popover.tsx` - Popover
- `tooltip.tsx` - Tooltip
- `hover-card.tsx` - Hover card
- `alert-dialog.tsx` - Confirmation dialog

**Feedback Components:**
- `toast.tsx` - Toast notification
- `sonner.tsx` - Sonner toast provider
- `alert.tsx` - Alert banner
- `skeleton.tsx` - Loading skeleton
- `spinner.tsx` - Loading spinner
- `progress.tsx` - Progress bar

**Navigation Components:**
- `tabs.tsx` - Tab navigation
- `accordion.tsx` - Accordion
- `collapsible.tsx` - Collapsible
- `navigation-menu.tsx` - Navigation menu
- `breadcrumb.tsx` - Breadcrumbs
- `menubar.tsx` - Menu bar

**Data Display:**
- `table.tsx` - Data table
- `badge.tsx` - Badge/tag
- `avatar.tsx` - User avatar
- `chart.tsx` - Chart component

**Form Components:**
- `form.tsx` - Form wrapper
- `label.tsx` - Form label
- `field.tsx` - Form field

**Utilities:**
- `empty.tsx` - Empty state
- `command.tsx` - Command palette
- `calendar.tsx` - Date picker
- `date-range-picker.tsx` - Date range

---

## Component Communication Patterns

### 1. Props Down
```typescript
// Parent passes data to child
<PostCard post={post} analysis={analysis} />
```

### 2. Events Up
```typescript
// Child notifies parent via callback
<AnalysisForm onSubmit={(data) => handleSubmit(data)} />
```

### 3. Context
```typescript
// Global state via context
const { user, analyses } = useAppContext()
```

### 4. Custom Events
```typescript
// Cross-component communication
window.dispatchEvent(new CustomEvent('analysis-created', {
  detail: analysis
}))
```

### 5. URL State
```typescript
// State in URL
const analysisId = usePathname().split('/app/')[1]
```

---

## State Management Patterns

### Local State (useState)
```typescript
// Component-specific state
const [isOpen, setIsOpen] = useState(false)
```

### Context State
```typescript
// Global app state
const { user, analyses } = useAppContext()
```

### URL State
```typescript
// State in URL params
const router = useRouter()
router.push(`/app/${analysisId}`)
```

### Server State (Future: React Query)
```typescript
// Cached server state
const { data } = useQuery(['analysis', id], () => 
  analysisApi.getAnalysisRequest(id)
)
```

---

## Component Lifecycle

### Mount
```typescript
useEffect(() => {
  // Component mounted
  loadData()
}, [])
```

### Update
```typescript
useEffect(() => {
  // Dependency changed
  updateData()
}, [dependency])
```

### Unmount
```typescript
useEffect(() => {
  return () => {
    // Cleanup
    cleanup()
  }
}, [])
```

---

## Performance Patterns

### Memoization
```typescript
// Memoize expensive computations
const expensiveValue = useMemo(() => {
  return computeExpensiveValue(data)
}, [data])

// Memoize callbacks
const handleClick = useCallback(() => {
  doSomething()
}, [dependency])
```

### Component Memoization
```typescript
// Prevent unnecessary re-renders
export const PostCard = React.memo(({ post }) => {
  return <div>{post.content}</div>
})
```

### Lazy Loading
```typescript
// Code splitting
const HeavyComponent = dynamic(() => import('./HeavyComponent'), {
  loading: () => <Skeleton />,
  ssr: false
})
```

---

## Styling Patterns

### Tailwind Utilities
```typescript
<div className="flex items-center gap-4 p-4">
```

### Conditional Classes
```typescript
<div className={cn(
  "base-class",
  isActive && "active-class"
)}>
```

### Variants (CVA)
```typescript
const buttonVariants = cva("base", {
  variants: {
    variant: {
      default: "bg-primary",
      outline: "border"
    }
  }
})
```

---

## Testing Patterns

### Component Testing
```typescript
// Test component rendering
render(<PostCard post={mockPost} />)
expect(screen.getByText(mockPost.content)).toBeInTheDocument()
```

### Hook Testing
```typescript
// Test custom hooks
const { result } = renderHook(() => useRealtimeStatus(id))
expect(result.current.latestStatus).toBeDefined()
```

### Integration Testing
```typescript
// Test component interactions
fireEvent.click(getByText('Submit'))
await waitFor(() => {
  expect(getByText('Success')).toBeInTheDocument()
})
```

---

## Best Practices

### 1. Component Size
- Keep components focused (single responsibility)
- Extract sub-components when >200 lines
- Use composition over large components

### 2. Props Interface
- Define clear TypeScript interfaces
- Use optional props with defaults
- Document prop purposes

### 3. State Management
- Prefer local state for component-specific
- Use context for truly global state
- Avoid prop drilling (use context)

### 4. Performance
- Memoize expensive computations
- Use React.memo for pure components
- Lazy load heavy components

### 5. Accessibility
- Use semantic HTML
- Add ARIA labels
- Support keyboard navigation
- Test with screen readers

---

## Component Checklist

When creating a new component:

- [ ] TypeScript types defined
- [ ] Props interface documented
- [ ] Error handling implemented
- [ ] Loading states handled
- [ ] Accessibility considered
- [ ] Responsive design tested
- [ ] Dark mode supported
- [ ] Performance optimized
- [ ] Tests written (if applicable)

---

**Last Updated**: 2025-01-XX

