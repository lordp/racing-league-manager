from django.core.management.base import BaseCommand, CommandError
from standings.models import *
import json
from datetime import datetime, timezone
import time


class Command(BaseCommand):
    help = 'Import FSR results'

    def handle_datetime(self, start_time):
        d = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
        t = time.mktime(d.timetuple())

        return datetime.fromtimestamp(t, timezone.utc).replace(hour=14)

    def add_arguments(self, parser):
        parser.add_argument('filename', type=str)
        parser.add_argument('season_id', type=int)

    def handle(self, *args, **options):
        with open(options['filename']) as infile:
            races = json.load(infile)

        season = Season.objects.get(pk=options['season_id'])
        for r in races:
            start_time = self.handle_datetime(r['start_time'])
            race, _ = Race.objects.get_or_create(
                name=r['track'],
                short_name=r['short_name'],
                start_time=start_time,
                season=season
            )

            for res in r['results']:
                driver, _ = Driver.objects.get_or_create(name=res['driver'])
                team, _ = Team.objects.get_or_create(name=res['team'])

                result, _ = Result.objects.get_or_create(
                    race=race,
                    driver=driver,
                    team=team,
                    position=res['pos'],
                    qualifying=res['qpos'],
                    note=res['penalty'] if res['penalty'] != 'No penalty imposed.' else ''
                )

            print(r['race_number'], r['track'], len(r['results']))

