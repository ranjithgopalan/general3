---
name: kb-build
description: Build (or rebuild) the application's card/graph knowledge base from the corpus under inputs/ -- typed knowledge cards with stable ids, a typed-edge graph.json and an evidence map anchoring every card to a source locus. Cite-or-abstain; a claim without a locus is not a card. Output layout is the one fe_core.kb.cards reads.
license: Proprietary
metadata:
  author: ADLC KB Team
  version: "0.1.0"
  organization: AIG
  plugin: AIDLC-kb
allowed-tools: Read Write Edit Glob Grep Bash TodoWrite
---

# kb-build — reverse-engineer the corpus into a card / graph KB

You are the orchestrator of a **reverse-engineering** pass. The corpus (RED, business
specs, schema dumps, source, screen captures already OCR'd to text) is under
`inputs/`. Produce the knowledge base under **`kb/`** in the working directory, in
exactly this layout:

```
kb/
  knowledge/
    entities/ENT-*.md         data entities (attributes, cardinality, lifecycle)
    rules/BR-*.md             business rules (condition -> outcome, owner, source)
    requirements/FR-*.md      functional requirements (as-is behaviour)
    screens/SCR-*.md          screens / forms (fields, actions, navigation)
    workflows/WF-*.md         workflows / processes (steps, actors, systems)
    components/CMP-*.md       code components / modules (only from source or RED)
    apis/API-*.md             endpoints / interfaces / integrations
    ontology/graph.json       {"nodes":[{id,kind,label}], "edges":[{source,target,label}]}
  evidence/evidence-map.jsonl {id, source_doc, locus:{page|section|line|cell}, snippet, confidence}
  cards.jsonl                 flat export: {id,kind,label,summary,body,sources[]}
  _build-report.md            counts per kind, gate results, open questions
```

## Card format (one file per card)

```markdown
---
id: BR-<APP>-0007            # PREFIX-<APP>-<NNNN>; PREFIX in ENT|BR|FR|SCR|WF|CMP|API
kind: BR
label: Minimum premium floor
summary: One sentence, verbatim-close to the source.
sources: [inputs/RED.docx#p12, inputs/rules.xlsx#Rules!B14]
tags: [pricing, underwriting]
---
# BR-<APP>-0007 — Minimum premium floor

**Statement.** <the rule / entity / requirement, cited>
**Evidence.** <quote or near-quote from the source with its locus>
**Related.** ENT-<APP>-0003 (governs), SCR-<APP>-0011 (enforced on)
```

`<APP>` is the application code (from the project configuration block or the
folder name under `inputs/`), upper-case, 2–6 chars. Ids are **stable**: rebuilds
keep existing ids for the same fact (read `kb/cards.jsonl` first when it exists).

## Workflow (track with TodoWrite; gates fail-closed)

1. **Plan** — `Glob inputs/**`; classify each file (spec / schema / code / screen /
   other). Read `kb/cards.jsonl` if present (rebuild keeps ids). Choose `<APP>`.
   Binary sources (`.docx/.pdf/.xlsx/.pptx`) have an extracted **`<name>.<ext>.txt` sidecar** —
   read the sidecar, never the binary. Large sidecars (a RED can be millions of characters):
   read them **in windows** with `Read` `offset`/`limit` (≈ 400 lines at a time), extracting cards
   per window and keeping a running `kb/_progress.md` (last offset per file) so a resumed
   session continues where it stopped. Cite the locus as `file.txt#L<start>-L<end>` plus the
   nearest section heading.
2. **Extract per file** — for each source, extract candidate cards **with a locus**
   (page, section heading, sheet!cell, or file:line). No locus → no card. Write the
   evidence-map line as you write the card.
3. **Synthesise the graph** — after all files: reconcile duplicates (same fact,
   two sources → one card, two evidence lines), then build `graph.json`. Edge
   labels from this closed set: `GOVERNS`, `DEPENDS_ON`, `SCREEN_OF`, `PART_OF`,
   `IMPLEMENTS`, `CALLS`, `REFERENCES`, `TRIGGERS`, `PRODUCES`. Every card is a
   node; every edge endpoint must be an existing node.
4. **Export** — write `cards.jsonl` (one line per card) from the card files.
5. **Gate** — run the deterministic check and fix what it reports:
   `python ${CLAUDE_PLUGIN_ROOT}/skills/kb-check/kb_check.py kb`
   It fails on: duplicate ids, malformed ids, edges to unknown nodes, cards without
   evidence, evidence without a card, empty label/summary. Repeat until it passes.
6. **Report** — write `kb/_build-report.md`: cards per kind, nodes/edges, evidence
   count, gate result, and an *Open questions* list of anything ambiguous in the
   sources (never resolve ambiguity by inventing).

## Rules
- **Budget-aware, breadth-first.** Your session has a bounded number of turns. Do not try to
  read a huge corpus end to end: first locate the table of contents / section headings
  (`Grep` for headings), then extract from the sections that carry entities, rules, screens
  and workflows; write cards as you go so a partial pass still yields a valid, gated KB.
  Reserve the last ~15 turns for graph.json, cards.jsonl, the gate and the report — a KB
  that fails the gate is worth nothing; a smaller KB that passes is the deliverable.
- **Cite or abstain.** Never write a card you cannot anchor to a locus.
- Do not read files outside `inputs/` and `kb/`.
- Write incrementally (a card file per Write); do not buffer the whole KB in one message.
- Keep summaries ≤ 40 words; put detail in the body.
