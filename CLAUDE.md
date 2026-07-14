# HikeCast — agent instructions

Weather companion for hiking in the Romanian Carpathians (FastAPI + PostGIS
backend in `backend/`, React 19 + Tailwind v4 frontend in `frontend/`).
Portfolio project + real-use tool, built with tests and browser verification.

## Before doing ANY work

1. Read `docs/CHANGELOG.md` — current state, prioritised next steps, run
   commands, conventions, and hard-won gotchas. It is written for you.
2. When touching a design decision, check `docs/decisions/DECISIONS.md`
   (referenced as "DECISIONS NNN") before re-litigating it.

## Non-negotiable rules

- The user reviews and **commits himself**. Leave the tree uncommitted at
  session end and suggest a conventional-commit split.
- Light UI only: stone neutrals, white surfaces, single green-700 accent.
  Never dark slate / neon "AI look".
- Small diffs. Tests for critical paths as you build (pure logic gets
  hand-computed unit tests). Verify UI changes in the browser before
  claiming done — hard-reload first (Tailwind v4 HMR lies).
- Explain the WHY in code comments and to the user (teach-as-you-go).

## At the end of every session

Update `docs/CHANGELOG.md` (CURRENT STATE + NEXT UP + prepend a SESSION LOG
entry). Add/update a DECISIONS entry when a judgement call was made.
