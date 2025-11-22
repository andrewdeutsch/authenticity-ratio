# Issue Type Validation Analysis

## Purpose
Review all LLM-generated issue types across dimensions to identify which ones should allow general guidance (not require concrete "Change 'X' → 'Y'" rewrites).

## Current General Guidance Exemptions

These issue types are currently exempt from requiring concrete rewrites:

```python
GENERAL_GUIDANCE_ISSUES = [
    'inconsistent voice',
    'tone shift', 
    'brand voice inconsistency',
    'vocabulary',
    'improvement_opportunity',
    'poor readability',
    'inappropriate tone'
]
```

## Issue Types by Dimension

### Coherence (Lines 306-312 in scoring_llm_client.py)

| Issue Type | Requires Concrete Rewrite? | Currently Exempt? | Recommendation |
|------------|---------------------------|-------------------|----------------|
| `inconsistent_voice` | ❌ No - general voice issues | ✅ Yes | ✅ Correct |
| `vocabulary` | ❌ No - word choice patterns | ✅ Yes | ✅ Correct |
| `tone_shift` | ❌ No - tone consistency | ✅ Yes | ✅ Correct |
| `contradictory_claims` | ✅ Yes - specific claims | ❌ No | ✅ Correct |
| `broken_links` | ✅ Yes - specific URLs | ❌ No | ✅ Correct |

**Status:** ✅ All coherence issues correctly configured

---

### Verification (Lines 313-317)

| Issue Type | Requires Concrete Rewrite? | Currently Exempt? | Recommendation |
|------------|---------------------------|-------------------|----------------|
| `unverified_claims` | ✅ Yes - specific claims need citations | ❌ No | ✅ Correct |
| `fake_engagement` | ⚠️ Maybe - metrics analysis | ❌ No | ⚠️ Consider adding |
| `unlabeled_ads` | ✅ Yes - specific ads to label | ❌ No | ✅ Correct |

**Status:** ⚠️ `fake_engagement` might benefit from general guidance (e.g., "Monitor engagement patterns for bot activity" rather than "Change '1000 likes' → '50 real likes'")

---

### Transparency (Lines 318-323)

| Issue Type | Requires Concrete Rewrite? | Currently Exempt? | Recommendation |
|------------|---------------------------|-------------------|----------------|
| `missing_privacy_policy` | ❌ No - structural issue | ❌ No | ⚠️ Consider adding |
| `no_ai_disclosure` | ❌ No - structural issue | ❌ No | ⚠️ Consider adding |
| `missing_data_source_citations` | ✅ Yes - specific citations needed | ❌ No | ✅ Correct |
| `hidden_sponsored_content` | ✅ Yes - specific content to label | ❌ No | ✅ Correct |

**Status:** ⚠️ `missing_privacy_policy` and `no_ai_disclosure` are structural issues that can't have concrete rewrites - they need general guidance like "Add a privacy policy link to footer"

---

### Provenance (Lines 324-328)

| Issue Type | Requires Concrete Rewrite? | Currently Exempt? | Recommendation |
|------------|---------------------------|-------------------|----------------|
| `unclear_authorship` | ❌ No - structural issue | ❌ No | ⚠️ Consider adding |
| `missing_metadata` | ❌ No - structural issue | ❌ No | ⚠️ Consider adding |
| `no_schema_markup` | ❌ No - structural issue | ❌ No | ⚠️ Consider adding |

**Status:** ⚠️ All provenance issues are structural (missing elements) rather than text rewrites - they need general guidance

---

### Resonance (Lines 329-332)

| Issue Type | Requires Concrete Rewrite? | Currently Exempt? | Recommendation |
|------------|---------------------------|-------------------|----------------|
| `poor_readability` | ❌ No - overall readability | ✅ Yes | ✅ Correct |
| `inappropriate_tone` | ❌ No - tone matching | ✅ Yes | ✅ Correct |

**Status:** ✅ All resonance issues correctly configured

---

## Recommendations

### High Priority - Add to Exemption List

These issue types are **structural** (missing elements) and cannot have concrete text rewrites:

```python
# Transparency structural issues
'missing_privacy_policy',
'no_ai_disclosure',

# Provenance structural issues  
'unclear_authorship',
'missing_metadata',
'no_schema_markup',
```

**Rationale:** You can't show a concrete rewrite for "add a privacy policy link" - it's a structural addition, not a text change.

### Medium Priority - Consider Adding

These might benefit from general guidance:

```python
# Verification
'fake_engagement',  # Metrics analysis, not text changes
```

**Rationale:** Fake engagement is detected through pattern analysis, not specific text that needs rewriting.

### Low Priority - Keep As-Is

These correctly require concrete rewrites:

- `unverified_claims` - Need specific citations
- `unlabeled_ads` - Need specific labels
- `contradictory_claims` - Need specific claim corrections
- `broken_links` - Need specific URL fixes
- `missing_data_source_citations` - Need specific citations
- `hidden_sponsored_content` - Need specific labels

---

## Proposed Updated List

```python
GENERAL_GUIDANCE_ISSUES = [
    # Coherence (tone/voice)
    'inconsistent voice',
    'tone shift', 
    'brand voice inconsistency',
    'vocabulary',
    
    # Resonance (audience fit)
    'poor readability',
    'inappropriate tone',
    
    # High-score optimizations
    'improvement_opportunity',
    
    # Transparency structural issues
    'missing_privacy_policy',
    'no_ai_disclosure',
    
    # Provenance structural issues
    'unclear_authorship',
    'missing_metadata',
    'no_schema_markup',
    
    # Verification pattern analysis
    'fake_engagement'
]
```

---

## Impact Assessment

### If We Add These Exemptions:

✅ **Benefits:**
- Structural issues will show remedies instead of being filtered out
- More helpful guidance for missing elements
- Better user experience

⚠️ **Risks:**
- Might allow some vague LLM responses through
- Need to ensure predefined remedies exist for all structural issues

### Mitigation:

1. Add predefined remedies for all structural issue types
2. Keep confidence thresholds high (≥0.8) for these issues
3. Monitor for vague/unhelpful suggestions

---

## Next Steps (If Approved)

1. Add predefined remedies for structural issues to `remedies` dictionary
2. Update `GENERAL_GUIDANCE_ISSUES` list with structural issue types
3. Test with content that has structural issues
4. Monitor for quality of suggestions
