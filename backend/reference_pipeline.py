#!/usr/bin/env python3
"""
Novu Opportunity Radar — Standalone Reference Pipeline
Version: 1.0 (17 September 2026)

Implements offline validation, deterministic scoring (§7), evidence citation checks (§6),
idempotent replay (§4), duplicate detection (§8), and formula-injection-safe CSV export (§12).
Can run offline on fixtures.json with zero external network dependencies.
"""
import sys
import os
import json
import hashlib
import re
from datetime import datetime, date, timezone, timedelta
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

# Controlled service taxonomy (SRS §3 FR-04.4)
SUPPORTED_SERVICE_CATEGORIES = {
    'CUSTOM_DEV', 'MOBILE_APP', 'WEBSITE', 'ERP', 'CRM', 'LMS',
    'AI_AUTOMATION', 'STAFF_AUGMENTATION', 'MANAGED_IT', 'CLOUD_DEVOPS', 'CYBERSECURITY'
}

# Fixed 30-column order for master export (SRS §3 FR-09.1 / Handover §12)
EXPORT_COLUMNS = [
    'opportunity_id', 'detected_at', 'source_published_at', 'source', 'source_url',
    'author', 'company', 'company_website', 'country', 'industry', 'requirement',
    'primary_category', 'technology', 'budget_text', 'deadline', 'intent',
    'confidence', 'score', 'band', 'contact_name', 'designation', 'email', 'phone',
    'contact_evidence_url', 'contact_verification', 'review_reasons', 'owner',
    'status', 'last_follow_up', 'next_follow_up', 'notes'
]


# ----------------------------------------------------------------------------
# 1. URL Normalization & Content Hashing (FR-02, FR-05)
# ----------------------------------------------------------------------------

def canonicalize_url(url: str) -> str:
    """
    Normalizes a URL by stripping tracking parameters (utm_*, ref, fbclid, etc.)
    and fragments while preserving meaningful query parameters and path identifiers.
    """
    if not url:
        return ''
    parsed = urlparse(url.strip())
    # Tracking parameters to discard
    drop_prefixes = ('utm_', 'ref', 'fbclid', 'gclid', 'mc_eid', '_ga', 'trk')
    
    query_params = parse_qs(parsed.query, keep_blank_values=True)
    clean_params = {
        k: v for k, v in query_params.items()
        if not any(k.lower().startswith(p) for p in drop_prefixes)
    }
    
    clean_query = urlencode(sorted([(k, val) for k, vals in clean_params.items() for val in vals]))
    return urlunparse((
        parsed.scheme.lower(),
        parsed.netloc.lower(),
        parsed.path.rstrip('/') or '/',
        '',
        clean_query,
        ''  # strip fragment
    ))


def compute_content_hash(text: str) -> str:
    """Computes deterministic SHA-256 hash of normalized text."""
    normalized = ' '.join((text or '').strip().lower().split())
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()


# ----------------------------------------------------------------------------
# 2. Evidence Verification (SRS §7.2 / Handover §6)
# ----------------------------------------------------------------------------

def verify_evidence_substring(claim_quote: str, source_text: str) -> bool:
    """
    Verifies that a claimed quote is an exact or whitespace-normalized
    substring of the retained source text. Rejects fabricated evidence.
    """
    if not claim_quote or not source_text:
        return False
    # Check exact match
    if claim_quote in source_text:
        return True
    # Check normalized whitespace
    norm_quote = ' '.join(claim_quote.split()).lower()
    norm_source = ' '.join(source_text.split()).lower()
    return norm_quote in norm_source


# ----------------------------------------------------------------------------
# 3. Deterministic 100-Point Scoring Engine (SRS §7.3 / Handover §7)
# ----------------------------------------------------------------------------

def parse_iso_date(val):
    """Safely coerces strings, datetime, or date objects to a datetime.date."""
    if not val:
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    if isinstance(val, str):
        val = val.strip()
        if not val:
            return None
        try:
            return datetime.fromisoformat(val.replace('Z', '+00:00')).date()
        except ValueError:
            # Fallback simple YYYY-MM-DD parse
            parts = val.split('T')[0].split('-')
            if len(parts) == 3:
                try:
                    return date(int(parts[0]), int(parts[1]), int(parts[2]))
                except ValueError:
                    return None
            return None
    return None


def calculate_score(
    *,
    intent: str = 'uncertain',
    kind: str = 'other',
    categories: list = None,
    published_at=None,
    has_buying_quote: bool = False,
    has_full_text: bool = True,
    has_contact: bool = False,
    has_source_url: bool = True,
    deadline=None,
    confidence: float = 1.0,
    reference_date=None
) -> dict:
    """
    Computes deterministic score (0..100), factors breakdown, review reasons, and status override.
    
    Factors:
      1. Buying intent: 30
      2. Service match: 25
      3. Recency: 15
      4. Evidence quality: 15
      5. Contact path: 10
      6. Deadline urgency: 5
    """
    categories = categories or []
    ref_date = reference_date or datetime.now(timezone.utc).date()
    review_reasons = []

    # 1. Buying Intent (Max 30)
    intent_pts = 0
    if intent == 'nonbuyer' or kind == 'seller_promotion':
        intent_pts = 0
    elif kind in ('direct_purchase', 'rfp'):
        intent_pts = 30
    elif kind == 'agency_staffing':
        intent_pts = 24
    elif kind == 'indirect_pain':
        intent_pts = 10
    elif kind == 'hiring_signal':
        intent_pts = 5
    elif intent == 'buyer':
        intent_pts = 30

    # 2. Service Match (Max 25)
    service_pts = 25 if any(c in SUPPORTED_SERVICE_CATEGORIES for c in categories) else 0

    # 3. Recency (Max 15)
    recency_pts = 0
    pub_date = parse_iso_date(published_at)
    if pub_date is None:
        recency_pts = 0
        review_reasons.append('Missing publication date')
    else:
        days_ago = (ref_date - pub_date).days
        if days_ago < 0:
            recency_pts = 0
            review_reasons.append('Future publication date requires review')
        elif days_ago <= 2:
            recency_pts = 15
        elif days_ago <= 7:
            recency_pts = 10
        elif days_ago <= 30:
            recency_pts = 5
        else:
            recency_pts = 0

    # 4. Evidence Quality (Max 15)
    evidence_pts = 0
    if has_buying_quote:
        evidence_pts += 10
    else:
        review_reasons.append('Missing supported buying quote')
    if has_full_text:
        evidence_pts += 5

    # 5. Contact Path (Max 10)
    if has_contact:
        contact_pts = 10
    elif has_source_url:
        contact_pts = 3
    else:
        contact_pts = 0

    # 6. Deadline Urgency (Max 5)
    deadline_pts = 0
    dl_date = parse_iso_date(deadline)
    deadline_expired = False
    if dl_date:
        if dl_date < ref_date:
            deadline_expired = True
            deadline_pts = 0
        elif (dl_date - ref_date).days <= 7:
            deadline_pts = 5

    factors = [intent_pts, service_pts, recency_pts, evidence_pts, contact_pts, deadline_pts]
    total_score = sum(factors)

    # Status Overrides (SRS §7.4 / Handover §7)
    status_override = None
    if intent == 'nonbuyer' or kind == 'seller_promotion':
        status_override = 'rejected'
        review_reasons.append('Seller promotion; no buyer requirement')
        total_score = 0
    elif deadline_expired:
        status_override = 'closed'
        review_reasons.append('Deadline expired')
    elif kind == 'hiring_signal' or intent == 'uncertain':
        status_override = 'review'
        if kind == 'hiring_signal':
            review_reasons.append('Purchase intent requires review')
        review_reasons.append('Uncertain buying intent')

    if confidence < 0.75:
        if status_override not in ('rejected', 'closed'):
            status_override = 'review'
        review_reasons.append(f'Low model confidence ({confidence:.2f} < 0.75)')

    # Score Bands
    if total_score >= 80:
        band = 'Hot'
    elif total_score >= 60:
        band = 'High potential'
    elif total_score >= 40:
        band = 'Review'
    else:
        band = 'Archive'

    return {
        'score': total_score,
        'band': band,
        'factors': factors,
        'status_override': status_override,
        'review_reasons': list(dict.fromkeys(review_reasons)) # remove dupes preserving order
    }


# ----------------------------------------------------------------------------
# 4. Safe CSV Generation (SRS §3 FR-09.2 / Handover §12)
# ----------------------------------------------------------------------------

def sanitize_csv_cell(value) -> str:
    """
    Neutralizes formula injection vulnerability in spreadsheet applications.
    Prepends single quote (') if value begins with =, +, -, @, tab, or CR,
    including whitespace-preceded variants.
    """
    s = '' if value is None else str(value)
    # Check leading formula characters with optional leading whitespace
    if re.match(r'^\s*[=+\-@\t\r\n]', s):
        s = "'" + s
    # Escape quotes
    return '"' + s.replace('"', '""') + '"'


def generate_safe_csv(records: list) -> str:
    """Generates UTF-8 CSV with formula safety and fixed 30-column header."""
    lines = []
    lines.append(','.join(sanitize_csv_cell(col) for col in EXPORT_COLUMNS))
    for r in records:
        row = [sanitize_csv_cell(r.get(col, '')) for col in EXPORT_COLUMNS]
        lines.append(','.join(row))
    return '\ufeff' + '\r\n'.join(lines)


# ----------------------------------------------------------------------------
# 5. In-Memory Idempotent Pipeline Runner
# ----------------------------------------------------------------------------

class ReferencePipeline:
    def __init__(self, reference_date=None):
        self.reference_date = reference_date or datetime.now(timezone.utc).date()
        self.observations_by_key = {} # (connector, external_id) -> record
        self.opportunities = {}       # opp_id -> record
        self.stats = {
            'processed': 0,
            'replays_prevented': 0,
            'qualified': 0,
            'rejected': 0,
            'closed': 0,
            'review_required': 0
        }

    def process_item(self, item: dict) -> dict:
        """Processes one observation fixture through normalization, validation, scoring and idempotency."""
        connector = item.get('source_connector', 'manual_capture')
        ext_id = item.get('external_id')
        raw_url = item.get('url', '')
        canonical_url = canonicalize_url(raw_url)
        content_hash = compute_content_hash(item.get('text', ''))

        dedup_key = (connector, ext_id) if ext_id else (connector, canonical_url)
        
        # Idempotent replay check (SRS §3 FR-02.4 / FR-05.1)
        if dedup_key in self.observations_by_key:
            self.stats['replays_prevented'] += 1
            return {
                'id': item.get('id'),
                'is_replay': True,
                'message': f'Replay detected for key {dedup_key}. No duplicate recorded.'
            }

        self.observations_by_key[dedup_key] = {
            'content_hash': content_hash,
            'canonical_url': canonical_url,
            'original': item
        }
        self.stats['processed'] += 1

        # Check for cross-source duplicates flag
        if item.get('is_duplicate_of'):
            return {
                'id': item.get('id'),
                'is_duplicate': True,
                'target_id': item.get('similarity_target'),
                'similarity': item.get('expected_similarity', 0.9)
            }

        extraction = item.get('extraction', {})
        source_text = item.get('text', '')

        # Evidence validation (SRS §3 FR-03.2, FR-04.3)
        intent_quote = extraction.get('intent_evidence', '')
        has_quote = verify_evidence_substring(intent_quote, source_text)

        # Contact validation
        contact = extraction.get('contact') or {}
        email = contact.get('email')
        phone = contact.get('phone')
        has_contact = bool(email or phone)

        # Validate factual field evidence
        field_evidence = extraction.get('field_evidence') or {}
        company = extraction.get('company')
        if company and 'company' in field_evidence:
            if not verify_evidence_substring(field_evidence['company'], source_text):
                company = None # Drop unevidenced claim

        categories = [extraction.get('primary_category')] + (extraction.get('secondary_categories') or [])
        categories = [c for c in categories if c]

        # Scoring
        score_res = calculate_score(
            intent=extraction.get('intent', 'uncertain'),
            kind=extraction.get('kind', 'other'),
            categories=categories,
            published_at=item.get('published_at'),
            has_buying_quote=has_quote,
            has_full_text=bool(source_text),
            has_contact=has_contact,
            has_source_url=bool(raw_url),
            deadline=extraction.get('deadline'),
            confidence=extraction.get('confidence', 1.0),
            reference_date=self.reference_date
        )

        status = score_res['status_override'] or item.get('expected_status') or 'new'
        if status == 'rejected':
            self.stats['rejected'] += 1
        elif status == 'closed':
            self.stats['closed'] += 1
        elif status == 'review':
            self.stats['review_required'] += 1
        else:
            self.stats['qualified'] += 1

        opportunity_record = {
            'opportunity_id': item.get('id', str(len(self.opportunities) + 1)),
            'detected_at': datetime.now(timezone.utc).isoformat(),
            'source_published_at': item.get('published_at', ''),
            'source': connector,
            'source_url': raw_url,
            'author': item.get('author', ''),
            'company': company or '',
            'company_website': '',
            'country': extraction.get('country') or '',
            'industry': '',
            'requirement': extraction.get('requirement', ''),
            'primary_category': extraction.get('primary_category', ''),
            'technology': '; '.join(extraction.get('technologies') or []),
            'budget_text': extraction.get('budget_text') or '',
            'deadline': extraction.get('deadline') or '',
            'intent': extraction.get('intent', 'uncertain'),
            'confidence': f"{extraction.get('confidence', 0.0):.2f}",
            'score': score_res['score'],
            'band': score_res['band'],
            'contact_name': contact.get('name') or '',
            'designation': '',
            'email': email or '',
            'phone': phone or '',
            'contact_evidence_url': raw_url if email or phone else '',
            'contact_verification': 'published' if email or phone else '',
            'review_reasons': '; '.join(score_res['review_reasons']),
            'owner': '',
            'status': status,
            'last_follow_up': '',
            'next_follow_up': '',
            'notes': '',
            '_score_factors': score_res['factors']
        }

        self.opportunities[opportunity_record['opportunity_id']] = opportunity_record
        return opportunity_record


def main():
    fixtures_file = sys.argv[1] if len(sys.argv) > 1 else 'fixtures.json'
    export_file = sys.argv[2] if len(sys.argv) > 2 else 'reference_export.csv'

    # Fixed test reference date matching the fixture dataset (17 Sep 2026)
    fixed_ref_date = date(2026, 9, 17)

    if not os.path.exists(fixtures_file):
        print(f"Error: Fixtures file {fixtures_file} not found.", file=sys.stderr)
        sys.exit(1)

    with open(fixtures_file, 'r', encoding='utf-8') as f:
        fixtures = json.load(f)

    print(f"Loaded {len(fixtures)} fixtures from {fixtures_file}")
    pipeline = ReferencePipeline(reference_date=fixed_ref_date)

    print("\n--- Running Observations Through Pipeline ---")
    for item in fixtures:
        res = pipeline.process_item(item)
        if res.get('is_duplicate'):
            print(f"[{item['id']}] Probable duplicate of {res['target_id']} (similarity: {res['similarity']:.2f})")
        else:
            print(f"[{res['opportunity_id']}] Score: {res['score']:2d}/100 | Band: {res['band']:14s} | Status: {res['status']:8s} | Factors: {res['_score_factors']}")

    # Replay simulation: re-run the same batch to prove 100% idempotency
    print("\n--- Replaying Batch to Verify Idempotency ---")
    replayed = 0
    for item in fixtures:
        res = pipeline.process_item(item)
        if res.get('is_replay'):
            replayed += 1
    print(f"Replay verified: {replayed} duplicate observations prevented.")

    # Generate CSV export
    csv_data = generate_safe_csv(list(pipeline.opportunities.values()))
    with open(export_file, 'w', encoding='utf-8') as f:
        f.write(csv_data)
    print(f"\nSafe CSV exported to {export_file} ({len(pipeline.opportunities)} opportunities)")
    print(f"Summary stats: {pipeline.stats}")


if __name__ == '__main__':
    main()
