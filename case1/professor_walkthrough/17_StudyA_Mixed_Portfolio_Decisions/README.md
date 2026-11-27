# 17 StudyA Mixed Portfolio Decisions

Move from controlled same-hardware assignment to mixed investment strategies. Present the class-specific three-objective Pareto sets, then A1 representative strategies and multimetric cost/import/spill/cycle frontier. No cross-class installed-cost ranking.

## Figure sequence (Python outputs verified)

- Figure 44: Eight original matched-hardware portfolios: pass, fail and unresolved territory evidence by factor. Source: case1/studies/SEEDExchange_StudyA_Synthesis_2026-11-22/MATCHED_34HOUSE_PORTFOLIO_EVIDENCE_2026-11-27_v2.csv.
- Figure 45: 307 nondominated portfolios across four separate physical classes; reference loss-cost, SS and spill. Source: case1/studies/SEEDExchange_StudyA_Synthesis_2026-11-22/MIXED_PORTFOLIO_COMPLETE_PARETO_2026-11-27_v3.csv.
- Figure 46: Five A1 representative strategies: loss-cost, imports, spill and capacity-weighted battery cycles. Source: case1/studies/SEEDExchange_StudyA_Synthesis_2026-11-22/MIXED_PORTFOLIO_COMPLETE_REPRESENTATIVES_2026-11-27_v3.csv.
- Figure 49: Cost versus imports for all 307 class-specific nondominated portfolios; color encodes DC spill or physical-window equivalent cycles. Source: case1/studies/SEEDExchange_StudyA_Synthesis_2026-11-22/MIXED_PORTFOLIO_COMPLETE_PARETO_2026-11-27_v3.csv.

Generator: [Python script](../generate_study_a_conclusion_figures.py). [Signed input plan](../STUDY_A_FIGURE_PLAN_2026-11-27.json). PNG/SVG byte hashes independently verified against the successful rendering job; see [verified output manifest](../STUDY_A_FIGURES_41_49_VERIFIED_MANIFEST.json). No source study is moved.

## Published figures

- Figure 44: [PNG](python_figures/44_matched_portfolio_evidence.png) · [SVG](python_figures/44_matched_portfolio_evidence.svg)
- Figure 45: [PNG](python_figures/45_mixed_portfolio_pareto.png) · [SVG](python_figures/45_mixed_portfolio_pareto.svg)
- Figure 46: [PNG](python_figures/46_a1_investment_strategies.png) · [SVG](python_figures/46_a1_investment_strategies.svg)
- Figure 49: [PNG](python_figures/49_technoeconomic_pareto_multimetric.png) · [SVG](python_figures/49_technoeconomic_pareto_multimetric.svg)

Figure 49 displays battery cycles on the existing three-objective nondominated set, not a four-objective optimization.
