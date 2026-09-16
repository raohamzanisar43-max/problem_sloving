"""
Load example opportunities matching the official interface prototype.
"""
from datetime import datetime, timezone, date
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from apps.sources.models import Source, SearchTerm
from apps.opportunities.models import Opportunity
from apps.scoring.engine import compute_score

User = get_user_model()


DEMO_LEADS = [
    {
        'public_id': 'demo-1',
        'requirement': 'ERP development partner for fleet operations',
        'text': 'Looking for an ERP development partner for fleet operations. Please contact procurement@example.invalid.',
        'categories': ['ERP', 'CUSTOM_DEV'],
        'primary_category': 'ERP',
        'published': datetime(2026, 9, 14, 9, 0, tzinfo=timezone.utc),
        'intent': 'buyer',
        'kind': 'direct_purchase',
        'email': 'procurement@example.invalid',
        'status': 'new',
        'confidence': 0.92,
    },
    {
        'public_id': 'demo-2',
        'requirement': 'Managed cloud and IT helpdesk provider',
        'text': 'Seeking a managed IT services provider to manage cloud and helpdesk.',
        'categories': ['MANAGED_IT', 'CLOUD_DEVOPS'],
        'primary_category': 'MANAGED_IT',
        'published': datetime(2026, 9, 13, 9, 0, tzinfo=timezone.utc),
        'intent': 'buyer',
        'kind': 'direct_purchase',
        'email': '',
        'status': 'new',
        'confidence': 0.90,
    },
    {
        'public_id': 'demo-3',
        'requirement': 'Full time mobile developer hiring signal',
        'text': 'We are hiring a full time mobile developer.',
        'categories': ['MOBILE_APP'],
        'primary_category': 'MOBILE_APP',
        'published': datetime(2026, 9, 14, 9, 0, tzinfo=timezone.utc),
        'intent': 'uncertain',
        'kind': 'hiring_signal',
        'email': '',
        'status': 'review',
        'confidence': 0.70,
    },
    {
        'public_id': 'demo-4',
        'requirement': 'Website agency seller promotion',
        'text': 'Our agency builds websites and has discounts this month.',
        'categories': ['WEBSITE'],
        'primary_category': 'WEBSITE',
        'published': datetime(2026, 9, 14, 9, 0, tzinfo=timezone.utc),
        'intent': 'nonbuyer',
        'kind': 'seller_promotion',
        'email': '',
        'status': 'rejected',
        'confidence': 0.95,
    },
    {
        'public_id': 'demo-5',
        'requirement': 'School LMS implementation tender',
        'text': 'Tender for a school LMS implementation. Closing date 2026-09-10.',
        'categories': ['LMS'],
        'primary_category': 'LMS',
        'published': datetime(2026, 9, 1, 9, 0, tzinfo=timezone.utc),
        'deadline': date(2026, 9, 10),
        'intent': 'buyer',
        'kind': 'rfp',
        'email': '',
        'status': 'closed',
        'confidence': 0.88,
    },
]

SOURCES = [
    {
        'name': 'Web search',
        'connector_type': 'web_search',
        'enabled': False,
        'access_state': 'credential_required',
        'planned_route': 'Licensed search API',
    },
    {
        'name': 'Approved feeds',
        'connector_type': 'rss',
        'enabled': False,
        'access_state': 'select_source_list',
        'planned_route': 'RSS and portal adapters',
    },
    {
        'name': 'X',
        'connector_type': 'x',
        'enabled': False,
        'access_state': 'account_required',
        'planned_route': 'Official recent search',
    },
    {
        'name': 'Reddit',
        'connector_type': 'reddit',
        'enabled': False,
        'access_state': 'commercial_agreement',
        'planned_route': 'Approved Data API',
    },
    {
        'name': 'LinkedIn',
        'connector_type': 'linkedin',
        'enabled': False,
        'access_state': 'conditional',
        'planned_route': 'Supported integration or manual capture',
    },
    {
        'name': 'Manual references',
        'connector_type': 'manual',
        'enabled': True,
        'access_state': 'planned_mvp',
        'planned_route': 'Paste URL and permitted excerpt',
    },
]

SEARCH_GROUPS = [
    ('Software partners', [
        '"looking for software development company"',
        '"seeking software development partner"',
    ]),
    ('Development teams', [
        '"need dedicated development team"',
        '"offshore development team"',
    ]),
    ('Managed IT services', [
        '"looking for managed IT services"',
        '"recommend an MSP"',
    ]),
    ('Business systems', [
        '"ERP implementation RFP"',
        '"school management software required"',
    ]),
    ('Roman Urdu', [
        '"software house chahiye"',
        '"app banwani hai"',
    ]),
]


class Command(BaseCommand):
    help = 'Seed demo users, sources, search terms and example opportunities'

    def handle(self, *args, **options):
        self.stdout.write('Seeding Novu Opportunity Radar demo data…')

        # Users
        users = [
            ('admin', 'admin123', 'admin', 'Administrator'),
            ('manager', 'manager123', 'sales_manager', 'Sales Manager'),
            ('executive', 'exec123', 'sales_executive', 'Sales Executive A'),
            ('executive_b', 'exec123', 'sales_executive', 'Sales Executive B'),
        ]
        for username, password, role, display in users:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={'role': role, 'display_name': display, 'is_staff': role == 'admin'},
            )
            if created:
                user.set_password(password)
                user.role = role
                user.display_name = display
                if role == 'admin':
                    user.is_staff = True
                    user.is_superuser = True
                user.save()
                self.stdout.write(f'  Created user {username}')
            else:
                self.stdout.write(f'  User {username} already exists')

        # Sources
        for s in SOURCES:
            obj, created = Source.objects.get_or_create(
                name=s['name'],
                defaults=s,
            )
            if created:
                self.stdout.write(f'  Source: {obj.name}')

        # Search terms
        for group, queries in SEARCH_GROUPS:
            for q in queries:
                SearchTerm.objects.get_or_create(
                    group_name=group,
                    query=q,
                    defaults={'market': 'PK', 'language': 'en', 'enabled': True},
                )

        # Opportunities
        for lead in DEMO_LEADS:
            result = compute_score(
                intent=lead['intent'],
                kind=lead['kind'],
                categories=lead['categories'],
                published_at=lead['published'],
                has_quote=True,
                has_full_text=True,
                email=lead.get('email', ''),
                source_url=f"https://example.invalid/opportunities/{lead['public_id']}",
                deadline=lead.get('deadline'),
            )
            status = lead.get('status') or result.get('status_override') or 'new'
            if result.get('status_override'):
                status = result['status_override']

            opp, created = Opportunity.objects.update_or_create(
                public_id=lead['public_id'],
                defaults={
                    'requirement': lead['requirement'],
                    'text': lead['text'],
                    'intent': lead['intent'],
                    'kind': lead['kind'],
                    'confidence': lead['confidence'],
                    'primary_category': lead['primary_category'],
                    'categories': lead['categories'],
                    'score': result['score'],
                    'band': result['band'],
                    'score_factors': result['factors'],
                    'review_reasons': result['review_reasons'] or lead.get('reasons', []),
                    'status': status,
                    'email': lead.get('email', ''),
                    'contact_evidence_url': (
                        f"https://example.invalid/opportunities/{lead['public_id']}"
                        if lead.get('email') else ''
                    ),
                    'contact_verification': 'published' if lead.get('email') else '',
                    'source_url': f"https://example.invalid/opportunities/{lead['public_id']}",
                    'source_name': 'example_web',
                    'source_published_at': lead['published'],
                    'detected_at': datetime(2026, 9, 15, 9, 0, tzinfo=timezone.utc),
                    'deadline': lead.get('deadline'),
                },
            )
            action = 'Created' if created else 'Updated'
            self.stdout.write(f'  {action} opportunity {opp.public_id} score={opp.score}')

        self.stdout.write(self.style.SUCCESS('Demo data ready.'))
        self.stdout.write('Login: admin / admin123  ·  manager / manager123  ·  executive / exec123')
