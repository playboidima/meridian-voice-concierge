# English Admin Content Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every seeded FAQ shown in the admin interface English while safely upgrading existing installations.

**Architecture:** Keep the 47 authoritative seed records in English. During startup, recognize only the exact legacy Ukrainian seed questions, update those rows in place, regenerate their embeddings, and leave user-created FAQ rows unchanged.

**Tech Stack:** Python 3.12, SQLAlchemy, PostgreSQL/pgvector, pytest, React/Vite, Docker Compose

**Spec:** User-approved design in the current task: all interface-visible content must be English.

## Global Constraints

- Keep exactly 47 built-in FAQ records.
- Do not translate or modify user-created FAQ records.
- Preserve IDs when upgrading a legacy seed row when no English duplicate exists.
- Regenerate embeddings from English content.
- Do not add secrets or external translation services.

---

### Task 1: English seed catalog

**Files:**
- Modify: `backend/app/seed_data.py`
- Create: `backend/tests/test_seed_data.py`

**Interfaces:**
- Produces: `FAQS` with 47 English question/answer records and legacy question mapping.

- [ ] Write a test asserting all user-visible seed text is English and the catalog still has 47 unique questions.
- [ ] Run the test and verify that it fails on the current Ukrainian catalog.
- [ ] Translate the catalog without changing PRD facts.
- [ ] Run the test and verify that it passes.

### Task 2: Safe existing-database upgrade

**Files:**
- Modify: `backend/app/seed.py`
- Modify: `backend/app/services/embeddings.py`
- Modify: `backend/app/services/faq_search.py`
- Test: `backend/tests/test_seed_data.py`

**Interfaces:**
- Produces: a startup reconciliation function that updates exact legacy seed rows and preserves custom rows.

- [ ] Write a failing SQLite behavior test with a legacy seed row and a custom Ukrainian FAQ.
- [ ] Implement legacy-row reconciliation before PostgreSQL upsert.
- [ ] Keep curated search aliases/passages available through the legacy-to-English key mapping.
- [ ] Run focused tests until green.

### Task 3: English scenarios and full verification

**Files:**
- Modify: `backend/tests/test_prd_scenarios.py`
- Modify: `backend/tests/test_semantic_search_gaps.py`
- Modify: `README.md`

**Interfaces:**
- Verifies: English FAQ responses, unknown-question safety, frontend display, and clean Docker startup.

- [ ] Update expected seeded questions and answers to English.
- [ ] Update documentation that still describes Ukrainian internal FAQ content.
- [ ] Run the complete Backend, Agent, admin test/build suites.
- [ ] Rebuild Docker services and verify health plus database content.

