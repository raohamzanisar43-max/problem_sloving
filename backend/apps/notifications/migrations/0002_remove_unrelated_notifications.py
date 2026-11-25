from django.db import migrations


def remove_unrelated(apps, schema_editor):
    # Notifications are only for replies to posts applied to through NovuRadar;
    # earlier ones raised for ordinary mailbox emails (no lead) are removed.
    apps.get_model('notifications', 'Notification').objects.filter(opportunity__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(remove_unrelated, migrations.RunPython.noop),
    ]
