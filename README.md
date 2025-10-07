# Authenticity Ratio (AR) Tool

## Overview
Authenticity Ratio (AR) is a KPI that measures authentic vs. inauthentic brand-linked content across channels. It reframes authenticity as a brand health metric for CMOs/boards.

## Formula
**Core:** AR = (Verified Authentic Content ÷ Total Brand-Linked Content) × 100

**Extended (with suspect):** AR = (A + 0.5S) ÷ (A + S + I) × 100
- A = Authentic, S = Suspect, I = Inauthentic

## 5D Trust Dimensions
Content is scored on:
- **Provenance** – origin, traceability, metadata (20%)
- **Verification** – factual accuracy vs. trusted DBs (20%)
- **Transparency** – disclosures, clarity (20%)
- **Coherence** – consistency across channels (20%)
- **Resonance** – cultural fit, organic engagement (20%)

## Pipeline
Ingest → Normalize → Enrich (metadata + fact-check) → Score (5D rubric) → Classify (A/S/I) → Compute AR → Report

## Project Structure
```
AR/
├── config/                 # Configuration files
├── data/                   # Data storage and processing
├── ingestion/              # Data collection modules
├── scoring/                # 5D scoring and classification
├── reporting/              # Report generation and dashboards
├── utils/                  # Shared utilities and helpers
├── tests/                  # Test files
├── docs/                   # Documentation
└── scripts/                # Deployment and maintenance scripts
```

## Quick Start
1. Set up configuration in `config/`
2. Run data ingestion: `python -m ingestion.reddit_crawler`
3. Process and score content: `python -m scoring.pipeline`
4. Generate reports: `python -m reporting.generator`

## Database
Uses AWS Athena with S3 storage for normalized content and scores.
