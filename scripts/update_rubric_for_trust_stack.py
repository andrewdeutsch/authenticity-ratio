#!/usr/bin/env python3
"""
Update rubric.json for Trust Stack v2.0:
- Enable only the 36 selected attributes
- Add dimension field to each attribute
- Update version to v2.0-trust-stack
- Add parsed scoring rules
"""
import json
import os
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
RUBRIC_PATH = os.path.join(PROJECT_ROOT, "config", "rubric.json")
BACKUP_PATH = RUBRIC_PATH + ".bak-" + datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

# 36 selected attributes mapped to dimensions
SELECTED_ATTRIBUTES = {
    # Provenance (7)
    "ai_vs_human_labeling_clarity": "provenance",
    "author_brand_identity_verified": "provenance",
    "c2pa_cai_manifest_present": "provenance",
    "canonical_url_matches_declared_source": "provenance",
    "digital_watermark_fingerprint_detected": "provenance",
    "exif_metadata_integrity": "provenance",
    "source_domain_trust_baseline": "provenance",

    # Resonance (7)
    "community_alignment_index": "resonance",
    "creative_recency_vs_trend": "resonance",
    "cultural_context_alignment": "resonance",
    "language_locale_match": "resonance",
    "personalization_relevance_embedding_similarity": "resonance",
    "readability_grade_level_fit": "resonance",
    "tone_sentiment_appropriateness": "resonance",

    # Coherence (8)
    "brand_voice_consistency_score": "coherence",
    "broken_link_rate": "coherence",
    "claim_consistency_across_pages": "coherence",
    "email_asset_consistency_check": "coherence",
    "engagement_to_trust_correlation": "coherence",
    "multimodal_consistency_score": "coherence",
    "temporal_continuity_versions": "coherence",
    "trust_fluctuation_index": "coherence",

    # Transparency (6)
    "ai_explainability_disclosure": "transparency",
    "ai_generated_assisted_disclosure_present": "transparency",
    "bot_disclosure_response_audit": "transparency",
    "caption_subtitle_availability_accuracy": "transparency",
    "data_source_citations_for_claims": "transparency",
    "privacy_policy_link_availability_clarity": "transparency",

    # Verification (8)
    "ad_sponsored_label_consistency": "verification",
    "agent_safety_guardrail_presence": "verification",
    "claim_to_source_traceability": "verification",
    "engagement_authenticity_ratio": "verification",
    "influencer_partner_identity_verified": "verification",
    "review_authenticity_confidence": "verification",
    "seller_product_verification_rate": "verification",
    "verified_purchaser_review_rate": "verification",
}

def parse_scoring_rule(rule_str: str) -> dict:
    """Parse scoring rule string into structured format"""
    rule_str = rule_str.lower()

    # Common patterns
    if "10 if" in rule_str and ("1 if" in rule_str or "absent" in rule_str):
        return {
            "type": "boolean",
            "max_value": 10,
            "min_value": 1,
            "description": rule_str
        }
    elif "map" in rule_str and "1–10" in rule_str or "1-10" in rule_str:
        return {
            "type": "continuous",
            "min_value": 1,
            "max_value": 10,
            "description": rule_str
        }
    elif "%" in rule_str or "percentage" in rule_str:
        return {
            "type": "percentage",
            "min_value": 1,
            "max_value": 10,
            "description": rule_str
        }
    else:
        return {
            "type": "categorical",
            "min_value": 1,
            "max_value": 10,
            "description": rule_str
        }

def main():
    print(f"Loading rubric from {RUBRIC_PATH}...")
    with open(RUBRIC_PATH, "r", encoding="utf-8") as f:
        rubric = json.load(f)

    # Backup current rubric
    print(f"Backing up to {BACKUP_PATH}...")
    with open(BACKUP_PATH, "w", encoding="utf-8") as f:
        json.dump(rubric, f, indent=2, ensure_ascii=False)

    # Update version
    rubric["version"] = "2.0-trust-stack"
    rubric["updated_at"] = datetime.utcnow().isoformat() + "Z"
    rubric["selected_attributes_count"] = len(SELECTED_ATTRIBUTES)

    # Update attributes
    updated_count = 0
    for attr in rubric["attributes"]:
        attr_id = attr["id"]

        if attr_id in SELECTED_ATTRIBUTES:
            # Enable and add dimension
            attr["enabled"] = True
            attr["dimension"] = SELECTED_ATTRIBUTES[attr_id]

            # Parse scoring rule if available
            if "source_row" in attr and "Scoring Rule (1–10)" in attr["source_row"]:
                scoring_rule = attr["source_row"]["Scoring Rule (1–10)"]
                attr["scoring_rule_parsed"] = parse_scoring_rule(scoring_rule)

            # Add detection method from source_row
            if "source_row" in attr and "How to Collect (API/Scrape)" in attr["source_row"]:
                attr["detection_method"] = attr["source_row"]["How to Collect (API/Scrape)"]

            updated_count += 1
            print(f"  ✓ Enabled: {attr['label']} [{attr['dimension']}]")
        else:
            # Disable non-selected attributes
            attr["enabled"] = False
            # Still add dimension for future use
            if "source_row" in attr and "Unified Dimension" in attr["source_row"]:
                attr["dimension"] = attr["source_row"]["Unified Dimension"].lower()

    print(f"\nUpdated {updated_count} attributes")
    print(f"Enabled: {sum(1 for a in rubric['attributes'] if a.get('enabled'))}")
    print(f"Disabled: {sum(1 for a in rubric['attributes'] if not a.get('enabled'))}")

    # Validate distribution
    dimension_counts = {}
    for attr in rubric["attributes"]:
        if attr.get("enabled"):
            dim = attr.get("dimension", "unknown")
            dimension_counts[dim] = dimension_counts.get(dim, 0) + 1

    print("\nDimension distribution:")
    for dim, count in sorted(dimension_counts.items()):
        print(f"  {dim}: {count} attributes")

    # Write updated rubric
    print(f"\nWriting updated rubric to {RUBRIC_PATH}...")
    with open(RUBRIC_PATH, "w", encoding="utf-8") as f:
        json.dump(rubric, f, indent=2, ensure_ascii=False)

    print("✓ Done!")

if __name__ == "__main__":
    main()
