"""
Freelancer.com collector — live client projects from Freelancer.com's public
projects API (no key, no cost).

Every project there is a client asking for work, so the collector only has to
keep the ones that are software work and match the search keywords:

  * the project's main skill must be in a software category (a "PHP" or
    "Mobile App Development" project, not "Photography" that also lists HTML);
  * its title, description or skills must contain the keyword's important
    words (see content_filters.keyword_core);
  * it must have been posted within ``max_age_days`` (source setting, default 7).
"""
import logging
import re
from datetime import datetime, timedelta, timezone as dt_tz

import httpx

from .base import BaseCollector

logger = logging.getLogger(__name__)

API_URL = 'https://www.freelancer.com/api/projects/0.1/projects/active/'
PROJECT_URL = 'https://www.freelancer.com/projects/{seo_url}'

# Freelancer.com job categories that are software work.
SOFTWARE_CATEGORIES = {
    'Websites, IT & Software',
    'Mobile Phones & Computing',
    'Artificial Intelligence',
}

# Skills Freelancer files under a software category that are marketing,
# media or admin work rather than building software.
_NON_SOFTWARE_SKILL_RE = re.compile(
    r'\b(?:marketing|seo|link building|social media|social networking|instagram|facebook|twitter|'
    r'tiktok|youtube|advertising|adwords|ads|content|art|video|animation|image|music|voice|'
    r'writing|data entry|excel|virtual assistant|technical support|customer|translation|'
    r'analytics|research|photo\w*)\b',
    re.IGNORECASE,
)

CURRENCY_SIGNS = {'USD': '$', 'EUR': '€', 'GBP': '£', 'INR': '₹', 'AUD': 'A$', 'CAD': 'C$',
                  'SGD': 'S$', 'NZD': 'NZ$', 'HKD': 'HK$', 'PKR': 'Rs '}


def _money(value):
    return f'{value:,.0f}' if value is not None else ''


def budget_text(project):
    """'$750–1,500 USD', '₹1,500–12,500 INR (≈ $18–150)', '$15–25/hr USD'."""
    budget = project.get('budget') or {}
    currency = project.get('currency') or {}
    code = currency.get('code') or 'USD'
    sign = CURRENCY_SIGNS.get(code, currency.get('sign') or '')
    low, high = budget.get('minimum'), budget.get('maximum')
    if low is None and high is None:
        return ''
    hourly = '/hr' if project.get('type') == 'hourly' else ''
    if low and high and high > low * 100:
        high = None  # placeholder maximum such as 10,000,000,000: show "from"
    span = _money(low) if high in (None, low) else f'{_money(low)}–{_money(high)}'
    if high is None and budget.get('maximum'):
        span += '+'
    text = f'{sign}{span}{hourly} {code}'
    rate = currency.get('exchange_rate')
    if code != 'USD' and rate:
        usd_low = (low or 0) * rate
        usd_high = (high or low or 0) * rate
        usd = f'${usd_low:,.0f}' if high in (None, low) else f'${usd_low:,.0f}–{usd_high:,.0f}'
        text += f' (≈ {usd}{hourly})'
    return text[:120]


def primary_skill(project):
    """The skill in the project's URL (its main skill), else the first one."""
    jobs = project.get('jobs') or []
    prefix = (project.get('seo_url') or '').split('/')[0].replace('-', '_').lower()
    for job in jobs:
        if (job.get('seo_url') or '').replace('-', '_').lower() == prefix:
            return job
    return jobs[0] if jobs else None


def is_software_skill(job):
    category = (job.get('category') or {}).get('name') or ''
    return category in SOFTWARE_CATEGORIES and not _NON_SOFTWARE_SKILL_RE.search(job.get('name') or '')


def is_software_project(project):
    """
    At least half of the project's skills must be software skills. Clients
    tag a logo or ads job with a stray "PHP" or "HTML", so one software skill
    alone is not enough.
    """
    jobs = project.get('jobs') or []
    software = sum(1 for job in jobs if is_software_skill(job))
    return software >= 1 and software * 2 >= len(jobs)


def project_url(project):
    seo = project.get('seo_url')
    return PROJECT_URL.format(seo_url=seo) if seo else f'https://www.freelancer.com/projects/{project.get("id")}'


def to_row(project):
    skills = [j.get('name') for j in (project.get('jobs') or []) if j.get('name')]
    title = (project.get('title') or '').strip()
    description = (project.get('description') or project.get('preview_description') or '').strip()
    budget = budget_text(project)
    bids = (project.get('bid_stats') or {}).get('bid_count')
    lines = [title, '', description]
    if skills:
        lines += ['', 'Skills: ' + ', '.join(skills)]
    if budget:
        lines.append(f'Budget: {budget}')
    url = project_url(project)
    submitted = project.get('time_submitted')
    return {
        'external_id': str(project.get('id')),
        'original_url': url,
        'canonical_url': url,
        'title': title[:500],
        'text': '\n'.join(lines)[:8000],
        'author': '',
        'source_published_at': datetime.fromtimestamp(submitted, tz=dt_tz.utc) if submitted else None,
        'raw_payload': {
            'platform': 'freelancer',
            'id': project.get('id'),
            'type': project.get('type'),
            'budget': project.get('budget'),
            'currency': {k: (project.get('currency') or {}).get(k) for k in ('code', 'sign', 'exchange_rate')},
            'budget_text': budget,
            'skills': skills,
            'primary_skill': (primary_skill(project) or {}).get('name', ''),
            'bid_count': bids,
            'language': project.get('language'),
        },
    }


def search_query(term_query):
    """Freelancer search works best with the keyword's important words only."""
    from apps.sources.content_filters import keyword_core, ROLE_WORDS
    words = [w for w in keyword_core(term_query) if w not in ROLE_WORDS]
    readable = {'fullstack': 'full stack', 'reactnative': 'react native'}
    return ' '.join(sorted(readable.get(w, w) for w in words))


class FreelancerCollector(BaseCollector):
    def __init__(self, source):
        super().__init__(source)
        self._seen_queries = set()

    def fetch_observations(self, term_query: str, market: str = 'PK') -> list[dict]:
        from apps.sources.content_filters import matched_keyword

        query = search_query(term_query)
        # Keywords that differ only in filler words ("need a developer" /
        # "looking for a developer") give the same search; run it once.
        if query in self._seen_queries:
            return []
        self._seen_queries.add(query)

        settings = self.source.settings or {}
        max_age = timedelta(days=int(settings.get('max_age_days', 7) or 7))
        params = {
            'limit': int(settings.get('limit', 50) or 50),
            'full_description': 'true',
            'job_details': 'true',
            'sort_field': 'time_submitted',
            'languages[]': settings.get('language', 'en'),
        }
        if query:
            params['query'] = query
        with httpx.Client(timeout=25, headers={'User-Agent': 'novu-radar/1.0'}) as client:
            resp = client.get(API_URL, params=params)
            resp.raise_for_status()
        payload = resp.json()
        if payload.get('status') != 'success':
            raise RuntimeError(f'Freelancer API error: {payload.get("message") or payload.get("status")}')

        cutoff = datetime.now(dt_tz.utc) - max_age
        rows = []
        for project in (payload.get('result') or {}).get('projects') or []:
            if project.get('frontend_project_status', 'open') != 'open' or project.get('deleted'):
                continue
            if not is_software_project(project):
                continue
            row = to_row(project)
            if row['source_published_at'] and row['source_published_at'] < cutoff:
                continue
            if not matched_keyword(title=row['title'], text=row['text'], keywords=[term_query],
                                   marketplace=True):
                continue
            rows.append(row)
        logger.info('Freelancer.com %r: %d matching project(s)', query or term_query, len(rows))
        return rows


# ── Lead fields straight from the project (no LLM call needed) ───────────────

_CATEGORY_RULES = [
    ('MOBILE_APP', ('mobile app', 'android', 'iphone', 'ios', 'flutter', 'react native', 'kotlin', 'swift')),
    ('AI_AUTOMATION', ('artificial intelligence', 'machine learning', 'ai ', 'openai', 'chatgpt', 'automation',
                       'chatbot', 'llm', 'deep learning', 'natural language')),
    ('ERP', ('erp', 'odoo', 'sap')),
    ('CRM', ('crm', 'salesforce', 'hubspot', 'zoho')),
    ('LMS', ('lms', 'moodle', 'e-learning')),
    ('CLOUD_DEVOPS', ('aws', 'azure', 'devops', 'docker', 'kubernetes', 'google cloud', 'linux')),
    ('CYBERSECURITY', ('security', 'penetration', 'pentest')),
    ('WEBSITE', ('website', 'wordpress', 'shopify', 'woocommerce', 'html', 'php', 'web development',
                 'web design', 'ecommerce', 'landing page', 'css', 'wix', 'webflow')),
]


def categories_for(skills, title=''):
    text = ' ' + ' '.join(skills + [title]).lower() + ' '
    found = [cat for cat, words in _CATEGORY_RULES if any(w in text for w in words)]
    return found or ['CUSTOM_DEV']


def lead_fields(observation):
    """Opportunity fields for a Freelancer.com project observation."""
    raw = observation.raw_payload or {}
    skills = list(raw.get('skills') or [])
    categories = categories_for(skills, observation.title or '')
    return {
        'requirement': (observation.title or observation.text[:120])[:500],
        'intent': 'buyer',
        'kind': 'direct_purchase',
        'primary_category': categories[0],
        'categories': categories,
        'technology': skills[:12],
        'company_name': '',
        'company_domain': '',
        'country': '',
        'industry': '',
        'budget_text': raw.get('budget_text', '') or '',
        'deadline': None,
        'email': '',
        'phone': '',
        'contact_name': '',
        'confidence': 0.95,
    }
