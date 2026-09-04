"""Main application entry point for Multi-Agent AI System."""

import argparse
import asyncio
import logging
import sys

from app_factory import build_application
from cli import CLIApplication
from config import get_settings

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("main")


def main() -> int:
    """Initialize system dependencies and run CLI application."""
    parser = argparse.ArgumentParser(description="Multi-Agent AI System Orchestration Entrypoint")
    parser.add_argument(
        "instruction",
        nargs="?",
        default=None,
        help="Optional single-shot instruction text. If omitted, starts interactive CLI mode.",
    )
    parser.add_argument(
        "--simulate",
        "--mock",
        action="store_true",
        help="Force deterministic simulation/mock mode without calling Gemini API.",
    )
    args = parser.parse_args()

    try:
        settings = get_settings()
    except Exception:
        settings = None

    # Build application orchestrator using factory
    orchestrator = build_application(settings=settings, simulation_mode=args.simulate)
    cli_app = CLIApplication(orchestrator=orchestrator)

    if args.instruction:
        # Non-interactive single-shot mode
        return asyncio.run(cli_app.run_single_shot(args.instruction))
    else:
        # Interactive CLI mode
        return asyncio.run(cli_app.run_interactive())


if __name__ == "__main__":
    sys.exit(main())
