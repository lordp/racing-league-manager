from django.core.management.base import BaseCommand
from standings.models import Season, Track
import logging

class Command(BaseCommand):
    help = 'Update season stats and track records'

    def handle(self, *args, **options):
        logger = logging.getLogger(__name__)

        for season in Season.objects.all():
            logger.info('Updating stats for {}'.format(season.name))
            season.update_stats()

        for track in Track.objects.all():
            logger.info('Updating records for {}'.format(track.name))
            track.update_records()
