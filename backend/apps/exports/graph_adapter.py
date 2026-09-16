"""
Microsoft Graph workbook adapter.
Writes opportunities to a named Excel Online table via the Graph API.
Requires MSAL (already in requirements.txt via msal>=1.28).

Usage:
  adapter = GraphAdapter()
  if adapter.is_configured():
      adapter.append_rows(opportunities_queryset)
"""
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

# Column mapping: Opportunity field -> Excel column header
COLUMN_MAP = [
    ('public_id', 'ID'),
    ('requirement', 'Requirement'),
    ('company_name', 'Company'),
    ('country', 'Country'),
    ('primary_category', 'Service'),
    ('score', 'Score'),
    ('band', 'Band'),
    ('status', 'Status'),
    ('email', 'Email'),
    ('budget_text', 'Budget'),
    ('source_url', 'Source URL'),
    ('source_published_at', 'Published'),
    ('detected_at', 'Detected'),
]


class GraphAdapter:
    """
    Connects to Microsoft Graph and writes/updates rows in a cloud workbook.
    Feature-flagged: only active when MS_GRAPH_CLIENT_ID is configured.
    """

    def __init__(self):
        r = settings.RADAR
        self._client_id = r.get('MS_GRAPH_CLIENT_ID', '')
        self._client_secret = r.get('MS_GRAPH_CLIENT_SECRET', '')
        self._tenant_id = r.get('MS_GRAPH_TENANT_ID', '')
        self._workbook_id = r.get('MS_GRAPH_WORKBOOK_ID', '')
        self._table_name = r.get('MS_GRAPH_TABLE_NAME', 'OpportunityRadar')
        self._token = None

    def is_configured(self) -> bool:
        return bool(self._client_id and self._client_secret and self._tenant_id)

    def _acquire_token(self) -> str:
        import msal
        authority = f'https://login.microsoftonline.com/{self._tenant_id}'
        app = msal.ConfidentialClientApplication(
            self._client_id,
            authority=authority,
            client_credential=self._client_secret,
        )
        result = app.acquire_token_for_client(
            scopes=['https://graph.microsoft.com/.default']
        )
        if 'access_token' not in result:
            raise RuntimeError(f'MSAL token error: {result.get("error_description", result)}')
        return result['access_token']

    def _headers(self) -> dict:
        if not self._token:
            self._token = self._acquire_token()
        return {
            'Authorization': f'Bearer {self._token}',
            'Content-Type': 'application/json',
        }

    def _row(self, opp) -> list:
        row = []
        for field, _ in COLUMN_MAP:
            val = getattr(opp, field, '')
            if val is None:
                val = ''
            elif hasattr(val, 'isoformat'):
                val = val.isoformat()
            else:
                val = str(val)
            row.append(val)
        return row

    def append_rows(self, opportunities, sync_job=None) -> int:
        import httpx
        if not self.is_configured():
            logger.warning('GraphAdapter not configured — skipping write')
            return 0
        if not self._workbook_id:
            raise RuntimeError('MS_GRAPH_WORKBOOK_ID must be set')

        url = (
            f'https://graph.microsoft.com/v1.0/me/drive/items/'
            f'{self._workbook_id}/workbook/tables/\'{self._table_name}\'/rows/add'
        )
        rows = [self._row(o) for o in opportunities]
        payload = {'values': rows}

        with httpx.Client(timeout=30) as client:
            resp = client.post(url, json=payload, headers=self._headers())
            resp.raise_for_status()

        logger.info('GraphAdapter: wrote %d rows to workbook', len(rows))
        if sync_job:
            sync_job.counters = {'rows_written': len(rows)}
            sync_job.state = 'completed'
            from django.utils import timezone
            sync_job.finished_at = timezone.now()
            sync_job.save(update_fields=['counters', 'state', 'finished_at'])

        return len(rows)

