# Multi-Agent AI System

A production-grade Python Multi-Agent AI System built with the official `google-genai` SDK and Gemini models.

## Architecture

```
                         USER
                           │
                           ▼
                    ┌─────────────┐
                    │  CLI Layer  │
                    └──────┬──────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │   Orchestrator  │
                  └────────┬────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │   Owner Agent   │
                  └────────┬────────┘
                           │
              ┌────────────┴────────────┐
              │                         │
              ▼                         ▼
       ┌─────────────┐           ┌─────────────┐
       │  CS Agent   │           │  Ads Agent  │
       └──────┬──────┘           └──────┬──────┘
              │                         │
              └────────────┬────────────┘
                           │
                      errors/failures
                           │
                           ▼
                  ┌─────────────────┐
                  │ Debugger Agent  │
                  └────────┬────────┘
                           │
                           ▼
                 Self-Debugging Loop
```

### Component Responsibilities

- **CLI Layer (`cli.py`)**: Real-time progress display, user instruction entry, interactive command handlers (`/help`, `/status`, `/agents`, `/exit`).
- **Application Orchestrator (`orchestrator.py`)**: Central application coordinator. Manages correlation request IDs, execution trace logging, Owner Agent decision processing, allowlist-based specialist agent routing, error handling, and `SelfDebuggingLoop` integration.
- **Owner Agent (`agents/owner_agent.py`)**: Primary supervisory and decision-making agent. Evaluates instructions and routes tasks to specialist agents (`cs-agent`, `ads-agent`).
- **Customer Service Agent (`agents/cs_agent.py`)**: Specialized customer inquiry resolution agent operating strictly within grounded facts.
- **Ads Agent (`agents/ads_agent.py`)**: Campaign performance analytics and optimization advisory agent. *Strictly restricted from automatically modifying external ad campaigns.*
- **Debugger Agent (`agents/debugger_agent.py`)**: Automated exception capture and diagnostic analysis agent. *Strictly restricted from executing code or modifying files automatically.*
- **Self-Debugging Loop (`agents/debugging_loop.py`)**: Managed loop capturing uncaught agent exceptions, sanitizing sensitive credentials, and triggering Debugger Agent analysis.
- **AgentEngine & MessageBus (`agents/engine.py`, `agents/message_bus.py`)**: Core execution engine enforcing recursion limits and typed asynchronous inter-agent message passing.

---

## Installation & Setup

### Requirements
- Python 3.11+
- Virtual environment (`venv`)

### 1. Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Environment Configuration

Copy `.env.example` to `.env` and set your API keys:

```bash
cp .env.example .env
```

Environment variables:
- `GOOGLE_API_KEY` or `GEMINI_API_KEY`: Google Gemini API Key.
- `GEMINI_MODEL`: Model identifier (default: `gemini-2.5-flash`).

---

## Usage

### Interactive CLI Mode

Run without arguments to start the interactive CLI loop:

```bash
python main.py
```

### Deterministic Mock / Simulation Mode

Run without requiring a Gemini API key:

```bash
python main.py --simulate
```

### One-Shot Command Execution

Execute a single prompt directly from the terminal:

```bash
python main.py --simulate "Analyze our advertising campaign ROAS performance."
```

### Interactive CLI Commands

- `/help` - Display command help and usage instructions.
- `/status` - Display system status and registered agent counts.
- `/agents` - List active registered agents in the registry.
- `/exit` or `/quit` - Exit the interactive CLI mode.

---

## Safety Boundaries & Principles

1. **Non-Destructive Debugger**: The Debugger Agent and `SelfDebuggingLoop` generate root-cause analysis and patch recommendations. They **never** automatically execute shell commands or modify source files.
2. **Ads Agent Advisory Scope**: The Ads Agent produces diagnostic analytics and recommendations only. It **never** executes live campaign budget or targeting changes automatically.
3. **Grounded CS Responses**: The CS Agent resolves customer inquiries based solely on verified grounded facts and explicitly flags missing information when needed.
4. **Allowlist Routing**: The Orchestrator validates all agent execution targets against a strict security allowlist (`owner`, `cs-agent`, `ads-agent`, `debugger-agent`) via `AgentRouter`.

---

## Testing

Run the complete test suite:

```bash
python -m pytest
```

---

## Manual Local Acceptance Testing Sequence

To manually test all key Phase 4 flows:

### Test A: Launch Interactive Simulation
```bash
python main.py --simulate
```

### Test B: View Active Agents
```
> /agents
```
*Expected Output:* Displays `owner`, `cs-agent`, `ads-agent`, and `debugger-agent`.

### Test C: Customer Service Instruction
```
> Analyze our customer service response time and refund policy.
```
*Expected Output:* Real-time trace showing `[OWNER]` routing decision to `[CS]`, followed by structured customer service output.

### Test D: Advertising Analysis Instruction
```
> Analyze our ad campaign performance and ROAS metrics.
```
*Expected Output:* Real-time trace showing `[OWNER]` routing decision to `[ADS]`, followed by campaign performance findings and advisory recommendations.

### Test E: Exit CLI
```
> /exit
```
