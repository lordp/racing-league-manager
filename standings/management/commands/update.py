from django.core.management.base import BaseCommand, CommandError
from standings.models import SeasonStats, Season


class Command(BaseCommand):
    help = 'Update season stats and track records'

    def handle(self, *args, **options):
        for season in Season.objects.all():
            season.update_stats()
