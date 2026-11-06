import type { Localized } from "@/lib/i18n";

export interface DeferredEntry {
  readonly id: string;
  readonly title: Localized;
  readonly truth: Localized;
  readonly workaround: Localized;
  readonly removal: Localized;
}

export const DEFERRED_ENTRIES: readonly DeferredEntry[] = [
  {
    id: "D-FE-001",
    title: { de: "Kein Endpunkt zum Auflisten aller Verhandlungen", en: "No endpoint listing all runs" },
    truth: {
      de: "GET /api/v1/runs existiert nicht. Die einzige Leseoperation ist GET /api/v1/runs/{run_id}.",
      en: "GET /api/v1/runs does not exist. The only read operation is GET /api/v1/runs/{run_id}.",
    },
    workaround: {
      de: "Das Dashboard führt einen lokalen Index (hps.runs.v1) und bietet „Verhandlung per Kennung öffnen“.",
      en: "The dashboard keeps a local index (hps.runs.v1) and offers “open a run by identifier”.",
    },
    removal: {
      de: "Ein paginierter GET /api/v1/runs mit Frage, Phase, Runde und Zeitstempel.",
      en: "A paginated GET /api/v1/runs with question, phase, round and timestamp.",
    },
  },
  {
    id: "D-FE-002",
    title: { de: "Kein Endpunkt zum Auflisten von Evidenzpaketen", en: "No endpoint listing evidence packs" },
    truth: {
      de: "Positionen brauchen evidence_ids, aber GET /api/v1/evidence/packs existiert nicht als Liste.",
      en: "Positions need evidence_ids, but GET /api/v1/evidence/packs does not exist as a list.",
    },
    workaround: {
      de: "Die Einstellungen importieren das demo-seed.json; die fünf Paketkennungen erscheinen im Paketwähler.",
      en: "Settings imports demo-seed.json; the five pack identifiers appear in the pack picker.",
    },
    removal: {
      de: "GET /api/v1/evidence/packs?snapshot_id=… oder ein Paket pro Thema im Run-Kontext.",
      en: "GET /api/v1/evidence/packs?snapshot_id=…, or one pack per topic in the run context.",
    },
  },
  {
    id: "D-FE-004",
    title: { de: "Ereignis-Endpunkt ohne cursor und limit", en: "Events endpoint has no cursor or limit" },
    truth: {
      de: "Laut OpenAPI akzeptiert GET /runs/{id}/events nur until_round; die im Prompt genannten Query-Parameter cursor und limit fehlen.",
      en: "Per OpenAPI, GET /runs/{id}/events accepts only until_round; the cursor and limit parameters named in the prompt are absent.",
    },
    workaround: {
      de: "Die Konsole lädt das vollständige Ereignisprotokoll und sortiert clientseitig nach sequence.",
      en: "The console fetches the full event log and sorts client-side by sequence.",
    },
    removal: {
      de: "Keyset-Paginierung nach sequence (cursor, limit) im Endpunkt.",
      en: "Keyset pagination by sequence (cursor, limit) in the endpoint.",
    },
  },
  {
    id: "D-FE-005",
    title: { de: "Brief-Abschnitte tragen statements statt title/body", en: "Brief sections carry statements, not title/body" },
    truth: {
      de: "BriefSectionBody ist {kind, ordinal, statements[]}; die im Prompt gezeigte Form {title, body} existiert nicht.",
      en: "BriefSectionBody is {kind, ordinal, statements[]}; the {title, body} shape shown in the prompt does not exist.",
    },
    workaround: {
      de: "Der Renderer zeigt jeden CitedStatement mit Status und Belegnummern; die Abschnittsüberschrift stammt aus kind.",
      en: "The renderer shows every CitedStatement with status and citation numbers; the section heading comes from kind.",
    },
    removal: {
      de: "Entweder die Dokumentation korrigieren oder title/body additiv ergänzen.",
      en: "Either correct the documentation or add title/body additively.",
    },
  },
  {
    id: "D-FE-006",
    title: { de: "Kandidaten ohne Passage-Text und ohne Quellenstufe", en: "Candidates without passage text or authority tier" },
    truth: {
      de: "CandidateBody enthält passage_id, stance, score und provenance, aber keinen Text und keine tier.",
      en: "CandidateBody contains passage_id, stance, score and provenance, but no text and no tier.",
    },
    workaround: {
      de: "Die Evidenzseite lädt GET /passages/{id} je Kandidat; die Streudiagramm-Achse zeigt den numerischen Autoritätswert.",
      en: "The evidence page fetches GET /passages/{id} per candidate; the scatter axis shows the numeric authority score.",
    },
    removal: {
      de: "text und tier in CandidateBody aufnehmen oder einen Batch-Passage-Endpunkt anbieten.",
      en: "Include text and tier in CandidateBody, or provide a batch passage endpoint.",
    },
  },
  {
    id: "D-FE-007",
    title: { de: "Nutzung ohne Kreuztabelle Institution × Runde", en: "Usage without a stakeholder × round cross-tab" },
    truth: {
      de: "GET /runs/{id}/usage liefert Summen je Institution und je Runde, aber keine Kombination.",
      en: "GET /runs/{id}/usage returns totals per stakeholder and per round, but not the combination.",
    },
    workaround: {
      de: "Zwei Small-Multiple-Raster (Institutionen, Runden) mit gemeinsamem Maßstab sowie ein Budgetgauge.",
      en: "Two small-multiple grids (stakeholders, rounds) with a shared scale, plus a budget gauge.",
    },
    removal: {
      de: "by_stakeholder_round[{stakeholder, round, …}] im Usage-Response.",
      en: "by_stakeholder_round[{stakeholder, round, …}] in the usage response.",
    },
  },
  {
    id: "D-FE-008",
    title: { de: "Institutionen nur als Zusammenfassung", en: "Institutions only as summaries" },
    truth: {
      de: "GET /stakeholders liefert Identität, Zählwerte und Profilversion. Es gibt kein GET /stakeholders/{id} für Mandat, Budget oder Vetoklassen.",
      en: "GET /stakeholders returns identity, counts and profile version. There is no GET /stakeholders/{id} for mandate, budget or veto classes.",
    },
    workaround: {
      de: "Die Institutionsseite zeigt die Zusammenfassung, Historie, Machtquellen und einen sichtbaren Hinweis auf die Lücke.",
      en: "The institutions page shows the summary, history, power sources and a visible note about the gap.",
    },
    removal: {
      de: "Ein Leseendpunkt für das vollständige Stakeholder-Profil oder Einbettung in die Zusammenfassung.",
      en: "A read endpoint for the full stakeholder profile, or embedding it in the summary.",
    },
  },
  {
    id: "D-FE-009",
    title: { de: "Keine Koalitionsliste", en: "No coalition list" },
    truth: {
      de: "Koalitionen können nur angelegt werden; ein GET /runs/{id}/coalitions existiert nicht.",
      en: "Coalitions can be created, but GET /runs/{id}/coalitions does not exist.",
    },
    workaround: {
      de: "Koalitionen und ihre Vorschläge werden aus CoalitionFormed-Ereignissen gelesen.",
      en: "Coalitions and their proposals are read from CoalitionFormed events.",
    },
    removal: {
      de: "Ein Leseendpunkt für Koalitionen mit Angeboten und Status.",
      en: "A read endpoint for coalitions with offers and status.",
    },
  },
  {
    id: "D-FE-010",
    title: { de: "Keine Positions- und Argumentlisten; Ereignisse ohne Text", en: "No position or argument lists; events without text" },
    truth: {
      de: "Positionen und Argumente haben keine GET-Endpunkte. ArgumentSubmitted und InitialPositionStated tragen keine Texte, nur Kennungen.",
      en: "Positions and arguments have no GET endpoints. ArgumentSubmitted and InitialPositionStated carry no text, only identifiers.",
    },
    workaround: {
      de: "Die Positionsseite leitet Haltungen und Revisionen aus dem Ereignisprotokoll ab und nennt die fehlenden Texte ausdrücklich.",
      en: "The positions page derives stances and revisions from the event log and explicitly names the missing text.",
    },
    removal: {
      de: "GET /runs/{id}/positions und /arguments mit Texten oder Textfelder in den Ereignissen.",
      en: "GET /runs/{id}/positions and /arguments with text, or text fields in the events.",
    },
  },
  {
    id: "D-FE-011",
    title: { de: "Keine Frage in RunResponse", en: "No question in RunResponse" },
    truth: {
      de: "GET /runs/{id} enthält Phase, Runde und Bindungen, aber nicht die Policy-Frage.",
      en: "GET /runs/{id} contains phase, round and bindings, but not the policy question.",
    },
    workaround: {
      de: "Die Frage kommt aus dem lokalen Run-Index; bei „per Kennung öffnen“ wird die Lücke benannt.",
      en: "The question comes from the local run index; with “open by identifier” the gap is named.",
    },
    removal: {
      de: "question dem RunResponse hinzufügen.",
      en: "Add question to RunResponse.",
    },
  },
  {
    id: "D-FE-012",
    title: { de: "Attribution ist client-declared", en: "Attribution is client-declared" },
    truth: {
      de: "Der Dienst prüft die Anwesenheit einer invocation_id, nicht ihre Herkunft (W8).",
      en: "The service checks presence of an invocation_id, not its provenance (W8).",
    },
    workaround: {
      de: "Die Oberfläche füllt inv_<run>_<round>_<stakeholder>_<n> und kennzeichnet sie als client-declared.",
      en: "The UI fills inv_<run>_<round>_<stakeholder>_<n> and labels it client-declared.",
    },
    removal: {
      de: "Eine run-scoped Invocation-Lookup im Orchestrator.",
      en: "A run-scoped invocation lookup in the orchestrator.",
    },
  },
  {
    id: "D-FE-013",
    title: { de: "Standard-LLM ist scripted", en: "Default LLM is scripted" },
    truth: {
      de: "Ohne LLM_PROVIDER=openai-compatible liefert der Dienst deterministische Platzhalter.",
      en: "Without LLM_PROVIDER=openai-compatible the service returns deterministic placeholders.",
    },
    workaround: {
      de: "Einstellungen und Dashboard zeigen llm: scripted dauerhaft an.",
      en: "Settings and the dashboard show llm: scripted persistently.",
    },
    removal: {
      de: "Den Provider im Deployment konfigurieren.",
      en: "Configure the provider in the deployment.",
    },
  },
  {
    id: "D-FE-014",
    title: { de: "Preise können Null sein", en: "Prices may be zero" },
    truth: {
      de: "SIMULATION_ALLOW_ZERO_PRICE erlaubt einen Lauf ohne Preistabelle; Kosten werden als 0 gemessen.",
      en: "SIMULATION_ALLOW_ZERO_PRICE allows a run without a price table; cost is measured as 0.",
    },
    workaround: {
      de: "Kostenkarten zeigen den Hinweis „Preise nicht konfiguriert“.",
      en: "Cost cards show “prices not configured”.",
    },
    removal: {
      de: "SIMULATION_ALLOW_ZERO_PRICE=false mit gesetzten Preisen.",
      en: "SIMULATION_ALLOW_ZERO_PRICE=false with configured prices.",
    },
  },
  {
    id: "D-FE-015",
    title: { de: "open_position_ids bleibt nach dem Schließen gefüllt", en: "open_position_ids stays populated after close" },
    truth: {
      de: "Das Feld ist ein letzter bekannter Stand, keine Aussage über Änderbarkeit.",
      en: "The field is a last-known snapshot, not a statement about mutability.",
    },
    workaround: {
      de: "Die Oberfläche leitet keine Schreibbarkeit daraus ab und zeigt den Schließzustand separat.",
      en: "The UI does not infer writability from it and shows closure separately.",
    },
    removal: {
      de: "Das Feld beim Schließen leeren oder in open/closed positions teilen.",
      en: "Clear it on close, or split it into open/closed positions.",
    },
  },
  {
    id: "D-FE-016",
    title: { de: "Herkunft liefert 404 bis zur Offenlegung", en: "Provenance returns 404 until disclosed" },
    truth: {
      de: "GET /positions/{id}/provenance antwortet 404, bis eine Offenlegung geschrieben ist.",
      en: "GET /positions/{id}/provenance answers 404 until a disclosure is written.",
    },
    workaround: {
      de: "404 wird als „noch nicht offengelegt“ dargestellt; die Offenlegung ist ein expliziter Schritt.",
      en: "404 is rendered as “not yet disclosed”; disclosure is an explicit step.",
    },
    removal: {
      de: "Ein 200 mit absence-Objekt oder automatische Offenlegung.",
      en: "A 200 with an absence object, or automatic disclosure.",
    },
  },
  {
    id: "D-FE-017",
    title: { de: "Integrationstests leeren die Demo-Datenbank (#421)", en: "Integration tests wipe the demo database (#421)" },
    truth: {
      de: "Ein Testlauf kann den Seed entfernen.",
      en: "A test run can remove the seed.",
    },
    workaround: {
      de: "Die README verlangt, nach jedem Backend-Testlauf make demo-seed erneut auszuführen.",
      en: "The README requires re-running make demo-seed after any backend test run.",
    },
    removal: {
      de: "Ein separater Test-Datenbankschema oder ein idempotenter Seed im Testlauf.",
      en: "A separate test database schema, or an idempotent seed in the test run.",
    },
  },
  {
    id: "D-FE-018",
    title: { de: "Ereignisnamen weichen vom Prompt ab", en: "Event names differ from the prompt" },
    truth: {
      de: "Tatsächlich emittiert werden ConflictTopicOpened, CoalitionOffered, CoalitionOfferDeclined und ArgumentSubmitted; die im Prompt genannten ConflictOpened/ConflictResolved/CoalitionOfferMade existieren nicht.",
      en: "Actually emitted are ConflictTopicOpened, CoalitionOffered, CoalitionOfferDeclined and ArgumentSubmitted; the prompt's ConflictOpened/ConflictResolved/CoalitionOfferMade do not exist.",
    },
    workaround: {
      de: "Der Feed zeigt bekannte Namen lokalisiert und unbekannte Namen unverändert; Rohdaten bleiben aufklappbar.",
      en: "The feed localizes known names and leaves unknown names unchanged; raw data stays expandable.",
    },
    removal: {
      de: "Ereignisnamen im Prompt an das Domänenvokabular angleichen.",
      en: "Align the prompt's event names with the domain vocabulary.",
    },
  },
  {
    id: "D-FE-019",
    title: { de: "Resume verlangt ein action-Feld", en: "Resume requires an action field" },
    truth: {
      de: "POST /runs/{id}:resume verwendet PauseResumeBody, in dem action erforderlich ist, obwohl der Handler sie überschreibt.",
      en: "POST /runs/{id}:resume uses PauseResumeBody, where action is required even though the handler overrides it.",
    },
    workaround: {
      de: "Die Oberfläche sendet action: resume.",
      en: "The UI sends action: resume.",
    },
    removal: {
      de: "Ein eigenes ResumeBody ohne action.",
      en: "A dedicated ResumeBody without action.",
    },
  },
  {
    id: "D-FE-020",
    title: { de: "Historienabruf verlangt usable_only", en: "History read requires usable_only" },
    truth: {
      de: "GET /stakeholders/{id}/history hat usable_only als erforderlichen Query-Parameter ohne Standardwert.",
      en: "GET /stakeholders/{id}/history has usable_only as a required query parameter without a default.",
    },
    workaround: {
      de: "Die Oberfläche sendet immer true oder false.",
      en: "The UI always sends true or false.",
    },
    removal: {
      de: "Einen Standardwert im Endpunkt setzen.",
      en: "Set a default in the endpoint.",
    },
  },
];
