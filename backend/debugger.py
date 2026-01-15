#!/usr/bin/env python
"""
Debug script for testing the Browser Agent locally.

Usage:
    python debugger.py --task "Navigate to google and search for playwright" --url "https://google.com" --provider perplexity --api-key "pplx-xxx"
    
    Or set environment variables:
    export PERPLEXITY_API_KEY="pplx-xxx"
    export GEMINI_API_KEY="xxx"
    python debugger.py --task "Your task" --url "https://example.com"
"""

import argparse
import asyncio
import os
import sys
from datetime import datetime

# Add the src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from browser_agent.models import AgentRequest
from browser_agent.models.agent import LLMProvider
from browser_agent.services.agent import AgentService


def get_api_key(provider: str, explicit_key: str | None) -> str:
    """Get API key from argument or environment variable."""
    if explicit_key:
        return explicit_key
    
    env_vars = {
        "gemini": "GEMINI_API_KEY",
        "perplexity": "PERPLEXITY_API_KEY",
        "hf": "HUGGINGFACE_API_KEY",
    }
    
    env_var = env_vars.get(provider)
    if env_var:
        key = os.environ.get(env_var)
        if key:
            return key
    
    print(f"❌ No API key provided for {provider}")
    print(f"   Either pass --api-key or set {env_var} environment variable")
    sys.exit(1)


def format_event(event, event_num: int) -> None:
    """Pretty print an event."""
    colors = {
        "log": "\033[94m",      # Blue
        "screenshot": "\033[92m", # Green
        "code": "\033[93m",     # Yellow
        "error": "\033[91m",    # Red
        "complete": "\033[95m", # Magenta
    }
    reset = "\033[0m"
    
    event_type = event.type.value
    color = colors.get(event_type, "")
    
    print(f"\n{color}{'='*60}")
    print(f"EVENT #{event_num}: {event_type.upper()}")
    print(f"{'='*60}{reset}")
    
    if event.message:
        print(f"📝 {event.message}")
    
    if event.screenshot:
        print(f"📸 Screenshot captured ({len(event.screenshot)} chars)")
        # Optionally save screenshot
        # import base64
        # with open(f"screenshot_{event_num}.png", "wb") as f:
        #     f.write(base64.b64decode(event.screenshot))
        # print(f"   Saved to screenshot_{event_num}.png")
    
    if event.code:
        print(f"💻 Generated Code:")
        print(f"{'-'*60}")
        print(event.code)
        print(f"{'-'*60}")


async def run_agent(args: argparse.Namespace) -> None:
    """Run the agent with the given arguments."""
    # Get API key
    api_key = get_api_key(args.provider, args.api_key)
    
    # Map provider string to enum
    provider_map = {
        "gemini": LLMProvider.GEMINI,
        "perplexity": LLMProvider.PERPLEXITY,
        "hf": LLMProvider.HUGGINGFACE,
    }
    provider = provider_map.get(args.provider)
    if not provider:
        print(f"❌ Unknown provider: {args.provider}")
        print(f"   Available: gemini, perplexity, hf")
        sys.exit(1)
    
    # Create request
    print("\n" + "="*60)
    print("🤖 BROWSER AGENT DEBUGGER")
    print("="*60)
    print(f"📋 Task: {args.task}")
    print(f"🌐 URL: {args.url}")
    print(f"🔌 Provider: {args.provider}")
    print(f"👁️ Headless: {args.headless}")
    print(f"🔑 API Key: {api_key[:10]}..." if len(api_key) > 10 else f"🔑 API Key: {api_key}")
    print("="*60 + "\n")
    
    request = AgentRequest(
        task=args.task,
        url=args.url,
        provider=provider,
        api_key=api_key,
        headless=args.headless,
    )
    
    # Run agent
    service = AgentService()
    event_count = 0
    start_time = datetime.now()
    
    print("🚀 Starting agent...\n")
    
    try:
        async for event in service.run(request):
            event_count += 1
            format_event(event, event_count)
            
            if args.max_events and event_count >= args.max_events:
                print(f"\n⚠️ Stopping after {args.max_events} events (--max-events)")
                break
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
    
    # Summary
    elapsed = datetime.now() - start_time
    print("\n" + "="*60)
    print("📊 SUMMARY")
    print("="*60)
    print(f"Total events: {event_count}")
    print(f"Elapsed time: {elapsed.total_seconds():.2f}s")
    print("="*60 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Debug the Browser Agent locally",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage with Perplexity
  python debugger.py --task "Go to google and search for AI" --url "https://google.com" --provider perplexity --api-key "pplx-xxx"
  
  # With Gemini and visible browser
  python debugger.py --task "Click login button" --url "https://example.com" --provider gemini --api-key "xxx" --no-headless
  
  # Using environment variables
  export PERPLEXITY_API_KEY="pplx-xxx"
  python debugger.py --task "Test the website" --url "https://example.com"
        """
    )
    
    parser.add_argument(
        "--task", "-t",
        required=True,
        help="The task for the agent to perform"
    )
    
    parser.add_argument(
        "--url", "-u",
        required=True,
        help="The starting URL"
    )
    
    parser.add_argument(
        "--provider", "-p",
        default="perplexity",
        choices=["gemini", "perplexity", "hf"],
        help="LLM provider (default: perplexity)"
    )
    
    parser.add_argument(
        "--api-key", "-k",
        default=None,
        help="API key (or use environment variable)"
    )
    
    parser.add_argument(
        "--headless",
        action="store_true",
        default=True,
        help="Run browser in headless mode (default: True)"
    )
    
    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Show browser window (disable headless mode)"
    )
    
    parser.add_argument(
        "--max-events", "-m",
        type=int,
        default=100,
        help="Maximum events before stopping (default: 100)"
    )
    
    args = parser.parse_args()
    
    # Handle headless flag
    if args.no_headless:
        args.headless = False
    
    # Run
    asyncio.run(run_agent(args))


if __name__ == "__main__":
    main()
