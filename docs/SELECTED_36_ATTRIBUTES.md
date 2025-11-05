# Selected 36 Trust Stack Attributes for Initial Implementation

## Selection Criteria
1. **Detectability**: Can be detected with current data sources (Reddit, Amazon, YouTube, Brave)
2. **Clear Scoring Rules**: Well-defined 1-10 scoring methodology
3. **Balanced Coverage**: Proportional representation across 5 dimensions
4. **Impact**: High impact on trust measurement

## Distribution
- **Provenance**: 7 attributes (19.4%)
- **Resonance**: 7 attributes (19.4%)
- **Coherence**: 8 attributes (22.2%)
- **Transparency**: 6 attributes (16.7%)
- **Verification**: 8 attributes (22.2%)

---

## PROVENANCE (7 attributes)

### 1. AI vs Human Labeling Clarity
- **How to Collect**: Scrape for meta tags or labels ('AI-generated', 'human-created')
- **Scoring**: 10 if clearly labeled; 5 if ambiguous; 1 if missing
- **Detection**: Check meta tags, schema.org, content body for AI disclosure

### 2. Author/brand identity verified
- **How to Collect**: Extract byline; cross-check against verified accounts
- **Scoring**: 10 if verified; 3 if unknown
- **Detection**: Check for verified badges, blue checks, platform verification APIs

### 3. C2PA/CAI manifest present
- **How to Collect**: HTTP HEAD/GET; parse content-type & manifest
- **Scoring**: 10 if present & valid; 5 if present but invalid; 1 if missing
- **Detection**: Parse C2PA metadata from images/videos

### 4. Canonical URL matches declared source
- **How to Collect**: Scrape `<link rel='canonical'>` and compare
- **Scoring**: 10 if exact match; 5 if partial; 1 if mismatch
- **Detection**: Extract canonical URL from HTML, compare to actual URL

### 5. Digital watermark/fingerprint detected
- **How to Collect**: Download asset; run watermark detector
- **Scoring**: 10 if strong match; 1 if none
- **Detection**: Image analysis for watermarks (Digimarc-style)

### 6. EXIF/metadata integrity
- **How to Collect**: Read EXIF; check editing history
- **Scoring**: 10 if intact; 5 if stripped; 1 if spoofed
- **Detection**: Parse EXIF data from images

### 7. Source domain trust baseline
- **How to Collect**: Resolve domain score from curated list
- **Scoring**: Map domain score 1–10
- **Detection**: Check domain against NewsGuard-style reputation lists

---

## RESONANCE (7 attributes)

### 8. Community Alignment Index
- **How to Collect**: Graph-community overlap between content values and engaged audience
- **Scoring**: 10 if high alignment; 1 if misaligned
- **Detection**: Analyze hashtags, mentions, engagement patterns

### 9. Creative recency vs trend
- **How to Collect**: Compare against trending topics list
- **Scoring**: 10 if aligned; 5 neutral; 1 tone-deaf
- **Detection**: Compare content topics to current trends

### 10. Cultural Context Alignment
- **How to Collect**: Detect mentions of local events, holidays, cultural references
- **Scoring**: 10 if aligned; 1 if irrelevant
- **Detection**: NER + knowledge base for cultural events

### 11. Language/locale match
- **How to Collect**: Detect language; compare to user/market
- **Scoring**: 10 if match; 5 if multilingual; 1 if mismatch
- **Detection**: Language detection (langdetect, fastText)

### 12. Personalization relevance
- **How to Collect**: Embed user/context & content; cosine similarity
- **Scoring**: Map similarity to 1–10 scale
- **Detection**: Embedding similarity analysis

### 13. Readability grade level fit
- **How to Collect**: Compute FKGL/SMOG vs audience
- **Scoring**: 10 if within target; 1 if off
- **Detection**: Flesch-Kincaid Grade Level, SMOG index

### 14. Tone & sentiment appropriateness
- **How to Collect**: Classifier vs brand tone guide
- **Scoring**: 10 if within band; 5 borderline; 1 off-tone
- **Detection**: Sentiment analysis models

---

## COHERENCE (8 attributes)

### 15. Brand voice consistency score
- **How to Collect**: N-gram/embedding vs style corpus
- **Scoring**: 10 if z-score within band
- **Detection**: Embedding similarity to brand style guide

### 16. Broken link rate
- **How to Collect**: Crawl & check HTTP codes
- **Scoring**: 10 if <1%; 1 if >10%
- **Detection**: Link validation in content

### 17. Claim consistency across pages
- **How to Collect**: Extract claims; fuzzy match & check contradictions
- **Scoring**: 10 if no contradictions; lower if found
- **Detection**: NLI/contradiction detection models

### 18. Email-Asset Consistency Check
- **How to Collect**: Validate email claims/pricing match landing page
- **Scoring**: 10 if consistent; 1 if contradictory
- **Detection**: Cross-channel content comparison

### 19. Engagement-to-Trust Correlation
- **How to Collect**: Ingest engagement metrics (CTR, dwell time, conversion)
- **Scoring**: 10 if high positive correlation; 1 if negative
- **Detection**: Analyze engagement patterns vs trust signals

### 20. Multimodal Consistency Score
- **How to Collect**: Compare captions/titles vs transcript/voiceover
- **Scoring**: 10 if >0.9 semantic match; 1 if <0.5
- **Detection**: ASR + embeddings (cosine similarity)

### 21. Temporal continuity (versions)
- **How to Collect**: Track content version history
- **Scoring**: 10 if change log present & consistent
- **Detection**: Check for version history metadata

### 22. Trust Fluctuation Index
- **How to Collect**: Time-series sentiment volatility after content drops
- **Scoring**: 10 if low volatility; 1 if high sustained volatility
- **Detection**: Sentiment analysis over time

---

## TRANSPARENCY (6 attributes)

### 23. AI Explainability Disclosure
- **How to Collect**: Detect 'why you're seeing this' or 'powered by' explanations
- **Scoring**: 10 if visible; 1 if absent
- **Detection**: Look for explanation UI elements

### 24. AI-generated/assisted disclosure present
- **How to Collect**: Detect disclosure label/schema
- **Scoring**: 10 if present & clear; 1 if absent
- **Detection**: Check schema.org/CreativeWork + custom labels

### 25. Bot Disclosure + Response Audit
- **How to Collect**: Evaluate whether AI/chatbots self-identify
- **Scoring**: 10 if all three present (disclosure, sources, human path); 1 if none
- **Detection**: Check bot identification patterns

### 26. Caption/Subtitle Availability & Accuracy
- **How to Collect**: Check availability and alignment with ASR transcript
- **Scoring**: 10 if available & accurate; 1 if absent/inaccurate
- **Detection**: ASR vs caption comparison

### 27. Data source citations for claims
- **How to Collect**: Parse footnotes/citations
- **Scoring**: 10 if cites verified sources
- **Detection**: Citation parser, link extraction

### 28. Privacy policy link availability & clarity
- **How to Collect**: Scrape presence; readability test
- **Scoring**: 10 if clear and accessible
- **Detection**: Find privacy policy links, readability analysis

---

## VERIFICATION (8 attributes)

### 29. Ad/Sponsored Label Consistency
- **How to Collect**: Detect and cross-check 'ad/sponsored' labels
- **Scoring**: 10 if consistent; 1 if missing
- **Detection**: Ad label detection across surfaces

### 30. Agent Safety Guardrail Presence
- **How to Collect**: Detect safety guardrails for bots
- **Scoring**: 10 if present & effective; 1 if absent
- **Detection**: Check for safety features in bot responses

### 31. Claim-to-source traceability
- **How to Collect**: Link each claim to source URL/doc
- **Scoring**: 10 if all claims traced
- **Detection**: Citation linking and validation

### 32. Engagement Authenticity Ratio
- **How to Collect**: Run bot/sybil detection on likes, comments, followers
- **Scoring**: 10 if >90% authentic; 1 if <50%
- **Detection**: Bot detection models on engagement data

### 33. Influencer/partner identity verified
- **How to Collect**: Cross-check handle KYC/blue checks
- **Scoring**: 10 if verified; 1 if not
- **Detection**: Platform verification status

### 34. Review Authenticity Confidence
- **How to Collect**: Classify review set for bots/incentivized/fake patterns
- **Scoring**: 10 if >90% authentic; 1 if <60%
- **Detection**: Review graph analysis + NLP

### 35. Seller & Product Verification Rate
- **How to Collect**: Measure % listings with verified sellers/reviews
- **Scoring**: 10 if >90% verified; 1 if <40%
- **Detection**: Marketplace verification APIs

### 36. Verified purchaser review rate
- **How to Collect**: Pull reviews; check 'verified purchase'
- **Scoring**: Map % to 1–10
- **Detection**: Check verified purchase badges

---

## Implementation Priority

### Phase 1 (Immediate - Detectable from existing metadata)
- Author/brand identity verified
- Source domain trust baseline
- Language/locale match
- Readability grade level fit
- Tone & sentiment appropriateness
- Broken link rate
- Privacy policy link availability
- Verified purchaser review rate

### Phase 2 (Medium - Requires additional parsing)
- AI vs Human Labeling Clarity
- Canonical URL matches declared source
- Community Alignment Index
- Brand voice consistency score
- Claim consistency across pages
- Data source citations for claims
- Ad/Sponsored Label Consistency
- Influencer/partner identity verified

### Phase 3 (Advanced - Requires specialized detection)
- C2PA/CAI manifest present
- Digital watermark/fingerprint detected
- EXIF/metadata integrity
- Multimodal Consistency Score
- Caption/Subtitle Availability & Accuracy
- Engagement Authenticity Ratio
- Review Authenticity Confidence
- Seller & Product Verification Rate

---

## Deferred Attributes (36 remaining from original 72)

The remaining 36 attributes can be added in future releases as:
- Detection capabilities improve
- Additional data sources become available
- More sophisticated analysis tools are integrated

Examples of deferred attributes:
- AI-Generated Media Label Check (requires advanced media analysis)
- Creator-Brand Disclosure Match (requires influencer registry)
- Duplicate/perceptual hash match rate (requires image corpus)
- First-seen timestamp (requires historical crawl data)
- Accessibility compliance (WCAG) (requires a11y audit tools)
- Design system token usage (requires design token registry)
- And 30+ more...
