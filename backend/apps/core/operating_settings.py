"""
The operating settings surfaced on the Settings screen.

Each entry declares where its default comes from and whether an administrator
may change it at runtime. Editable values are persisted in `AppSetting`;
everything else is reported read-only so the screen shows what the deployment
is actually running rather than a hard-coded illustration.
"""
from django.conf import settings


def _radar(key, fallback=None):
    return settings.RADAR.get(key, fallback)


# key -> definition. `default` is a callable so environment changes are picked
# up without reimporting this module.
REGISTRY = {
    'qualification_confidence': {
        'label': 'Qualification confidence',
        'description': 'Below this level, extracted leads are held for review instead of entering the queue.',
        'type': 'float',
        'editable': True,
        'min': 0.0,
        'max': 1.0,
        'default': lambda: _radar('QUALIFICATION_CONFIDENCE', 0.75),
    },
    'collection_interval_minutes': {
        'label': 'Collection schedule',
        'description': 'How often enabled sources are polled. Source adapter limits still apply.',
        'type': 'int',
        'editable': True,
        'min': 5,
        'max': 1440,
        'unit': 'minutes',
        'default': lambda: _radar('COLLECTION_INTERVAL_MINUTES', 15),
    },
    'duplicate_similarity_threshold': {
        'label': 'Duplicate similarity threshold',
        'description': 'Pairs at or above this cosine similarity are raised for manager review.',
        'type': 'float',
        'editable': True,
        'min': 0.5,
        'max': 1.0,
        'default': lambda: _radar('DUPLICATE_SIMILARITY_THRESHOLD', 0.80),
    },
    'alert_min_score': {
        'label': 'Alert threshold',
        'description': 'Leads scoring at or above this value raise an internal email alert.',
        'type': 'int',
        'editable': True,
        'min': 0,
        'max': 100,
        'default': lambda: _radar('ALERT_MIN_SCORE', 80),
    },
    'alert_email': {
        'label': 'Alert recipient',
        'description': 'Internal mailbox for high-score alerts. Leave blank to disable alerting.',
        'type': 'str',
        'editable': True,
        'default': lambda: _radar('ALERT_EMAIL', ''),
    },
    'excerpt_retention_days': {
        'label': 'Retention proposal',
        'description': 'How long source excerpts are retained. Review source conditions before changing.',
        'type': 'int',
        'editable': True,
        'min': 1,
        'max': 3650,
        'unit': 'days',
        'default': lambda: _radar('EXCERPT_RETENTION_DAYS', 90),
    },
    'report_timezone': {
        'label': 'Report timezone',
        'description': 'All events are stored in UTC and displayed in this timezone.',
        'type': 'str',
        'editable': False,
        'default': lambda: settings.TIME_ZONE,
    },
    'llm_provider': {
        'label': 'Extraction provider',
        'description': 'Set with the LLM_PROVIDER environment variable. "stub" runs fully offline.',
        'type': 'str',
        'editable': False,
        'default': lambda: _radar('LLM_PROVIDER', 'stub'),
    },
    'external_outreach': {
        'label': 'External outreach',
        'description': 'Sales drafts are prepared for human review. The MVP never sends messages automatically.',
        'type': 'str',
        'editable': False,
        'default': lambda: 'Manual send',
    },
    'default_markets': {
        'label': 'Pilot markets',
        'description': 'Default markets for the starter query groups.',
        'type': 'str',
        'editable': False,
        'default': lambda: ', '.join(_radar('DEFAULT_MARKETS', []) or []),
    },
}

_CASTS = {
    'int': int,
    'float': float,
    'str': str,
}


def get_setting(key):
    """Resolve one setting: database override first, environment default second."""
    definition = REGISTRY[key]
    from .models import AppSetting

    if definition['editable']:
        try:
            row = AppSetting.objects.filter(pk=key).first()
        except Exception:
            # Table not migrated yet (e.g. during the initial migrate run).
            row = None
        if row is not None:
            return row.value
    return definition['default']()


def coerce(key, raw):
    """
    Validate and cast an incoming value for `key`.

    Raises ValueError with a human-readable message when the value is not
    acceptable, so the API can return it directly.
    """
    definition = REGISTRY[key]
    if not definition['editable']:
        raise ValueError(f'{definition["label"]} is set by the deployment environment and cannot be edited here.')

    cast = _CASTS[definition['type']]
    try:
        value = cast(raw)
    except (TypeError, ValueError):
        raise ValueError(f'{definition["label"]} must be a {definition["type"]}.')

    if 'min' in definition and value < definition['min']:
        raise ValueError(f'{definition["label"]} must be at least {definition["min"]}.')
    if 'max' in definition and value > definition['max']:
        raise ValueError(f'{definition["label"]} must be at most {definition["max"]}.')
    return value


def snapshot():
    """Every setting with its resolved value, for the Settings screen."""
    items = []
    for key, definition in REGISTRY.items():
        items.append({
            'key': key,
            'label': definition['label'],
            'description': definition['description'],
            'type': definition['type'],
            'editable': definition['editable'],
            'unit': definition.get('unit', ''),
            'min': definition.get('min'),
            'max': definition.get('max'),
            'value': get_setting(key),
        })
    return items
