from django.db import migrations, models

REDDIT_SETTINGS = {
    'lookback': '14 hours',
    'first_lookback': '3 days',
    'max_posts_per_subreddit': 60,
    'max_posts_per_phrase': 15,
    'max_charge_usd_per_call': 0.3,
}


def enable_reddit(apps, schema_editor):
    # Reddit posts now come through Apify (APIFY_TOKEN), so the source is turned
    # on; without a token its runs simply report that the token is missing.
    Source = apps.get_model('sources', 'Source')
    source = Source.objects.filter(connector_type='reddit').order_by('created_at').first()
    if source is None:
        source = Source(connector_type='reddit')
    source.name = 'Reddit'
    source.enabled = True
    source.access_state = 'ready'
    source.planned_route = 'Apify automation-lab/reddit-scraper: hiring subreddits + client phrases'
    source.settings = {**(source.settings or {}), **REDDIT_SETTINGS}
    source.save()


def disable_reddit(apps, schema_editor):
    apps.get_model('sources', 'Source').objects.filter(connector_type='reddit').update(enabled=False)


class Migration(migrations.Migration):

    dependencies = [
        ('sources', '0002_freelancer_source'),
    ]

    operations = [
        migrations.AlterField(
            model_name='source',
            name='connector_type',
            field=models.CharField(choices=[('web_search', 'Licensed web search'), ('rss', 'RSS / public website'), ('rfp_portal', 'RFP / tender portal'), ('x', 'X (Twitter) recent search'), ('reddit', 'Reddit hiring posts (via Apify)'), ('linkedin', 'LinkedIn (conditional)'), ('manual', 'Manual capture'), ('freelancer', 'Freelancer.com projects')], max_length=32),
        ),
        migrations.RunPython(enable_reddit, disable_reddit),
    ]
