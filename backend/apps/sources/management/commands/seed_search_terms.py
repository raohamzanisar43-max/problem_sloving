"""
Load the search terms for Novu's target leads: people and organisations that want a website or a
larger software project built, or need AML / compliance, accounting & tax or governance & audit
services — in Pakistan and abroad.

    python manage.py seed_search_terms              # add/refresh the curated terms
    python manage.py seed_search_terms --replace    # also disable every other term on the source

Safe to re-run. Job-post noise is excluded in the query itself with Brave's `-` operator.
"""
from django.core.management.base import BaseCommand, CommandError

from apps.sources.models import SearchTerm, Source

NO_JOBS = '-jobs -hiring -vacancy -career -internship'

# (group, market, query). Brave cannot filter by Pakistan, so the PK market is targeted in the
# query text: place names, "Pakistan" and Roman Urdu.
TERMS = [
    # Websites — international
    ('Website — international', 'WORLD', f'"need a website built" OR "need someone to build my website" {NO_JOBS}'),
    ('Website — international', 'WORLD', f'"looking for a web design agency" OR "looking for a web development company" {NO_JOBS}'),
    ('Website — international', 'WORLD', f'"website redesign" "request for proposal" {NO_JOBS}'),
    ('Website — international', 'WORLD', f'"need an e-commerce website" OR "want to build an online store" {NO_JOBS}'),
    # Websites — Pakistan
    ('Website — Pakistan', 'PK', f'"website development" Pakistan "looking for" OR "need" company {NO_JOBS}'),
    ('Website — Pakistan', 'PK', f'"e-commerce website" Pakistan Karachi OR Lahore OR Islamabad "need" OR "looking for" {NO_JOBS}'),
    ('Website — Pakistan', 'PK', '"website banwani hai" OR "website chahiye" OR "website banwana hai"'),
    # High-level projects — international
    ('Projects — international', 'WORLD', f'"request for proposal" "custom software development" {NO_JOBS}'),
    ('Projects — international', 'WORLD', f'"RFP" "mobile app development" {NO_JOBS}'),
    ('Projects — international', 'WORLD', f'"looking for a software development partner" OR "looking for a software development company" {NO_JOBS}'),
    ('Projects — international', 'WORLD', f'"ERP implementation" OR "CRM implementation" "request for proposal" {NO_JOBS}'),
    ('Projects — international', 'WORLD', f'"AI automation" OR "AI platform" "request for proposal" OR "looking for a development partner" {NO_JOBS}'),
    # High-level projects — Pakistan
    ('Projects — Pakistan', 'PK', f'tender OR EOI "software development" OR "web portal" OR "mobile app" Pakistan {NO_JOBS}'),
    ('Projects — Pakistan', 'PK', f'"looking for a software house" OR "need a software company" Pakistan {NO_JOBS}'),
    ('Projects — Pakistan', 'PK', '"software house chahiye" OR "app banwani hai" OR "software banwana hai"'),
    ('Projects — Pakistan', 'PK', f'"management system" OR "ERP" Pakistan school OR hospital OR "supply chain" "required" OR "RFP" {NO_JOBS}'),
]


# Client-supplied keyword list, kept verbatim by group. Each phrase is searched as an exact phrase, with
# job-post words excluded so "looking for an outsourced MLRO" does not match recruiters.
CLIENT_KEYWORDS = {
    'Accounting & tax services': [
        'looking for a VAT consultant', 'looking for accounting services', 'looking for financial modelling services',
        'looking for financial reporting support', 'looking for tax compliance services', 'need a corporate tax consultant',
        'need a cybersecurity risk assessment', 'need an outsourced CFO', 'need management accounts preparation',
        'need outsourced bookkeeping', 'need tax filing support',
    ],
    'AML & compliance services': [
        'looking for a compliance retainer', 'looking for AML audit services', 'looking for AML risk assessment services',
        'looking for an AML gap assessment', 'looking for an AML policy consultant', 'looking for an outsourced compliance officer',
        'looking for an outsourced MLRO', 'looking for compliance manual preparation', 'looking for KYC policy development',
        'looking for MLRO services', 'looking for sanctions policy development', 'need a compliance health check',
        'need a fractional compliance officer', 'need a transaction monitoring policy', 'need an AML compliance program',
        'need an AML consultant', 'need an enterprise wide risk assessment', 'need an external MLRO',
        'need an independent AML review', 'need compliance outsourcing services', 'need compliance remediation support',
        'need KYB policy development',
    ],
    'Governance & audit services': [
        'looking for a corporate governance consultant', 'looking for an enterprise risk management consultant',
        'looking for audit readiness support', 'looking for operational audit services', 'looking for outsourced internal audit',
        'looking for SOP development services', 'need a policy development consultant', 'need a process audit',
        'need an internal audit consultant', 'need an internal controls review', 'need board advisory services',
    ],
    'Business systems': ['school management software required'],
    'Managed IT services': ['recommend an MSP'],
    'Software partners': ['looking for software development company'],
    'Development teams': ['need dedicated development team', 'offshore development team'],
    'Client project requests': [
        'looking for a developer to build', 'looking for a freelance developer', 'looking for someone to develop my website',
        'need a django developer to build', 'need a full stack developer for my project', 'need a python developer for my project',
        'need help building my web application', 'need someone to build my website', 'seeking a developer to build my app',
    ],
}

TERMS += [
    (group, 'WORLD', f'"{phrase}" {NO_JOBS}')
    for group, phrases in CLIENT_KEYWORDS.items()
    for phrase in phrases
]


class Command(BaseCommand):
    help = 'Load the curated website / high-level-project search terms'

    def add_arguments(self, parser):
        parser.add_argument('--source', default=None, help='Source name (default: first enabled web search source).')
        parser.add_argument('--replace', action='store_true', help='Disable all other terms on the source.')

    def handle(self, *args, **options):
        sources = Source.objects.filter(connector_type='web_search')
        source = (sources.filter(name__iexact=options['source']).first() if options['source']
                  else sources.filter(enabled=True).first())
        if source is None:
            raise CommandError('No matching web search source. Create and enable one first.')

        keep = set()
        created = 0
        for group, market, query in TERMS:
            term, was_created = SearchTerm.objects.update_or_create(
                source=source, group_name=group, query=query,
                defaults={'market': market, 'language': 'en', 'enabled': True},
            )
            keep.add(term.pk)
            created += was_created

        disabled = 0
        if options['replace']:
            disabled = SearchTerm.objects.filter(source=source, enabled=True).exclude(pk__in=keep).update(enabled=False)

        self.stdout.write(self.style.SUCCESS(
            f'{source.name}: {created} term(s) added, {len(TERMS) - created} refreshed, {disabled} disabled.'
        ))
