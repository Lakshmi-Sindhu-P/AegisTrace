# AegisTrace — Bounded Landscape Scan

**Retrieved:** 2026-10-08. **Method caveat:** the `web_search` tool was unavailable (no API key) in this session. Findings come from direct page/PDF fetches plus the arXiv and Semantic Scholar APIs, with Brave HTML search as a discovery fallback that rate-limited intermittently. Coverage is therefore **not exhaustive** — absence of prior art below means "not found under these constraints," not "does not exist." Vendor-published numbers are labelled as such and were not independently audited.

---

## 1. IS THE NEED REAL?

**Yes — the problem is acknowledged in peer-reviewed literature and by a standards body, not only by vendors.** Three concrete facts:

1. **Peer-reviewed consensus.** Tariq, Chhetri, Nepal & Paris, *"Alert Fatigue in Security Operations Centres: Research Challenges and Opportunities,"* **ACM Computing Surveys, 2025** ([10.1145/3723158](https://dl.acm.org/doi/10.1145/3723158)). Abstract: *"Recent studies, by both industry and academia, have highlighted the problem of alert fatigue and burnout in SOC."* It reviews both literature *and* industry solutions, and identifies four major causes. This is the strongest non-commercial evidence.
2. **Vendor-sponsored survey (marketing-adjacent — treat as indicative).** Vectra AI, *2023 State of Threat Detection*, n=2,000 SecOps professionals, as reported by [Security Magazine](https://www.securitymagazine.com/articles/99674-90-of-soc-analysts-believe-current-threat-detection-tools-are-effective): analysts *"are unable to deal with 67% of the daily alerts received, with 83% reporting that alerts are false positives and not worth their time"*; *"97% of SOC analysts worry about missing a relevant security event because it's buried under a flood of alerts."* Vectra sells detection software; I could not find a published methodology for its *"$3.3 billion annually"* triage-cost figure. Note the survey is internally inconsistent — 90% still rated their tools "effective."
3. **Standards body treats false positives as a decision input.** **NIST SP 800-61r3** (April 2025, [nvlpubs.nist.gov](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-61r3.pdf)): *"Apply incident criteria to known and assumed characteristics of analyzed activity, and consider known false positives to determine whether an incident should be declared."* It also directs: *"Regularly conduct manual reviews of log events for technologies that cannot be sufficiently monitored through automation."*

**Evidence vs. marketing:** the ACM survey and NIST establish the problem without a product to sell. The Vectra numbers are directionally consistent but self-interested. Notably, **NIST SP 800-61r3 never uses the phrase "alert fatigue"** (I grepped the full text: zero hits) — the standards framing is about false-positive handling and incident declaration, not analyst burden.

---

## 2. COMMERCIAL LANDSCAPE (AI copilot / triage / investigation)

All quotes below are from the vendor's own page, fetched 2026-10-08.

| # | Vendor / product | What it claims (verbatim) | Triage vs. autonomous responder |
|---|---|---|---|
| 1 | **Microsoft** — Security Copilot Security Alert Triage Agent ([learn.microsoft.com](https://learn.microsoft.com/en-us/defender-xdr/security-alert-triage-agent)) | *"an autonomous agent embedded in Microsoft Defender that helps security teams triage alerts at scale"*; *"deliver clear verdicts"* | **Triage assistant** ("autonomous" = runs unprompted; output is a verdict, not an action). Preview. |
| 2 | **Microsoft** — Phishing Triage Agent ([learn.microsoft.com](https://learn.microsoft.com/en-us/defender-xdr/phishing-triage-agent)) | *"helps security teams scale the triage and classification of user-reported phishing emails"* | **Triage assistant.** Remediation automation lives in Defender AIR, configured separately. |
| 3 | **Google** — Google Security Operations (SecOps) ([cloud.google.com](https://cloud.google.com/security-operations)) | *"Gemini investigative chat assistant… AI-generated case summaries and recommendations on how to respond"* | **Triage assistant + separate SOAR.** *"Build playbooks that automate common response actions."* Hybrid; automation is human-authored. |
| 4 | **Palo Alto Networks** — Cortex XSIAM ([paloaltonetworks.com](https://www.paloaltonetworks.com/cortex/cortex-xsiam)) | *"the autonomous SOC"*; *"automated triage and guided actions"*; *"it blocks the world's most advanced threats"* | **Hybrid → autonomous responder** (markets blocking). |
| 5 | **CrowdStrike** — Charlotte AI / Agentic SOAR ([crowdstrike.com](https://www.crowdstrike.com/en-us/platform/charlotte-ai/)) | *"Agentic SOC"*; *"automate repetitive tasks with CrowdStrike's agentic security workforce"*; *"Respond at machine speed"* | **Hybrid, leaning autonomous.** |
| 6 | **Dropzone AI** — AI SOC Analyst ([dropzone.ai](https://www.dropzone.ai/)) | *"Investigates alerts end to end across your full tool stack, 24/7, cutting investigation time by 85% while showing the evidence behind each verdict"* | **Triage/investigation assistant.** The 85% figure is an unverified vendor metric. Note: "evidence behind each verdict" is already a marketing claim. |
| 7 | **Prophet Security** — AI SOC Platform ([prophetsecurity.ai](https://www.prophetsecurity.ai/)) | *"A constellation of AI agents that investigates every alert with senior-analyst depth"* | **Triage/investigation assistant.** |
| 8 | **Torq** — AI SOC Platform ([torq.io](https://www.torq.io/)) | *"Every alert needs attention. Not every alert needs a human."*; *"Socrates… autonomously remediates critical threats"* | **Autonomous responder.** Explicitly sells *"agentic response, either completely autonomously or with human-on-the-loop oversight."* |

**UNVERIFIED:** **SentinelOne Purple AI** — the product is widely referenced, but every product URL I probed on sentinelone.com returned 404 in this session; no primary page verified. **Radiant Security** — `radiantsecurity.ai` did not resolve; correct domain unverified. Splunk's AI Assistant page likewise could not be fetched.

---

## 3. AUTOMATED RESPONSE / BLOCKING

**Who acts automatically.** EDR/XDR: Microsoft Defender for Endpoint **AIR** — *"remediation actions can occur automatically or only upon approval by your security operations team"* ([learn.microsoft.com](https://learn.microsoft.com/en-us/defender-endpoint/automated-investigations)). SOAR: Google SecOps playbooks, Torq (autonomous remediation), Palo Alto Cortex AgentiX. IPS/inline blocking is the classic case but I did not verify a specific current vendor doc.

**Documented risks of false positives in automated response:**

1. **Vendors' own root-cause analysis admits FP spikes from automated delivery.** CrowdStrike *Channel File 291* RCA (2024-08-06, [PDF](https://www.crowdstrike.com/wp-content/uploads/2024/08/Channel-File-291-Incident-Root-Cause-Analysis-08.06.2024.pdf)): *"Staged deployment mitigates impact if a new Template Instance causes failures such as system crashes, **false-positive detection volume spikes** or performance issues."* Its own remediation was to *"Provide customer control over the deployment of Rapid Response Content updates."*
2. **Blast radius is fleet-scale.** Microsoft ([blogs.microsoft.com, 2024-07-20](https://blogs.microsoft.com/blog/2024/07/20/helping-our-customers-through-the-crowdstrike-outage/)): *"We currently estimate that CrowdStrike's update affected 8.5 million Windows devices."* (This was a faulty content update, not an FP-triggered response — the distinction matters.)
3. **Vendors mandate audit-first precisely because blocking breaks production.** Microsoft ASR docs ([learn.microsoft.com](https://learn.microsoft.com/en-us/defender-endpoint/attack-surface-reduction-rules-deployment-test)): *"Testing attack surface reduction (ASR) rules is a critical step in your deployment. You need to determine if any ASR rules will block your line-of-business apps."* Microsoft also gates blast radius by approval: *"If 10 or more devices are found during this expansion process… then that expansion action requires an approval."*
4. **The canonical failure mode: automated remediation + false positive = outage.** Wikipedia's *Antivirus software* article (§"Problems caused by false positives", [en.wikipedia.org](https://en.wikipedia.org/wiki/Antivirus_software)) states the mechanism: *"if an antivirus program is configured to immediately delete or quarantine infected files, as is common on Microsoft Windows antivirus applications, a false positive in an essential file can render the Windows operating system or some applications unusable."* Documented cases it aggregates (press-reported, tertiary source — flagged as such): **April 2010** McAfee VirusScan flagged `svchost.exe` on Windows XP SP3, *"causing a reboot loop and loss of all network access"*; **May 2007** a faulty Symantec signature *"mistakenly removed essential operating system files, leaving thousands of PCs unable to boot"*; **October 2011** Microsoft Security Essentials removed Google Chrome.
5. **Academic framing of the risk.** Ligo et al., *"Autonomous Cyber Defense Introduces Risk: Can We Manage the Risk?"* (2022, [arXiv:2201.11148](https://arxiv.org/abs/2201.11148)): *"autonomous cyber defenses introduce risks of unintended harm. Actions arising from autonomous defense agents may have harmful consequences of functional, safety, security, ethical, or moral nature."*

---

## 4. RESEARCH LANDSCAPE

**(A) LLM grounding / hallucination evaluation in security — WELL-STUDIED.**
- Ullah et al. 2023, **SecLLMHolmes** ([arXiv:2312.12575](https://arxiv.org/abs/2312.12575)): *"LLMs provide non-deterministic responses, incorrect and unfaithful reasoning, and perform poorly in real-world scenarios"*; finds *"significant non-robustness in even the most advanced models like `PaLM2' and `GPT-4'."*
- Zhang et al. 2024, **Cybench** ([arXiv:2408.08926](https://arxiv.org/abs/2408.08926)).
- Jajodia et al. 2026, **SIABENCH** / *"Before You Hand Over the Wheel"* ([arXiv:2603.06422](https://arxiv.org/abs/2603.06422)) — 135 alert-triage scenarios + 25 incident workflows; the closest *triage-evaluation* prior art.

**(B) LLM alert triage / SOC automation — CROWDED AND MOVING FAST.**
- Wei et al. 2025, **CORTEX** ([arXiv:2510.00311](https://arxiv.org/abs/2510.00311)): *"a multi-agent LLM architecture for high-stakes alert triage in which specialized agents collaborate over real evidence."* **This is the closest prior art to AegisTrace's core idea.** Agents *collaborate* over shared evidence; it also releases a production SOC investigation dataset.
- Habibzadeh et al. 2025, *LLMs for SOCs: A Comprehensive Survey* ([arXiv:2509.10858](https://arxiv.org/abs/2509.10858)).
- *"It is Not Yet Another Tool: … Agentic AI Companion in a Security Operations Center"* ([arXiv:2609.06250](https://arxiv.org/abs/2609.06250)); *"Beyond the Hype: … Practical Limitations in SOCs"* ([arXiv:2608.17154](https://arxiv.org/abs/2608.17154)).
- *"Can Risk-Based Alerting Mitigate Cybersecurity Alert Fatigue?"* ([arXiv:2609.02465](https://arxiv.org/abs/2609.02465)).

**(C) Uncertainty-aware / abstention-capable triage — MATURE IN GENERAL ML, THIN IN SECURITY.**
- Wen et al. 2024, *Know Your Limits: A Survey of Abstention in LLMs* ([arXiv:2407.18418](https://arxiv.org/abs/2407.18418)).
- Geifman & El-Yaniv 2017, *Selective Classification for DNNs* ([arXiv:1705.08500](https://arxiv.org/abs/1705.08500)) — risk-targeted reject option.
- Chowdhury & (2nd author) 2026, *Decision-Aware Trust Signal Alignment for SOC Alert Triage* ([arXiv:2601.04486](https://arxiv.org/abs/2601.04486)) — calibrated confidence + uncertainty cues + cost-sensitive thresholds. **Directly overlaps the "uncertainty-aware triage" claim.**
- Li 2026, *Post-Hoc Trajectory-Risk Certification for Modular LLM-Based Security Agents* ([arXiv:2608.05199](https://arxiv.org/abs/2608.05199)) — conformal guarantees across *staged* security pipelines. Highly relevant and recent.

**(D) Provenance-first evidence chains — MATURE PRE-LLM, EMERGING POST-LLM.**
- King & Chen 2003, *Backtracking Intrusions* (SOSP); Bates et al. 2015, *Trustworthy Whole-System Provenance* ([USENIX Security](https://www.usenix.org/conference/usenixsecurity15/technical-sessions/presentation/bates)); Han et al. 2020, **UNICORN** ([arXiv:2001.01525](https://arxiv.org/abs/2001.01525)); *Kairos* ([arXiv:2308.05034](https://arxiv.org/abs/2308.05034)).
- Mukherjee et al. 2025, **PROVSEEK** ([arXiv:2508.21323](https://arxiv.org/abs/2508.21323)) — LLM agents fusing *"knowledge from threat reports with evidence from system provenance data."* Provenance + multi-agent LLM already combined.
- Wang et al. 2026, *From Agent Traces to Trust: Evidence Tracing and Execution Provenance in LLM Agents* ([arXiv:2606.04990](https://arxiv.org/abs/2606.04990)) — defines *"execution provenance as the typed graph of an agent execution and evidence tracing as its projection onto evidence-support relations."* This is the generalized form of "evidence bundles with claim support."

**(E) Independent multi-LLM adjudication / review — GENERAL WORK MATURE, SECURITY-SPECIFIC NASCENT.**
- Du et al. 2023, *Multiagent Debate* ([arXiv:2305.14325](https://arxiv.org/abs/2305.14325)); Zheng et al. 2023, *LLM-as-a-Judge / MT-Bench* ([arXiv:2306.05685](https://arxiv.org/abs/2306.05685)); Verga et al. 2024, *Replacing Judges with Juries (PoLL)* ([arXiv:2404.18796](https://arxiv.org/abs/2404.18796)).
- Mohsin et al. 2025, *A Unified Framework for Human AI Collaboration in SOCs with Trusted Autonomy* ([arXiv:2505.23397](https://arxiv.org/abs/2505.23397)) — five autonomy levels mapped to HITL roles and trust thresholds. **Overlaps the human-oversight contribution.**
- Okada et al. 2026, *MESSALA / Multi-perspective Report Evaluation for SOCs* ([arXiv:2601.03013](https://arxiv.org/abs/2601.03013)) — multi-perspective LLM evaluation of SOC reports. Overlaps "independent multi-model assessment."
- Boboila et al. 2026, **BlueSTAR** ([arXiv:2609.11852](https://arxiv.org/abs/2609.11852)) — tiered agentic architecture; *"unconstrained LLM actions can introduce significant operational risk."*
- **Cautionary data point:** Drammeh 2025, *Multi-Agent LLM Orchestration… for Incident Response* ([arXiv:2511.15755](https://arxiv.org/abs/2511.15755)) was **withdrawn by the author**: *"A code audit found the multi-agent arm's action list is a source constant, not model output, and the scorer reads only that field."* Do not cite its numbers. This is direct evidence that measurement validity is a live weakness in this subfield.

---

## 5. THE GAP

**Honest headline: the space is crowded, not open.** Every individual component of AegisTrace has published or commercial precedent — multi-agent LLM triage (CORTEX), provenance-grounded LLM forensics (PROVSEEK), uncertainty-aware SOC triage (2601.04486), conformal risk certification for staged security agents (2608.05199), autonomy/HITL frameworks for SOCs (2505.23397), multi-perspective LLM assessment (2601.03013), and "evidence behind each verdict" as a *marketing* claim (Dropzone). A paper that presents "LLM + provenance + multiple models + human oversight" as a novel architecture will most likely be read as incremental.

**The least-served area I can actually defend is the *ablation*, not the architecture.** Under these search constraints I found **no security-triage work that treats *independence between assessors* as the experimental variable.** The existing multi-model SOC work has agents *collaborate* over shared evidence (CORTEX) or debate with sight of each other's answers (2305.14325). AegisTrace's distinguishing design is the opposite: two roles **frozen and mutually blind**, where *disagreement itself is the escalation signal*. Whether independence improves calibration, false-positive rate, or escalation quality versus collaboration is, as far as I can find, unmeasured.

Three further defensible, narrower openings:

1. **Claim-level observed-vs-inferred separation, measured.** Provenance-based detection is mature and evidence-tracing taxonomies now exist (2606.04990), but I found no security study that formally partitions each claim into "observed fact" vs "model inference" and then measures whether that partition changes analyst error rates. Dropzone markets evidence-backed verdicts; nobody appears to have *tested* the effect.
2. **Analyst-decision outcomes rather than recommendation quality.** Nearly all prior work measures FP reduction or recommendation quality. Almost none measures whether the *human's decision* improves — over-reliance, automation bias, calibration drift. Automation bias is named as a risk in **EU AI Act Article 14** ([artificialintelligenceact.eu](https://artificialintelligenceact.eu/article/14/)) yet appears unmeasured in SOC triage.
3. **Evaluation rigor as the contribution.** The withdrawn 2511.15755 shows the subfield has a leakage/validity problem. A reproducible, leakage-controlled, pre-registered benchmark with genuine analyst ground truth would be valuable *even without architectural novelty*.

**Blunt recommendation.** If the owner can run a controlled human study, lead with gap 1 or 2 — independence ablation plus analyst-decision outcomes — and position the architecture as the instrument, not the finding. If a human study is not feasible, gap 3 (rigorous benchmark) is the more honest contribution. Also note the positioning risk: Torq already sells *"human-on-the-loop"* autonomy, so "human always decides" is a differentiator against *current marketing*, not a universally shared norm — and CORTEX claims to have released a production SOC dataset, which is both a competitive threat and a potential dependency worth checking before committing.

---

## 6. CONFIDENCE AND LIMITS

**Could not verify.** (a) **SentinelOne Purple AI** — no live primary page reachable (every probed product URL on sentinelone.com returned 404). (b) **Splunk** AI Assistant — page fetch failed. (c) **Radiant Security** — domain did not resolve. (d) A specific **IPS/inline-blocking** vendor doc — not verified; section 3's EDR/SOAR/AV claims are sourced, the IPS claim is generic. (e) Section 3's pre-2012 outage cases rest on a **tertiary** source (Wikipedia) that aggregates press reports; I did not retrieve the original contemporaneous advisories, so treat those specific dates as second-hand. (f) The widely-circulated title *"Do You Know What You Don't Know? … Cybersecurity Question Answering"* **could not be verified**; arXiv 2312.12575 is actually SecLLMHolmes under a different title — do not propagate that title. (g) Google's Gemini-in-SecOps *documentation* pages 404 (docs migrated to docs.cloud.google.com); the product-page claim is verified instead.

**Unverified vendor statistics (do not reuse as fact).** Dropzone "85% investigation-time reduction"; Vectra "$3.3B annually" (no published methodology found); Palo Alto "98% MTTR reduction / 300% ROI / 100% MITRE coverage"; CrowdStrike "2.5x more detection leads."

**Where sources conflict.** Vendor marketing pushes autonomy while the same vendors' deployment docs mandate audit-first and approval gating (Microsoft ASR/AIR) — the marketing and the operational guidance are in tension. Vectra's survey simultaneously reports 90% tool satisfaction and 97% fear of missing events. And 2511.15755 was withdrawn *after* publication, so its widely-quoted "100% vs 1.7% actionable" figures are unsafe.

**Preprint caveat.** Most 2026 items in section 4 are **arXiv preprints, not peer-reviewed**; the 26xx identifiers are recent and titles/venues may change. Section 1's ACM Computing Surveys paper is the only peer-reviewed source among my three "need is real" facts.

**A deeper study would need to:** (i) read **full texts** of CORTEX, PROVSEEK, SIABENCH, 2608.05199, 2601.03013 and 2505.23397 — abstracts cannot rule out overlap, and these are precisely where redundancy would hide; (ii) run a **systematic search** of USENIX Security / NDSS / CCS / S&P / ACSAC 2024–2026 plus DFRWS and IFIP DF for provenance-plus-triage work; (iii) confirm whether CORTEX's production SOC dataset is actually obtainable (it is a hard dependency for any empirical claim); (iv) treat all commercial capability claims as unverified until tested hands-on — no independent evaluation of these products was found; (v) check regulatory positioning if EU deployment is contemplated (AI Act Annex III high-risk classification for law-enforcement/forensic uses, and Art. 14 oversight obligations).
