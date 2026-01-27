"""
LaTeX Report Generator

Converts research state into a LaTeX document.
"""

import re
from datetime import datetime
from .state import KalshiResearchState


def escape_latex(text: str) -> str:
    """Escape special LaTeX characters."""
    if not text:
        return ""
    replacements = [
        ('\\', r'\textbackslash{}'),
        ('&', r'\&'),
        ('%', r'\%'),
        ('$', r'\$'),
        ('#', r'\#'),
        ('_', r'\_'),
        ('{', r'\{'),
        ('}', r'\}'),
        ('~', r'\textasciitilde{}'),
        ('^', r'\textasciicircum{}'),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def generate_latex_report(state: KalshiResearchState) -> str:
    """Generate a LaTeX document from research state."""

    # Calculate market pricing display
    yes_odds = next((o for o in state.market_odds if o['outcome'].lower() == 'yes'), None)
    no_odds = next((o for o in state.market_odds if o['outcome'].lower() == 'no'), None)

    yes_pct = f"{yes_odds['implied_probability'] * 100:.1f}" if yes_odds else "N/A"
    no_pct = f"{no_odds['implied_probability'] * 100:.1f}" if no_odds else "N/A"

    # Independent estimates
    yes_est = next((p for p in state.estimated_probabilities if p['outcome'].lower() == 'yes'), None)
    no_est = next((p for p in state.estimated_probabilities if p['outcome'].lower() == 'no'), None)

    yes_est_pct = f"{yes_est['estimated_probability'] * 100:.1f}" if yes_est else "N/A"
    no_est_pct = f"{no_est['estimated_probability'] * 100:.1f}" if no_est else "N/A"

    # Build persona recommendations table rows
    persona_rows = ""
    for rec in state.persona_recommendations:
        persona_name = escape_latex(rec.get('persona', '').replace('_', ' ').title())
        position = escape_latex(rec.get('suggested_position', 'N/A'))
        rationale = escape_latex(rec.get('rationale', '')[:100] + '...' if len(rec.get('rationale', '')) > 100 else rec.get('rationale', ''))
        persona_rows += f"        {persona_name} & {position} & {rationale} \\\\\n        \\hline\n"

    # Build scenarios
    scenarios_tex = ""
    for scenario in state.scenarios:
        s_type = escape_latex(scenario.get('type', '').replace('_', ' ').title())
        s_desc = escape_latex(scenario.get('description', ''))
        s_shift = escape_latex(scenario.get('probability_shift', ''))
        triggers = scenario.get('key_triggers', [])
        triggers_tex = "\n".join([f"            \\item {escape_latex(t)}" for t in triggers])

        scenarios_tex += f"""
    \\subsection*{{{s_type}}}
    {s_desc}

    \\textbf{{Probability Shift:}} {s_shift}

    \\textbf{{Key Triggers:}}
    \\begin{{itemize}}
{triggers_tex}
    \\end{{itemize}}
"""

    # Edge analysis
    edge_text = escape_latex(state.edge_analysis or "No edge analysis available.")

    # Research summary
    research_text = escape_latex(state.research_summary or "No research summary available.")

    # Sources
    sources_tex = "\n".join([f"    \\item {escape_latex(s)}" for s in state.sources]) if state.sources else "    \\item No sources cited"

    latex = f"""\\documentclass[11pt,a4paper]{{article}}

\\usepackage[utf8]{{inputenc}}
\\usepackage[T1]{{fontenc}}
\\usepackage{{lmodern}}
\\usepackage{{geometry}}
\\usepackage{{graphicx}}
\\usepackage{{booktabs}}
\\usepackage{{array}}
\\usepackage{{xcolor}}
\\usepackage{{fancyhdr}}
\\usepackage{{titlesec}}
\\usepackage{{amsmath}}
\\usepackage{{amssymb}}

\\geometry{{margin=1in}}

% Colors
\\definecolor{{kalshipurple}}{{RGB}}{{102, 51, 153}}
\\definecolor{{bullgreen}}{{RGB}}{{34, 139, 34}}
\\definecolor{{bearred}}{{RGB}}{{178, 34, 34}}

% Header/Footer
\\pagestyle{{fancy}}
\\fancyhf{{}}
\\fancyhead[L]{{\\textcolor{{kalshipurple}}{{Kalshi Research Report}}}}
\\fancyhead[R]{{\\thepage}}
\\fancyfoot[C]{{\\small Generated on {datetime.now().strftime("%B %d, %Y")}}}

% Section formatting
\\titleformat{{\\section}}{{\\Large\\bfseries\\color{{kalshipurple}}}}{{\\thesection}}{{1em}}{{}}
\\titleformat{{\\subsection}}{{\\large\\bfseries}}{{\\thesubsection}}{{1em}}{{}}

\\begin{{document}}

% Title
\\begin{{center}}
    {{\\LARGE\\bfseries\\textcolor{{kalshipurple}}{{Market Research Report}}}}

    \\vspace{{0.5cm}}

    {{\\Large {escape_latex(state.market_title or "Unknown Market")}}}

    \\vspace{{0.3cm}}

    {{\\small Market Reference: \\texttt{{{escape_latex(state.market_url_or_id or "N/A")}}}}}
\\end{{center}}

\\vspace{{1cm}}

%% ============================================
\\section{{Market Overview}}
%% ============================================

\\begin{{tabular}}{{@{{}}ll@{{}}}}
    \\textbf{{Resolution Criteria:}} & \\parbox[t]{{10cm}}{{{escape_latex(state.resolution_criteria or "Not specified")}}} \\\\[0.5em]
    \\textbf{{Expiration:}} & {escape_latex(state.expiration_date or "Not specified")} \\\\
\\end{{tabular}}

%% ============================================
\\section{{Market Pricing vs Independent Estimate}}
%% ============================================

\\begin{{center}}
\\begin{{tabular}}{{lcc}}
    \\toprule
    \\textbf{{Outcome}} & \\textbf{{Market Price}} & \\textbf{{Independent Estimate}} \\\\
    \\midrule
    \\textcolor{{bullgreen}}{{Yes}} & {yes_pct}\\% & {yes_est_pct}\\% \\\\
    \\textcolor{{bearred}}{{No}} & {no_pct}\\% & {no_est_pct}\\% \\\\
    \\bottomrule
\\end{{tabular}}
\\end{{center}}

\\vspace{{0.5cm}}

\\textbf{{Confidence Level:}} {escape_latex((state.confidence_level or "Not specified").title())}

%% ============================================
\\section{{Edge Analysis}}
%% ============================================

{edge_text}

%% ============================================
\\section{{Research Summary}}
%% ============================================

{research_text}

\\subsection*{{Sources}}
\\begin{{itemize}}
{sources_tex}
\\end{{itemize}}

%% ============================================
\\section{{Persona-Based Recommendations}}
%% ============================================

\\begin{{center}}
\\begin{{tabular}}{{|p{{3cm}}|p{{3cm}}|p{{8cm}}|}}
    \\hline
    \\textbf{{Persona}} & \\textbf{{Position}} & \\textbf{{Rationale}} \\\\
    \\hline
{persona_rows}\\end{{tabular}}
\\end{{center}}

%% ============================================
\\section{{Scenario Analysis}}
%% ============================================
{scenarios_tex}

%% ============================================
\\section*{{Disclaimer}}
%% ============================================

{{\\small\\textit{{This research report is for informational purposes only and does not constitute financial advice, investment advice, or a recommendation to buy or sell any securities or prediction market contracts. Prediction markets involve risk of loss. Past performance does not guarantee future results. Always do your own research and consider your own risk tolerance before participating in any market.}}}}

\\end{{document}}
"""
    return latex


def save_latex_report(state: KalshiResearchState, output_path: str) -> str:
    """Generate and save LaTeX report to file."""
    latex_content = generate_latex_report(state)
    with open(output_path, 'w') as f:
        f.write(latex_content)
    return output_path
