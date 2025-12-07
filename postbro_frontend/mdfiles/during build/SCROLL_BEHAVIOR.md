# Scroll Behavior Documentation

## Overview

This document describes how scroll behavior works in the analysis/chat screen.

## Scroll Rules

### 1. Initial Load of Existing Analysis
**Action**: Scroll to bottom (once)
**When**: 
- Analysis was already `completed` when loaded from sidebar
- Posts and chat messages are loaded
- User has NOT interacted yet

**Implementation**:
- `wasCompletedOnLoadRef` tracks if analysis was completed on initial load
- `hasScrolledToBottomRef` prevents double-scrolling
- `userHasInteractedRef` disables scroll after user interaction

### 2. User Sends a Message
**Action**: Scroll user message to top of viewport
**When**: User clicks send or presses Enter
**Implementation**:
- Handled by `chat-messages.tsx`
- `scrollLatestMessageToTop()` calculates position and scrolls
- Adds `pb-[30vh]` padding to allow scroll space

### 3. During AI Streaming
**Action**: NO auto-scroll
**When**: AI is generating response
**Implementation**:
- User controls scrolling during streaming
- No interference with user's reading position

### 4. After User Interaction
**Action**: Disable all auto-scroll
**When**: User sends a message or manually scrolls
**Implementation**:
- `userHasInteractedRef.current = true` disables future auto-scrolls
- Reset when switching to different analysis

## Flow Diagram

```
User clicks analysis in sidebar
        │
        ▼
Load analysis data (API call)
        │
        ▼
Is analysis already completed?
        │
   ┌────┴────┐
   │ YES     │ NO
   │         │
   ▼         ▼
Mark as     Continue
"wasCompletedOnLoad"
        │
        ▼
Load posts (parallel)
        │
        ▼
Load chat messages
        │
        ▼
Set messagesLoaded = true
        │
        ▼
use-scroll-behavior hook triggers
        │
        ▼
Check conditions:
- wasCompletedOnLoad? ✓
- messagesLoaded? ✓
- posts.length > 0? ✓
- !userHasInteracted? ✓
- !hasScrolledToBottom? ✓
        │
        ▼
Scroll to bottom (multiple attempts)
        │
        ▼
Mark hasScrolledToBottom
```

## Debug Logs

Look for these console logs to debug scroll issues:

```
🎯 [Scroll] Will scroll to bottom for existing analysis: {id}
✅ [Scroll] Attempt N succeeded
⏭️ [Scroll] Skipping - {reason}
⚠️ [Scroll] Attempt N failed, will retry
```

## Common Issues

### Scroll not happening
1. Check if `wasCompletedOnLoadRef` has the analysis ID
2. Check if `messagesLoaded` is true
3. Check if `posts.length > 0`
4. Check if `userHasInteractedRef.current` is false
5. Check if `hasScrolledToBottomRef` doesn't already have the ID

### Scroll happening multiple times
1. Check if `hasScrolledToBottomRef` is being set correctly
2. Check if scroll is being attempted before marking complete

### Scroll interrupted
1. Check if user interaction is being detected incorrectly
2. Check if other components are triggering scroll events

## Files Involved

- `hooks/use-scroll-behavior.ts` - Main scroll logic for initial load
- `components/app/chat-messages.tsx` - User message scroll to top
- `hooks/use-analysis-state.ts` - State and refs
- `hooks/use-analysis-loader.ts` - Sets `wasCompletedOnLoadRef` and `messagesLoaded`
- `ui/analysis-status.tsx` - Renders ChatMessages and calls `onMessagesLoaded`




## Overview

This document describes how scroll behavior works in the analysis/chat screen.

## Scroll Rules

### 1. Initial Load of Existing Analysis
**Action**: Scroll to bottom (once)
**When**: 
- Analysis was already `completed` when loaded from sidebar
- Posts and chat messages are loaded
- User has NOT interacted yet

**Implementation**:
- `wasCompletedOnLoadRef` tracks if analysis was completed on initial load
- `hasScrolledToBottomRef` prevents double-scrolling
- `userHasInteractedRef` disables scroll after user interaction

### 2. User Sends a Message
**Action**: Scroll user message to top of viewport
**When**: User clicks send or presses Enter
**Implementation**:
- Handled by `chat-messages.tsx`
- `scrollLatestMessageToTop()` calculates position and scrolls
- Adds `pb-[30vh]` padding to allow scroll space

### 3. During AI Streaming
**Action**: NO auto-scroll
**When**: AI is generating response
**Implementation**:
- User controls scrolling during streaming
- No interference with user's reading position

### 4. After User Interaction
**Action**: Disable all auto-scroll
**When**: User sends a message or manually scrolls
**Implementation**:
- `userHasInteractedRef.current = true` disables future auto-scrolls
- Reset when switching to different analysis

## Flow Diagram

```
User clicks analysis in sidebar
        │
        ▼
Load analysis data (API call)
        │
        ▼
Is analysis already completed?
        │
   ┌────┴────┐
   │ YES     │ NO
   │         │
   ▼         ▼
Mark as     Continue
"wasCompletedOnLoad"
        │
        ▼
Load posts (parallel)
        │
        ▼
Load chat messages
        │
        ▼
Set messagesLoaded = true
        │
        ▼
use-scroll-behavior hook triggers
        │
        ▼
Check conditions:
- wasCompletedOnLoad? ✓
- messagesLoaded? ✓
- posts.length > 0? ✓
- !userHasInteracted? ✓
- !hasScrolledToBottom? ✓
        │
        ▼
Scroll to bottom (multiple attempts)
        │
        ▼
Mark hasScrolledToBottom
```

## Debug Logs

Look for these console logs to debug scroll issues:

```
🎯 [Scroll] Will scroll to bottom for existing analysis: {id}
✅ [Scroll] Attempt N succeeded
⏭️ [Scroll] Skipping - {reason}
⚠️ [Scroll] Attempt N failed, will retry
```

## Common Issues

### Scroll not happening
1. Check if `wasCompletedOnLoadRef` has the analysis ID
2. Check if `messagesLoaded` is true
3. Check if `posts.length > 0`
4. Check if `userHasInteractedRef.current` is false
5. Check if `hasScrolledToBottomRef` doesn't already have the ID

### Scroll happening multiple times
1. Check if `hasScrolledToBottomRef` is being set correctly
2. Check if scroll is being attempted before marking complete

### Scroll interrupted
1. Check if user interaction is being detected incorrectly
2. Check if other components are triggering scroll events

## Files Involved

- `hooks/use-scroll-behavior.ts` - Main scroll logic for initial load
- `components/app/chat-messages.tsx` - User message scroll to top
- `hooks/use-analysis-state.ts` - State and refs
- `hooks/use-analysis-loader.ts` - Sets `wasCompletedOnLoadRef` and `messagesLoaded`
- `ui/analysis-status.tsx` - Renders ChatMessages and calls `onMessagesLoaded`



