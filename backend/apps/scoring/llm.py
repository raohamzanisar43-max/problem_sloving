"""
LLM client factory — stub / OpenAI / Gemini.
All clients implement:
  extract(text: str) -> dict   # opportunity fields from raw text
  draft(opportunity) -> str    # outreach email draft
"""
import json
import logging
from django.conf import settings
from .capability_profile import profile_summary, CAPABILITY_PROFILE

logger = logging.getLogger(__name__)

EXTRACTION_SCHEMA = {
    'requirement': 'str — one sentence summary of the buyer requirement',
    'intent': 'buyer | nonbuyer | uncertain',
    'kind': 'direct_purchase | rfp | agency_staffing | hiring_signal | indirect_pain | seller_promotion | other',
    'primary_category': 'ERP | CRM | LMS | MOBILE_APP | WEBSITE | CUSTOM_DEV | AI_AUTOMATION | STAFF_AUGMENTATION | MANAGED_IT | CLOUD_DEVOPS | CYBERSECURITY | (leave blank if none)',
    'categories': 'list of matching categories from above',
    'technology': 'list of technologies mentioned',
    'company_name': 'str or blank',
    'company_domain': 'str or blank',
    'country': 'str or blank',
    'industry': 'str or blank',
    'budget_text': 'str or blank — exact budget mention if present',
    'deadline': 'YYYY-MM-DD or null',
    'email': 'str or blank',
    'phone': 'str or blank',
    'contact_name': 'str or blank',
    'confidence': 'float 0.0–1.0 — your extraction confidence',
}


EXTRACTION_GUIDANCE = (
    'Novu Labs sells websites, e-commerce sites, web applications, mobile apps, ERP/CRM/LMS systems, '
    'AI and automation, and other custom software projects. Judge the text as a sales researcher looking '
    'for BUYERS who want to commission such a project. '
    'Use intent=buyer with kind=direct_purchase (or rfp for a formal tender/proposal request) only when the '
    'author or organisation is seeking to have a website or software project built or bought. '
    'Job postings, recruitment, vacancies, internships and "join our team" text are kind=hiring_signal with '
    'intent=uncertain. '
    'Agencies, freelancers, platforms or companies advertising their own services, portfolios, pricing, '
    'templates, tutorials, "top 10" lists and directories are intent=nonbuyer with kind=seller_promotion. '
    'Use primary_category WEBSITE for website, redesign or e-commerce needs, and the matching category for '
    'larger projects. Give the buyer country when stated, and keep confidence low when the text is vague.'
)


def extraction_system_prompt() -> str:
    return (
        'You are an opportunity extraction assistant. '
        'Extract structured fields from the given source text. '
        f'{EXTRACTION_GUIDANCE} '
        f'Return ONLY valid JSON matching this schema: {json.dumps(EXTRACTION_SCHEMA)}. '
        'Do not infer facts not present in the text. Set unknown fields to blank or null.'
    )


class StubClient:
    """Offline stub — returns template-level output without any API call."""

    def extract(self, text: str) -> dict:
        return {
            'requirement': text[:120],
            'intent': 'uncertain',
            'kind': 'other',
            'primary_category': '',
            'categories': [],
            'technology': [],
            'company_name': '',
            'company_domain': '',
            'country': '',
            'industry': '',
            'budget_text': '',
            'deadline': None,
            'email': '',
            'phone': '',
            'contact_name': '',
            'confidence': 0.0,
        }

    def draft(self, opportunity) -> tuple[str, str]:
        """Returns (content, model_version)."""
        svc = opportunity.primary_category or 'software services'
        text = (
            f"Hi,\n\n"
            f"We came across your requirement: {opportunity.requirement}.\n\n"
            f"Novu Labs specialises in {svc} and would love to explore how we can help.\n\n"
            f"Could we schedule a 20-minute call this week?\n\n"
            f"Best regards,\n"
            f"Novu Sales Team\n"
            f"{CAPABILITY_PROFILE['contact']['email']} | {CAPABILITY_PROFILE['contact']['website']}"
        )
        return text, 'template-v1'


class OpenAIClient:
    def __init__(self):
        import openai
        self._client = openai.OpenAI(api_key=settings.RADAR['LLM_API_KEY'])
        self._model = settings.RADAR.get('LLM_MODEL', 'gpt-4o-mini')

    def extract(self, text: str) -> dict:
        system = extraction_system_prompt()
        try:
            resp = self._client.chat.completions.create(
                model=self._model,
                messages=[{'role': 'system', 'content': system},
                           {'role': 'user', 'content': text[:3000]}],
                response_format={'type': 'json_object'},
                temperature=0,
            )
            return json.loads(resp.choices[0].message.content)
        except Exception as exc:
            logger.error('OpenAI extract failed: %s', exc)
            return StubClient().extract(text)

    def draft(self, opportunity) -> tuple[str, str]:
        profile = profile_summary()
        prompt = (
            f"Company profile:\n{profile}\n\n"
            f"Buyer requirement: {opportunity.requirement}\n"
            f"Company: {opportunity.company_name or 'Unknown'}\n"
            f"Category: {opportunity.primary_category or 'software services'}\n"
            f"Budget: {opportunity.budget_text or 'not stated'}\n\n"
            "Write a concise, professional outreach email (≤150 words) from Novu Labs "
            "to this prospect. Be specific about how Novu can help. "
            "Do not make up facts. End with a clear call to action."
        )
        try:
            resp = self._client.chat.completions.create(
                model=self._model,
                messages=[{'role': 'user', 'content': prompt}],
                temperature=0.4,
            )
            content = resp.choices[0].message.content
            return content, f'{self._model}-draft-v1'
        except Exception as exc:
            logger.error('OpenAI draft failed: %s', exc)
            return StubClient().draft(opportunity)


class GeminiClient:
    def __init__(self):
        from google import genai
        self._client = genai.Client(api_key=settings.RADAR['LLM_API_KEY'])
        self._model = settings.RADAR.get('LLM_MODEL', 'gemini-2.0-flash')

    def extract(self, text: str) -> dict:
        system = extraction_system_prompt()
        try:
            resp = self._client.models.generate_content(
                model=self._model,
                contents=f'{system}\n\nText to analyse:\n{text[:3000]}',
            )
            raw = resp.text.strip()
            # Strip markdown fences if present
            if raw.startswith('```'):
                raw = raw.split('```')[1]
                if raw.startswith('json'):
                    raw = raw[4:]
            return json.loads(raw)
        except Exception as exc:
            logger.error('Gemini extract failed: %s', exc)
            return StubClient().extract(text)

    def draft(self, opportunity) -> tuple[str, str]:
        profile = profile_summary()
        prompt = (
            f"Company profile:\n{profile}\n\n"
            f"Buyer requirement: {opportunity.requirement}\n"
            f"Company: {opportunity.company_name or 'Unknown'}\n"
            f"Category: {opportunity.primary_category or 'software services'}\n"
            f"Budget: {opportunity.budget_text or 'not stated'}\n\n"
            "Write a concise, professional outreach email (≤150 words) from Novu Labs "
            "to this prospect. Be specific about how Novu can help. "
            "Do not make up facts. End with a clear call to action."
        )
        try:
            resp = self._client.models.generate_content(model=self._model, contents=prompt)
            return resp.text, f'{self._model}-draft-v1'
        except Exception as exc:
            logger.error('Gemini draft failed: %s', exc)
            return StubClient().draft(opportunity)

class GroqClient:
    """
    Groq's free tier allows far more requests per day than Gemini's free
    tier, so this is used once the Gemini daily quota runs out. Groq exposes
    an OpenAI-compatible API, so this re-uses the `openai` package with a
    different base URL.
    """
    def __init__(self):
        import openai
        self._client = openai.OpenAI(
            api_key=settings.RADAR['LLM_API_KEY'],
            base_url='https://api.groq.com/openai/v1',
        )
        self._model = settings.RADAR.get('LLM_MODEL', 'llama-3.3-70b-versatile')

    def extract(self, text: str) -> dict:
        system = extraction_system_prompt()
        try:
            resp = self._client.chat.completions.create(
                model=self._model,
                messages=[{'role': 'system', 'content': system},
                           {'role': 'user', 'content': text[:3000]}],
                response_format={'type': 'json_object'},
                temperature=0,
            )
            return json.loads(resp.choices[0].message.content)
        except Exception as exc:
            logger.error('Groq extract failed: %s', exc)
            return StubClient().extract(text)

    def draft(self, opportunity) -> tuple[str, str]:
        profile = profile_summary()
        prompt = (
            f"Company profile:\n{profile}\n\n"
            f"Buyer requirement: {opportunity.requirement}\n"
            f"Company: {opportunity.company_name or 'Unknown'}\n"
            f"Category: {opportunity.primary_category or 'software services'}\n"
            f"Budget: {opportunity.budget_text or 'not stated'}\n\n"
            "Write a concise, professional outreach email (≤150 words) from Novu Labs "
            "to this prospect. Be specific about how Novu can help. "
            "Do not make up facts. End with a clear call to action."
        )
        try:
            resp = self._client.chat.completions.create(
                model=self._model,
                messages=[{'role': 'user', 'content': prompt}],
                temperature=0.4,
            )
            content = resp.choices[0].message.content
            return content, f'{self._model}-draft-v1'
        except Exception as exc:
            logger.error('Groq draft failed: %s', exc)
            return StubClient().draft(opportunity)
PROVIDERS = {
    'openai': (OpenAIClient, 'openai'),
    'azure': (OpenAIClient, 'openai'),
    'gemini': (GeminiClient, 'google-genai'),
    'groq': (GroqClient, 'openai'),
    'stub': (StubClient, None),
}


def LLMClient():
    """
    Factory — returns the client for the configured LLM_PROVIDER.

    A misconfigured provider falls back to the offline stub rather than taking
    the pipeline down, but it is logged at error level: silently producing
    template text while the operator believes a real model is running would be
    worse than a noisy failure.
    """
    provider = (settings.RADAR.get('LLM_PROVIDER') or 'stub').lower()
    if provider not in PROVIDERS:
        logger.error(
            'LLM_PROVIDER=%r is not recognised (expected one of %s) — using the offline stub.',
            provider, ', '.join(sorted(PROVIDERS)),
        )
        return StubClient()

    client_class, package = PROVIDERS[provider]
    if client_class is StubClient:
        return StubClient()

    try:
        return client_class()
    except ImportError as exc:
        logger.error(
            'LLM_PROVIDER=%s but the %s package is not installed (%s) — '
            'falling back to the offline stub. Run: pip install %s',
            provider, package, exc, package,
        )
    except Exception as exc:
        logger.error(
            'LLM_PROVIDER=%s could not be initialised (%s) — falling back to the offline stub.',
            provider, exc,
        )
    return StubClient()


def active_provider():
    """The provider actually in use, for display on the Settings screen."""
    configured = (settings.RADAR.get('LLM_PROVIDER') or 'stub').lower()
    client = LLMClient()
    resolved = 'stub' if isinstance(client, StubClient) else configured
    return {'configured': configured, 'active': resolved, 'degraded': resolved != configured}

