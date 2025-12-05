# PostBro Chat Feature Implementation Plan

## Overview
Add a chat feature that allows users to ask follow-up questions about analyzed posts. The chat will use Gemini API to provide conversational responses based on the original post analysis.

## Architecture Decisions

### Session Model
- **ChatSession** → **PostAnalysis** (one-to-one per post)
- Each analyzed post can have one chat session
- Session is created lazily (on first message, not automatically after analysis)

### Data Storage
- **PostAnalysis**: Keeps structured JSON analysis (unchanged)
- **ChatSession**: Tracks active/archived chat sessions per post
- **ChatMessage**: Stores user messages and AI responses (conversational only)

### Context Building
- Include: Post data, analysis summary, chat history
- Use chat-specific prompt (tuned for conversations, not full analysis)
- Track tokens for analytics

---

## Phase 1: Database Models & Migrations

### 1.1 Create ChatSession Model
**File**: `postbro_backend/analysis/models.py`

```python
class ChatSession(models.Model):
    class Status(models.TextChoices):
        ACTIVE = 'active', _('Active')
        ARCHIVED = 'archived', _('Archived')
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_sessions')
    post_analysis = models.OneToOneField(
        PostAnalysis,
        on_delete=models.CASCADE,
        related_name='chat_session',
        help_text='The post analysis this chat session belongs to'
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['post_analysis']),
        ]
```

### 1.2 Create ChatMessage Model
**File**: `postbro_backend/analysis/models.py`

```python
class ChatMessage(models.Model):
    class Role(models.TextChoices):
        USER = 'user', _('User')
        ASSISTANT = 'assistant', _('Assistant')
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name='messages',
        help_text='The chat session this message belongs to'
    )
    role = models.CharField(max_length=20, choices=Role.choices)
    content = models.TextField(help_text='Message content')
    tokens_used = models.IntegerField(
        null=True,
        blank=True,
        help_text='Number of tokens used for this message (for analytics)'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['session', 'created_at']),
        ]
```

### 1.3 Create Migration
```bash
python manage.py makemigrations analysis --name add_chat_models
python manage.py migrate
```

---

## Phase 2: Chat Prompt & Context Building

### 2.1 Create Chat Prompt Template
**File**: `postbro_backend/analysis/prompts/chat.txt`

```
🟦 SYSTEM PROMPT

You are PostBro AI assistant — an expert social media strategist helping users understand their post analysis.

A user has analyzed a social media post and received an initial analysis. Now they're asking follow-up questions.

Your role:
- Answer questions about the post analysis, performance, strategies, and insights
- Reference the original analysis when relevant
- Be conversational, helpful, and specific
- Use framework names (Curiosity Stack, Retention Loop, etc.) when appropriate
- Provide actionable advice when asked

Context provided:
- Original post data (caption, metrics, media)
- Initial analysis summary (key takeaways, creator context, viral status, frameworks)
- Previous conversation history

Be concise but thorough. If asked about something not in the analysis, say so clearly.

🟩 USER PROMPT

Post Context:
Platform: {{platform}}
Creator: {{creator_context}}
Caption: {{caption}}
Metrics: {{metrics_summary}}

Initial Analysis Summary:
{{analysis_summary}}

Previous Conversation:
{{chat_history}}

Current Question:
{{user_message}}
```

### 2.2 Create Context Builder Service
**File**: `postbro_backend/analysis/services/chat_context_builder.py`

**Functions**:
1. `build_analysis_summary(post_analysis: PostAnalysis) -> str`
   - Condenses PostAnalysis fields into a readable summary
   - Includes: quick takeaways, creator context, viral status, frameworks, key insights
   - Max 300 words

2. `build_post_context(post: Post) -> dict`
   - Extracts post data: caption, metrics, media URLs
   - Returns structured dict

3. `build_chat_history(messages: QuerySet) -> str`
   - Formats previous messages as conversation
   - Format: "User: [message]\nAssistant: [response]\n..."
   - Includes last 20 messages (to stay within token limits)

4. `build_chat_prompt(post_analysis: PostAnalysis, user_message: str, chat_history: QuerySet) -> str`
   - Combines all context into final prompt
   - Uses chat.txt template
   - Returns formatted prompt string

---

## Phase 3: Gemini Chat Service

### 3.1 Create Chat Service
**File**: `postbro_backend/analysis/services/chat_service.py`

**Function**: `send_chat_message(session_id: str, user_message: str, user_id: str) -> dict`

**Flow**:
1. Get ChatSession by ID (with post_analysis, post)
2. Validate user owns session
3. Build context using chat_context_builder
4. Call Gemini API (2.5 Flash) with chat prompt
5. Parse response
6. Save user message to ChatMessage
7. Save AI response to ChatMessage
8. Log to ExternalAPICallLog (analytics)
9. Return response dict

**Error Handling**:
- Session not found → 404
- User doesn't own session → 403
- Gemini API error → 500 with retry logic
- Invalid message → 400

**Token Tracking**:
- Extract token usage from Gemini response
- Save to ChatMessage.tokens_used
- Log to analytics

---

## Phase 4: API Endpoints (Django REST Framework)

### 4.1 Create Serializers
**File**: `postbro_backend/analysis/serializers.py`

```python
class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ['id', 'role', 'content', 'tokens_used', 'created_at']
        read_only_fields = ['id', 'tokens_used', 'created_at']

class ChatSessionSerializer(serializers.ModelSerializer):
    messages = ChatMessageSerializer(many=True, read_only=True)
    post_analysis_id = serializers.UUIDField(source='post_analysis.id', read_only=True)
    
    class Meta:
        model = ChatSession
        fields = ['id', 'post_analysis_id', 'status', 'messages', 'created_at', 'updated_at']
        read_only_fields = ['id', 'status', 'created_at', 'updated_at']
```

### 4.2 Create Views
**File**: `postbro_backend/analysis/views.py`

#### Endpoint 1: Create Chat Session
**Route**: `POST /api/chat/sessions/`

**Request Body**:
```json
{
  "post_analysis_id": "uuid"
}
```

**Logic**:
1. Get PostAnalysis by ID
2. Validate user owns the analysis request
3. Check if session already exists (get or create)
4. Return session with messages

**Response**:
```json
{
  "session_id": "uuid",
  "post_analysis_id": "uuid",
  "status": "active",
  "messages": [],
  "created_at": "timestamp"
}
```

#### Endpoint 2: Send Message
**Route**: `POST /api/chat/sessions/{session_id}/messages/`

**Request Body**:
```json
{
  "message": "How can I improve this post?"
}
```

**Logic**:
1. Get ChatSession by ID
2. Validate user owns session
3. Call chat_service.send_chat_message()
4. Return new messages (user + assistant)

**Response**:
```json
{
  "user_message": {
    "id": "uuid",
    "role": "user",
    "content": "How can I improve this post?",
    "created_at": "timestamp"
  },
  "assistant_message": {
    "id": "uuid",
    "role": "assistant",
    "content": "Based on the analysis...",
    "tokens_used": 150,
    "created_at": "timestamp"
  }
}
```

#### Endpoint 3: Get Chat History
**Route**: `GET /api/chat/sessions/{session_id}/messages/`

**Response**:
```json
{
  "session_id": "uuid",
  "messages": [
    {
      "id": "uuid",
      "role": "user",
      "content": "...",
      "created_at": "timestamp"
    },
    {
      "id": "uuid",
      "role": "assistant",
      "content": "...",
      "tokens_used": 150,
      "created_at": "timestamp"
    }
  ]
}
```

#### Endpoint 4: List User Sessions
**Route**: `GET /api/chat/sessions/`

**Query Params**: `?post_analysis_id={uuid}` (optional filter)

**Response**:
```json
{
  "sessions": [
    {
      "id": "uuid",
      "post_analysis_id": "uuid",
      "status": "active",
      "message_count": 5,
      "updated_at": "timestamp"
    }
  ]
}
```

### 4.3 Update URLs
**File**: `postbro_backend/analysis/urls.py`

```python
urlpatterns = [
    # ... existing patterns ...
    path('chat/sessions/', views.create_chat_session, name='create_chat_session'),
    path('chat/sessions/<uuid:session_id>/messages/', views.chat_session_messages, name='chat_session_messages'),
    path('chat/sessions/<uuid:session_id>/', views.get_chat_session, name='get_chat_session'),
    path('chat/sessions/', views.list_chat_sessions, name='list_chat_sessions'),
]
```

---

## Phase 5: Analytics Integration

### 5.1 Log Chat API Calls
**File**: `postbro_backend/analysis/services/chat_service.py`

- Log each Gemini API call to `ExternalAPICallLog`
- Include: endpoint, request_tokens, response_tokens, cost (if available)
- Track for analytics dashboard

### 5.2 Track Chat Metrics
- Message count per session
- Token usage per message
- Session duration
- Average messages per session

**Note**: Usage limits for chat will be implemented later (Phase 6+)

---

## Phase 6: Error Handling & Edge Cases

### 6.1 Error Scenarios
1. **Session not found**: Return 404 with clear message
2. **User doesn't own session**: Return 403
3. **PostAnalysis not found**: Return 400
4. **Gemini API error**: Return 500, log error, optionally retry
5. **Invalid message (empty)**: Return 400
6. **Token limit exceeded**: Truncate chat history, keep last N messages

### 6.2 Token Management
- Gemini 2.5 Flash: 1M context window
- Strategy: Keep last 20 messages in context
- If approaching limit: Truncate older messages, keep most recent

### 6.3 Session Management
- Auto-archive old sessions (optional, future)
- Limit active sessions per user (optional, future)

---

## Phase 7: Frontend Implementation

### 7.1 Chat UI Component
**File**: `postbro_frontend/components/ChatInterface.tsx` (or similar)

**Features**:
- Chat input at bottom
- Message list (user messages on right, AI on left)
- Auto-scroll to latest message
- Loading state while AI responds
- Error handling display

**State Management**:
- `sessionId`: Current chat session ID
- `messages`: Array of chat messages
- `isLoading`: Boolean for loading state
- `error`: Error message if any

### 7.2 Integration with Analysis View
**File**: `postbro_frontend/app/dashboard/analysis/[id]/page.tsx` (or similar)

**Changes**:
1. Add "Ask a question" button below analysis results
2. On click: Create chat session (if not exists) or load existing
3. Show ChatInterface component
4. Display chat history if session exists

### 7.3 API Client Functions
**File**: `postbro_frontend/lib/api/chat.ts` (or similar)

```typescript
// Create or get chat session
async function createChatSession(postAnalysisId: string): Promise<ChatSession>

// Send message
async function sendChatMessage(sessionId: string, message: string): Promise<ChatMessageResponse>

// Get chat history
async function getChatHistory(sessionId: string): Promise<ChatMessage[]>

// List user sessions
async function listChatSessions(postAnalysisId?: string): Promise<ChatSession[]>
```

### 7.4 UI/UX Considerations
- **Initial State**: Show "Ask a question" button
- **After First Message**: Show chat interface with history
- **Message Display**: 
  - User messages: Right-aligned, distinct styling
  - AI messages: Left-aligned, distinct styling
  - Timestamps: Show relative time (e.g., "2 minutes ago")
- **Loading State**: Show typing indicator while AI responds
- **Error State**: Display error message, allow retry
- **Empty State**: Show placeholder when no messages

### 7.5 Real-time Updates (Optional, Future)
- Use Supabase Realtime to update chat messages
- Or use polling for simplicity (start with polling)

---

## Phase 8: Testing & Validation

### 8.1 Backend Tests
- Test session creation
- Test message sending
- Test context building
- Test error handling
- Test token tracking

### 8.2 Frontend Tests
- Test chat UI rendering
- Test message sending
- Test error states
- Test loading states

### 8.3 Integration Tests
- Test full flow: analysis → chat session → messages
- Test multiple messages in sequence
- Test chat history persistence

---

## Phase 9: Future Enhancements (Post-MVP)

### 9.1 Usage Limits
- Track chat messages per user
- Implement plan-based limits (Free: X messages/day, Pro: Y messages/day)
- Add usage tracking to analytics

### 9.2 Multi-Post Chat
- Allow chat sessions that reference multiple posts
- Useful for comparing posts or asking about multiple analyses

### 9.3 Chat Export
- Export chat history as text/PDF
- Include in post analysis export

### 9.4 Chat Search
- Search within chat history
- Filter by date, keywords

### 9.5 Auto-Archive
- Archive sessions after X days of inactivity
- Clean up old archived sessions

---

## Implementation Order

1. **Phase 1**: Database models & migrations
2. **Phase 2**: Chat prompt & context building
3. **Phase 3**: Gemini chat service
4. **Phase 4**: API endpoints
5. **Phase 5**: Analytics integration
6. **Phase 6**: Error handling
7. **Phase 7**: Frontend implementation
8. **Phase 8**: Testing
9. **Phase 9**: Future enhancements (later)

---

## Notes

- **No usage limits initially**: Focus on making chat work, add limits later
- **Lazy session creation**: Create session on first message, not after analysis
- **Token management**: Keep last 20 messages in context, truncate if needed
- **Analytics**: Track everything for future plan-based restrictions
- **Error handling**: Comprehensive error handling from the start
- **Frontend**: Start simple, enhance later

---

## Success Criteria

- ✅ User can ask questions about analyzed posts
- ✅ AI responds with relevant, helpful answers
- ✅ Chat history persists and loads correctly
- ✅ Error handling works properly
- ✅ Analytics tracking is in place
- ✅ Frontend UI is functional and user-friendly






