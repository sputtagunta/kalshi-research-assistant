#!/usr/bin/env python3
"""
Kalshi Research Assistant - Main Entry Point

A research assistant that analyzes Kalshi prediction markets and provides
structured recommendations for different participant personas.

Usage:
    python -m src.main "MARKET_INPUT"
    python -m src.main --interactive
    python -m src.main --help
"""

import argparse
import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.graph.workflow import run_research, DEFAULT_PERSONAS
from src.graph.state import KalshiResearchState
from src.graph.latex_generator import save_latex_report


def print_report(state: KalshiResearchState) -> None:
    """Print the final research report."""
    if state.input_validation_error:
        print("\n" + "="*60)
        print("VALIDATION ERROR")
        print("="*60)
        print(f"\n{state.input_validation_error}\n")
        return

    if state.final_output:
        print("\n" + state.final_output)
    else:
        print("\n" + "="*60)
        print("WORKFLOW INCOMPLETE")
        print("="*60)
        print("\nThe workflow did not complete successfully.")
        if state.errors:
            print("\nErrors encountered:")
            for error in state.errors:
                print(f"  - {error}")


def interactive_mode() -> None:
    """Run in interactive mode, prompting for market input."""
    print("\n" + "="*60)
    print("KALSHI RESEARCH ASSISTANT")
    print("="*60)
    print("\nThis assistant analyzes Kalshi prediction markets and provides")
    print("research-based suggestions for different participant personas.")
    print("\nNote: This is for informational purposes only, not financial advice.")
    print("-"*60)

    while True:
        print("\nEnter a Kalshi market to analyze:")
        print("  - URL: https://kalshi.com/markets/...")
        print("  - Ticker: KXBTC-24DEC31-100K")
        print("  - Description: 'Will BTC exceed $100K by end of 2024?'")
        print("\nOr type 'quit' to exit.\n")

        market_input = input("> ").strip()

        if market_input.lower() in ("quit", "exit", "q"):
            print("\nGoodbye!")
            break

        if not market_input:
            print("Please enter a market to analyze.")
            continue

        print("\nStarting research workflow...\n")
        state = run_research(market_input, verbose=True)
        print_report(state)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Kalshi Research Assistant - Analyze prediction markets",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.main "KXBTC-24DEC31-100K"
  python -m src.main "https://kalshi.com/markets/kxbtc/btc-100k"
  python -m src.main "Will the Fed cut rates in January 2025?"
  python -m src.main --interactive

Note: Requires ANTHROPIC_API_KEY environment variable to be set.

DISCLAIMER: This tool provides research and analysis for informational
purposes only. It does not constitute financial advice. Prediction
markets involve risk of loss. Always do your own research.
        """
    )

    parser.add_argument(
        "market",
        nargs="?",
        help="Kalshi market to analyze (URL, ticker, or description)"
    )

    parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="Run in interactive mode"
    )

    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress progress messages"
    )

    parser.add_argument(
        "--personas",
        nargs="+",
        choices=DEFAULT_PERSONAS,
        default=DEFAULT_PERSONAS,
        help="Personas to generate recommendations for"
    )

    parser.add_argument(
        "--output",
        type=str,
        help="Save report to file (markdown)"
    )

    parser.add_argument(
        "--tex",
        type=str,
        metavar="FILE",
        help="Generate LaTeX report and save to FILE"
    )

    args = parser.parse_args()

    # Check for API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY environment variable not set.")
        print("\nTo set it:")
        print("  export ANTHROPIC_API_KEY='your-api-key'")
        sys.exit(1)

    # Run in appropriate mode
    if args.interactive:
        interactive_mode()
    elif args.market:
        verbose = not args.quiet
        state = run_research(
            args.market,
            personas=args.personas,
            verbose=verbose
        )

        if args.tex:
            tex_path = save_latex_report(state, args.tex)
            print(f"\nLaTeX report saved to: {tex_path}")
            print(f"Compile with: pdflatex {tex_path}")
        elif args.output:
            output_path = Path(args.output)
            if state.final_output:
                output_path.write_text(state.final_output)
                print(f"\nReport saved to: {output_path}")
            else:
                print(f"\nNo report to save - workflow incomplete")
        else:
            print_report(state)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
