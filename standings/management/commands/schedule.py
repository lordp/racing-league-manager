from django.core.management.base import BaseCommand, CommandError
from standings.models import *
import json
from datetime import datetime, timezone
import time


class Command(BaseCommand):
    help = 'Import schedule'

    def handle_datetime(self, start_time):
        d = datetime.strptime(start_time, '%Y-%m-%d %H:%M')
        t = time.mktime(d.timetuple())

        return datetime.fromtimestamp(t, timezone.utc)

    def add_arguments(self, parser):
        parser.add_argument('filename', type=str)
        parser.add_argument('key', type=str)

    def handle(self, *args, **options):
        with open(options['filename']) as infile:
            schedule = json.load(infile)

        map = {
            'srca': League.objects.get(pk=2),
            'vec': League.objects.get(pk=6),
            'vlms': League.objects.get(pk=7),
            'gpvwc': League.objects.get(pk=4),
            'fsr': League.objects.get(pk=3),
            'rf2wec': League.objects.get(pk=1),
        }

        for event in schedule[options['key']]:

            date = self.handle_datetime(event['date'])
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

