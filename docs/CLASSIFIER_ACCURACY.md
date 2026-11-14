# Classifier accuracy report

Phase 7 requires a labeled set of representative prompts and a script that
reports classifier accuracy. This is the first measurement of
`backend/app/core/classifier.py`; it records where the rule-based classifier
works and where it does not.

- Date: 2026-11-14
- Data: `backend/tests/data/classifier_prompts.json` — 62 prompts, all five
  categories, unique phrasings
- Script: `backend/scripts/evaluate_classifier.py`
- Reproduction:

  ```
  cd backend
  .venv/Scripts/python.exe scripts/evaluate_classifier.py
  ```

Labels are the category a user would expect for that phrasing under the
rubric below, not the classifier's output. The dataset was written before the
script was run, and no prompt was added or relabeled afterwards to improve the
score.

## Labeling rubric

| Category | Prompt shape |
| :--- | :--- |
| `CODING` | Writing, reviewing, debugging, or explaining code. |
| `RESEARCH` | Comparing options, weighing evidence, gathering findings. |
| `WRITING` | Producing or rewriting prose documents: emails, posts, essays, summaries. |
| `PLANNING_DECISION` | Plans, architectures, roadmaps, sequencing, decisions. |
| `GENERAL` | Conversation, quick facts, short personal messages. |

Five prompts use an explicit `@skill` prefix, which the classifier checks
before any heuristic.

## Result

```
Overall: 41/62 (66.1%)

By category:
  CODING             10/14 (71.4%)
  RESEARCH            8/13 (61.5%)
  WRITING             5/12 (41.7%)
  PLANNING_DECISION   6/11 (54.5%)
  GENERAL            12/12 (100.0%)
```

Every one of the 21 misses predicted `GENERAL`:

```
CODING             -> GENERAL            4
PLANNING_DECISION  -> GENERAL            5
RESEARCH           -> GENERAL            5
WRITING            -> GENERAL            7
```

No prompt was mapped to the wrong specific category: the failure mode is
under-classification, not misfiling. That matters because `GENERAL` routes to
the fastest/cheapest model (Groq `gpt-oss-20b` by default), so a miss trades
answer quality for cost rather than breaking the request.

### Missed prompts

| Expected | Prompt |
| :--- | :--- |
| CODING | Why does my Python script throw a KeyError when loading config? |
| CODING | Review this pull request diff for security issues. |
| CODING | Convert this callback-heavy module to async/await. |
| CODING | What is the time complexity of this binary search function? |
| RESEARCH | Which embedding model should I pick for semantic search? |
| RESEARCH | Survey the current browser automation landscape. |
| RESEARCH | What evidence supports Postgres over DynamoDB for this workload? |
| RESEARCH | Give me an overview of retrieval-augmented generation research. |
| RESEARCH | Weigh the tradeoffs between self-hosting and managed services. |
| WRITING | Rewrite this paragraph in a friendlier tone. |
| WRITING | Draft a cover letter for a backend internship. |
| WRITING | Write product announcement copy for our beta launch. |
| WRITING | Polish these release notes for clarity. |
| WRITING | Turn these bullet points into a short proposal. |
| WRITING | Write a LinkedIn post announcing my new role. |
| WRITING | Draft a thank-you note to the interview panel. |
| PLANNING_DECISION | Help me decide between hiring a contractor or a full-time engineer. |
| PLANNING_DECISION | Should we launch the beta in March or wait for more testing? |
| PLANNING_DECISION | Lay out a six-month roadmap for the product. |
| PLANNING_DECISION | What is the best sequencing for these three releases? |
| PLANNING_DECISION | Which database design tradeoffs matter most for this schema? |

## Interpretation

1. The heuristics only recognize a narrow set of stock phrasings (`debug this`,
   `compare X and Y`, `draft an email`, `plan a`). Natural variants fall
   through to `GENERAL`.
2. `WRITING` is the weakest category (41.7%) because only four literal
   triggers exist; `rewrite`, `polish`, `turn into`, `cover letter`, and
   `announcement` are not covered.
3. `@skill` prefixes are exact: all five prefixed prompts classified
   correctly. Explicit skill use is a reliable fallback for users who care
   about routing.
4. Manual mode is unaffected — the user picks the model directly.

## Follow-up (not part of Phase 7)

Phase 7 exists to measure, not to tune. If the owner wants Auto mode to route
better, the actionable work is:

- Add intent patterns for `rewrite|polish|shorten|turn .* into` (WRITING),
  `roadmap|sequencing|decide between|should we` (PLANNING_DECISION),
  `evidence|survey|overview of .* research|which .* should i pick`
  (RESEARCH), and `pull request|async/await|time complexity|KeyError|throw`
  (CODING).
- Re-run this dataset after any change; `backend/tests/test_classifier_dataset.py`
  fails if accuracy drops below 0.60 (the recorded 66.1% minus a small
  regression margin).

Any classifier change must keep the existing `tests/test_classifier.py`
expectations intact or explicitly revise them with a decision-log entry.
