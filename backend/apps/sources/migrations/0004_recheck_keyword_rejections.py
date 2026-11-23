from django.db import migrations

# Keywords written with search syntax ("-jobs -hiring ...", OR) used to fail the
# keyword gate for every post. Leads rejected only for that reason are removed so
# their posts are processed again, with the corrected matching, on the source's
# next run (unlinked observations are always re-processed).
KEYWORD_REJECTION = 'Filtered out at collection: Does not match any search keyword'


def recheck(apps, schema_editor):
    Opportunity = apps.get_model('opportunities', 'Opportunity')
    stale = [
        pk for pk, reasons in Opportunity.objects.filter(status='rejected').values_list('id', 'review_reasons')
        if reasons and reasons[0] == KEYWORD_REJECTION
    ]
    for start in range(0, len(stale), 500):
        Opportunity.objects.filter(pk__in=stale[start:start + 500]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('sources', '0003_reddit_via_apify'),
        ('opportunities', '0002_add_advisory_categories'),
        ('observations', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(recheck, migrations.RunPython.noop),
    ]
