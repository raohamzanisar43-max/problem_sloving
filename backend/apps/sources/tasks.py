"""
Celery tasks for the collection, extraction and duplicate-detection pipeline.

Every task here is also callable synchronously, so the whole pipeline can be
exercised with `python manage.py run_collection` on a machine with no broker.
"""
import importlib
import logging
import math
import re
from collections import Counter

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from apps.core.operating_settings import get_setting

logger = logging.getLogger(__name__)

COLLECTOR_MAP = {
    'web_search': 'apps.sources.collectors.brave.BraveCollector',
    'x': 'apps.sources.collectors.x_collector.XCollector',
    'reddit': 'apps.sources.collectors.reddit_collector.RedditCollector',
    'rss': 'apps.sources.collectors.rss_collector.RSSCollector',
    'rfp_portal': 'apps.sources.collectors.rss_collector.RSSCollector',
}


def _import_collector(dotted_path):
    module_path, class_name = dotted_path.rsplit('.', 1)
    mod = importlib.import_module(module_path)
    return getattr(mod, class_name)


def _extract_and_score(observation, source, llm):
    """
    Run extraction + scoring for one Observation and persist the resulting
    Opportunity, its evidence link, any published contact and its outbox event.

    Returns the Opportunity, or None when the observation was not qualified.
    """
    from apps.contacts.models import Contact
    from apps.exports.outbox import emit_for_opportunity
    from apps.opportunities.models import Opportunity, OpportunityObservation
    from apps.scoring.engine import compute_score
    from apps.sources.content_filters import lead_rejection_reason

    # Agency/vendor marketing guides are rejected before scoring, without
    # spending an LLM call: the model reliably reads "how to find a
    # developer" as buyer language even when the author is the one selling,
    # so this deterministic check is a cheaper and more reliable net than an
    # LLM classification call alone (see content_filters.py).
    # A lead a person captured by hand is never filtered out.
    rejection = None if source.connector_type == 'manual' else lead_rejection_reason(
        title=observation.title, text=observation.text, url=observation.original_url,
    )
    if rejection:
        fields = {
            'requirement': (observation.title or observation.text[:120]),
            'intent': 'nonbuyer',
            'kind': 'seller_promotion',
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
            'confidence': 1.0,
        }
    else:
        fields = llm.extract(observation.text) or {}

    score_result = compute_score(
        intent=fields.get('intent', 'uncertain'),
        kind=fields.get('kind', 'other'),
        categories=fields.get('categories', []),
        published_at=observation.source_published_at,
        has_quote=bool(observation.text),
        has_full_text=len(observation.text) > 100,
        email=fields.get('email', ''),
        phone=fields.get('phone', ''),
        source_url=observation.original_url,
        deadline=fields.get('deadline'),
    )

    confidence = float(fields.get('confidence') or 0.0)
    threshold = float(get_setting('qualification_confidence'))
    status = score_result.get('status_override') or 'new'
    review_reasons = list(score_result['review_reasons'])
    if rejection:
        # Distinct prefix from REFILTER_PREFIX: these were never extracted by the
        # model, so they must not be "restored" when an ignore word is removed.
        review_reasons.insert(0, f'Filtered out at collection: {rejection}')

    # A low-confidence extraction never lands straight in the sales queue.
    if status == 'new' and confidence < threshold:
        status = 'review'
        review_reasons.append(
            f'Extraction confidence {confidence:.2f} below threshold {threshold:.2f}'
        )

    with transaction.atomic():
        opportunity = Opportunity.objects.create(
            requirement=fields.get('requirement') or observation.title or observation.text[:120],
            text=observation.text[:2000],
            intent=fields.get('intent', 'uncertain'),
            kind=fields.get('kind', 'other'),
            confidence=confidence,
            primary_category=fields.get('primary_category', '') or '',
            categories=fields.get('categories', []) or [],
            technology=fields.get('technology', []) or [],
            company_name=fields.get('company_name', '') or '',
            company_domain=fields.get('company_domain', '') or '',
            country=fields.get('country', '') or '',
            industry=fields.get('industry', '') or '',
            budget_text=fields.get('budget_text', '') or '',
            deadline=fields.get('deadline') or None,
            email=fields.get('email', '') or '',
            phone=fields.get('phone', '') or '',
            contact_name=fields.get('contact_name', '') or '',
            contact_evidence_url=observation.original_url if (fields.get('email') or fields.get('phone')) else '',
            contact_verification='published' if (fields.get('email') or fields.get('phone')) else '',
            source_url=observation.original_url,
            source_name=source.name,
            source_published_at=observation.source_published_at,
            score=score_result['score'],
            band=score_result['band'],
            score_factors=score_result['factors'],
            review_reasons=review_reasons,
            status=status,
        )
        OpportunityObservation.objects.create(
            opportunity=opportunity,
            observation=observation,
            is_canonical=True,
        )
        # A published contact is stored with its provenance so the sales team
        # can always see where the address came from (handover §8).
        if opportunity.email or opportunity.phone:
            Contact.objects.create(
                opportunity=opportunity,
                company_name=opportunity.company_name,
                company_domain=opportunity.company_domain,
                name=opportunity.contact_name,
                email=opportunity.email,
                phone=opportunity.phone,
                evidence_url=observation.original_url,
                verification='published',
                is_primary=True,
                fetched_at=timezone.now(),
            )
        emit_for_opportunity(opportunity, reason='collected')

    return opportunity


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def collect_source(self, source_id, run_id=None):
    """
    Run the collector for a single Source and pipe new Observations through
    the scoring engine to create Opportunity records.

    When `run_id` is supplied the existing Run row is reused, so a manually
    triggered run does not produce a second, orphaned record.
    """
    from apps.observations.models import Observation
    from apps.scoring.llm import LLMClient
    from apps.sources.models import Run, SearchTerm, Source

    try:
        source = Source.objects.get(pk=source_id)
    except Source.DoesNotExist:
        logger.error('Source %s not found', source_id)
        return {'error': 'source_not_found'}

    run = None
    if run_id:
        run = Run.objects.filter(pk=run_id).first()
    if run is None:
        run = Run.objects.create(source=source, state='queued', trigger='schedule')
    if run.source_id is None:
        run.source = source
        run.save(update_fields=['source'])

    if not source.enabled:
        logger.info('Source %s is disabled — skipping', source.name)
        run.counters = {'skipped': 'source disabled'}
        run.save(update_fields=['counters'])
        run.mark_finished(state='completed')
        return run.counters

    collector_path = COLLECTOR_MAP.get(source.connector_type)
    if not collector_path:
        logger.warning('No collector for type %s', source.connector_type)
        run.counters = {'skipped': f'no collector for {source.connector_type}'}
        run.save(update_fields=['counters'])
        run.mark_finished(state='completed')
        return run.counters

    try:
        collector = _import_collector(collector_path)(source)
    except Exception as exc:
        # A missing optional dependency or a broken adapter fails this source
        # only; the scheduled sweep carries on with the rest.
        logger.exception('Collector %s unavailable: %s', collector_path, exc)
        message = f'Collector unavailable: {exc}'
        source.last_error = message[:500]
        source.save(update_fields=['last_error'])
        run.counters = {'errors': 1}
        run.save(update_fields=['counters'])
        run.mark_finished(state='failed', error=message[:500])
        return run.counters

    terms = list(source.search_terms.filter(enabled=True))
    if not terms:
        # Use the shared term list when none are attached to this source.
        terms = list(SearchTerm.objects.filter(enabled=True, source__isnull=True))

    fetched, new_count, duplicates, errors = collector.run(run, terms)
    logger.info('Source %s: %d new observations', source.name, new_count)

    # ── Extraction + scoring for each unprocessed observation ──
    llm = LLMClient()
    unprocessed = Observation.objects.filter(
        source=source,
        linked_opportunities__isnull=True,
    ).order_by('-fetched_at')[:200]

    qualified = 0
    extraction_errors = 0
    for obs in unprocessed:
        try:
            if _extract_and_score(obs, source, llm):
                qualified += 1
        except Exception as exc:
            extraction_errors += 1
            logger.exception('Extraction failed for observation %s: %s', obs.id, exc)

    counters = {
        'fetched': fetched,
        'new': new_count,
        'duplicates': duplicates,
        'errors': len(errors) + extraction_errors,
        'qualified': qualified,
    }
    run.counters = counters
    run.save(update_fields=['counters'])
    state = 'partial' if (errors or extraction_errors) else 'completed'
    run.mark_finished(state=state, error='; '.join(errors))
    return counters


@shared_task
def collect_all_sources():
    """
    Scheduled entry point: run every enabled source in turn.

    One failing connector must not stop the others (handover §15), so each
    source is isolated and its failure recorded on its own Run.
    """
    from apps.sources.models import Source

    results = {}
    for source in Source.objects.filter(enabled=True).exclude(connector_type='manual'):
        try:
            results[source.name] = collect_source(str(source.id))
        except Exception as exc:
            logger.exception('Source %s failed: %s', source.name, exc)
            results[source.name] = {'error': str(exc)[:200]}
    return results


# ── Duplicate detection ───────────────────────────────────────────────────────

_TOKEN_RE = re.compile(r'[a-z0-9]+')


def _tokens(text):
    """Unigrams plus bigrams, lowercased — enough signal for short requirements."""
    words = _TOKEN_RE.findall((text or '').lower())
    bigrams = [f'{a}_{b}' for a, b in zip(words, words[1:])]
    return words + bigrams


def _tfidf_vectors(documents):
    """
    Build L2-normalised tf-idf vectors with the standard library only.

    Avoids pulling scikit-learn and numpy (~100 MB) into the runtime image for
    what is a handful of short strings.
    """
    token_lists = [_tokens(d) for d in documents]
    n_docs = len(token_lists)

    document_frequency = Counter()
    for tokens in token_lists:
        document_frequency.update(set(tokens))

    vectors = []
    for tokens in token_lists:
        counts = Counter(tokens)
        total = sum(counts.values()) or 1
        vector = {}
        for token, count in counts.items():
            tf = count / total
            idf = math.log((1 + n_docs) / (1 + document_frequency[token])) + 1.0
            vector[token] = tf * idf
        norm = math.sqrt(sum(w * w for w in vector.values()))
        if norm:
            vector = {t: w / norm for t, w in vector.items()}
        vectors.append(vector)
    return vectors


def _cosine(a, b):
    if len(a) > len(b):
        a, b = b, a
    return sum(weight * b.get(token, 0.0) for token, weight in a.items())


@shared_task
def find_duplicates(threshold=None):
    """
    Detect near-duplicate Opportunities by tf-idf cosine similarity and record
    each pair above the threshold as a DuplicateCandidate for manager review.
    """
    from apps.opportunities.models import DuplicateCandidate, Opportunity

    if threshold is None:
        threshold = float(get_setting('duplicate_similarity_threshold'))

    rows = list(
        Opportunity.objects.exclude(status__in=['rejected', 'closed'])
        .order_by('-detected_at')
        .values('id', 'requirement', 'company_name')[:500]
    )
    if len(rows) < 2:
        return 0

    documents = [f"{r['requirement']} {r['company_name']}" for r in rows]
    vectors = _tfidf_vectors(documents)
    ids = [str(r['id']) for r in rows]

    created = 0
    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            similarity = _cosine(vectors[i], vectors[j])
            if similarity < threshold:
                continue
            id_a, id_b = sorted([ids[i], ids[j]])
            # The pair is ordered so the same two records cannot be recorded
            # twice under swapped column assignments.
            _, was_created = DuplicateCandidate.objects.get_or_create(
                opportunity_a_id=id_a,
                opportunity_b_id=id_b,
                defaults={'similarity': similarity, 'decision': 'pending'},
            )
            if was_created:
                created += 1

    logger.info('find_duplicates: %d new candidate pairs', created)
    return created