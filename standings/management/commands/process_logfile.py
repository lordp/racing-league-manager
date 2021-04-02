from django.core.management.base import BaseCommand
from datetime import datetime
import pytz
from standings.models import Race, LogFile
import requests
import os


base_url = "http://racefiles.formula-simracing.net/{season}/ResultsReplays/{division}/{round_number}-{race}/{filename}"
qualifying_filename = "{division}{year}_R{round_number}_Q.xml"
race_filename = "{division}{year}_R{round_number}_R.xml"


class Command(BaseCommand):
    help = 'Search for and download log files to process for specific races'

    def debug(self, msg):
        now = str(datetime.now().replace(microsecond=0))
        print(f"[{now}] {msg}")

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
            log_file_tag = race.season.division.log_file_tag
            if race.start_time < now:
                self.debug(f"Found {race.name}")
                files = [
                    qualifying_filename.format(
                        year=race.start_time.strftime('%y'),
                        division=log_file_tag,
                        round_number=f"{race.round_number:02d}"
                    ),
                    race_filename.format(
                        year=race.start_time.strftime('%y'),
                        division=log_file_tag,
                        round_number=f"{race.round_number:02d}"
                    )
                ]

                for file in files:
                    if (file,) not in race.logfile_set.values_list("file"):
                        self.debug(f"{file} unprocessed, checking...")
                        url = base_url.format(
                            season=race.season.name,
                            division=log_file_tag,
                            round_number=f"{race.round_number:02d}",
                            race=race.short_name,
                            filename=file
                        )

                        req = requests.get(url)
                        if req.status_code in [200, 304]:
                            with open(file, 'wb') as outfile:
                                outfile.write(req.content)

                            logfile = LogFile(race=race, file=file)
                            self.debug(f"Processing {file}... ")
                            logfile.process()
                            self.debug(f"done.")

                            os.remove(file)
                        else:
                            self.debug(f"{file} not found, or other error ({req.status_code})")
