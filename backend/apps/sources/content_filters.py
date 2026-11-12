"""
Deterministic pre-scoring content filter (handover: "reject before scoring").

Agency/vendor blog posts — "How to find an app developer", "Top 10 signs you
need a software partner", "Everything You Need To Know About Offshore Teams"
— repeatedly slip through as buyer-sounding content: they talk at length
about "finding a developer" or "managing an offshore team" in exactly the
vocabulary a real buyer would use, even though no one is asking Novu for
anything. The author is a software/app agency publishing marketing content
to attract its own clients.

IMPORTANT: when a post comes from the Brave web-search collector, `text` is
only Brave's short result `description` (one or two sentences) — never the
full article body. A byline, "written by our co-founder", or a chat-widget
greeting almost never survives into that snippet, even on a post that is
unambiguously an agency blog. So this can't rely on body self-promo markers
alone the way it could for a pasted full article: the TITLE is the one field
that is always present and always meaningful, and a handful of title shapes
("Everything You Need To Know About X", "Top N ...", "Ultimate Guide to X",
"Organizations use X to save money") are essentially never how a genuine
buyer phrases their own request, so those are treated as sufficient on
their own. Weaker shapes ("How to manage/build/scale X") still need a
self-promo marker in the body or a blog-ish URL path as corroboration.

This runs BEFORE the LLM extraction call: it never reaches a human reviewer
and never spends an LLM call on something the model might score as a
hiring_signal or indirect_pain purely because of its buyer-ish phrasing.

An explicit first-person buyer statement anywhere in the title or text
always overrides every rule here, since a genuine prospect can title a post
"How do I find a good dev team? (we need one)".
"""
import re
from urllib.parse import urlparse

# Title shapes that are, on their own, essentially never how a genuine buyer
# phrases their own request — these fire without needing any other signal.
_STRONG_GUIDE_PHRASE_RE = re.compile(
    r'\bultimate\s+guide\b'
    r'|\bcomplete\s+guide\b'
    r'|\bstep[- ]by[- ]step\s+guide\b'
    r'|\beverything\s+you\s+need\s+to\s+know\b'
    r'|\btop\s+\d+\b'
    r'|\b\d+\s+(best|top)\b'
    r'|\bthings\s+to\s+(consider|know)\s+(before|when)\b'
    r'|\bsigns\s+(you|your\s+\w+)\s+need\b'
    r'|\bpros\s+and\s+cons\b'
    r'|\bbenefits\s+of\b'
    r'|\bwhat\s+is\s+(a|an|the)\b.*\?'
    r'|\b(organizations?|companies|businesses)\s+(use|choose|turn\s+to|are\s+using|rely\s+on)\b',
    re.IGNORECASE,
)

# Weaker "how to <verb> X" shapes — still guide-like, but common enough in a
# genuine question that they need a second signal (self-promo body text or
# a blog-ish URL path) before being treated as agency content.
_GUIDE_TITLE_RE = re.compile(
    r'\bhow\s+to\s+(find|choose|hire|select|pick|manage|build|scale|run|outsource|'
    r'set\s*up|structure|evaluate|work\s+with|start|implement|use)\b'
    r'|\bguide\s+to\b',
    re.IGNORECASE,
)

# ── Domain-based rejection ───────────────────────────────────────────────────
# A whole class of noise isn't agency marketing prose at all — it's a job
# board listing (someone hiring an EMPLOYEE), a freelance-marketplace gig
# page (a FREELANCER advertising themselves — seller, not buyer), a video,
# or a third-party software/agency review-and-directory site (ranking OTHER
# companies). None of these can ever be a buyer directly asking Novu for
# services, no matter how buyer-ish the title/snippet reads, because broad
# search terms like "hire a developer" or "offshore development team"
# surface all of these constantly. Checked by domain, not text, so it holds
# regardless of snippet length or phrasing.
_VIDEO_DOMAINS = {'youtube.com', 'youtu.be', 'vimeo.com', 'tiktok.com'}

_FREELANCE_MARKETPLACE_DOMAINS = {
    'upwork.com', 'fiverr.com', 'freelancer.com', 'peopleperhour.com',
    'guru.com', 'toptal.com', 'flexjobs.com',
}

_JOB_BOARD_DOMAINS = {
    'indeed.com', 'glassdoor.com', 'ziprecruiter.com', 'dice.com',
    'simplyhired.com', 'monster.com', 'careerbuilder.com', 'wellfound.com',
    'roberthalf.com', 'builtin.com', 'weworkremotely.com', 'jobrapido.com',
    'freehire.me', 'easyjob.one', 'remoteok.com', 'stackoverflow.com',
    'twine.net', 'codementor.io', 'arc.dev', 'turing.com', 'business.com',
}

_DIRECTORY_REVIEW_DOMAINS = {
    'clutch.co', 'goodfirms.co', 'designrush.com', 'businessofapps.com',
    'g2.com', 'capterra.com', 'softwareworld.co', 'techreviewer.co', 'getapp.com',
}

_DATA_STATISTICS_DOMAINS = {
    'fred.stlouisfed.org', 'statista.com', 'ycharts.com', 'tradingeconomics.com',
}

_NON_LEAD_DOMAINS = (
    _VIDEO_DOMAINS | _FREELANCE_MARKETPLACE_DOMAINS | _JOB_BOARD_DOMAINS
    | _DIRECTORY_REVIEW_DOMAINS | _DATA_STATISTICS_DOMAINS
)

# LinkedIn is not blocked wholesale — a genuine LinkedIn post asking for a
# developer has to stay — but a URL specifically under /jobs/ is always a
# job listing, same as Indeed.
_LINKEDIN_JOBS_DOMAINS = {'linkedin.com'}
_JOB_LISTING_PATH_RE = re.compile(r'^/jobs?/', re.IGNORECASE)

# Job-description boilerplate: a company describing the CANDIDATE it wants
# to hire as an employee (degree, years of experience, soft skills) reads
# very differently from a buyer describing a PROJECT it wants built (scope,
# budget, deadline) — even though both mention "developer" and "looking for".
_JOB_DESCRIPTION_RE = re.compile(
    r"\b(bachelor'?s|master'?s)\s+degree\b"
    r'|\b\d+\+?\s+years?\s+of\s+experience\b'
    r'|\bequal\s+opportunity\s+employer\b'
    r'|\bsalary\s+(range|search)\b'
    r'|\bjob\s+type\s*[:\-]\s*(contract|full[- ]time|part[- ]time)\b',
    re.IGNORECASE,
)

# A blog/article URL path is a reliable signal regardless of how short the
# collected snippet is — unlike body text, the URL is always available.
_BLOG_URL_PATH_RE = re.compile(
    r'/(blog|resources?|insights?|guides?|articles?|knowledge-base|learn)/',
    re.IGNORECASE,
)

# The piece is talking about the author/agency itself, not asking Novu for
# anything — bylines, company boilerplate, chat-widget greetings, CTAs.
_SELF_PROMO_RE = re.compile(
    r'\bco-?founder\s+of\b'
    r'|\bwritten\s+by\b'
    r'|\babout\s+the\s+author\b'
    r'|\bwelcome\s+to\s+\w[\w.\- ]*!'                       # chat-widget greeting
    r'|\b(our|this)\s+agency\b'
    r'|\bwe\s+(are|’re)\s+a\s+(leading|top|trusted)\b'  # agency self-intro
    r'|\bcontact\s+(us|our\s+team)\s+(today|now)\b'
    r'|\b(get|request)\s+a\s+free\s+(quote|consultation)\b'
    r'|\bschedule\s+a\s+(free\s+)?(call|consultation|demo)\b',
    re.IGNORECASE,
)

# First-person buyer language that overrides a guide-ish title — this is
# what tells a real request for Novu's own services apart from an agency
# explaining, in the abstract, how someone else should go about hiring.
_BUYER_OVERRIDE_RE = re.compile(
    r'\bwe\s+(are|’re)\s+(looking\s+for|seeking|hiring|need)\b'
    r'|\b(our|my)\s+(company|startup|team)\s+(needs|is\s+looking\s+for|is\s+seeking)\b'
    r'|\bplease\s+(contact|reach\s+out|quote)\s+(me|us)\b'
    r'|\brfp\b',
    re.IGNORECASE,
)


def is_known_non_lead_domain(url: str) -> bool:
    """
    True when the URL is on a job board, freelance marketplace, video
    platform, or third-party software/agency directory — see the module
    docstring above this function's section for why these are rejected
    unconditionally, by domain rather than by anything in the text.
    """
    if not url:
        return False
    parsed = urlparse(url)
    netloc = parsed.netloc.lower().split(':')[0]
    if netloc.startswith('www.'):
        netloc = netloc[4:]
    if not netloc:
        return False

    if netloc in _NON_LEAD_DOMAINS or any(netloc.endswith('.' + d) for d in _NON_LEAD_DOMAINS):
        return True

    is_linkedin = netloc in _LINKEDIN_JOBS_DOMAINS or any(
        netloc.endswith('.' + d) for d in _LINKEDIN_JOBS_DOMAINS
    )
    if is_linkedin and _JOB_LISTING_PATH_RE.match(parsed.path or ''):
        return True

    return False


def is_job_description_posting(text: str) -> bool:
    """
    True when the text reads like a job description for an EMPLOYEE —
    "Bachelor's degree", "3+ years of experience", "Equal Opportunity
    Employer" — rather than a buyer describing a PROJECT it wants built.
    Needs two independent JD markers, not one, since a single phrase like
    "years of experience" can legitimately appear in a real request too.
    """
    if not text:
        return False
    return len(_JOB_DESCRIPTION_RE.findall(text)) >= 2


def is_agency_marketing_content(*, title: str = '', text: str = '', url: str = '') -> bool:
    """
    True when a post reads as agency/vendor self-promotion — a guide,
    listicle or marketing article written to attract clients — rather than
    someone asking Novu for services.

    A real buyer statement anywhere in the title or text always wins, so a
    true RFP that happens to use a "Top 5 mistakes" framing is never
    misfiled here. Beyond that:
      - a strong guide/listicle title phrase is sufficient on its own
        (see _STRONG_GUIDE_PHRASE_RE's docstring for why);
      - a weaker "how to <verb> X" title needs a second signal — a
        self-promotional marker in the body, or a blog-ish URL path —
        because body text is often just a short search-result snippet
        that never carries a byline or chat-widget greeting.
    """
    title = title or ''
    text = text or ''
    url = url or ''

    if _BUYER_OVERRIDE_RE.search(text) or _BUYER_OVERRIDE_RE.search(title):
        return False

    if _STRONG_GUIDE_PHRASE_RE.search(title):
        return True

    has_guide_shape = bool(_GUIDE_TITLE_RE.search(title) or _GUIDE_TITLE_RE.search(text[:200]))
    if not has_guide_shape:
        return False

    has_self_promo = bool(_SELF_PROMO_RE.search(text))
    has_blog_path = bool(_BLOG_URL_PATH_RE.search(url))
    return has_self_promo or has_blog_path

# ── Strict "client wants software built" gate ────────────────────────────────
# The radar should surface only posts that read like a Fiverr/Upwork job post:
# a client asking for a developer or for software to be built. Everything else
# (agency articles, hiring guides, employee job ads, directories) is rejected
# before scoring.

# Default ignore words. Editable at runtime from the Settings screen
# ("ignore_keywords"); any match in the title, snippet or URL rejects the post.
DEFAULT_IGNORE_KEYWORDS = [
    'how to hire', 'how to find', 'how do i find', 'how do you find', 'how can i find',
    'where to find', 'where can i find', 'guide', 'tips', 'tutorial', 'course', 'bootcamp',
    'top 10', 'best companies', 'development company', 'development companies',
    'development services', 'our services', 'we offer', 'hire dedicated',
    'hire remote developers', 'cost to build', 'how much does it cost', 'salary',
    'job description', 'interview questions', 'resume', 'template', 'case study',
    # advice / comparison questions, not a request
    'how to build', 'how to make', 'how to create', 'how much does it', 'costs',
    'best way to', 'best place to', 'best sites', 'best freelance', 'where to hire',
    'where should i', 'should i hire', 'should i build', 'anyone recommend',
    'where is a good place', 'where do you find', 'what do i need to', 'recommendations',
    # sellers advertising themselves
    'for hire', 'anyone looking for', 'available for', 'hire expert', 'hire top',
    'hire offshore', 'hire remote', 'risk-free trial', 'try before you pay',
    # employee job listings
    'jobs', 'job openings', 'careers', 'companies hiring', 'results for',
    'position', 'full-time', 'apply now', 'join our team',
]

# Positive signal: the post itself is a client request for software work.
_DEV_ROLE = (
    r'(?:developers?|devs?|programmers?|coders?|engineers?|freelancers?|designers?|'
    r'agency|team|contractors?|expert|someone|somebody|help)'
)
_CLIENT_REQUEST_RE = re.compile(
    r"\b(?:i|we)(?:'m|\s+am|'re|\s+are)?\s+(?:currently\s+)?(?:looking\s+for|seeking|searching\s+for|"
    r"in\s+need\s+of|need|want\s+to\s+hire|would\s+like\s+to\s+hire|hiring)\b"
    r"|\b(?:looking\s+for|seeking|need|hiring|hire)\s+(?:an?\s+|some\s+)?(?:[\w.+#/-]+\s+){0,3}" + _DEV_ROLE + r"\b"
    r"|\bneed\s+(?:someone|somebody|help|a\s+dev\w*)\s+(?:to\s+)?(?:build|develop|create|make|design|code|fix|finish)"
    r"|\b(?:build|develop|create|make)\s+(?:my|our)\s+(?:\w+\s+){0,2}(?:website|app|application|platform|"
    r"software|saas|store|portal|dashboard|tool|system|mvp)\b"
    r"|\b(?:developers?|programmers?|freelancers?|devs?)\s+(?:needed|wanted|required)\b"
    r"|\[(?:hiring|task)\]",
    re.IGNORECASE,
)

# Domain names that belong to software/IT agencies — their pages are marketing,
# even when a snippet quotes an example buyer sentence.
_AGENCY_DOMAIN_RE = re.compile(
    r'(?:technolog|solutions|infotech|softech|softwares?|systems|labs|studio|agency|consult|'
    r'webdesign|appdev|devshop|outsourc|digital|infosys|itservices|webs?olutions)',
    re.IGNORECASE,
)

# Agency/staffing landing pages: "Hire React Native Developers", "Hire a Django
# Developer | Remote or Onsite". A client writes "need/looking for", not an
# imperative "Hire ..." headline.
_HIRE_LANDING_TITLE_RE = re.compile(
    r'^\s*hire\b|\bhire\s+(?:\w+\s+){0,3}developers\b',
    re.IGNORECASE,
)

# Freelance-marketplace URLs that are a CLIENT's project post (not a seller gig).
_MARKETPLACE_PROJECT_RE = re.compile(
    r'(?:upwork\.com/(?:freelance-jobs/apply|jobs)/'
    r'|freelancer\.com/projects/'
    r'|peopleperhour\.com/freelance-jobs/'
    r'|guru\.com/d/jobs/)',
    re.IGNORECASE,
)


def _netloc(url):
    netloc = urlparse(url or '').netloc.lower().split(':')[0]
    return netloc[4:] if netloc.startswith('www.') else netloc


def _parse_keywords(raw):
    if isinstance(raw, (list, tuple)):
        items = raw
    else:
        items = re.split(r'[,\n]', raw or '')
    return [k.strip().lower() for k in items if k and k.strip()]


def get_ignore_keywords():
    """Ignore words from the Settings screen, falling back to the defaults."""
    try:
        from apps.core.operating_settings import get_setting
        raw = get_setting('ignore_keywords')
    except Exception:
        raw = DEFAULT_IGNORE_KEYWORDS
    return _parse_keywords(raw)


def lead_rejection_reason(*, title='', text='', url='', ignore_keywords=None):
    """
    Return a short human-readable reason when the post is NOT a client asking
    for software to be built, or None when it should be kept and scored.
    """
    title, text, url = title or '', text or '', url or ''
    haystack = f'{title}\n{text}'.lower()
    url_l = url.lower()

    keywords = get_ignore_keywords() if ignore_keywords is None else _parse_keywords(ignore_keywords)
    is_marketplace_project = bool(_MARKETPLACE_PROJECT_RE.search(url))

    # Marketplace project URLs contain words like "freelance-jobs", so only
    # their title/text is checked against the ignore words.
    url_words = '' if is_marketplace_project else url_l.replace('-', ' ').replace('_', ' ')
    for kw in keywords:
        pattern = r'(?<!\w)' + re.escape(kw) + r'(?!\w)'
        if re.search(pattern, haystack):
            return f'Ignore word: "{kw}"'
        if url_words and re.search(pattern, url_words):
            return f'Ignore word in URL: "{kw}"'

    if _HIRE_LANDING_TITLE_RE.search(title):
        return 'Agency "Hire developers" landing page'

    if not is_marketplace_project:
        if is_known_non_lead_domain(url):
            return 'Job board / directory / marketplace / video site'
        if _AGENCY_DOMAIN_RE.search(_netloc(url)):
            return 'Software agency website (marketing content)'

    if is_job_description_posting(text):
        return 'Employee job description, not a client project'
    if is_agency_marketing_content(title=title, text=text, url=url):
        return 'Agency guide / marketing article'

    if not is_marketplace_project and not _CLIENT_REQUEST_RE.search(haystack):
        return 'No client request for a developer or software'
    return None
