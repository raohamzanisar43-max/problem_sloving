from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .operating_settings import REGISTRY, coerce, snapshot
from .permissions import IsAdmin, IsSalesStaff


@api_view(['GET'])
@permission_classes([AllowAny])
def health(request):
    return Response({
        'status': 'ok',
        'service': 'novu-opportunity-radar',
        'version': '1.0.0',
    })


class OperatingSettingsView(APIView):
    """
    GET  — the operating settings this deployment is actually running.
    PATCH — administrators update the editable ones; others are environment-set.
    """

    def get_permissions(self):
        if self.request.method == 'PATCH':
            return [IsAdmin()]
        return [IsSalesStaff()]

    def get(self, request):
        from apps.scoring.llm import active_provider

        return Response({
            'settings': snapshot(),
            'editable': request.user.is_admin_role,
            'provider': active_provider(),
        })

    def patch(self, request):
        from .models import AppSetting

        updates = request.data if isinstance(request.data, dict) else {}
        unknown = [k for k in updates if k not in REGISTRY]
        if unknown:
            return Response({'detail': f'Unknown setting(s): {", ".join(sorted(unknown))}'}, status=400)

        errors = {}
        cleaned = {}
        for key, raw in updates.items():
            try:
                cleaned[key] = coerce(key, raw)
            except ValueError as exc:
                errors[key] = str(exc)
        if errors:
            return Response({'detail': 'Invalid values.', 'errors': errors}, status=400)

        for key, value in cleaned.items():
            AppSetting.objects.update_or_create(
                pk=key, defaults={'value': value, 'updated_by': request.user},
            )

        return Response({'settings': snapshot(), 'editable': True, 'updated': sorted(cleaned)})
