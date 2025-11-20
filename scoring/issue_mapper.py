"""
Issue mapper for LLM + Attribute Detector integration
Maps LLM-identified issue types to Trust Stack attribute IDs
"""

# Map LLM issue types to attribute detector IDs
LLM_TO_ATTRIBUTE_MAP = {
    # Transparency issues
    "missing_privacy_policy": "privacy_policy_link_availability_clarity",
    "no_ai_disclosure": "ai_generated_assisted_disclosure_present",
    "missing_data_citations": "data_source_citations_for_claims",
    "hidden_sponsored_content": "ad_sponsored_label_consistency",
    
    # Provenance issues
    "unclear_authorship": "author_brand_identity_verified",
    "missing_metadata": "metadata_completeness",
    "no_schema_markup": "schema_compliance",
    
    # Verification issues
    "unverified_claims": "claim_to_source_traceability",
    "fake_engagement": "engagement_authenticity_ratio",
    "unlabeled_ads": "ad_sponsored_label_consistency",
    
    # Coherence issues
    "inconsistent_voice": "brand_voice_consistency_score",
    "broken_links": "broken_link_rate",
    "contradictory_claims": "claim_consistency_across_pages",
    
    # Resonance issues
    "poor_readability": "readability_grade_level_fit",
    "inappropriate_tone": "tone_sentiment_appropriateness",
}

# Reverse mapping: attribute ID to common LLM issue type
ATTRIBUTE_TO_LLM_MAP = {v: k for k, v in LLM_TO_ATTRIBUTE_MAP.items()}


def map_llm_issue_to_attribute(llm_issue_type: str) -> str:
    """
    Map an LLM issue type to an attribute ID
    
    Args:
        llm_issue_type: Issue type from LLM (e.g., "missing_privacy_policy")
    
    Returns:
        Attribute ID (e.g., "privacy_policy_link_availability_clarity")
        Returns None if no mapping exists
    """
    return LLM_TO_ATTRIBUTE_MAP.get(llm_issue_type)


def map_attribute_to_llm_issue(attribute_id: str) -> str:
    """
    Map an attribute ID to an LLM issue type
    
    Args:
        attribute_id: Attribute ID (e.g., "privacy_policy_link_availability_clarity")
    
    Returns:
        LLM issue type (e.g., "missing_privacy_policy")
        Returns None if no mapping exists
    """
    return ATTRIBUTE_TO_LLM_MAP.get(attribute_id)
