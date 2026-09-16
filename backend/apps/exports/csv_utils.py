"""
Safe CSV generation with formula-injection protection (handover §12).
"""
import csv
import io
import re


DANGEROUS_PREFIX = re.compile(r'^[\s]*[=+\-@]|^\s*[\t\r\n]')


def safe_cell(value) -> str:
    s = '' if value is None else str(value)
    if DANGEROUS_PREFIX.match(s):
        s = "'" + s
    return s


CSV_COLUMNS = [
    'opportunity_id', 'detected_at', 'source_published_at', 'source', 'source_url',
    'author', 'company', 'company_website', 'country', 'industry',
    'requirement', 'primary_category', 'technology', 'budget_text', 'deadline',
    'intent', 'confidence', 'score', 'band',
    'contact_name', 'designation', 'email', 'phone',
    'contact_evidence_url', 'contact_verification', 'review_reasons',
    'owner', 'status', 'last_follow_up', 'next_follow_up', 'notes',
]


def opportunity_to_row(opp) -> dict:
    owner_name = ''
    if opp.owner:
        owner_name = opp.owner.display_name or opp.owner.username
    return {
        'opportunity_id': opp.public_id or str(opp.id),
        'detected_at': opp.detected_at.isoformat() if opp.detected_at else '',
        'source_published_at': opp.source_published_at.isoformat() if opp.source_published_at else '',
        'source': opp.source_name or '',
        'source_url': opp.source_url or '',
        'author': '',
        'company': opp.company_name or '',
        'company_website': opp.company_domain or '',
        'country': opp.country or '',
        'industry': opp.industry or '',
        'requirement': opp.requirement or '',
        'primary_category': opp.primary_category or '',
        'technology': ';'.join(opp.technology or []),
        'budget_text': opp.budget_text or '',
        'deadline': opp.deadline.isoformat() if opp.deadline else '',
        'intent': opp.intent or '',
        'confidence': opp.confidence,
        'score': opp.score,
        'band': opp.band or '',
        'contact_name': opp.contact_name or '',
        'designation': opp.contact_designation or '',
        'email': opp.email or '',
        'phone': opp.phone or '',
        'contact_evidence_url': opp.contact_evidence_url or '',
        'contact_verification': opp.contact_verification or '',
        'review_reasons': '; '.join(opp.review_reasons or []),
        'owner': owner_name,
        'status': opp.status or '',
        'last_follow_up': '',
        'next_follow_up': '',
        'notes': opp.notes or '',
    }


def build_csv(opportunities) -> bytes:
    buffer = io.StringIO()
    # UTF-8 BOM for Excel
    buffer.write('\ufeff')
    writer = csv.DictWriter(buffer, fieldnames=CSV_COLUMNS, lineterminator='\r\n')
    writer.writeheader()
    for opp in opportunities:
        row = opportunity_to_row(opp)
        safe_row = {k: safe_cell(v) for k, v in row.items()}
        writer.writerow(safe_row)
    return buffer.getvalue().encode('utf-8')
