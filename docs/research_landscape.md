# Research Landscape Scan

**Status:** bounded, tooling-limited scan recorded 2026-10-08. This is a positioning aid for the
research-contribution goal, not a systematic review and not a market study.

**Method and limits:** sources were retrieved from the open OpenAlex scholarly index
(`https://api.openalex.org`) on 2026-10-08 using seven topical queries. Titles, years, and DOIs are
reported as the index returned them; **the papers were not read in full**, and citation counts are
index snapshots, not quality judgements. General web search was unavailable during this scan
(`web_search` has no configured API key; DuckDuckGo returned a bot challenge; Bing RSS returned
irrelevant dictionary results), so **commercial product claims could not be verified** and are
deliberately omitted rather than guessed.

A second, deeper pass was run the same day using direct page and PDF fetches plus the arXiv and
Semantic Scholar APIs (general web search remained unavailable). It confirmed the need is recognised
outside vendor marketing — Tariq, Chhetri, Nepal & Paris, *Alert Fatigue in Security Operations
Centres: Research Challenges and Opportunities*, ACM Computing Surveys, 2025
(https://doi.org/10.1145/3723158), and NIST SP 800-61r3 (April 2025), which directs analysts to
*"consider known false positives to determine whether an incident should be declared."* The deeper
pass also surfaced prior art the OpenAlex queries missed, recorded in section 2A.

## 1. Is the need real?

Alert fatigue and triage overload in security operations centres are the explicit subject of multiple
2024–2026 peer-indexed surveys and frameworks, for example:

- *AI-Driven Security Alert Screening and Alert Fatigue Mitigation in Security Operations Centers: A Survey* (2026), arXiv:2605.08316.
- *AI-Augmented SOC: A Survey of LLMs and Agents for Security Automation* (2025), https://doi.org/10.3390/jcp5040095 (35 indexed citations).
- *A Machine Learning and Optimization Framework for Efficient Alert Management in a Cybersecurity Operations Center* (2024), https://doi.org/10.1145/3644393.
- *On the Use of AutoML for Combating Alert Fatigue in Security Operations Centers* (2024), https://doi.org/10.1007/978-3-031-54129-2_36.

That the problem is repeatedly named in the literature is evidence the need is recognised. It is
**not** evidence of market size, willingness to pay, or product demand, none of which this scan
established.

## 2. Who is already working on this?

The space is **not empty**. Grouped by theme (all retrieved via OpenAlex):

**A. Evidence-grounded / LLM-assisted SOC investigation — closest to this project**

- *Argus: Evidence-Grounded LLM-Assisted Investigation for Security Operations Centers* (2026), https://doi.org/10.5281/zenodo.22259142 — the nearest neighbour found; the "evidence-grounded LLM SOC investigation" idea is already published.
- *Insider Threat Detection and Evidence-Grounded Triage Using a Heterogeneous Dual-Branch Network and a Constrained LLM Agent* (2026), https://doi.org/10.3390/app16147054.
- *Auditable and Robust LLM-Based Phishing Detection via Provenance-Guided Evidence Contracts* (2026), https://doi.org/10.32604/cmc.2026.085276.
- *Autonomous Security Alert Triage Using LLM Based Agentic Investigation with Tool Augmented Reasoning* (2026), https://doi.org/10.32628/cseit261213109.
- *Decision-Aware Trust Signal Alignment for SOC Alert Triage* (2026), arXiv:2601.04486.
- *CORTEX: Multi-Agent LLM Architecture for High-Stakes Alert Triage* (2025), arXiv:2510.00311 —
  specialised agents **collaborate over shared real evidence**; the closest prior art to this
  project's core idea, and it also releases a production SOC investigation dataset.
- *PROVSEEK: Provenance plus Multi-Agent LLM Forensics* (2025), arXiv:2508.21323 — LLM agents fusing
  threat-report knowledge with system provenance data; provenance plus multi-agent LLM is already
  combined.
- *Before You Hand Over the Wheel* / SIABENCH (2026), arXiv:2603.06422 — 135 alert-triage scenarios
  and 25 incident workflows; the closest triage-evaluation prior art.
- *Post-Hoc Trajectory-Risk Certification for Modular LLM-Based Security Agents* (2026),
  arXiv:2608.05199 — conformal guarantees across staged security pipelines.
- *A Unified Framework for Human AI Collaboration in SOCs with Trusted Autonomy* (2025),
  arXiv:2505.23397 — five autonomy levels mapped to human-in-the-loop roles; overlaps the
  human-oversight contribution.
- *MESSALA: Multi-perspective Report Evaluation for SOCs* (2026), arXiv:2601.03013 —
  multi-perspective LLM evaluation; overlaps "independent multi-model assessment".

**B. Explainability and trust**

- *SoK: Explainable Machine Learning for Computer Security Applications* (2023), https://doi.org/10.1109/eurosp57164.2023.00022 (60 indexed citations).

**C. LLM risks inside the SOC (injection, hallucination, contamination)**

- *LLM-powered SOC Assistants: Prompt Injection Risks in Threat Triage* (2026), https://doi.org/10.2139/ssrn.7179658.
- *Adversarial Hallucination Engineering: Targeted Misdirection Attacks Against LLM Powered Security Operations Centers* (2025), https://doi.org/10.20944/preprints202512.0913.v1.
- *Context Contamination in LLM Analysis of Network Security Logs: Poison with Passive Prompt Injection* (2026), arXiv:2607.14493.
- *MiniCheck: Efficient Fact-Checking of LLMs on Grounding Documents* (2024), https://doi.org/10.18653/v1/2024.emnlp-main.499.

**D. Evaluation under scarcity and on this dataset family**

- *Evaluating meta-learning strategies for zero-day intrusion detection under data scarcity* (2026), https://doi.org/10.1038/s41598-026-50116-x.
- *Robust Semi-Supervised Temporal Intrusion Detection for Adversarial Cloud Networks* (2026), arXiv:2604.12655.
- *Benchmark-Based Reference Model for Evaluating Botnet Detection Tools Driven by Traffic-Flow Analytics* (2020), https://doi.org/10.3390/s20164501.
- *Efficient Detection of Botnet Traffic by Features Selection and Decision Trees* (2021), https://doi.org/10.1109/access.2021.3108222.
- *Botnet Detection on CTU-13 Using Lightweight Machine Learning Models* (2026), arXiv:2605.23004.

## 3. Where is the gap?

The finding that matters most is negative: **"evidence-grounded LLM-assisted SOC investigation" is
already an occupied and rapidly growing area.** A contribution framed only as "we built an
evidence-grounded LLM triage system" would land in a crowded field with several 2026 neighbours.

Three thinner areas remain, and they align with the corrected detector diagnosis in
[phase3_evaluation_diagnosis.md](phase3_evaluation_diagnosis.md):

1. **Evaluation under label scarcity.** Published detection work reports metrics on labelled subsets.
   The AegisTrace artifacts show the labelled subset was 5.7% of validation rows and 67.8% malicious,
   while 94.3% of rows carried no label. Honest reporting of that unlabelled majority — and of the
   unknown-label alert workload as a first-class result rather than a footnote — is not well served.
2. **Independence between assessors as the experimental variable.** This is the sharpest finding of
   the deeper pass. Existing multi-model SOC work has agents *collaborate* over shared evidence
   (CORTEX) or debate with sight of each other's answers, and multi-perspective evaluation work
   (MESSALA) aggregates views. No security-triage work was found that treats *mutual blindness*
   between frozen assessors as the variable under test, with disagreement itself as the escalation
   signal. Whether independence improves calibration, false-positive rate, or escalation quality
   relative to collaboration appears unmeasured.
3. **Uncertainty routing to a human as the measured outcome.** The literature optimises detector
   scores; the human-oversight-first question — does structured uncertainty help a reviewer escalate
   correctly without eliminating expert review — is comparatively unaddressed.

## 3A. Commercial and regulatory context

All quotes below are from vendor pages fetched 2026-10-08; vendor metrics are unverified.

- **Triage assistants:** Microsoft Security Alert Triage Agent (*"an autonomous agent… that helps
  security teams triage alerts at scale"*), Google Security Operations (*"AI-generated case summaries
  and recommendations on how to respond"*), Dropzone AI (*"cutting investigation time by 85% while
  showing the evidence behind each verdict"*), Prophet Security.
- **Autonomous responders:** Palo Alto Cortex XSIAM (*"the autonomous SOC"*), Torq (*"Every alert
  needs attention. Not every alert needs a human."*; *"autonomously remediates critical threats"*),
  CrowdStrike Charlotte AI.
- **Documented risk:** Microsoft's own deployment guidance mandates audit-first testing for attack
  surface reduction rules and requires approval before expanding past ten devices; CrowdStrike's
  Channel File 291 root-cause analysis names *"false-positive detection volume spikes"* as a
  deployment hazard. Marketing pushes autonomy while the same vendors' operational guidance gates it.
- **Regulatory:** EU AI Act Article 14 places human-oversight obligations on high-risk systems and
  names automation bias as a risk; the deeper pass found no SOC-triage study that measures analyst
  decision quality under those conditions.

Two consequences for positioning: *"human always decides"* differentiates against current vendor
marketing but is not a universal norm, and *"evidence behind each verdict"* is already a marketing
claim (Dropzone), so it cannot carry the contribution on its own.

## 4. Recommended framing

Position the contribution as **method and measurement**, not as another triage system: how to
evaluate evidence-grounded triage honestly when most traffic is unlabelled, how to report unknown-label
workload, and how independently frozen dual-role adjudication behaves under a no-agreement-as-truth
rule. The detection work already recorded is the substrate for that question, not the headline.

## 5. Confidence and limits

- Single open index; papers not read; no systematic query strategy; citation counts are snapshots.
- Commercial products and market sizing were **not** verified and are not claimed.
- Search tooling was unavailable, so relevant work outside OpenAlex may have been missed.
- Re-run with a configured search provider and full-text reading before any external claim.
- **Measurement-validity warning:** arXiv:2511.15755, a widely quotable multi-agent LLM
  incident-response paper, was **withdrawn by its author** after a code audit found the multi-agent
  arm's action list was a source constant rather than model output. Its numbers must not be cited, and
  it is direct evidence that leakage and validity controls are a live weakness in this subfield.
- Closest prior art (CORTEX, PROVSEEK, SIABENCH, 2608.05199, 2601.03013, 2505.23397) was assessed
  from abstracts and pages, **not full texts**; redundancy could still hide there.
- No independent evaluation of the commercial products above was found; their capability claims are
  unverified.
