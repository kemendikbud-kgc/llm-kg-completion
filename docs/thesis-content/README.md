# Thesis Content - Quick Reference

This folder contains markdown content ready to copy into your thesis document.

## Files

| File | Target Section | Content |
|------|----------------|---------|
| `bab-2-1-4-metrik-kg.md` | BAB 2.1.4 (NEW) | KG evaluation metrics theory with LaTeX formulas |
| `bab-4-hasil.md` | BAB 4.X | Results tables (fill in "-" with actual values) |
| `lampiran-2-kuesioner.md` | LAMPIRAN 2 | Full teacher validation questionnaire |

## Copy Instructions

### For Google Docs:
1. Open the markdown file in a text editor (VS Code, Notepad)
2. Copy the content
3. Paste into Google Docs
4. Format headings (Heading 1, 2, 3) as needed
5. For LaTeX formulas ($...$), use:
   - Google Docs Add-ons → MathType / EquatIO
   - Or insert → Equation

### For Microsoft Word:
1. Open markdown file
2. Copy content
3. Paste into Word
4. Use Equation Editor for formulas (Alt + =)

### For LaTeX Thesis:
The formulas are already in LaTeX format ($...$), ready to use directly.

## Placeholder Values

Tables in `bab-4-hasil.md` contain "-" placeholders. Fill these with actual values after:
1. Running the KG pipeline on all 3 subjects
2. Computing metrics via `get_graph_quality_metrics()`
3. Collecting teacher survey responses

## Formula Reference

Key formulas included:

| Metric | Formula |
|--------|---------|
| Average Degree Centrality | $ADC = \frac{1}{|V|} \sum_{v \in V} \frac{deg(v)}{|V| - 1}$ |
| Modularity | $Q = \frac{1}{2m}\sum_{ij}\left[A_{ij} - \frac{k_i k_j}{2m}\right]\delta(c_i, c_j)$ |
| Graph Density | $\rho = \frac{|E|}{|V|(|V| - 1)}$ |
| Description Completeness | $DC = \frac{|\{e : desc(e) \neq \emptyset\}|}{|E|}$ |
| Typed Relation Ratio | $TRR = \frac{|T_{typed}|}{|T_{SIMILAR\_TO}|}$ |
| Cohen's Kappa | $\kappa = \frac{p_o - p_e}{1 - p_e}$ |
| Composite Quality | $Q_{composite} = \sum_{i=1}^{4} w_i \cdot S_i$ |

## Next Steps

1. **Run experiments** to get actual metric values
2. **Generate survey items** from KG (sample 10 concepts, 5 relations per subject)
3. **Create Google Form** using the questionnaire template
4. **Collect responses** from 3 teachers
5. **Analyze results** and fill in BAB 4 tables
6. **Compute Cohen's Kappa** if multiple teachers rate same items
