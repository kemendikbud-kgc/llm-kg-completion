# Paper Analysis: A Survey on LLM-as-a-Judge

> Extracted for the **LLM-Assisted Knowledge Graph Completion for Curriculum Analysis** thesis.
> Focus: can an LLM serve as a tiebreaker between disagreeing human expert reviewers of KG triples?

---

## 1. Paper Metadata

- **Title:** A Survey on LLM-as-a-Judge
- **Authors:** Jiawei Gu, Xuhui Jiang, Zhichao Shi, Hexiang Tan, Xuehao Zhai, Chengjin Xu, Wei Li, Yinghan Shen, Shengjie Ma, Honghao Liu, Saizhuo Wang, Kun Zhang, Yuanzhuo Wang, Wen Gao, Lionel Ni, Jian Guo
- **Year:** 2024 (preprint, submitted Nov 23 2024; latest rev. Oct 2025) → published in *The Innovation*, 2026
- **Venue/Journal:** *The Innovation* (Cell Press / Elsevier, ISSN 2666-6758) — this is the ScienceDirect PII `S2666675825004564` you linked
- **Paper Type:** Survey (with a proposed reliability benchmark)
- **DOI/URL:** 10.1016/j.xinn.2025.101253 · arXiv:2411.15594 · https://www.sciencedirect.com/science/article/pii/S2666675825004564

---

## 2. Comprehensive Summary

**Research Context & Motivation.**
Evaluating open-ended, subjective outputs (generated text, reasoning chains, and — relevant to us — knowledge triples) at scale is expensive and inconsistent when done by human experts. The survey frames its central question as *"How can reliable LLM-as-a-Judge systems be built?"* and positions LLM judges as a scalable, cost-effective, consistent alternative (or supplement) to expert evaluation. The recurring caveat throughout is that reliability is **not free** — it must be engineered through careful design.

**Methodology & Approach.**
The survey organizes the field around three reliability strategies: (1) **improving consistency** of judgments, (2) **mitigating systematic biases**, and (3) **adapting to diverse assessment scenarios**. It catalogues how LLM judges are built (prompt-based scoring, pairwise comparison, reference-based vs reference-free judging, single vs multi-judge ensembles, fine-tuned judge models) and introduces a benchmark for measuring judge reliability. Across the literature it synthesizes, agreement with human raters (correlation, and for categorical labels, Cohen's/Fleiss' κ) is the standard yardstick for whether a judge is trustworthy.

**Key Findings & Results.**
The headline conclusion is qualified optimism: well-designed LLM judges can approximate human agreement on many tasks, but **ensuring reliability remains a significant open challenge**, and naive use imports characteristic biases. The most-cited failure modes in this literature (which the survey consolidates) are **position bias** (favoring the first/last option in pairwise judging), **verbosity bias** (preferring longer answers), **self-preference / self-enhancement bias** (a model rating outputs from its own family more favorably), and sensitivity to prompt and rubric wording. The practical takeaway: validate the judge against human consensus on a held-out set *before* trusting it, and apply debiasing (position randomization, rubric grounding, ensembling).

**Contributions & Novelty.**
- Unified taxonomy of LLM-as-a-judge methods (what to judge, how to judge, how to improve it).
- Consolidation of reliability-enhancement techniques: consistency, bias mitigation, scenario adaptation.
- A benchmark/methodology for evaluating the reliability of LLM judges themselves.
- A catalogue of bias types and mitigation strategies. **← most relevant to us**
- Cross-domain survey of applications (NLG, reasoning verification, multimodal, medicine/law/finance).
- Framework for hybrid human+LLM evaluation pipelines. **← most relevant to us (tiebreaker)**

**Limitations & Future Work (as acknowledged).**
- Reliability of LLM judges is still unsolved; biases persist even with mitigation.
- Domain-specific judging (e.g. high-school biology correctness) needs grounding the survey does not fully resolve.
- Self-preference bias is especially problematic when the judge and the generator share a model family.

---

## 3. Method Extraction

#### Method: Reference-grounded LLM judging (judge with the source text)
- **Description:** Instead of asking the LLM "is this triple correct?" in a vacuum, give it the *source passage* the triple was extracted from plus the triple, and ask it to rate against that evidence. Grounding the judge in the source dramatically reduces hallucinated verdicts and self-preference, because the judge checks faithfulness to a reference rather than its own prior.
- **How It Works:** (1) retrieve the chapter/subtopic text or `source_description` for the triple; (2) prompt the judge with rubric = the 4 review categories (correct / partial / wrong / missing); (3) require a rating **plus a rationale citing the source**; (4) parse to a structured verdict.
- **Applicable To:** A new `judge.py` consuming the same data as `completion.py`; reuses `schemas.py` patterns and `llama_setup.get_llm()`.
- **Implementation Complexity:** Low–Medium — one structured-output program, same stack you already use for extraction.
- **Expected Benefit:** A calibrated third vote on the ~64 single-reviewer biology triples and an adjudicator candidate for the ~52 two-reviewer splits.
- **Dependencies:** None new — litellm + LlamaIndex `LLMTextCompletionProgram` + a Pydantic `JudgeVerdict`.
- **Risks/Tradeoffs:** Self-preference if the judge model = the extractor model; mitigated by using a *different family*.
- **Paper Reference:** Reliability → consistency & bias-mitigation strategies; reference-based vs reference-free judging.

#### Method: Multi-judge ensemble with majority/confidence aggregation
- **Description:** Run 2–3 different LLM judges (different families) and aggregate. Reduces any single model's idiosyncratic bias; disagreement among judges is itself a useful "this triple is genuinely ambiguous" signal.
- **How It Works:** Query N judges → collect verdicts → majority vote, or escalate to human if judges split.
- **Applicable To:** `judge.py` aggregation layer; mirrors the human agreement gate you already designed.
- **Implementation Complexity:** Medium — N× cost, prompt/parse plumbing.
- **Expected Benefit:** Higher agreement with human consensus; fewer biased single-model calls.
- **Dependencies:** Access to ≥2 model families (you have Gemini + OpenAI + Anthropic via litellm).
- **Risks/Tradeoffs:** Cost; correlated errors if all judges trained on similar data.
- **Paper Reference:** Multi-judge ensembling under "improving consistency / mitigating biases".

#### Method: Calibrate the judge against human-agreed cases (validation-first)
- **Description:** Before using the LLM on disagreements, measure how well it reproduces the verdicts on triples where the **humans already agreed**. Report Cohen's κ between judge and human consensus. Only trust the judge on splits if it clears an agreement threshold on the agreed set.
- **How It Works:** (1) take all triples with ≥2 human ratings that agree; (2) run the judge blind; (3) compute accuracy + κ vs human consensus; (4) gate downstream use on the result.
- **Applicable To:** Evaluation script + thesis Bab 4 methodology.
- **Implementation Complexity:** Low — you already have the human data in `data/expert_feedback/`.
- **Expected Benefit:** Turns "we used an LLM tiebreaker" into a *defensible, measured* claim for the viva.
- **Dependencies:** `scikit-learn` for `cohen_kappa_score`.
- **Risks/Tradeoffs:** If κ is low, you learn the judge is *not* trustworthy here — which is itself a valid finding.
- **Paper Reference:** "Methodologies for evaluating the reliability of LLM-as-a-Judge."

#### Method: Position & verbosity debiasing
- **Description:** When judging pairwise or comparing the triple's description against alternatives, randomize option order and control for length so the judge doesn't reward longer/first answers.
- **How It Works:** Shuffle order across runs; normalize/penalize length in the rubric.
- **Applicable To:** `judge.py` prompt construction.
- **Implementation Complexity:** Low.
- **Expected Benefit:** Removes two of the best-documented LLM-judge biases.
- **Risks/Tradeoffs:** Minimal.
- **Paper Reference:** Bias catalogue (position bias, verbosity bias).

---

## 4. Priority Matrix

| Method | Impact | Effort | Fit | Priority (Impact×Fit/Effort) |
|--------|:------:|:------:|:---:|:----:|
| Calibrate judge vs human-agreed cases | 5 | 1 | 5 | **25.0** |
| Reference-grounded LLM judging | 5 | 2 | 5 | **12.5** |
| Multi-judge ensemble | 4 | 3 | 4 | **5.3** |
| Position/verbosity debiasing | 3 | 1 | 4 | **12.0** |

Calibration first is the cheapest, highest-value move: it tells you whether the tiebreaker idea is even valid for your data before you build the rest.

---

## 5. Gap Analysis

**What the paper does that we don't:**
- Treats evaluation/judgment as a first-class, *measured* component (we currently have no automated quality gate on triples).
- Provides bias taxonomy + mitigation we can apply directly to a judge.
- Distinguishes reference-based vs reference-free judging — we have rich `source_description` text to ground a reference-based judge.

**What we do that the paper doesn't cover:**
- A concrete domain (Indonesian high-school curriculum) with real expert ratings already collected — i.e. a ready-made gold set to calibrate against.
- A 4-category rubric (correct/partial/wrong/missing) already operationalized in the review app.

**Key architectural differences:**
- The survey is method-agnostic; our pipeline is a fixed extract→graph→complete flow. A judge slots in as a *new* post-review stage, not a change to existing steps.

**Opportunities for synthesis:**
- Use the human-agreement data as the validation set for an LLM judge → publish the judge's κ vs humans → then deploy it as a *flagging/assistive* tiebreaker, not a silent arbiter.

---

## 6. Implementation Roadmap (top 3)

### Calibrate judge vs human-agreed cases
**Files:** new `experiments/scripts/llm_judge_calibration.py`
```python
# 1. load per-expert files in data/expert_feedback/ + resolved triples
# 2. keep triples where >=2 humans agree -> human_consensus[idx]
# 3. for each, run judge (different family than extractor) on (triple, source_description)
# 4. verdict in {correct, partial, wrong, missing}
# 5. report accuracy + cohen_kappa_score(human, judge), confusion matrix per category
```
**Testing:** sanity-check on the 5 `wrong`-consensus triples — judge should also flag them.
**Challenge:** mapping free-form judge output to the 4 labels → use structured Pydantic output.

### Reference-grounded LLM judging (`judge.py`)
```python
class JudgeVerdict(BaseModel):
    rating: Literal["correct","partial","wrong","missing"]
    rationale: str
    confidence: float
# prompt: source_description + triple + 4-category rubric; require rationale citing source
```
**Integration:** reads same triples JSON; writes a `judge` block parallel to expert files.

### Multi-judge ensemble
Wrap `judge.py` over Gemini + Anthropic + OpenAI; majority vote; if judges split → escalate to human queue (don't auto-decide).

---

## 7. Action Items

1. [ ] Build the calibration script and compute the **LLM-judge vs human-consensus κ** per subject (do this FIRST — it validates the whole idea).
2. [ ] Choose a judge model from a **different family than the extractor** (extractor was Gemini → judge with Anthropic/OpenAI) to avoid self-preference.
3. [ ] Implement reference-grounded `JudgeVerdict` structured output using the 4-category rubric.
4. [ ] Apply position/verbosity debiasing in the judge prompt.
5. [ ] Use the judge only as a **third vote / tie-flagger**, with human making the final call on splits — record this protocol in Bab 3.
6. [ ] If κ is high, extend the judge as a cheap second opinion on the **single-reviewer** triples (64 in biology).
7. [ ] Report judge agreement, bias checks, and the human-final-authority protocol in the thesis methodology for defensibility.
8. [ ] Add the bias taxonomy (position/verbosity/self-preference) to the limitations section.

---

## Honest Opinion: LLM-as-a-Judge as a Tiebreaker (project-specific)

**Verdict: Yes, but as a _calibrated, grounded, human-supervised assistant_ — never as the silent final arbiter between two experts.**

The strongest project-specific caveat: **the triples were themselves LLM-generated** (Gemini extraction). Using an LLM to judge LLM output triggers exactly the **self-preference bias** this survey warns about — the judge may rate the extractor's phrasing as correct because it matches its own priors, inflating your quality numbers. Mitigation: judge with a *different model family* than the extractor, and ground every verdict in the source text.

Second caveat — thesis defensibility: letting a machine *decide* between two disagreeing domain experts is hard to defend in an undergrad viva. Far more defensible framings:
- **Tie-flagger, not tie-breaker:** the LLM surfaces the disagreement + a grounded rationale; a human makes the final call.
- **Validated third vote:** prove the judge reproduces human consensus (report κ) before trusting it on splits.
- **Scale where humans are absent:** the cheap win is the 64 single-reviewer biology triples, not overruling experts.

Bottom line: the method is legitimate and well-supported by this survey, but its value here is **calibration-gated and assistive**. Measure the judge against your existing human-agreement data first; if κ is high, use it to flag and pre-screen; keep humans as final authority on genuine expert splits.
