from django.core.management.base import BaseCommand
from standings.models import Season, Track


class Command(BaseCommand):
    help = 'Update season stats and track records'

    def handle(self, *args, **options):
        for season in Season.objects.all():
            season.update_stats()

        for track in Track.objects.all():
            track.update_records()
