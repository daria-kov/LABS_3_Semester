"""Utility functions and helpers for the Deep Research agent."""

import asyncio
import logging
import os
from datetime import datetime
from typing import Annotated, Any, Dict, List, Literal, Optional

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    MessageLikeRepresentation,
    filter_messages,
)
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import (
    BaseTool,
    InjectedToolArg,
    StructuredTool,
    tool,
)
from tavily import AsyncTavilyClient

from configuration import Configuration, SearchAPI
from prompts import summarize_webpage_prompt
from state import ResearchComplete, Summary

##########################
# Tavily Search Tool Utils
##########################
TAVILY_SEARCH_DESCRIPTION = (
    "A search engine optimized for comprehensive, accurate, and trusted results. "
    "Useful for when you need to answer questions about current events."
)
@tool(description=TAVILY_SEARCH_DESCRIPTION)
async def tavily_search(
    queries: List[str],
    max_results: Annotated[int, InjectedToolArg] = 5,
    topic: Annotated[Literal["general", "news", "finance"], InjectedToolArg] = "general",
    config: RunnableConfig = None
) -> str:
    """Fetch and summarize search results from Tavily search API.

    Args:
        queries: List of search queries to execute
        max_results: Maximum number of results to return per query
        topic: Topic filter for search results (general, news, or finance)
        config: Runtime configuration for API keys and model settings

    Returns:
        Formatted string containing summarized search results
    """
    # Step 1: Execute search queries asynchronously
    search_results = await tavily_search_async(
        queries,
        max_results=max_results,
        topic=topic,
        include_raw_content=True,
        config=config
    )

    # Step 2: Deduplicate results by URL to avoid processing the same content multiple times
    unique_results = {}
    for response in search_results:
        for result in response['results']:
            url = result['url']
            if url not in unique_results:
                unique_results[url] = {**result, "query": response['query']}

    # Step 3: Set up the summarization model with configuration
    configurable = Configuration.from_runnable_config(config)

    # Character limit to stay within model token limits (configurable)
    max_char_to_include = configurable.max_content_length

    # Initialize summarization model (GigaChat)
    model_api_key = get_api_key_for_model(configurable.summarization_model, config)

    # Используем GigaChat напрямую вместо init_chat_model
    try:
        from langchain_gigachat import GigaChat
        summarization_model = GigaChat(
            credentials=model_api_key,
            scope="GIGACHAT_API_CORP",
            model="GigaChat-2-Max",
            verify_ssl_certs=False,
            profanity_check=False,
            max_tokens=configurable.summarization_model_max_tokens
        ).with_structured_output(Summary).with_retry(
            stop_after_attempt=configurable.max_structured_output_retries
        )
    except ImportError:
        # Fallback если GigaChat не установлен
        from langchain.chat_models import init_chat_model
        summarization_model = init_chat_model(
            model=configurable.summarization_model,
            max_tokens=configurable.summarization_model_max_tokens,
            api_key=model_api_key,
            tags=["langsmith:nostream"]
        ).with_structured_output(Summary).with_retry(
            stop_after_attempt=configurable.max_structured_output_retries
        )

    # Step 4: Create summarization tasks (skip empty content)
    async def noop():
        """No-op function for results without raw content."""
        return None

    summarization_tasks = [
        noop() if not result.get("raw_content")
        else summarize_webpage(
            summarization_model,
            result['raw_content'][:max_char_to_include]
        )
        for result in unique_results.values()
    ]

    # Step 5: Execute all summarization tasks in parallel
    summaries = await asyncio.gather(*summarization_tasks)

    # Step 6: Combine results with their summaries
    summarized_results = {
        url: {
            'title': result['title'],
            'content': result['content'] if summary is None else summary
        }
        for url, result, summary in zip(
            unique_results.keys(),
            unique_results.values(),
            summaries
        )
    }

    # Step 7: Format the final output
    if not summarized_results:
        return "No valid search results found. Please try different search queries or use a different search API."

    formatted_output = "Search results: \n\n"
    for i, (url, result) in enumerate(summarized_results.items()):
        formatted_output += f"\n\n--- SOURCE {i+1}: {result['title']} ---\n"
        formatted_output += f"URL: {url}\n\n"
        formatted_output += f"SUMMARY:\n{result['content']}\n\n"
        formatted_output += "\n\n" + "-" * 80 + "\n"

    return formatted_output

async def tavily_search_async(
    search_queries,
    max_results: int = 5,
    topic: Literal["general", "news", "finance"] = "general",
    include_raw_content: bool = True,
    config: RunnableConfig = None
):
    """Execute multiple Tavily search queries asynchronously.

    Args:
        search_queries: List of search query strings to execute
        max_results: Maximum number of results per query
        topic: Topic category for filtering results
        include_raw_content: Whether to include full webpage content
        config: Runtime configuration for API key access

    Returns:
        List of search result dictionaries from Tavily API
    """
    # Initialize the Tavily client with API key from config
    tavily_client = AsyncTavilyClient(api_key=get_tavily_api_key(config))

    # Create search tasks for parallel execution
    search_tasks = [
        tavily_client.search(
            query,
            max_results=max_results,
            include_raw_content=include_raw_content,
            topic=topic
        )
        for query in search_queries
    ]

    # Execute all search queries in parallel and return results
    search_results = await asyncio.gather(*search_tasks)
    return search_results

async def summarize_webpage(model: BaseChatModel, webpage_content: str) -> str:
    """Summarize webpage content using AI model with timeout protection.

    Args:
        model: The chat model configured for summarization
        webpage_content: Raw webpage content to be summarized

    Returns:
        Formatted summary with key excerpts, or original content if summarization fails
    """
    try:
        # Create prompt with current date context
        prompt_content = summarize_webpage_prompt.format(
            webpage_content=webpage_content,
            date=get_today_str()
        )

        # Execute summarization with timeout to prevent hanging
        summary = await asyncio.wait_for(
            model.ainvoke([HumanMessage(content=prompt_content)]),
            timeout=60.0  # 60 second timeout for summarization
        )

        # Format the summary with structured sections
        formatted_summary = (
            f"<summary>\n{summary.summary}\n</summary>\n\n"
            f"<key_excerpts>\n{summary.key_excerpts}\n</key_excerpts>"
        )

        return formatted_summary

    except asyncio.TimeoutError:
        # Timeout during summarization - return original content
        logging.warning("Summarization timed out after 60 seconds, returning original content")
        return webpage_content
    except Exception as e:
        # Other errors during summarization - log and return original content
        logging.warning(f"Summarization failed with error: {str(e)}, returning original content")
        return webpage_content

##########################
# Reflection Tool Utils
##########################

@tool(description="Strategic reflection tool for research planning")
def think_tool(reflection: str) -> str:
    """Tool for strategic reflection on research progress and decision-making.

    Use this tool after each search to analyze results and plan next steps systematically.
    This creates a deliberate pause in the research workflow for quality decision-making.

    When to use:
    - After receiving search results: What key information did I find?
    - Before deciding next steps: Do I have enough to answer comprehensively?
    - When assessing research gaps: What specific information am I still missing?
    - Before concluding research: Can I provide a complete answer now?

    Reflection should address:
    1. Analysis of current findings - What concrete information have I gathered?
    2. Gap assessment - What crucial information is still missing?
    3. Quality evaluation - Do I have sufficient evidence/examples for a good answer?
    4. Strategic decision - Should I continue searching or provide my answer?

    Args:
        reflection: Your detailed reflection on research progress, findings, gaps, and next steps

    Returns:
        Confirmation that reflection was recorded for decision-making
    """
    return f"Reflection recorded: {reflection}"

##########################
# Tool Utils
##########################

async def get_search_tool(search_api: SearchAPI):
    """Configure and return search tools based on the specified API provider.

    Args:
        search_api: The search API provider to use (Anthropic, OpenAI, Tavily, GigaChat or None)

    Returns:
        List of configured search tool objects for the specified provider
    """
    if search_api == SearchAPI.TAVILY:
        # Configure Tavily search tool with metadata
        search_tool = tavily_search
        search_tool.metadata = {
            **(search_tool.metadata or {}),
            "type": "search",
            "name": "web_search"
        }
        return [search_tool]

    elif search_api == SearchAPI.GIGACHAT:
        # GigaChat doesn't have native search, use Tavily as fallback
        search_tool = tavily_search
        search_tool.metadata = {
            **(search_tool.metadata or {}),
            "type": "search",
            "name": "web_search"
        }
        return [search_tool]

    elif search_api == SearchAPI.NONE:
        # No search functionality configured
        return []

    # Default fallback for unknown search API types
    return []

async def get_all_tools(config: RunnableConfig):
    """Assemble complete toolkit including research and search tools.

    Args:
        config: Runtime configuration specifying search API settings

    Returns:
        List of all configured and available tools for research operations
    """
    # Start with core research tools
    tools = [tool(ResearchComplete), think_tool]

    # Add configured search tools
    configurable = Configuration.from_runnable_config(config)
    search_api = SearchAPI(get_config_value(configurable.search_api))
    search_tools = await get_search_tool(search_api)
    tools.extend(search_tools)

    return tools

def get_notes_from_tool_calls(messages: list[MessageLikeRepresentation]):
    """Extract notes from tool call messages."""
    return [tool_msg.content for tool_msg in filter_messages(messages, include_types="tool")]

##########################
# Agent Thought Logging
##########################

class ThoughtLogger:
    """Logger for agent thoughts and reasoning process."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ThoughtLogger, cls).__new__(cls)
            cls._instance.thoughts = []
            cls._instance.enabled = True
        return cls._instance

    def log_thought(self, agent_type: str, thought: str, context: str = ""):
        """Log a thought from an agent."""
        if not self.enabled:
            return

        thought_record = {
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "agent_type": agent_type,
            "thought": thought,
            "context": context
        }
        self.thoughts.append(thought_record)

        # Print thought to console
        print(f"\n🤔 [{thought_record['timestamp']}] {agent_type.upper()} размышляет:")
        print("─" * 60)
        print(f"💭 {thought}")
        if context:
            print(f"\n📋 Контекст: {context}")
        print("─" * 60)

    def log_delegation(self, supervisor: str, task: str, researcher: str = ""):
        """Log a task delegation from supervisor to researcher."""
        if not self.enabled:
            return

        delegation_record = {
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "supervisor": supervisor,
            "task": task,
            "researcher": researcher
        }

        print(f"\n📋 [{delegation_record['timestamp']}] {supervisor} делегирует задачу:")
        print("─" * 60)
        print(f"🔍 Задача: {task}")
        if researcher:
            print(f"👨‍🔬 Исследователь: {researcher}")
        print("─" * 60)

    def log_search(self, researcher: str, query: str, results_count: int = 0):
        """Log a search query executed by a researcher."""
        if not self.enabled:
            return

        search_record = {
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "researcher": researcher,
            "query": query,
            "results": results_count
        }

        print(f"\n🔍 [{search_record['timestamp']}] {researcher} выполняет поиск:")
        print("─" * 60)
        print(f"📝 Запрос: {query}")
        if results_count > 0:
            print(f"📊 Найдено результатов: {results_count}")
        print("─" * 60)

    def clear(self):
        """Clear all logged thoughts."""
        self.thoughts.clear()

    def get_all_thoughts(self):
        """Get all logged thoughts."""
        return self.thoughts

    def enable(self):
        """Enable thought logging."""
        self.enabled = True

    def disable(self):
        """Disable thought logging."""
        self.enabled = False

# Global thought logger instance
thought_logger = ThoughtLogger()

def extract_reflection_from_tool_output(content: str) -> str:
    """Extract reflection content from think_tool output."""
    if "Reflection recorded:" in content:
        return content.replace("Reflection recorded:", "").strip()
    return content

##########################
# Model Provider Native Websearch Utils
##########################

def anthropic_websearch_called(response):
    """Detect if Anthropic's native web search was used in the response.

    Args:
        response: The response object from Anthropic's API

    Returns:
        True if web search was called, False otherwise
    """
    try:
        # Navigate through the response metadata structure
        usage = response.response_metadata.get("usage")
        if not usage:
            return False

        # Check for server-side tool usage information
        server_tool_use = usage.get("server_tool_use")
        if not server_tool_use:
            return False

        # Look for web search request count
        web_search_requests = server_tool_use.get("web_search_requests")
        if web_search_requests is None:
            return False

        # Return True if any web search requests were made
        return web_search_requests > 0

    except (AttributeError, TypeError):
        # Handle cases where response structure is unexpected
        return False

def openai_websearch_called(response):
    """Detect if OpenAI's web search functionality was used in the response.

    Args:
        response: The response object from OpenAI's API

    Returns:
        True if web search was called, False otherwise
    """
    # Check for tool outputs in the response metadata
    tool_outputs = response.additional_kwargs.get("tool_outputs")
    if not tool_outputs:
        return False

    # Look for web search calls in the tool outputs
    for tool_output in tool_outputs:
        if tool_output.get("type") == "web_search_call":
            return True

    return False


##########################
# Token Limit Exceeded Utils
##########################

def is_token_limit_exceeded(exception: Exception, model_name: str = None) -> bool:
    """Determine if an exception indicates a token/context limit was exceeded.

    Args:
        exception: The exception to analyze
        model_name: Optional model name to optimize provider detection

    Returns:
        True if the exception indicates a token limit was exceeded, False otherwise
    """
    error_str = str(exception).lower()

    # Step 1: Determine provider from model name if available
    provider = None
    if model_name:
        model_str = str(model_name).lower()
        if model_str.startswith('gigachat:'):
            provider = 'gigachat'

    # Step 2: Check provider-specific token limit patterns
    if provider == 'gigachat':
        return _check_gigachat_token_limit(exception, error_str)

    # Step 3: If provider unknown, check all providers
    return (
        _check_gigachat_token_limit(exception, error_str)
    )

def _check_gigachat_token_limit(exception: Exception, error_str: str) -> bool:
    """Check if exception indicates GigaChat token limit exceeded."""
    # Analyze exception metadata
    exception_type = str(type(exception))
    class_name = exception.__class__.__name__
    module_name = getattr(exception.__class__, '__module__', '')

    # Check if this is a GigaChat exception
    is_gigachat_exception = (
        'gigachat' in exception_type.lower() or
        'gigachat' in module_name.lower()
    )

    # GigaChat typically uses standard HTTP errors for token limits
    if is_gigachat_exception:
        # Look for token-related keywords in error message
        token_keywords = ['token', 'context', 'length', 'maximum', 'reduce', 'превышен', 'лимит']
        if any(keyword in error_str for keyword in token_keywords):
            return True

    return False

# NOTE: This may be out of date or not applicable to your models. Please update this as needed.
MODEL_TOKEN_LIMITS = {
    "gigachat:gigachat-2-max": 32768,
    "gigachat:gigachat-2": 32768,
    "gigachat:gigachat-1": 32768,
}

def get_model_token_limit(model_string):
    """Look up the token limit for a specific model.

    Args:
        model_string: The model identifier string to look up

    Returns:
        Token limit as integer if found, None if model not in lookup table
    """
    # Search through known model token limits
    for model_key, token_limit in MODEL_TOKEN_LIMITS.items():
        if model_key in model_string:
            return token_limit

    # Model not found in lookup table
    return None

def remove_up_to_last_ai_message(messages: list[MessageLikeRepresentation]) -> list[MessageLikeRepresentation]:
    """Truncate message history by removing up to the last AI message.

    This is useful for handling token limit exceeded errors by removing recent context.

    Args:
        messages: List of message objects to truncate

    Returns:
        Truncated message list up to (but not including) the last AI message
    """
    # Search backwards through messages to find the last AI message
    for i in range(len(messages) - 1, -1, -1):
        if isinstance(messages[i], AIMessage):
            # Return everything up to (but not including) the last AI message
            return messages[:i]

    # No AI messages found, return original list
    return messages

##########################
# Misc Utils
##########################

def get_today_str() -> str:
    """Get current date formatted for display in prompts and outputs.

    Returns:
        Human-readable date string in format like 'Mon Jan 15, 2024'
    """
    now = datetime.now()
    return f"{now:%a} {now:%b} {now.day}, {now:%Y}"

def get_config_value(value):
    """Extract value from configuration, handling enums and None values."""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    elif isinstance(value, dict):
        return value
    else:
        return value.value

def get_api_key_for_model(model_name: str, config: RunnableConfig):
    """Get API key for a specific model from environment or config."""
    should_get_from_config = os.getenv("GET_API_KEYS_FROM_CONFIG", "false")
    model_name = model_name.lower()

    if should_get_from_config.lower() == "true":
        api_keys = config.get("configurable", {}).get("apiKeys", {})
        if not api_keys:
            return None
        if model_name.startswith("openai:"):
            return api_keys.get("OPENAI_API_KEY")
        elif model_name.startswith("anthropic:"):
            return api_keys.get("ANTHROPIC_API_KEY")
        elif model_name.startswith("gigachat:"):
            return api_keys.get("GIGACHAT_API_KEY")
        return None
    else:
        if model_name.startswith("openai:"):
            return os.getenv("OPENAI_API_KEY")
        elif model_name.startswith("anthropic:"):
            return os.getenv("ANTHROPIC_API_KEY")
        elif model_name.startswith("gigachat:"):
            return os.getenv("GIGACHAT_API_KEY")
        return None

def get_tavily_api_key(config: RunnableConfig):
    """Get Tavily API key from environment or config."""
    should_get_from_config = os.getenv("GET_API_KEYS_FROM_CONFIG", "false")
    if should_get_from_config.lower() == "true":
        api_keys = config.get("configurable", {}).get("apiKeys", {})
        if not api_keys:
            return None
        return api_keys.get("TAVILY_API_KEY")
    else:
        return os.getenv("TAVILY_API_KEY")
