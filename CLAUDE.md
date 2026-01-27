# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Kalshi Research Assistant - A research tool that analyzes Kalshi prediction markets through an 8-step workflow powered by specialized Claude skills. This is a research analysis tool, NOT a trading bot.

## Build & Development Commands

```bash
# Install in development mode
pip install -e .

# Install with dev dependencies
pip install -e ".[dev]"

# Run CLI
python -m src.main "MARKET_INPUT"
# or after install:
kalshi-research "MARKET_INPUT"

# Format code
black .

# Lint
ruff check .

# Run tests
pytest
pytest --asyncio-mode=auto
```

## Architecture

### Kalshi API Integration

The system fetches live market data from Kalshi's public API (`src/graph/kalshi_api.py`):
- Base URL: `https://api.elections.kalshi.com/trade-api/v2`
- Extracts ticker from URLs like `https://kalshi.com/markets/.../TICKER`
- Fetches resolution criteria, expiration, and current prices
- No authentication required for public market data

### Workflow Pipeline

The system uses an 8-step sequential pipeline where each step calls a specialized Claude skill (system prompts in `.claude/skills/`):

1. **market_ingestor** → Validate user input (URL/ticker/description)
2. **market_parser** → Extract market mechanics (resolution, expiration, odds)
3. **independent_researcher** → Research market factors independently
4. **probability_estimator** → Form probability estimates before seeing market prices
5. **mispricing_analyst** → Compare estimates vs market pricing
6. **persona_recommender** → Generate 6 persona-specific suggestions
7. **scenario_analyst** → Stress test with best/worst/likely scenarios
8. **final_suggester** → Synthesize final markdown report

### Key Entry Points

- **CLI**: `src/main.py` - Command line interface
- **Programmatic**: `src.graph.workflow.run_research()` or `ResearchWorkflow` class

### State Flow

State is passed through the pipeline as `KalshiResearchState` (TypedDict). Each node reads required fields, validates them, calls Claude, and writes to specific output fields. Validation guards between steps ensure data integrity.

### Personas

The system generates recommendations for 6 personas defined in `.claude/personas.yaml`:
- `risk_averse`, `risk_seeking`, `news_driven`, `macro_thinker`, `casual_participant`, `data_analyst`

## Configuration

- Requires `ANTHROPIC_API_KEY` environment variable
- Uses `claude-sonnet-4-20250514` model with 4096 max tokens
- Code style: black + ruff, line-length 100
