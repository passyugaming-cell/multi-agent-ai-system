"""CLI Interaction Layer for Multi-Agent AI System.

Provides progress indicators, command processing (/help, /status, /agents, /exit),
interactive mode, and single-shot command line mode.
"""

import asyncio
import sys
from typing import List, Optional, TextIO

from orchestrator import (
    ApplicationOrchestrator,
    ExecutionStatus,
    ExecutionTraceEntry,
    OrchestrationRequest,
    OrchestrationResult,
)

CLI_WELCOME_MESSAGE = """
===================================================================
                MULTI-AGENT AI SYSTEM — CLI
===================================================================
Welcome to the Multi-Agent AI System interactive interface.
Enter natural language instructions for the system to process.
Special commands: /help, /status, /agents, /quit, /exit
===================================================================
"""

CLI_HELP_TEXT = """
Available Commands:
  /help    - Display this help message.
  /status  - Display system status and registered agents count.
  /agents  - List all active registered agents.
  /quit    - Exit the application.
  /exit    - Exit the application.

Or enter any natural-language prompt or instruction (e.g., 'Analyze customer service problem').
"""


class CLIOutputFormatter:
    """Centralized human-readable CLI output formatter."""

    def __init__(self, out_stream: TextIO = sys.stdout) -> None:
        """Initialize CLIOutputFormatter.

        Args:
            out_stream: Output text stream (default sys.stdout).
        """
        self.out_stream = out_stream

    def print_line(self, message: str = "") -> None:
        """Print a line to output stream."""
        self.out_stream.write(f"{message}\n")
        self.out_stream.flush()

    def print_trace_entry(self, entry: ExecutionTraceEntry) -> None:
        """Format and print real-time execution trace entry."""
        agent_tag = entry.agent_id.upper().replace("-AGENT", "")
        status_tag = entry.status.value

        if entry.status == ExecutionStatus.FAILED:
            prefix = "[ERROR]"
        elif entry.status == ExecutionStatus.DEBUGGING:
            prefix = "[DEBUGGER]"
        elif entry.status == ExecutionStatus.REQUIRES_HUMAN_REVIEW:
            prefix = "[HUMAN_REVIEW_REQUIRED]"
        else:
            prefix = f"[{agent_tag}]"

        self.print_line(f"{prefix} {entry.event}")

    def print_result(self, result: OrchestrationResult) -> None:
        """Format and print final orchestration result."""
        self.print_line()
        self.print_line("-------------------------------------------------------------------")
        self.print_line(f"[RESULT] Request ID: {result.request_id}")
        self.print_line(f"[STATUS] {result.status.value}")
        self.print_line("-------------------------------------------------------------------")
        self.print_line(result.final_response)
        self.print_line("-------------------------------------------------------------------")
        self.print_line()


class CLIApplication:
    """Interactive CLI application manager."""

    def __init__(
        self,
        orchestrator: ApplicationOrchestrator,
        formatter: Optional[CLIOutputFormatter] = None,
        in_stream: Optional[TextIO] = None,
    ) -> None:
        """Initialize CLIApplication.

        Args:
            orchestrator: ApplicationOrchestrator instance.
            formatter: CLIOutputFormatter instance.
            in_stream: Input stream (default sys.stdin).
        """
        self.orchestrator = orchestrator
        self.formatter = formatter or CLIOutputFormatter()
        self.in_stream = in_stream or sys.stdin

        # Connect orchestrator real-time trace callback to CLI formatter
        self.orchestrator.trace_callback = self.formatter.print_trace_entry

    def show_status(self) -> None:
        """Display system status."""
        registered_agents = self.orchestrator.registry.list_agents()
        self.formatter.print_line("\n[SYSTEM STATUS]")
        self.formatter.print_line(f"Active Agents Registered: {len(registered_agents)}")
        self.formatter.print_line(f"Message Bus: {type(self.orchestrator.message_bus).__name__}")
        self.formatter.print_line(f"Self-Debugging Loop: {'Enabled' if self.orchestrator.debugging_loop else 'Disabled'}\n")

    def show_agents(self) -> None:
        """List active registered agents."""
        agents = self.orchestrator.registry.list_agents()
        self.formatter.print_line("\n[REGISTERED AGENTS]")
        for agent in agents:
            self.formatter.print_line(f" - {agent.agent_id}: {agent.name} ({agent.description})")
        self.formatter.print_line()

    async def execute_instruction(self, instruction: str) -> OrchestrationResult:
        """Execute a single natural language instruction."""
        req = OrchestrationRequest(instruction=instruction)
        self.formatter.print_line(f"\n[REQUEST] ID: {req.request_id}")
        result = await self.orchestrator.handle_request(req)
        self.formatter.print_result(result)
        return result

    async def run_interactive(self) -> int:
        """Start interactive CLI loop until exit command or interruption."""
        self.formatter.print_line(CLI_WELCOME_MESSAGE)

        while True:
            try:
                self.formatter.out_stream.write("> ")
                self.formatter.out_stream.flush()

                # Read line asynchronously / gracefully from in_stream
                loop = asyncio.get_running_loop()
                raw_input = await loop.run_in_executor(None, self.in_stream.readline)

                if not raw_input:  # EOF (Ctrl+D)
                    self.formatter.print_line("\n[EOF received. Exiting...]")
                    break

                userInput = raw_input.strip()
                if not userInput:
                    continue

                # Process command or prompt instruction
                cmd = userInput.lower()
                if cmd in ("/exit", "/quit"):
                    self.formatter.print_line("[Exiting CLI...]")
                    break
                elif cmd == "/help":
                    self.formatter.print_line(CLI_HELP_TEXT)
                elif cmd == "/status":
                    self.show_status()
                elif cmd == "/agents":
                    self.show_agents()
                else:
                    await self.execute_instruction(userInput)

            except (KeyboardInterrupt, asyncio.CancelledError):
                self.formatter.print_line("\n[KeyboardInterrupt received. Exiting gracefully...]")
                break
            except Exception as e:
                self.formatter.print_line(f"\n[ERROR] CLI encountered an error: {e}")

        return 0

    async def run_single_shot(self, instruction: str) -> int:
        """Execute single-shot mode with a single prompt instruction."""
        result = await self.execute_instruction(instruction)
        return 0 if result.success else 1
