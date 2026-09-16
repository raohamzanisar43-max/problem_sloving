from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Roles from handover:
    - admin: credentials, source settings
    - sales_manager: review duplicates, assignment, all sales records
    - sales_executive: assigned opportunities + limited export
    """
    ROLE_CHOICES = [
        ('admin', 'Administrator'),
        ('sales_manager', 'Sales Manager'),
        ('sales_executive', 'Sales Executive'),
    ]
    role = models.CharField(max_length=32, choices=ROLE_CHOICES, default='sales_executive')
    display_name = models.CharField(max_length=120, blank=True)

    def __str__(self):
        return self.display_name or self.username

    @property
    def is_admin_role(self):
        return self.role == 'admin' or self.is_superuser

    @property
    def is_manager_role(self):
        return self.role in ('admin', 'sales_manager') or self.is_superuser
