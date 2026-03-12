# AI Crawler Placeholder

This document describes the crawler scaffold added in this phase.

## Why this phase is scaffold-only

The current product focus is still the competition assistant, agent runtime,
task API, and frontend demo loop. The crawler work in this phase is only a
reserved structure for future implementation.

This phase does not implement:

- real web crawling
- login flows
- proxy handling
- scheduling
- browser automation
- storage integration

## What is intentionally not introduced

- no new crawler dependencies
- no Redis / Celery / queue system
- no vector database / RAG
- no new database table

## What is intentionally not connected

- no runtime integration
- no API route
- no frontend page

## Suggested future direction

When crawler work starts for real, begin with a narrow path:

1. one site
2. one provider
3. one offline validation task

Only after that should the project consider extraction pipelines,
normalization, storage bridging, or runtime integration.
