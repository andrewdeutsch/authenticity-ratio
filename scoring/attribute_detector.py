"""
Trust Stack Attribute Detector
Detects 36 Trust Stack attributes from normalized content metadata
"""
import json
import re
from typing import List, Dict, Optional
from urllib.parse import urlparse
import logging

from data.models import NormalizedContent, DetectedAttribute

logger = logging.getLogger(__name__)


class TrustStackAttributeDetector:
    """Detects Trust Stack attributes from content metadata"""

    def __init__(self, rubric_path: str = "config/rubric.json"):
        """
        Initialize detector with rubric configuration

        Args:
            rubric_path: Path to rubric.json containing attribute definitions
        """
        with open(rubric_path, "r", encoding="utf-8") as f:
            self.rubric = json.load(f)

        # Load only enabled attributes
        self.attributes = {
            attr["id"]: attr
            for attr in self.rubric["attributes"]
            if attr.get("enabled", False)
        }

        logger.info(f"Loaded {len(self.attributes)} enabled Trust Stack attributes")

    def detect_attributes(self, content: NormalizedContent) -> List[DetectedAttribute]:
        """
        Detect all applicable Trust Stack attributes from content

        Args:
            content: Normalized content to analyze

        Returns:
            List of detected attributes with values 1-10
        """
        detected = []

        # Dispatch to specific detection methods
        detection_methods = {
            # Provenance
            "ai_vs_human_labeling_clarity": self._detect_ai_human_labeling,
            "author_brand_identity_verified": self._detect_author_verified,
            "c2pa_cai_manifest_present": self._detect_c2pa_manifest,
            "canonical_url_matches_declared_source": self._detect_canonical_url,
            "digital_watermark_fingerprint_detected": self._detect_watermark,
            "exif_metadata_integrity": self._detect_exif_integrity,
            "source_domain_trust_baseline": self._detect_domain_trust,

            # Resonance
            "community_alignment_index": self._detect_community_alignment,
            "creative_recency_vs_trend": self._detect_trend_alignment,
            "cultural_context_alignment": self._detect_cultural_context,
            "language_locale_match": self._detect_language_match,
            "personalization_relevance_embedding_similarity": self._detect_personalization,
            "readability_grade_level_fit": self._detect_readability,
            "tone_sentiment_appropriateness": self._detect_tone_sentiment,

            # Coherence
            "brand_voice_consistency_score": self._detect_brand_voice,
            "broken_link_rate": self._detect_broken_links,
            "claim_consistency_across_pages": self._detect_claim_consistency,
            "email_asset_consistency_check": self._detect_email_consistency,
            "engagement_to_trust_correlation": self._detect_engagement_trust,
            "multimodal_consistency_score": self._detect_multimodal_consistency,
            "temporal_continuity_versions": self._detect_temporal_continuity,
            "trust_fluctuation_index": self._detect_trust_fluctuation,

            # Transparency
            "ai_explainability_disclosure": self._detect_ai_explainability,
            "ai_generated_assisted_disclosure_present": self._detect_ai_disclosure,
            "bot_disclosure_response_audit": self._detect_bot_disclosure,
            "caption_subtitle_availability_accuracy": self._detect_captions,
            "data_source_citations_for_claims": self._detect_citations,
            "privacy_policy_link_availability_clarity": self._detect_privacy_policy,

            # Verification
            "ad_sponsored_label_consistency": self._detect_ad_labels,
            "agent_safety_guardrail_presence": self._detect_safety_guardrails,
            "claim_to_source_traceability": self._detect_claim_traceability,
            "engagement_authenticity_ratio": self._detect_engagement_authenticity,
            "influencer_partner_identity_verified": self._detect_influencer_verified,
            "review_authenticity_confidence": self._detect_review_authenticity,
            "seller_product_verification_rate": self._detect_seller_verification,
            "verified_purchaser_review_rate": self._detect_verified_purchaser,

            # 
            "schema_compliance": self._detect_schema_compliance,
            "metadata_completeness": self._detect_metadata_completeness,
            "llm_retrievability": self._detect_llm_retrievability,
            "canonical_linking": self._detect_canonical_linking,
            "indexing_visibility": self._detect_indexing_visibility,
            "ethical_training_signals": self._detect_ethical_training_signals,
        }

        for attr_id, detection_func in detection_methods.items():
            if attr_id in self.attributes:
                try:
                    result = detection_func(content)
                    if result:
                        detected.append(result)
                except Exception as e:
                    logger.warning(f"Error detecting {attr_id}: {e}")

        return detected

    # ===== PROVENANCE DETECTORS =====

    def _detect_ai_human_labeling(self, content: NormalizedContent) -> Optional[DetectedAttribute]:
        """Detect AI vs human labeling clarity"""
        text = (content.body + " " + content.title).lower()
        meta = content.meta or {}

        # Check for explicit AI labels
        ai_labels = ["ai-generated", "ai generated", "artificial intelligence", "generated by ai"]
        human_labels = ["human-created", "human created", "written by", "authored by"]

        has_ai_label = any(label in text for label in ai_labels)
        has_human_label = any(label in text for label in human_labels)

        # Check metadata
        has_meta_label = any(key in meta for key in ["ai_generated", "human_created", "author_type"])

        if has_ai_label or has_human_label or has_meta_label:
            return DetectedAttribute(
                attribute_id="ai_vs_human_labeling_clarity",
                dimension="provenance",
                label="AI vs Human Labeling Clarity",
                value=10.0,
                evidence="Clear labeling found in content or metadata",
                confidence=1.0
            )
        else:
            return DetectedAttribute(
                attribute_id="ai_vs_human_labeling_clarity",
                dimension="provenance",
                label="AI vs Human Labeling Clarity",
                value=1.0,
                evidence="No labeling found",
                confidence=1.0
            )

    def _detect_author_verified(self, content: NormalizedContent) -> Optional[DetectedAttribute]:
        """
        Detect author/brand identity verification with content-type awareness.

        Blog posts and articles warrant visible bylines, but corporate landing pages
        showing organizational/team attribution through structured data or subtle
        footer credits can still pass the Author Identity check.
        """
        meta = content.meta or {}

        # Determine content type
        content_type = self._determine_content_type(content)

        # Check for explicit verification (highest confidence)
        is_explicitly_verified = (
            meta.get("author_verified") == "true" or
            meta.get("verified") == "true" or
            "verified" in content.author.lower()
        )

        if is_explicitly_verified:
            return DetectedAttribute(
                attribute_id="author_brand_identity_verified",
                dimension="provenance",
                label="Author/brand identity verified",
                value=10.0,
                evidence=f"Verified author: {content.author}",
                confidence=1.0
            )

        # Check for visible byline (expected for blog/article content)
        has_visible_byline = content.author and content.author.lower() not in ['unknown', 'anonymous', '']

        # For blog/article content, require visible byline
        if content_type in ['blog', 'article', 'news']:
            if has_visible_byline:
                return DetectedAttribute(
                    attribute_id="author_brand_identity_verified",
                    dimension="provenance",
                    label="Author/brand identity verified",
                    value=8.0,
                    evidence=f"Visible byline present: {content.author}",
                    confidence=0.9
                )
            else:
                # If no visible byline for blog/article/news, check for structured
                # attribution (schema.org, meta tags, footer credits). Some pages
                # embed author/publisher data in JSON-LD where the author may be
                # a simple string; consult alternative attribution before
                # failing the byline requirement.
                attribution_result = self._check_alternative_attribution(content, meta)

                if attribution_result['found']:
                    # Use the attribution score (schema author/publisher or meta tag)
                    return DetectedAttribute(
                        attribute_id="author_brand_identity_verified",
                        dimension="provenance",
                        label="Author/brand identity verified",
                        value=attribution_result['score'],
                        evidence=attribution_result['evidence'],
                        confidence=attribution_result['confidence']
                    )
                else:
                    return DetectedAttribute(
                        attribute_id="author_brand_identity_verified",
                        dimension="provenance",
                        label="Author/brand identity verified",
                        value=2.0,
                        evidence="Missing byline - expected for blog/article content",
                        confidence=1.0
                    )

        # For corporate landing pages, check alternative attribution methods
        elif content_type == 'landing_page':
            attribution_result = self._check_alternative_attribution(content, meta)

            if attribution_result['found']:
                return DetectedAttribute(
                    attribute_id="author_brand_identity_verified",
                    dimension="provenance",
                    label="Author/brand identity verified",
                    value=attribution_result['score'],
                    evidence=attribution_result['evidence'],
                    confidence=attribution_result['confidence']
                )
            else:
                return DetectedAttribute(
                    attribute_id="author_brand_identity_verified",
                    dimension="provenance",
                    label="Author/brand identity verified",
                    value=3.0,
                    evidence="No attribution found - consider adding structured data or footer credits",
                    confidence=0.8
                )

        # For other content types, check both approaches
        else:
            if has_visible_byline:
                return DetectedAttribute(
                    attribute_id="author_brand_identity_verified",
                    dimension="provenance",
                    label="Author/brand identity verified",
                    value=7.0,
                    evidence=f"Author attribution present: {content.author}",
                    confidence=0.85
                )
            else:
                attribution_result = self._check_alternative_attribution(content, meta)
                if attribution_result['found']:
                    return DetectedAttribute(
                        attribute_id="author_brand_identity_verified",
                        dimension="provenance",
                        label="Author/brand identity verified",
                        value=attribution_result['score'],
                        evidence=attribution_result['evidence'],
                        confidence=attribution_result['confidence']
                    )
                else:
                    return DetectedAttribute(
                        attribute_id="author_brand_identity_verified",
                        dimension="provenance",
                        label="Author/brand identity verified",
                        value=3.0,
                        evidence="Author verification status unknown",
                        confidence=0.8
                    )

    def _determine_content_type(self, content: NormalizedContent) -> str:
        """
        Determine content type based on channel, URL patterns, and metadata.

        Returns:
            Content type: 'blog', 'article', 'news', 'landing_page', 'other'
        """
        url_lower = content.url.lower()

        # Check for blog/article/news patterns in URL
        blog_patterns = ['/blog/', '/article/', '/post/', '/news/', '/story/']
        if any(pattern in url_lower for pattern in blog_patterns):
            if '/blog/' in url_lower:
                return 'blog'
            elif '/news/' in url_lower or '/story/' in url_lower:
                return 'news'
            else:
                return 'article'

        # Check for landing page patterns
        landing_patterns = [
            url_lower.endswith('/'),  # Root or section homepage
            '/product/' in url_lower,
            '/solution/' in url_lower,
            '/service/' in url_lower,
            '/about' in url_lower,
            '/home' in url_lower
        ]
        if any(landing_patterns):
            return 'landing_page'

        # Check metadata for content type hints
        meta = content.meta or {}
        meta_type = meta.get('type', '').lower()
        if meta_type in ['article', 'blog', 'news', 'blogposting', 'newsarticle']:
            return meta_type

        # Check schema.org data
        schema_org = meta.get('schema_org')
        if schema_org:
            try:
                import json
                schema_data = json.loads(schema_org) if isinstance(schema_org, str) else schema_org
                if isinstance(schema_data, dict):
                    schema_type = schema_data.get('@type', '')
                    if isinstance(schema_type, str):
                        if 'Article' in schema_type or 'BlogPosting' in schema_type:
                            return 'blog' if 'Blog' in schema_type else 'article'
                        elif 'NewsArticle' in schema_type:
                            return 'news'
                        elif 'WebPage' in schema_type or 'Organization' in schema_type:
                            return 'landing_page'
            except:
                pass

        # Default based on channel
        if content.channel in ['reddit', 'twitter', 'facebook', 'instagram']:
            return 'social_post'
        elif content.channel in ['youtube', 'tiktok']:
            return 'video'

        return 'other'

    def _check_alternative_attribution(self, content: NormalizedContent, meta: Dict) -> Dict[str, any]:
        """
        Check for alternative attribution methods suitable for corporate landing pages.

        Looks for:
        - Structured data (schema.org author/contributor/publisher)
        - Meta author tags
        - Footer attribution indicators
        - About/credits page links

        Returns:
            Dict with keys: found (bool), score (float), evidence (str), confidence (float)
        """
        attribution_methods = []

        # Check schema.org structured data
        schema_org = meta.get('schema_org')
        if schema_org:
            try:
                import json
                schema_data = json.loads(schema_org) if isinstance(schema_org, str) else schema_org

                # Handle both single object and list of objects
                schema_list = schema_data if isinstance(schema_data, list) else [schema_data]

                for schema_item in schema_list:
                    if not isinstance(schema_item, dict):
                        continue

                    # Check for author
                    if 'author' in schema_item:
                        author = schema_item['author']
                        if isinstance(author, dict):
                            author_name = author.get('name', '')
                        else:
                            author_name = str(author)
                        if author_name:
                            attribution_methods.append(f"Schema.org author: {author_name}")

                    # Check for contributor
                    if 'contributor' in schema_item:
                        contributor = schema_item['contributor']
                        if isinstance(contributor, dict):
                            contrib_name = contributor.get('name', '')
                        else:
                            contrib_name = str(contributor)
                        if contrib_name:
                            attribution_methods.append(f"Schema.org contributor: {contrib_name}")

                    # Check for publisher
                    if 'publisher' in schema_item:
                        publisher = schema_item['publisher']
                        if isinstance(publisher, dict):
                            pub_name = publisher.get('name', '')
                        else:
                            pub_name = str(publisher)
                        if pub_name:
                            attribution_methods.append(f"Schema.org publisher: {pub_name}")
            except:
                pass

        # Check meta author tag
        meta_author = meta.get('author')
        if meta_author and meta_author.lower() not in ['unknown', 'anonymous', '']:
            attribution_methods.append(f"Meta author tag: {meta_author}")

        # Check for footer attribution indicators in meta
        footer_indicators = ['maintained_by', 'content_by', 'team', 'department']
        for indicator in footer_indicators:
            if indicator in meta and meta[indicator]:
                attribution_methods.append(f"Footer attribution: {meta[indicator]}")

        # Check for about/credits page links in meta
        about_links = ['about_url', 'credits_url', 'team_url']
        for link_key in about_links:
            if link_key in meta and meta[link_key]:
                attribution_methods.append(f"Credits page available: {meta[link_key]}")

        # Determine score based on attribution methods found
        if not attribution_methods:
            return {
                'found': False,
                'score': 3.0,
                'evidence': '',
                'confidence': 0.8
            }

        # Score based on type and quantity of attribution
        if any('Schema.org author:' in method for method in attribution_methods):
            score = 8.0
            confidence = 0.95
        elif any('Meta author tag:' in method for method in attribution_methods):
            score = 7.0
            confidence = 0.9
        elif any('Schema.org publisher:' in method or 'Schema.org contributor:' in method for method in attribution_methods):
            score = 7.0
            confidence = 0.9
        elif any('Footer attribution:' in method for method in attribution_methods):
            score = 6.0
            confidence = 0.85
        elif any('Credits page' in method for method in attribution_methods):
            score = 6.0
            confidence = 0.8
        else:
            score = 5.0
            confidence = 0.75

        evidence = "Alternative attribution found: " + "; ".join(attribution_methods[:2])  # Limit evidence length

        return {
            'found': True,
            'score': score,
            'evidence': evidence,
            'confidence': confidence
        }

    def _detect_c2pa_manifest(self, content: NormalizedContent) -> Optional[DetectedAttribute]:
        """Detect C2PA/CAI manifest presence"""
        meta = content.meta or {}

        has_c2pa = any(key in meta for key in ["c2pa_manifest", "cai_manifest", "content_credentials"])

        if has_c2pa:
            is_valid = meta.get("c2pa_valid") != "false"
            value = 10.0 if is_valid else 5.0
            evidence = "C2PA manifest present and valid" if is_valid else "C2PA manifest present but invalid"
            return DetectedAttribute(
                attribute_id="c2pa_cai_manifest_present",
                dimension="provenance",
                label="C2PA/CAI manifest present",
                value=value,
                evidence=evidence,
                confidence=1.0
            )
        else:
            return DetectedAttribute(
                attribute_id="c2pa_cai_manifest_present",
                dimension="provenance",
                label="C2PA/CAI manifest present",
                value=1.0,
                evidence="No C2PA manifest found",
                confidence=1.0
            )

    def _detect_canonical_url(self, content: NormalizedContent) -> Optional[DetectedAttribute]:
        """Detect canonical URL match"""
        meta = content.meta or {}
        canonical_url = meta.get("canonical_url", "")

        if not canonical_url:
            return None  # Can't determine without canonical URL

        # Parse both URLs
        try:
            canonical_domain = urlparse(canonical_url).netloc
            source_domain = urlparse(meta.get("url", "")).netloc

            if canonical_domain == source_domain:
                value = 10.0
                evidence = "Canonical URL matches source domain"
            elif canonical_domain in source_domain or source_domain in canonical_domain:
                value = 5.0
                evidence = "Partial canonical URL match"
            else:
                value = 1.0
                evidence = "Canonical URL mismatch"

            return DetectedAttribute(
                attribute_id="canonical_url_matches_declared_source",
                dimension="provenance",
                label="Canonical URL matches declared source",
                value=value,
                evidence=evidence,
                confidence=1.0
            )
        except Exception:
            return None

    def _detect_watermark(self, content: NormalizedContent) -> Optional[DetectedAttribute]:
        """Detect digital watermark/fingerprint"""
        meta = content.meta or {}

        has_watermark = any(key in meta for key in ["watermark", "fingerprint", "digital_signature"])

        if has_watermark:
            return DetectedAttribute(
                attribute_id="digital_watermark_fingerprint_detected",
                dimension="provenance",
                label="Digital watermark/fingerprint detected",
                value=10.0,
                evidence="Watermark detected in metadata",
                confidence=1.0
            )
        return None  # Only report if found

    def _detect_exif_integrity(self, content: NormalizedContent) -> Optional[DetectedAttribute]:
        """Detect EXIF/metadata integrity"""
        meta = content.meta or {}

        if "exif_data" in meta:
            exif_status = meta.get("exif_status", "intact")

            if exif_status == "intact":
                value = 10.0
                evidence = "EXIF metadata intact"
            elif exif_status == "stripped":
                value = 5.0
                evidence = "EXIF metadata stripped"
            else:  # spoofed
                value = 1.0
                evidence = "EXIF metadata spoofed"

            return DetectedAttribute(
                attribute_id="exif_metadata_integrity",
                dimension="provenance",
                label="EXIF/metadata integrity",
                value=value,
                evidence=evidence,
                confidence=1.0
            )
        return None

    def _detect_domain_trust(self, content: NormalizedContent) -> Optional[DetectedAttribute]:
        """Detect source domain trust baseline"""
        meta = content.meta or {}

        # Simple domain reputation based on source
        domain = meta.get("domain", "")
        source = content.src.lower()

        # Trusted platforms get higher scores
        trusted_sources = {
            "reddit": 7.0,
            "youtube": 7.0,
            "amazon": 8.0,
        }

        # Known high-trust domains
        trusted_domains = [
            ".gov", ".edu", ".org",
            "nytimes.com", "wsj.com", "bbc.com", "reuters.com"
        ]

        if source in trusted_sources:
            value = trusted_sources[source]
            evidence = f"Trusted platform: {source}"
        elif any(domain.endswith(td) for td in trusted_domains):
            value = 9.0
            evidence = f"High-trust domain: {domain}"
        else:
            value = 5.0  # Neutral
            evidence = f"Domain: {domain}"

        return DetectedAttribute(
            attribute_id="source_domain_trust_baseline",
            dimension="provenance",
            label="Source domain trust baseline",
            value=value,
            evidence=evidence,
            confidence=0.8
        )

    # ===== RESONANCE DETECTORS =====

    def _detect_community_alignment(self, content: NormalizedContent) -> Optional[DetectedAttribute]:
        """Detect community alignment index (placeholder)"""
        # TODO: Implement hashtag/mention graph analysis
        return None

    def _detect_trend_alignment(self, content: NormalizedContent) -> Optional[DetectedAttribute]:
        """Detect creative recency vs trend (placeholder)"""
        # TODO: Implement trend API integration
        return None

    def _detect_cultural_context(self, content: NormalizedContent) -> Optional[DetectedAttribute]:
        """Detect cultural context alignment (placeholder)"""
        # TODO: Implement NER + cultural knowledge base
        return None

    def _detect_language_match(self, content: NormalizedContent) -> Optional[DetectedAttribute]:
        """Detect language/locale match"""
        meta = content.meta or {}
        detected_lang = meta.get("language", "en")

        # Assume English is target for now
        target_lang = "en"

        if detected_lang == target_lang:
            value = 10.0
            evidence = f"Language match: {detected_lang}"
        else:
            value = 1.0
            evidence = f"Language mismatch: {detected_lang} (expected: {target_lang})"

        return DetectedAttribute(
            attribute_id="language_locale_match",
            dimension="resonance",
            label="Language/locale match",
            value=value,
            evidence=evidence,
            confidence=0.9
        )

    def _detect_personalization(self, content: NormalizedContent) -> Optional[DetectedAttribute]:
        """Detect personalization relevance (placeholder)"""
        # TODO: Implement embedding similarity
        return None

    def _detect_readability(self, content: NormalizedContent) -> Optional[DetectedAttribute]:
        """Detect readability grade level fit"""
        text = content.body

        # Simple readability heuristic (words per sentence)
        if not text or len(text) < 50:
            return None

        # Split into sentences using positive lookbehind (split after punctuation + whitespace)
        # This avoids the off-by-one error from re.split()
        sentence_list = re.split(r'(?<=[\.\!\?])\s+', text)
        # Filter out very short fragments (< 10 chars) that aren't real sentences
        sentence_list = [s.strip() for s in sentence_list if len(s.strip()) > 10]

        if len(sentence_list) == 0:
            return None

        words = len(text.split())
        words_per_sentence = words / len(sentence_list)

        # Target: 15-20 words per sentence (grade 8-10)
        if 12 <= words_per_sentence <= 22:
            value = 10.0
            evidence = f"Readable: {words_per_sentence:.1f} words/sentence"
        elif 8 <= words_per_sentence <= 30:
            value = 7.0
            evidence = f"Acceptable: {words_per_sentence:.1f} words/sentence"
        else:
            value = 4.0
            evidence = f"Difficult: {words_per_sentence:.1f} words/sentence"

        return DetectedAttribute(
            attribute_id="readability_grade_level_fit",
            dimension="resonance",
            label="Readability grade level fit",
            value=value,
            evidence=evidence,
            confidence=0.7
        )

    def _detect_tone_sentiment(self, content: NormalizedContent) -> Optional[DetectedAttribute]:
        """Detect tone & sentiment appropriateness (placeholder)"""
        # TODO: Integrate sentiment analysis model
        return None

    # ===== COHERENCE DETECTORS =====

    def _detect_brand_voice(self, content: NormalizedContent) -> Optional[DetectedAttribute]:
        """Detect brand voice consistency (placeholder)"""
        # TODO: Implement embedding similarity to brand corpus
        return None

    def _detect_broken_links(self, content: NormalizedContent) -> Optional[DetectedAttribute]:
        """Detect broken link rate"""
        text = content.body + " " + content.title

        # Find URLs in text
        urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', text)

        if not urls:
            return None  # No links to check

        # Check metadata for broken link info
        meta = content.meta or {}
        broken_count = int(meta.get("broken_links", 0))
        total_count = len(urls)

        if broken_count == 0:
            value = 10.0
            evidence = f"No broken links ({total_count} total)"
        else:
            broken_rate = broken_count / total_count
            if broken_rate < 0.01:
                value = 10.0
            elif broken_rate < 0.05:
                value = 7.0
            elif broken_rate < 0.10:
                value = 4.0
            else:
                value = 1.0
            evidence = f"{broken_count}/{total_count} broken links ({broken_rate:.1%})"

        return DetectedAttribute(
            attribute_id="broken_link_rate",
            dimension="coherence",
            label="Broken link rate",
            value=value,
            evidence=evidence,
            confidence=0.8
        )

    def _detect_claim_consistency(self, content: NormalizedContent) -> Optional[DetectedAttribute]:
        """Detect claim consistency across pages (placeholder)"""
        # TODO: Implement NLI/contradiction detection
        return None

    def _detect_email_consistency(self, content: NormalizedContent) -> Optional[DetectedAttribute]:
        """Detect email-asset consistency (placeholder)"""
        # TODO: Implement cross-channel comparison
        return None

    def _detect_engagement_trust(self, content: NormalizedContent) -> Optional[DetectedAttribute]:
        """Detect engagement-to-trust correlation"""
        # Skip detection for content types where engagement metrics aren't applicable
        if not self._should_have_engagement_metrics(content):
            return None

        # Use engagement metrics as proxy
        upvotes = content.upvotes or 0
        rating = content.rating or 0.0

        # High engagement + high rating = high trust
        if upvotes > 50 and rating > 4.0:
            value = 10.0
            evidence = f"High engagement ({upvotes} upvotes, {rating:.1f} rating)"
        elif upvotes > 10 and rating > 3.0:
            value = 7.0
            evidence = f"Moderate engagement ({upvotes} upvotes, {rating:.1f} rating)"
        else:
            value = 5.0
            evidence = f"Low engagement ({upvotes} upvotes, {rating:.1f} rating)"

        return DetectedAttribute(
            attribute_id="engagement_to_trust_correlation",
            dimension="coherence",
            label="Engagement-to-Trust Correlation",
            value=value,
            evidence=evidence,
            confidence=0.6
        )

    def _should_have_engagement_metrics(self, content: NormalizedContent) -> bool:
        """
        Determine if engagement metrics (upvotes, ratings) are expected for this content type.

        Returns False for:
        - Job boards and career sites
        - Corporate websites and landing pages
        - Documentation and knowledge bases
        - News sites (unless they have commenting systems)
        - Government and educational sites
        - Static informational pages

        Returns True for:
        - Social media platforms (reddit, youtube, instagram, tiktok)
        - Marketplaces with reviews (amazon, etsy, yelp)
        - Community forums and discussion boards
        - Review platforms
        """
        # Social platforms and marketplaces always have engagement features
        engagement_channels = {'reddit', 'youtube', 'amazon', 'instagram', 'tiktok',
                              'facebook', 'twitter', 'yelp', 'tripadvisor', 'etsy'}
        if content.channel.lower() in engagement_channels:
            return True

        # Platform types that typically have engagement
        if content.platform_type.lower() in {'social', 'marketplace'}:
            return True

        # Check URL patterns for non-engagement sites
        url_lower = content.url.lower()

        # Job boards and career sites
        job_patterns = ['careers.', 'jobs.', '/careers/', '/jobs/', 'apply.',
                       'greenhouse.io', 'lever.co', 'workday.com', 'taleo.net',
                       'jobvite.com', 'indeed.com', 'linkedin.com/jobs']
        if any(pattern in url_lower for pattern in job_patterns):
            return False

        # Corporate landing pages and marketing sites
        if content.platform_type.lower() == 'owned' and content.source_type.lower() == 'brand_owned':
            # Brand-owned content typically doesn't have engagement features
            # unless it's explicitly a community or review section
            if not any(keyword in url_lower for keyword in ['/reviews/', '/community/', '/forum/', '/comments/']):
                return False

        # Documentation and knowledge bases
        doc_patterns = ['docs.', '/docs/', '/documentation/', 'developer.', '/api/',
                       'help.', '/help/', 'support.', '/kb/', 'wiki.']
        if any(pattern in url_lower for pattern in doc_patterns):
            return False

        # Government and educational sites (typically informational)
        if any(domain in url_lower for domain in ['.gov', '.edu', '.mil']):
            return False

        # Default to True if we can't determine - let the metric run
        # This is conservative: we'd rather have false positives than miss real engagement issues
        return True

    def _detect_multimodal_consistency(self, content: NormalizedContent) -> Optional[DetectedAttribute]:
        """Detect multimodal consistency (placeholder)"""
        # TODO: Implement caption vs transcript comparison
        return None

    def _detect_temporal_continuity(self, content: NormalizedContent) -> Optional[DetectedAttribute]:
        """Detect temporal continuity (placeholder)"""
        # TODO: Check version history metadata
        return None

    def _detect_trust_fluctuation(self, content: NormalizedContent) -> Optional[DetectedAttribute]:
        """Detect trust fluctuation index (placeholder)"""
        # TODO: Implement time-series sentiment analysis
        return None

    # ===== TRANSPARENCY DETECTORS =====

    def _detect_ai_explainability(self, content: NormalizedContent) -> Optional[DetectedAttribute]:
        """Detect AI explainability disclosure"""
        text = (content.body + " " + content.title).lower()

        explainability_phrases = [
            "why you're seeing this",
            "powered by",
            "how this works",
            "algorithm",
            "recommendation"
        ]

        has_explainability = any(phrase in text for phrase in explainability_phrases)

        if has_explainability:
            return DetectedAttribute(
                attribute_id="ai_explainability_disclosure",
                dimension="transparency",
                label="AI Explainability Disclosure",
                value=10.0,
                evidence="Explainability disclosure found",
                confidence=1.0
            )
        else:
            return DetectedAttribute(
                attribute_id="ai_explainability_disclosure",
                dimension="transparency",
                label="AI Explainability Disclosure",
                value=1.0,
                evidence="No explainability disclosure",
                confidence=1.0
            )

    def _detect_ai_disclosure(self, content: NormalizedContent) -> Optional[DetectedAttribute]:
        """Detect AI-generated/assisted disclosure"""
        text = (content.body + " " + content.title).lower()
        meta = content.meta or {}

        ai_disclosure_phrases = [
            "ai-generated", "ai generated",
            "ai-assisted", "ai assisted",
            "generated by ai",
            "created with ai"
        ]

        has_disclosure = (
            any(phrase in text for phrase in ai_disclosure_phrases) or
            meta.get("ai_generated") == "true"
        )

        if has_disclosure:
            return DetectedAttribute(
                attribute_id="ai_generated_assisted_disclosure_present",
                dimension="transparency",
                label="AI-generated/assisted disclosure present",
                value=10.0,
                evidence="AI disclosure present",
                confidence=1.0
            )
        else:
            return DetectedAttribute(
                attribute_id="ai_generated_assisted_disclosure_present",
                dimension="transparency",
                label="AI-generated/assisted disclosure present",
                value=1.0,
                evidence="No AI disclosure",
                confidence=1.0
            )

    def _detect_bot_disclosure(self, content: NormalizedContent) -> Optional[DetectedAttribute]:
        """Detect bot disclosure (placeholder)"""
        # TODO: Check for bot self-identification
        return None

    def _detect_captions(self, content: NormalizedContent) -> Optional[DetectedAttribute]:
        """Detect caption/subtitle availability"""
        meta = content.meta or {}

        # Only applicable to video content
        if content.src != "youtube":
            return None

        has_captions = meta.get("has_captions") == "true"

        if has_captions:
            return DetectedAttribute(
                attribute_id="caption_subtitle_availability_accuracy",
                dimension="transparency",
                label="Caption/Subtitle Availability & Accuracy",
                value=10.0,
                evidence="Captions available",
                confidence=1.0
            )
        else:
            return DetectedAttribute(
                attribute_id="caption_subtitle_availability_accuracy",
                dimension="transparency",
                label="Caption/Subtitle Availability & Accuracy",
                value=1.0,
                evidence="No captions found",
                confidence=1.0
            )

    def _detect_citations(self, content: NormalizedContent) -> Optional[DetectedAttribute]:
        """Detect data source citations"""
        text = content.body

        # Look for citation patterns
        citation_patterns = [
            r'\[\d+\]',  # [1], [2], etc.
            r'\(\w+,? \d{4}\)',  # (Author, 2024)
            r'according to',
            r'source:',
            r'cited by'
        ]

        has_citations = any(re.search(pattern, text, re.IGNORECASE) for pattern in citation_patterns)

        if has_citations:
            return DetectedAttribute(
                attribute_id="data_source_citations_for_claims",
                dimension="transparency",
                label="Data source citations for claims",
                value=10.0,
                evidence="Citations found in text",
                confidence=0.8
            )
        else:
            return DetectedAttribute(
                attribute_id="data_source_citations_for_claims",
                dimension="transparency",
                label="Data source citations for claims",
                value=1.0,
                evidence="No citations found",
                confidence=0.8
            )

    def _detect_privacy_policy(self, content: NormalizedContent) -> Optional[DetectedAttribute]:
        """Detect privacy policy link"""
        text = (content.body + " " + content.title).lower()

        has_privacy_link = "privacy policy" in text or "privacy" in text

        if has_privacy_link:
            return DetectedAttribute(
                attribute_id="privacy_policy_link_availability_clarity",
                dimension="transparency",
                label="Privacy policy link availability & clarity",
                value=10.0,
                evidence="Privacy policy reference found",
                confidence=0.7
            )
        return None

    # ===== VERIFICATION DETECTORS =====

    def _detect_ad_labels(self, content: NormalizedContent) -> Optional[DetectedAttribute]:
        """Detect ad/sponsored label consistency"""
        text = (content.body + " " + content.title).lower()
        meta = content.meta or {}

        ad_labels = ["sponsored", "advertisement", "ad", "promoted", "paid partnership"]

        has_ad_label = (
            any(label in text for label in ad_labels) or
            meta.get("is_sponsored") == "true"
        )

        if has_ad_label:
            return DetectedAttribute(
                attribute_id="ad_sponsored_label_consistency",
                dimension="verification",
                label="Ad/Sponsored Label Consistency",
                value=10.0,
                evidence="Ad/sponsored label present",
                confidence=1.0
            )
        return None  # Only report if present

    def _detect_safety_guardrails(self, content: NormalizedContent) -> Optional[DetectedAttribute]:
        """Detect agent safety guardrails (placeholder)"""
        # TODO: Check for safety features in bot responses
        return None

    def _detect_claim_traceability(self, content: NormalizedContent) -> Optional[DetectedAttribute]:
        """Detect claim-to-source traceability (placeholder)"""
        # TODO: Implement claim linking
        return None

    def _detect_engagement_authenticity(self, content: NormalizedContent) -> Optional[DetectedAttribute]:
        """Detect engagement authenticity ratio"""

        # Determine content type to check if engagement is expected
        content_type = self._determine_content_type(content)

        # Skip engagement detection for landing pages and promotional pages
        # where user engagement (upvotes, helpful counts) is not expected
        if content_type == 'landing_page':
            return None

        # Only apply engagement scoring to content types where it's meaningful
        # (blog, article, news, social_post)
        if content_type not in ['blog', 'article', 'news', 'social_post']:
            return None

        # Check for signs of authentic engagement
        upvotes = content.upvotes or 0
        helpful_count = content.helpful_count or 0

        # Simple heuristic: high engagement = likely authentic
        if upvotes > 100 or helpful_count > 10:
            value = 9.0
            evidence = f"High authentic engagement ({upvotes} upvotes, {helpful_count} helpful)"
        elif upvotes > 10:
            value = 7.0
            evidence = f"Moderate engagement ({upvotes} upvotes)"
        else:
            value = 5.0  # Neutral
            evidence = f"Low engagement ({upvotes} upvotes)"

        return DetectedAttribute(
            attribute_id="engagement_authenticity_ratio",
            dimension="verification",
            label="Engagement Authenticity Ratio",
            value=value,
            evidence=evidence,
            confidence=0.6
        )

    def _detect_influencer_verified(self, content: NormalizedContent) -> Optional[DetectedAttribute]:
        """Detect influencer/partner identity verification"""
        # Similar to author verification
        meta = content.meta or {}

        is_verified = (
            meta.get("influencer_verified") == "true" or
            meta.get("verified") == "true"
        )

        if is_verified:
            return DetectedAttribute(
                attribute_id="influencer_partner_identity_verified",
                dimension="verification",
                label="Influencer/partner identity verified",
                value=10.0,
                evidence="Verified influencer/partner",
                confidence=1.0
            )
        return None

    def _detect_review_authenticity(self, content: NormalizedContent) -> Optional[DetectedAttribute]:
        """Detect review authenticity confidence"""
        # Only applicable to reviews
        if content.src != "amazon":
            return None

        # Simple heuristic based on verified purchase + helpful votes
        meta = content.meta or {}
        is_verified = meta.get("verified_purchase") == "true"
        helpful_count = content.helpful_count or 0

        if is_verified and helpful_count > 5:
            value = 10.0
            evidence = "Verified purchase with helpful votes"
        elif is_verified:
            value = 8.0
            evidence = "Verified purchase"
        else:
            value = 5.0
            evidence = "Unverified purchase"

        return DetectedAttribute(
            attribute_id="review_authenticity_confidence",
            dimension="verification",
            label="Review Authenticity Confidence",
            value=value,
            evidence=evidence,
            confidence=0.7
        )

    def _detect_seller_verification(self, content: NormalizedContent) -> Optional[DetectedAttribute]:
        """Detect seller & product verification rate (placeholder)"""
        # TODO: Implement marketplace verification checking
        return None

    def _detect_verified_purchaser(self, content: NormalizedContent) -> Optional[DetectedAttribute]:
        """Detect verified purchaser review rate"""
        # Only applicable to Amazon reviews
        if content.src != "amazon":
            return None

        meta = content.meta or {}
        is_verified = meta.get("verified_purchase") == "true"

        if is_verified:
            return DetectedAttribute(
                attribute_id="verified_purchaser_review_rate",
                dimension="verification",
                label="Verified purchaser review rate",
                value=10.0,
                evidence="Verified purchase badge present",
                confidence=1.0
            )
        else:
            return DetectedAttribute(
                attribute_id="verified_purchaser_review_rate",
                dimension="verification",
                label="Verified purchaser review rate",
                value=3.0,
                evidence="No verified purchase badge",
                confidence=1.0
            )

    # ===== AI READINESS DETECTORS =====

    def _detect_schema_compliance(self, content: NormalizedContent) -> Optional[DetectedAttribute]:
        """Detect schema.org compliance"""
        meta = content.meta or {}

        # Check for schema.org structured data
        has_schema = any(key in meta for key in ["schema_org", "json_ld", "microdata", "rdfa"])
        schema_valid = meta.get("schema_valid") != "false"

        if has_schema and schema_valid:
            value = 10.0
            evidence = "Complete and valid schema.org markup present"
        elif has_schema:
            value = 7.0
            evidence = "Schema.org markup present but may be incomplete"
        else:
            value = 1.0
            evidence = "No schema.org structured data detected"

        return DetectedAttribute(
            label="Schema.org Compliance",
            value=value,
            evidence=evidence,
            confidence=0.9
        )

    def _detect_metadata_completeness(self, content: NormalizedContent) -> Optional[DetectedAttribute]:
        """Detect metadata completeness"""
        meta = content.meta or {}

        # Check for key metadata fields
        required_fields = ["title", "description", "author", "date", "keywords"]
        present_fields = []

        if content.title and len(content.title.strip()) > 0:
            present_fields.append("title")
        if content.body and len(content.body.strip()) > 100:  # Assume body contains description
            present_fields.append("description")
        if content.author and len(content.author.strip()) > 0:
            present_fields.append("author")
        if content.published_at:
            present_fields.append("date")
        if meta.get("keywords") or meta.get("tags"):
            present_fields.append("keywords")

        # Check OG tags
        has_og_tags = any(key.startswith("og_") for key in meta.keys())
        if has_og_tags:
            present_fields.append("og_tags")

        completeness = len(present_fields) / len(required_fields)
        value = 1.0 + (completeness * 9.0)  # Scale 1-10

        return DetectedAttribute(
            attribute_id="metadata_completeness",
            label="Metadata Completeness",
            value=value,
            evidence=f"{len(present_fields)}/{len(required_fields)} key metadata fields present",
            confidence=1.0
        )

    def _detect_llm_retrievability(self, content: NormalizedContent) -> Optional[DetectedAttribute]:
        """Detect LLM retrievability (indexability)"""
        meta = content.meta or {}

        # Check robots meta tag
        robots_content = meta.get("robots", "").lower()
        has_noindex = "noindex" in robots_content
        has_nofollow = "nofollow" in robots_content

        # Check if content is indexable
        if has_noindex:
            value = 1.0
            evidence = "Content has noindex directive - not retrievable by LLMs"
        elif has_nofollow:
            value = 5.0
            evidence = "Content has nofollow directive - limited retrievability"
        else:
            # Check if sitemap or other indexing signals exist
            has_sitemap = meta.get("in_sitemap") == "true"
            if has_sitemap:
                value = 10.0
                evidence = "Fully indexable with sitemap presence"
            else:
                value = 8.0
                evidence = "Indexable but no explicit sitemap signal"

        return DetectedAttribute(
            attribute_id="llm_retrievability",
            label="LLM Retrievability",
            value=value,
            evidence=evidence,
            confidence=0.9
        )

    def _detect_canonical_linking(self, content: NormalizedContent) -> Optional[DetectedAttribute]:
        """Detect canonical URL presence and validity"""
        meta = content.meta or {}

        canonical_url = meta.get("canonical_url") or meta.get("canonical")
        current_url = content.url

        if canonical_url:
            # Check if canonical matches current URL
            if canonical_url == current_url or canonical_url.rstrip('/') == current_url.rstrip('/'):
                value = 10.0
                evidence = "Canonical URL present and matches current URL"
            else:
                value = 5.0
                evidence = f"Canonical URL present but points elsewhere: {canonical_url}"
        else:
            value = 1.0
            evidence = "No canonical URL specified"

        return DetectedAttribute(
            attribute_id="canonical_linking",
            label="Canonical Linking",
            value=value,
            evidence=evidence,
            confidence=1.0
        )

    def _detect_indexing_visibility(self, content: NormalizedContent) -> Optional[DetectedAttribute]:
        """Detect indexing visibility (sitemap, robots.txt)"""
        meta = content.meta or {}

        has_sitemap = meta.get("has_sitemap") == "true" or meta.get("in_sitemap") == "true"
        robots_allowed = meta.get("robots_txt_allowed") != "false"
        has_noindex = "noindex" in meta.get("robots", "").lower()

        # Calculate score based on indexing signals
        if has_sitemap and robots_allowed and not has_noindex:
            value = 10.0
            evidence = "Sitemap present, robots.txt allows crawling, no noindex tag"
        elif robots_allowed and not has_noindex:
            value = 7.0
            evidence = "Indexable but no sitemap detected"
        elif has_noindex:
            value = 1.0
            evidence = "Noindex tag prevents indexing"
        else:
            value = 3.0
            evidence = "Limited indexing signals"

        return DetectedAttribute(
            attribute_id="indexing_visibility",
            label="Indexing Visibility",
            value=value,
            evidence=evidence,
            confidence=0.8
        )

    def _detect_ethical_training_signals(self, content: NormalizedContent) -> Optional[DetectedAttribute]:
        """Detect AI training opt-out/ethical signals"""
        meta = content.meta or {}

        # Check for TDM (Text and Data Mining) reservations
        has_tdm_reservation = any(key in meta for key in ["tdm_reservation", "ai_training_optout", "robots_tdm"])

        # Check robots.txt for AI crawler directives
        robots_txt = meta.get("robots_txt", "").lower()
        has_ai_directive = any(bot in robots_txt for bot in ["gptbot", "ccbot", "anthropic-ai", "claude-web"])

        if has_tdm_reservation or has_ai_directive:
            value = 10.0
            evidence = "Clear AI training opt-out or TDM reservation signals present"
        elif meta.get("copyright") or meta.get("rights"):
            value = 5.0
            evidence = "Copyright/rights metadata present (ambiguous AI training policy)"
        else:
            value = 1.0
            evidence = "No AI training policy or TDM reservation signals"

        return DetectedAttribute(
            attribute_id="ethical_training_signals",
            label="Ethical Training Signals",
            value=value,
            evidence=evidence,
            confidence=0.7
        )
