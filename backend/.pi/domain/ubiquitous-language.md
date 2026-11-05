# Ubiquitous Language

> Canonical glossary for **health-policy-simulator**.
> All code MUST use these terms. Aliases/synonyms listed below are **prohibited** in source identifiers.
> Drift is detected by `.pi/scripts/validate-ubiquitous-language.sh`.

## Glossary

| Term | Definition | Bounded Context | Aliases/Synonyms | Examples |
|------|-----------|----------------|-----------------|---------|
| <!-- Add your terms here --> |  |  |  |  |
| <!-- Format: | TermName | What it means | ModuleName | Alias1, Alias2 | `code example` | --> |

## Adding New Terms

1. Identify the term used in conversation and code
2. Add a row to the Glossary table
3. Define the term's **bounded context** (which module it lives in)
4. List any **aliases/synonyms** that agents might mistakenly use
5. Provide **code examples** showing correct usage
6. Run `.pi/scripts/validate-ubiquitous-language.sh` to detect drift

> **Rule of thumb:** If two agents use different names for the same concept, add an entry.
> The canonical term is the one used in the architecture module documents.

## Term Conflicts (language gaps)

When the same term is used with different meanings by different parts of the
business (e.g. "transaction" = a database transaction for engineers but a
statement line for the business), that is a bounded-context boundary signal —
record the conflict here and resolve it in the exploration review:

| Term A | Term B | Why conflicting | Resolution |
|--------|--------|-----------------|-----------|
| <!-- e.g. Transaction | Booking | engineering vs business meaning | adopt "Booking" in Billing context --> |
| Document | A physical ingested source file before editorial segmentation. | EvidenceCorpus | file, pdf, source file | press_archive_2020_issue_142.pdf |
| Article | One editorial unit segmented out of a Document, carrying headline, date and page. | EvidenceCorpus | news item, story, post | 'Ärztekammer fordert mehr Kassenstellen' (2020-03-14, p. 7) |
| Passage | The smallest citable text span; the unit that is indexed, retrieved and cited. | EvidenceCorpus | chunk, snippet, fragment | Passage #3 of Article 17, offsets 1420-1985 |
| Authority Tier | Ranked credibility class of a source, driving evidence weight and claim admissibility. | EvidenceCorpus | trust level, credibility, source rank | legislation > official-statistics > scientific-study > press-report |
| Extraction Quality | Measured confidence that a Document's text faithfully represents the physical source. | EvidenceCorpus | ocr confidence, parse quality | ocr, 0.83, 1.2% missing glyphs, accepted |
| Provenance | Immutable locator bundle that lets any citation be resolved to a page and offset. | EvidenceCorpus | citation locator, source pointer | doc:D-142/article:A-17/page:7/offsets:1420-1985 |
| Corpus Snapshot | The versioned document set a simulation run searched, frozen at run start. | EvidenceCorpus | dataset version, index version | corpus-2020-v3 pinned to run R-11 |
| Evidence Pack | Frozen, balanced and scored set of supporting, contradicting and contextual evidence for one claim. | EvidenceRetrieval | context bundle, rag result, hits | EvidencePack EP-88 for claim 'specialist vacancies rose 12%' |
| Stance Label | Whether a passage supports, contradicts, contextualises or is tangential to a claim. | EvidenceRetrieval | polarity, sentiment | contradicting |
| Recency Policy | Configured decay that weights newer publications above older ones. | EvidenceRetrieval | decay, freshness boost | exp decay, half-life 18 months, reference 2020-12-31 |
| Evidence Score | Inspectable multi-component weighting including authority, relevance, recency and directness. | EvidenceRetrieval | confidence, relevance score | authority 1.0, bm25 8.4, cosine 0.81, recency 0.62, direct 1.0 |
| Evidence Gap | State where a claim has no evidence above threshold, forcing an unsupported flag rather than an invented citation. | EvidenceRetrieval | no results, missing data | gap on claim about 2035 spending projection |
| Directness | Whether a passage explicitly states the claim versus merely talking about the same topic. | EvidenceRetrieval | specificity, explicitness | direct: 'Die Wartezeiten stiegen um 22 Prozent' |
| Stakeholder | An institution of the Austrian healthcare system represented in the negotiation. Never a natural person. | StakeholderModel | actor, player, party, participant | Dachverband der Sozialversicherungsträger |
| Stakeholder Profile | Mandate, interests, constraints, budget limits and decision priorities of a Stakeholder. | StakeholderModel | persona spec, agent config | social insurance: cost containment weighted 0.4, legal competence limited to statutory benefits |
| Interest | A weighted goal the stakeholder optimises for, scoped to policy topics. | StakeholderModel | objective, preference | reduce waiting times, weight 0.35 |
| Constraint | A hard limit the stakeholder cannot concede in negotiation. | StakeholderModel | red line, limit, restriction | no additional federal spending beyond 5% |
| Budget Limit | Numeric spending envelope within which proposals are acceptable. | StakeholderModel | budget cap, cost ceiling | +5% vs 2020 baseline by 2025 |
| Historical Position | A provenance-backed past institutional stance, weighted lower than current events. | StakeholderModel | past statement, legacy stance | 2020 statement opposing mandatory telemedicine |
| Agent Binding | Immutable link of one Stakeholder Profile to the agent that negotiates on its behalf in a run. | StakeholderModel | persona binding, agent assignment | run R-11 / Stakeholder SV-01 / persona v2 |
| Simulation Run | One end-to-end negotiation over one policy question. | NegotiationSession | session, job, simulation | run R-11: waiting-time reduction question |
| Negotiation Mandate | Moderator framing of the question: objective, constraints, actors, rules, stopping conditions. | NegotiationSession | brief, task, setup | reduce waiting times 20% in 5 years, budget +5% max |
| Position | A stakeholder's current evidenced stance on a conflict topic, with revision lineage. | NegotiationSession | opinion, view, stance | Support telemedicine expansion for selected services |
| Argument | One turn's reasoned contribution with stance, claims and citations. | NegotiationSession | message, utterance, chat line | SV: new posts create recurring cost; cites EP-88 |
| Conflict Topic | A formalised point of institutional disagreement tracked across rounds. | NegotiationSession | issue, disagreement, gap | Number of additional contract positions |
| Coalition | Stakeholders aligned on one conflict topic behind an explicit shared proposal. | NegotiationSession | alliance, bloc | provinces + patient rep on rural mobile units |
| Revision Reason | Structured justification citing the arguments and evidence that caused a position change. | NegotiationSession | explanation, rationale | moved after EP-88 contradicted cost assumption |
| Stopping Condition | The named rule that terminated the run. | NegotiationSession | exit criterion, termination rule | round_cap_reached |
| Consensus Record | Derived per-topic outcome statement of agreement level among stakeholders. | ConsensusAnalysis | agreement summary, result | 4 of 9 support telemedicine expansion, threshold met |
| Majority Position | Stance carried by most weight-bearing stakeholders on a topic. | ConsensusAnalysis | winning view | expansion of contract positions in shortage regions |
| Minority Position | Dissenting stance with holders and reasons, preserved explicitly. | ConsensusAnalysis | dissent, objection | Ministry of Finance opposes recurring cost commitment |
| Compromise Package | Bundle of individually accepted, mutually compatible measures with provenance. | ConsensusAnalysis | deal, package, settlement | telemedicine + contract posts + digital triage + dashboard |
| Rejected Proposal | A measure that did not reach support and is documented as not carried. | ConsensusAnalysis | failed proposal, discarded option | nationwide remuneration cuts |
| Impact Assessment | Scenario effect estimate with explicit assumptions and uncertainty label. | ConsensusAnalysis | forecast, projection | waiting time -22%, budget +4.3%, modelled, medium confidence |
| Uncertainty Label | Stated basis of an estimate: evidenced, modelled or assumed. | ConsensusAnalysis | confidence, certainty | modelled |
| Decision Brief | The complete published negotiation result artefact with eight sections and resolvable citations. | DecisionBrief | report, result page, answer | DecisionBrief for run R-11, v1 |
| Brief Section | One of the eight mandated components of the brief. | DecisionBrief | chapter, block | Conflict Analysis |
| Citation Reference | Resolvable pointer from a brief statement to an evidence passage with provenance. | DecisionBrief | source note, footnote, link | → doc D-142, p.7, offsets 1420-1985 |
| Actor Summary | Institution, goals, constraints and adopted positions shown in the actors section. | DecisionBrief | agent card, participant profile | Social insurance: cost containment 0.4, telemedicine supporter |
| Position Timeline | Stance trajectory per stakeholder across rounds for the change visualisation. | DecisionBrief | evolution chart, stance history | patient rep: oppose → qualify → support (R1-R5) |
| Claim | A verifiable assertion from an argument, typed by what verification it requires. | ClaimValidation | fact, statement, assertion | waiting times rose 22% between 2015 and 2020 |
| Claim Verification | The audited verdict for a claim with its source set and comparison method. | ClaimValidation | fact check, validation | supported by Statistik Austria table, method: direct comparison |
| Unsupported Assertion | A claim with no adequate evidence, surfaced as low-confidence rather than removed. | ClaimValidation | unsourced claim, guess | 'telemedicine will cut costs by half' – no evidence |
| Contradiction Finding | Detected incompatibility between two verified claims or a claim and an authoritative figure. | ClaimValidation | conflict of figures, inconsistency | cost figure 3.2bn vs 4.1bn for the same year |
| Measure Reference | Normalised identity of a figure (measure, unit, period, geography) enabling comparison across agents. | ClaimValidation | metric key, dimension | waiting_time_days / AT / 2020 |
| Authoritative Source | A source tier admissible for verification, as opposed to press reporting. | ClaimValidation | ground truth, official data | SOZDOK legal text, Statistik Austria series |
| Article Section | Typed region of an article (headline, standfirst, body, caption, quotation) used for directness scoring and quotation screening. | EvidenceCorpus | zone, block type, layout part | headline of A-17 |
| Quotation Block | Span of quoted or reported speech of a named person; retained structurally, never promoted as agent evidence. | EvidenceCorpus | quote, citation of person, direct speech | '...' sagte der Obmann (excluded from evidence packs) |
| Canonical Article | The one article that owns citable passages when several syndicated copies exist. | EvidenceCorpus | original article, master copy | APA wire copy syndicated in 4 outlets → one canonical article |
| Language Tag | German variant marker driving tokenisation and embedding choice. | EvidenceCorpus | locale, lang code | de-AT |
| Quarantined Document | A document that failed the extraction quality gate and is excluded from citation but kept for diagnostics. | EvidenceCorpus | rejected file, bad scan | OCR confidence 0.41 on a skewed scan |
| Ingestion Run | One auditable batch execution of corpus ingestion with accepted, quarantined and failed counts. | EvidenceCorpus | import job, crawl, batch | run IR-7: 1,204 attempted, 1,180 accepted, 14 quarantined, 10 failed |
| Index Manifest | Published index version for a corpus snapshot, recording embedding model, indexed passages and searchable-since timestamp. | EvidenceCorpus | index state, vector version | manifest v12, model bge-m3, 480k passages, searchable since 2020-12-01T10:22Z |
| Retracted Passage | An indexed passage withdrawn because its document was retracted or reclassified as unusable. | EvidenceCorpus | removed chunk, deleted hit | passage P-9912 withdrawn after rights clarification |
| Authority Weight | Numeric trust weight derived from the corpus-owned source tier; the only way retrieval may express trust. | EvidenceRetrieval | trust score, credibility, AuthorityTier value | legislation → 1.0, press-report → 0.4 |
| Retrieval Trace | Reproducibility record per pack: index manifest version, models used, rewrite applied, stance counts. | EvidenceRetrieval | provenance of retrieval, audit log | manifest v12, embed bge-m3, rerank bge-reranker-v2 |
| Query Rewrite | Deterministic German-language expansion of a claim before search: compounds, umlauts, institutional synonyms. | EvidenceRetrieval | query expansion, normalisation | 'Kassenstellen' → 'Kassenvertragsstellen, Vertragsarztstellen' |
| Negotiating Power | Derived institutional leverage from mandate scope, budget authority, veto rights and coalition centrality; never assigned by an agent. | StakeholderModel | leverage, influence, weight | Ministry of Finance: high budget authority, no clinical mandate |
| Veto Right | Power to block a class of proposals outright, bounding what consensus is reachable. | StakeholderModel | blocking power, reserved competence | statutory benefit changes require insurer consent |
| Dependency | Directional relation between institutions (funding, approval, staffing, data) with strength and affected proposal classes. | StakeholderModel | link, reliance | hospitals depend on provinces for investment funding |
| Mandate Scope | Admissible range of agreement for an institution; bounds every concession its agent may make. | StakeholderModel | competence, remit | chamber may negotiate fees, not benefit baskets |
| Turn Assignment | A stakeholder's allocated floor in a round, with order, topic and used/passed/abstained outcome. | NegotiationSession | slot, speaking order | R3 turn 4: hospitals on financing, passed |
| Negotiation Phase | Monotonic process stage from position formation to closure that bounds legal commands. | NegotiationSession | stage, step | compromise |
| Proposal | Structured substance of a position: measure, quantified effect, target population, cost, affected institutions. | NegotiationSession | measure, plan, option | +200 contract posts in shortage regions; EUR 84m/yr; 5-year horizon |
| Proposal Component | One admissible part of a proposal with its own support record, assemblable into packages. | NegotiationSession | building block, item | digital specialist triage |
| Coalition Offer | Recorded invitation to join a shared proposal, with conditions and accept/decline outcome. | NegotiationSession | invitation, ask | provinces invited patient reps to joint rural proposal; declined |
| Scenario | A counterfactual assessed against a baseline: the measures of one package, a horizon, an affected population and stated assumptions. | ConsensusAnalysis | case, what-if, variant | package P-2 vs 2020 baseline, 5-year horizon, Austria |
| Feasibility Rating | Political, legal and administrative feasibility of a package with the basis for each rating. | ConsensusAnalysis | implementability, practicality | legal: high (within insurer competence); political: medium (provinces split) |
| Consensus Threshold | Support level the mandate requires for consensus, adjusted where veto rights apply. | ConsensusAnalysis | quorum, majority rule | two thirds of weight-bearing stakeholders |
| Veto-Blocked Outcome | A proposal that met the support threshold but is not consensus due to a blocking competence. | ConsensusAnalysis | blocked, vetoed | 7/9 support, blocked by insurer veto on benefit changes |
| Cited Statement | One statement of the brief with its citations, source claim ids and evidence status; the granularity at which transparency is enforced. | DecisionBrief | sentence, bullet, assertion | 'Waiting times fell 22% in the model' → EP-88, EP-91 |
| Rejected Proposal Record | A measure that failed to gather support, with blocking stakeholders and reasons. | DecisionBrief | failed motion, discarded option, not implemented | nationwide remuneration cuts — blocked by chamber + contract physicians |
| Simulation Disclaimer | Statement that the result is probabilistic agent reasoning over a pinned corpus, not a deterministic forecast and free of real-person positions. | DecisionBrief | caveat, note | 'Runs are non-deterministic; model and prompt versions are recorded per run.' |
| Reference Figure | Canonical authoritative value for one measure, with as-of date and source tier; the comparison baseline. | ClaimValidation | ground truth value, official figure, baseline | public_health_spend / AT / 2019 = EUR 42.1bn (Statistik Austria) |
| Tolerance Band | Admissible deviation below which two figures for one measure are treated as equal. | ClaimValidation | epsilon, rounding tolerance, spread | ±2% for survey-based measures |
| Expert Review | Escalation of an unsettled claim to a review step that returns a verdict with its basis. | ClaimValidation | manual check, second opinion, expert agent | claimed 12% rise; two surveys disagree; escalated |
| Round Learning | Persisted digest of a round's outcomes — which arguments held, which proposals moved, who coalesced — that agents must consume in the next round. | NegotiationSession | reflection, memory, feedback state, lessons | R2 learning: insurer's cost estimate was contradicted by EP-88 |
| Learning Application | Explicit reference from a later argument to the RoundLearning insight that caused it. | NegotiationSession | applied lesson, adaptation | medical chamber drops post-count demand citing R2 learning |
| Mandate Source | Citable legal or institutional instrument that grounds a veto right, competence or budget limit. | StakeholderModel | legal basis, statute reference, authority ground | ASVG provision on benefit changes requiring insurer consent |
| Attribution Strength | Whether a source explicitly attributes a stance to the institution, reports it, or merely mentions the institution. | StakeholderModel | confidence of attribution, how firmly stated | explicit attributed statement vs passing mention |
| Power Source Kind | Where an institution's authority derives from: legislation, statutory instrument, budget decision, institutional statute or agreement. | StakeholderModel | basis of power, authority type | budget decision |
| Estimate Basis | Provenance class of a figure: measured, derived, modelled, assumed or not estimated. | ConsensusAnalysis | confidence, source of number, how computed | derived from two ReferenceFigures |
| Derivation Input | Enumerated input behind a derived figure, cited so the calculation can be re-run or refuted. | ConsensusAnalysis | input, assumption source | RF-14 public_health_spend/AT/2019 + RF-22 population 2020 |
| Assumed Estimate | A figure without enumerated inputs, publishable only with an explicit assumed label. | ConsensusAnalysis | guess, illustrative value | budget impact assumed at +4% pending costing |
| Absence Finding | Auditable record that a stance produced no qualifying evidence, naming the queries and snapshot searched. | EvidenceRetrieval | no results, negative result | no contradicting evidence for a telemedicine cost claim; 6 queries over snapshot v12 |
| Recency Exemption | Designation of non-perishable source types (legislation, foundational studies, reference figures) that keep full weight regardless of age. | EvidenceRetrieval | no decay, timeless | statutory provision from 1955 exempt |
| Speaker Kind | Attribution class of a statement: institution, named person, anonymous or unattributed; decides citability. | EvidenceCorpus | attributed to, source type | institution: Dachverband der Sozialversicherungsträger |
| Authority Rule | Claim-type-specific source ordering used instead of one global authority scale. | EvidenceCorpus | ranking, precedence | quantitative: statistics > study > institutional statement > press |
| Institutional Statement | Retained, citable statement attributed to an institution rather than a person. | EvidenceCorpus | press release, official position | chamber statement on contract posts, citable with attribution |
| Verification Path | Type-specific route a claim takes: reference comparison, provision check, study appraisal, or no verification. | ClaimValidation | check type, how verified | causal → study appraisal |
| Causal Support | Appraisal of study evidence behind a causal claim, recorded as supported, contested or unaddressed. | ClaimValidation | evidence for causation, study backing | observational study, contested effect direction |
| Unverifiable Claim | A claim for which no applicable verification path exists, recorded as ambiguous rather than removed. | ClaimValidation | not checkable, out of scope | 'patients feel more secure' — qualitative, unverifiable |

