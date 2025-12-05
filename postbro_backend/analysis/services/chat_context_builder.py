"""
Chat Context Builder Service

Builds context for chat conversations by extracting and formatting:
- Post data
- Analysis summary
- Chat history
"""

import os
import logging
from typing import List, Dict, Any
from django.db.models import QuerySet

logger = logging.getLogger(__name__)


def extract_initial_analysis(chat_history: QuerySet) -> str:
    """
    Extract the full first AI message as the initial analysis summary.
    This replaces the PostAnalysis-based summary.
    
    Args:
        chat_history: QuerySet of ChatMessage objects (ordered by created_at)
    
    Returns:
        Full first AI message content (not truncated)
    """
    if not chat_history.exists():
        return "No initial analysis available."
    
    # Get the first AI message (the v2 analysis)
    first_ai_message = chat_history.filter(role='assistant').first()
    
    if first_ai_message:
        # Return full content (not truncated) - this contains the complete v2 analysis
        # including all media insights
        return first_ai_message.content
    
    return "No initial analysis available."


def build_post_context(post) -> Dict[str, Any]:
    """
    Extract post data for context.
    
    Args:
        post: Post instance
    
    Returns:
        Dictionary with post context data
    """
    metrics = post.metrics if isinstance(post.metrics, dict) else {}
    
    # Build metrics summary
    metrics_parts = []
    if metrics.get('likes'):
        metrics_parts.append(f"Likes: {metrics['likes']:,}")
    if metrics.get('views') or metrics.get('viewCount'):
        views = metrics.get('views') or metrics.get('viewCount', 0)
        metrics_parts.append(f"Views: {views:,}")
    if metrics.get('comments') or metrics.get('commentCount'):
        comments = metrics.get('comments') or metrics.get('commentCount', 0)
        metrics_parts.append(f"Comments: {comments:,}")
    if metrics.get('replies') or metrics.get('replyCount'):
        replies = metrics.get('replies') or metrics.get('replyCount', 0)
        metrics_parts.append(f"Replies: {replies:,}")
    
    metrics_summary = ", ".join(metrics_parts) if metrics_parts else "No metrics available"
    
    # Build creator context from post metrics (for backward compatibility)
    creator_context_parts = [f"@{post.username}"]
    if metrics.get('followers'):
        creator_context_parts.append(f"{metrics['followers']:,} followers")
    elif metrics.get('author', {}).get('followers'):
        creator_context_parts.append(f"{metrics['author']['followers']:,} followers")
    elif metrics.get('subscribers'):
        creator_context_parts.append(f"{metrics['subscribers']:,} subscribers")
    
    creator_context = ", ".join(creator_context_parts)
    
    return {
        'platform': post.platform.name if post.platform else 'unknown',
        'username': post.username,
        'caption': post.content[:500] if post.content else 'No caption',  # Truncate long captions
        'metrics_summary': metrics_summary,
        'posted_at': post.posted_at.isoformat() if post.posted_at else '',
        'creator_context': creator_context,
    }


def build_chat_history(messages: QuerySet, max_messages: int = 20, exclude_first_ai: bool = True) -> str:
    """
    Format previous messages as conversation history.
    Excludes the first AI message to avoid duplication with analysis_summary.
    
    Args:
        messages: QuerySet of ChatMessage objects (ordered by created_at)
        max_messages: Maximum number of messages to include (default: 20)
        exclude_first_ai: If True, exclude the first AI message (default: True)
    
    Returns:
        Formatted conversation history string
    """
    if not messages.exists():
        return "No previous conversation."
    
    # Get all messages
    all_messages = list(messages)
    
    # Exclude first AI message if requested (to avoid duplication with analysis_summary)
    if exclude_first_ai:
        first_ai_idx = None
        for i, msg in enumerate(all_messages):
            if msg.role == 'assistant':
                first_ai_idx = i
                break
        
        if first_ai_idx is not None:
            # Remove first AI message
            all_messages = all_messages[:first_ai_idx] + all_messages[first_ai_idx + 1:]
    
    # Get last N messages (after excluding first AI)
    recent_messages = all_messages[-max_messages:] if len(all_messages) > max_messages else all_messages
    
    if not recent_messages:
        return "No previous conversation (excluding initial analysis)."
    
    history_lines = []
    for msg in recent_messages:
        role_label = "User" if msg.role == 'user' else "Assistant"
        # Truncate very long messages, but preserve structure (numbered lists, etc.)
        # Increase limit to preserve more context for numbered references
        content = msg.content[:2000] if len(msg.content) > 2000 else msg.content
        if len(msg.content) > 2000:
            content += "..."
        history_lines.append(f"{role_label}: {content}")
    
    return "\n\n".join(history_lines) if history_lines else "No previous conversation (excluding initial analysis)."


def build_chat_prompt(
    post,
    user_message: str,
    chat_history: QuerySet = None,
    creator_context: str = None
) -> str:
    """
    Build the complete chat prompt from template and context.
    
    Args:
        post: Post instance (the post being analyzed)
        user_message: Current user message
        chat_history: QuerySet of previous ChatMessage objects (optional)
        creator_context: Creator context string (optional, for backward compatibility)
    
    Returns:
        Formatted prompt string ready for Gemini
    """
    # Load chat prompt template
    current_dir = os.path.dirname(os.path.abspath(__file__))
    prompt_path = os.path.join(current_dir, '..', 'prompts', 'chat.txt')
    prompt_path = os.path.abspath(prompt_path)
    
    try:
        with open(prompt_path, 'r', encoding='utf-8') as f:
            template = f.read()
    except FileNotFoundError:
        logger.error(f"❌ Chat prompt template not found at {prompt_path}")
        return ""
    except Exception as e:
        logger.error(f"❌ Error loading chat prompt template: {e}")
        return ""
    
    # Extract user prompt section
    user_prompt_start = template.find("🟩 USER PROMPT")
    if user_prompt_start == -1:
        logger.error("Could not find user prompt section in chat template")
        return ""
    
    user_prompt = template[user_prompt_start:]
    
    # Build context
    post_context = build_post_context(post)
    
    # Extract initial analysis from first AI message (full v2 analysis)
    if chat_history is not None:
        analysis_summary = extract_initial_analysis(chat_history)
        chat_history_text = build_chat_history(chat_history, exclude_first_ai=True)
    else:
        analysis_summary = "No initial analysis available."
        chat_history_text = "No previous conversation."
    
    # Get creator context (use provided or extract from post context)
    if not creator_context:
        creator_context = post_context.get('creator_context', f"@{post_context['username']}")
    
    # Replace template variables
    replacements = {
        '{{platform}}': post_context['platform'],
        '{{creator_context}}': creator_context,
        '{{caption}}': post_context['caption'],
        '{{metrics_summary}}': post_context['metrics_summary'],
        '{{analysis_summary}}': analysis_summary,
        '{{chat_history}}': chat_history_text,
        '{{user_message}}': user_message,
    }
    
    for key, value in replacements.items():
        user_prompt = user_prompt.replace(key, str(value))
    
    return user_prompt


def get_system_prompt() -> str:
    """
    Extract system prompt from chat template.
    
    Returns:
        System prompt string
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    prompt_path = os.path.join(current_dir, '..', 'prompts', 'chat.txt')
    prompt_path = os.path.abspath(prompt_path)
    
    try:
        with open(prompt_path, 'r', encoding='utf-8') as f:
            template = f.read()
    except FileNotFoundError:
        logger.error(f"❌ Chat prompt template not found at {prompt_path}")
        return ""
    except Exception as e:
        logger.error(f"❌ Error loading chat prompt template: {e}")
        return ""
    
    # Extract system prompt section (before "🟩 USER PROMPT")
    system_prompt_start = template.find("🟦 SYSTEM PROMPT")
    user_prompt_start = template.find("🟩 USER PROMPT")
    
    if system_prompt_start == -1 or user_prompt_start == -1:
        logger.error("Could not find system prompt section in chat template")
        return ""
    
    system_prompt = template[system_prompt_start:user_prompt_start]
    # Remove the header line
    system_prompt = '\n'.join(system_prompt.split('\n')[1:]).strip()
    
    return system_prompt

