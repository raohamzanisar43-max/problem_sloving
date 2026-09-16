from django.conf import settings as dj_settings
from django.db import models


class AppSetting(models.Model):
    """
    Administrator-editable operating setting.

    Values here override the environment defaults in ``settings.RADAR`` at
    runtime, so the pilot can be tuned without a redeploy. Credentials are
    deliberately NOT stored here — those stay in the environment (handover §13).
    """
    key = models.CharField(max_length=64, primary_key=True)
    value = models.JSONField()
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        dj_settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
    )

    class Meta:
        ordering = ['key']

    def __str__(self):
        return f'{self.key}={self.value}'
