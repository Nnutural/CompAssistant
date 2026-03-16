# Data Sources

This page describes where the repository currently gets data from.

## Existing local product data

| Source | Status | Access path | Refresh mode | Notes |
| --- | --- | --- | --- | --- |
| `backend/data/competitions.json` | implemented | competitions API and runtime tools | manual file update | current competition directory |
| `backend/data/competitions_enriched.json` | implemented | runtime tools | manual file update | enrichment keyed by field and competition id |
| `backend/data/eligibility_rules.json` | implemented | runtime tools | manual file update | product-level suitability rules |
| `backend/data/recommendation_rubric.json` | implemented | runtime tools | manual file update | ranking and eval scoring rubric |
| `backend/data/timeline_templates.json` | implemented | runtime tools | manual file update | reverse schedule templates |

## Existing runtime-generated data

| Source | Status | Access path | Refresh mode | Notes |
| --- | --- | --- | --- | --- |
| `backend/data/research_ledgers/*.json` | implemented | `LedgerRepository` | runtime generated | current run state source of truth |
| `backend/data/research_runtime_sessions.sqlite3` | implemented | Agents SDK runtime | runtime generated | provider session state only |

## Experimental local knowledge sources

| Source | Status | Access path | Refresh mode | Notes |
| --- | --- | --- | --- | --- |
| public static HTTP page | implemented | `backend/app/crawler/providers/http_provider.py` | on-demand fetch | no Playwright, no login, no dynamic rendering |
| local competition catalog JSON | implemented | `backend/app/crawler/sources/competition_catalog_source.py` | on-demand read | converts `competitions.json` rows into raw documents |
| local raw document store | implemented | `backend/data/local_knowledge/raw/` | on-demand write | stores raw document JSON payloads |
| local normalized document store | implemented | `backend/data/local_knowledge/normalized/` | on-demand write | stores normalized document JSON payloads |
| local sqlite knowledge index | implemented | `backend/data/local_knowledge/knowledge_index.sqlite3` | on-demand write | SQLite + FTS5 when available |

## Current minimal source set

- Policy or regulation source:
  Public static ministry policy page fetched over plain HTTP.
- Competition source:
  Existing `backend/data/competitions.json` converted into normalized documents.

## Explicit non-sources in this phase

- No Notion integration
- No Playwright capture
- No authenticated sites
- No CAPTCHA, proxy, or anti-bot bypass
- No direct agent access to raw webpages or raw crawler files
