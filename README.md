# Kalshi Research Assistant

A research assistant that analyzes Kalshi prediction markets and provides structured, persona-specific suggestions.

**This is a research tool, not financial advice.**

## What It Does

1. **Takes a user-provided Kalshi market** (URL, ticker, or description)
2. **Conducts independent research** on factors affecting the outcome
3. **Forms probability estimates** without looking at market prices
4. **Compares estimates to market pricing** to identify potential mispricings
5. **Generates persona-specific suggestions** for different participant types
6. **Produces a structured research report** with scenarios and risks

## Installation

```bash
# Clone or download the repository
cd kalshi-betting-bot

# Install dependencies
pip install -r requirements.txt

# Or install as a package
pip install -e .
```

## Configuration

Set your Anthropic API key:

```bash
export ANTHROPIC_API_KEY='your-api-key'
```

## Usage

### Command Line

```bash
# Analyze a specific market by ticker
python -m src.main "KXBTC-24DEC31-100K"

# Analyze by description
python -m src.main "Will the Fed cut rates in January 2025?"

# Run in interactive mode
python -m src.main --interactive

# Save report to file
python -m src.main "KXINX-24DEC31-6000" --output report.md

# Suppress progress messages
python -m src.main "MARKET" --quiet
```

### As a Python Module

```python
from src.graph.workflow import run_research

# Run analysis
state = run_research("KXBTC-24DEC31-100K")

# Access the final report
print(state.final_output)

# Or access individual components
print(state.research_summary)
print(state.estimated_probabilities)
print(state.edge_analysis)
```

## Workflow Architecture

The research workflow consists of 8 sequential steps, each powered by a specialized Claude skill:

```
market_ingestor    ─→  Validate user input
        │
market_parser      ─→  Extract market mechanics
        │
independent_researcher  ─→  Gather external research
        │
probability_estimator   ─→  Form independent estimates
        │
mispricing_analyst      ─→  Compare to market pricing
        │
persona_recommender     ─→  Generate persona suggestions
        │
scenario_analyst        ─→  Stress test the thesis
        │
final_suggester         ─→  Synthesize final report
```

## Participant Personas

The assistant generates suggestions for 6 different participant types:

| Persona | Description |
|---------|-------------|
| **risk_averse** | Prioritizes capital preservation, prefers high-confidence plays |
| **risk_seeking** | Comfortable with uncertainty, looks for asymmetric payoffs |
| **news_driven** | Trades on information flow, reacts to catalysts |
| **macro_thinker** | Considers big-picture trends and correlations |
| **casual_participant** | Limited time for analysis, wants simple thesis |
| **data_analyst** | Wants quantitative edge, skeptical of narratives |

## Project Structure

```
kalshi-betting-bot/
├── src/
│   ├── graph/
│   │   ├── state.py      # Workflow state definition
│   │   ├── nodes.py      # LangGraph nodes (Claude skill calls)
│   │   ├── validators.py # State validation guards
│   │   └── workflow.py   # Workflow orchestration
│   └── main.py           # CLI entry point
│
├── .claude/
│   ├── skills/           # Claude skill system prompts
│   │   ├── market_ingestor.md
│   │   ├── market_parser.md
│   │   ├── independent_researcher.md
│   │   ├── probability_estimator.md
│   │   ├── mispricing_analyst.md
│   │   ├── persona_recommender.md
│   │   ├── scenario_analyst.md
│   │   └── final_suggester.md
│   └── personas.yaml     # Persona definitions
│
├── requirements.txt
├── pyproject.toml
└── README.md
```

## Validation & Error Handling

The workflow enforces strict validation between steps:

- **No market inference** - if input is unclear, stops and requests clarification
- **No research without parsed mechanics** - ensures we know what resolves the market
- **No probability estimates without research** - estimates must be grounded
- **Probabilities must sum to ~1** - basic sanity check
- **All personas must be covered** - ensures complete output

## Limitations

- **No real-time data**: Research is based on Claude's knowledge and web search capabilities
- **No trade execution**: This is research only, not a trading bot
- **Not financial advice**: Outputs are reasoned opinions under uncertainty
- **Knowledge cutoff**: Claude's training data has a cutoff date

## Disclaimer

This tool provides research and analysis for informational purposes only. It does not constitute financial advice, investment advice, or a recommendation to buy or sell any prediction market contracts.

Prediction markets involve risk of loss. Past performance does not guarantee future results. Always do your own research and consider your own risk tolerance before participating in any market.

The authors are not responsible for any financial losses incurred through use of this tool.

## License

MIT
