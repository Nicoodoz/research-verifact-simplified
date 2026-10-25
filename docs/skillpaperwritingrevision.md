---
name: academic-paper-revision
description: Use when drafting or revising a journal-style academic manuscript, especially a LaTeX paper with formal methods, related work, experiments, and reviewer-driven structural changes.
author: Feng Hong
date: 2026-09-05
---

# Academic Paper Writing and Revision

Use this skill to improve the argument, terminology, and evidence flow of an academic paper. Treat sentence polishing as the final stage: first make the section logic correct, then make the prose concise.

## Working sequence

1. Read the target section and the immediately adjacent sections. Check the current notation, claims, figures, tables, and references before proposing edits.
2. Identify the section's job and preserve the paper's scientific scope, mechanism, equations, data, and reported conclusions unless the author explicitly authorizes changes.
3. For a structural rewrite, use brainstorming to agree on the section plan before editing. For a local edit, make the smallest change that resolves the stated problem.
4. Build a terminology and notation ledger. Use one name for each method, processing stage, variable, and metric, throughout the manuscript.
5. After editing a LaTeX manuscript, compile the main `.tex` file and inspect the log for errors, undefined references or commands, and newly introduced layout warnings.

## Argument-first principles

- Write in the order needed by the reader: purpose, motivation or intuition, design, formula or evidence, interpretation, and takeaway.
- Explain why a design choice follows from the objective or constraint; do not present an unmotivated geometric construction, parameter choice, or conclusion.
- State observations before explanations. Tie explanations to the mechanism or data, and hedge claims with `may` or `is consistent with` when the experiment does not establish causality.
- Remove repetition of material already visible in equations, tables, figures, or preceding paragraphs. Do not add detail merely to make a paragraph longer.
- Use the fewest symbols necessary. Define a symbol once, and never introduce a second symbol for an existing object.

## Section patterns

**Introduction.** Use: application problem and significance → related-work limitation and research gap → objective and either requirements or challenges → overview of the proposed designs → experiment overview → contribution summary. 

**Abstract.** Use: problem → prior limitation → proposed methods and their differing objectives → main empirical result. Keep it compact and do not repeat result details as a separate closing claim.

**Problem formulation.** Define the input, randomized output, domain, and complete mapping first. 

**Method design.** Begin the method section with an overview of the proposed model, mechanism, or system and its decomposition into major components or steps. State the number of components or steps and briefly introduce the role of each one. If an architecture figure is provided, describe it in the same paragraph and relate it to the problem decomposition. For each substantive step, mechanism, module, sub-step, or sub-module, follow the order: goal → principle and intuition → design → formula or derivation → discussion → conclusion. A property  must be presented as a design objective and justified before its equation is used.

**Related work.** State the classification criterion first. Establish hierarchy when one category is a refinement of another. Keep all work in a category together, and discuss that category's research gap only after its complete overview. Add transitions between related categories.

**Experiments.** Separate experimental setup (datasets, compared methods, metrics, parameters, repetitions) from results. Within each result subsection, use key trend → important comparison → mechanism or data-based explanation. Do not repeat exact table values unless they support a non-obvious point. For ablation, isolate components and compare their incremental contributions. For sensitivity, state the variable, utility/cost trade-off, and selected default. For runtime, group methods by computational regime before discussing causes.

**Conclusion.** In one concise passage, state the main contributions, the practical application scope, and the most relevant future work. Do not introduce new equations, methods, metrics, or unsupported claims. 

## Final consistency check

Before delivery, verify: method names and abbreviations are stable; input/report/output symbols match the formal model;  section, figure, table, and equation references are ordered; prose does not claim more than the evidence; and the compiled PDF reflects the edited source.
