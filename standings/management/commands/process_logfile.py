from django.core.management.base import BaseCommand
from datetime import datetime
import pytz
from standings.models import Race, LogFile
import requests


division_map = {
    "World Championship": "WC",
    "PRO": "PRO",
    "Academy": "ACA"
}

base_url = "http://racefiles.formula-simracing.net/{season}/ResultsReplays/{division}/{round_number}-{race}/{filename}"
qualifying_filename = "{division}{year}_R{round_number}_Q.xml"
race_filename = "{division}{year}_R{round_number}_R.xml"


class Command(BaseCommand):
    help = 'Search for and download log files to process for specific races'

    def add_arguments(self, parser):
        parser.add_argument('--date', type=str)

    def handle(self, *args, **options):
        if 'date' in options and options['date'] is not None:
            date = datetime.strptime(options['date'], '%Y-%m-%d')
        else:
            date = datetime.utcnow()

        start = date.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=pytz.utc)
        end = date.replace(hour=23, minute=59, second=59, microsecond=999999, tzinfo=pytz.utc)

        now = datetime.utcnow().replace(tzinfo=pytz.utc)

        races = Race.objects.filter(start_time__gte=start, start_time__lte=end)
        for race in races:
            if race.start_time < now:
                print(f"Found {race.name}")
                files = [
                    qualifying_filename.format(
                        year=race.start_time.strftime('%y'),
                        division=division_map.get(race.season.division.name),
                        round_number=race.round_number
                    ),
                    race_filename.format(
                        year=race.start_time.strftime('%y'),
                        division=division_map.get(race.season.division.name),
                        round_number=race.round_number
                    )
                ]

                for file in files:
                    if (file,) not in race.logfile_set.values_list("file"):
                        print(f"{file} unprocessed, checking...")
                        url = base_url.format(
                            season=race.season.name,
                            division=division_map.get(race.season.division.name),
                            round_number=race.round_number,
                            race=race.short_name,
                            filename=file
                        )

                        req = requests.get(url)
                        if req.status_code in [200, 304]:
                            with open(file, 'wb') as outfile:
                                outfile.write(req.content)

                            logfile = LogFile(race=race, file=file)
                            print(f"Processing {file}... ", end="")
                            logfile.process()
                            print(f"done.")
                        else:
                            print(f"[{req.status_code}] {file} not found, or other error")
