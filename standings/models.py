from django.db import models
from django.db.models import Count
from django_countries.fields import CountryField
from django.contrib import messages
from datetime import date
from lxml import etree
import os
import standings.utils


class PointSystem(models.Model):
    name = models.CharField(max_length=25)
    race_points = models.CharField(max_length=100)
    qualifying_points = models.CharField(max_length=100, blank=True)
    lead_lap = models.IntegerField(default=0)
    fastest_lap = models.IntegerField(default=0)
    most_laps_lead = models.IntegerField(default=0)

    def __str__(self):
        return "{} ({})".format(self.name, self.race_points)

    def to_dict(self, race=True):
        try:
            if race:
                return {int(k) + 1: int(v) for k, v in enumerate(self.race_points.split(','))}
            else:
                return {int(k) + 1: int(v) for k, v in enumerate(self.qualifying_points.split(','))}
        except ValueError:
            return {0: 0}


class League(models.Model):
    name = models.CharField(max_length=50)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def breadcrumbs(self):
        return [
            {"url": "league", "object": self},
        ]


class Division(models.Model):
    league = models.ForeignKey(League, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    description = models.CharField(max_length=250, blank=True)
    url = models.CharField(max_length=100, blank=True)
    order = models.CharField(max_length=50, blank=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return "{} ({})".format(self.name, self.league.name)

    def breadcrumbs(self):
        return [
            {"url": "league", "object": self.league},
            {"url": "division", "object": self},
        ]


class Track(models.Model):
    name = models.CharField(max_length=100)
    length = models.FloatField(default=0)
    version = models.CharField(max_length=25)
    country = CountryField(blank=True)

    def __str__(self):
        return '{} ({})'.format(self.name, self.country)


class Season(models.Model):
    division = models.ForeignKey(Division, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    description = models.CharField(max_length=250, blank=True)
    start_date = models.DateField(default=date.today)
    end_date = models.DateField(default=date.today)
    finalized = models.BooleanField(default=False)
    point_system = models.ForeignKey(PointSystem, on_delete=models.SET_NULL, null=True, blank=True)
    classification_type = models.CharField(max_length=10, blank=True)
    percent_classified = models.IntegerField(default=0)
    laps_classified = models.IntegerField(default=0)

    def __str__(self):
        return "{} ({})".format(self.name, self.division.name)

    def breadcrumbs(self):
        return [
            {"url": "league", "object": self.division.league},
            {"url": "division", "object": self.division},
            {"url": "season", "object": self}
        ]

    def race_count(self):
        return {
            "incomplete": self.race_set.annotate(Count('result')).filter(result__isnull=True).count(),
            "total": self.race_set.annotate(Count('result')).count()
        }

    def allocate_points(self, total_lap_count, driver_lap_count):
        if self.classification_type.lower() == 'percent':
            if driver_lap_count < (total_lap_count * (self.percent_classified / 100)):
                return False
        elif self.classification_type.lower() == 'laps':
            if driver_lap_count < total_lap_count - self.laps_classified:
                return False

        return True


class Race(models.Model):
    season = models.ForeignKey(Season, on_delete=models.CASCADE)
    point_system = models.ForeignKey(PointSystem, on_delete=models.SET_NULL, null=True, blank=True)
    round_number = models.IntegerField(default=1)
    name = models.CharField(max_length=100)
    short_name = models.CharField(max_length=3, null=True)
    start_time = models.DateTimeField()
    track = models.ForeignKey(Track, on_delete=models.SET_NULL, null=True)

    class Meta:
        ordering = ['round_number']

    def __str__(self):
        return "{} ({}, {})".format(self.name, self.season.name, self.season.division.name)

    def breadcrumbs(self):
        return [
            {"url": "league", "object": self.season.division.league},
            {"url": "division", "object": self.season.division},
            {"url": "season", "object": self.season},
            {"url": "race", "object": self}
        ]

    def fill_attributes(self):
        total_race_time = 0
        total_lap_count = 0

        ps = self.point_system if self.point_system else self.season.point_system

        for result in self.result_set.all():
            if result.position == 1:
                result.gap = '-'
                total_lap_count = result.race_laps
                total_race_time = result.race_time

            if result.race_laps < total_lap_count:
                result.gap = '{} laps down'.format(total_lap_count - result.race_laps)
            else:
                result.gap = standings.utils.format_time(result.race_time - total_race_time)

            if self.season.allocate_points(total_lap_count, result.race_laps):
                result.points = ps.to_dict().get(result.position, 0)
            else:
                result.points = 0

            result.save()

            (sort_criteria, _) = SortCriteria.objects.get_or_create(season=self.season, driver=result.driver)
            if result.position < sort_criteria.best_finish or sort_criteria.best_finish == 0:
                sort_criteria.best_finish = result.position
            sort_criteria.save()

    def tooltip(self):
        tooltip = "{name}<br/>{time}".format(
            time=self.start_time.strftime('%B %d %Y @ %H:%M'),
            name=self.name,
        )
        return tooltip


class Driver(models.Model):
    name = models.CharField(max_length=50)
    country = CountryField(blank=True)
    shortname = models.CharField(max_length=25, blank=True)
    birthday = models.DateField(null=True, blank=True)
    city = models.CharField(max_length=50, blank=True)
    helmet = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return "{} ({})".format(self.name, self.country)

    def collect_results(self):
        for driver in Driver.objects.filter(name=self.name):
            if driver is not self:
                driver.result_set.update(driver=self)


class Team(models.Model):
    name = models.CharField(max_length=50)
    url = models.CharField(max_length=100, blank=True)
    country = CountryField(blank=True)

    def __str__(self):
        return "{} ({})".format(self.name, self.id)


class SortCriteria(models.Model):
    season = models.ForeignKey(Season, on_delete=models.CASCADE)
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE)
    best_finish = models.IntegerField(default=0)


class Result(models.Model):
    race = models.ForeignKey(Race, on_delete=models.CASCADE)
    driver = models.ForeignKey(Driver, null=True, on_delete=models.SET_NULL)
    team = models.ForeignKey(Team, null=True, on_delete=models.SET_NULL)
    qualifying = models.IntegerField('Position', default=0)
    position = models.IntegerField(default=0)
    fastest_lap = models.BooleanField('Fastest lap in race', default=False)
    note = models.CharField(max_length=100, blank=True)
    subbed_by = models.ForeignKey(Driver, null=True, blank=True, on_delete=models.SET_NULL, related_name='substitute')
    allocate_points = models.ForeignKey(Team, null=True, blank=True, on_delete=models.SET_NULL,
                                        related_name='points_allocation')
    race_laps = models.IntegerField('Lap count', default=0)
    race_time = models.FloatField('Total time', default=0)
    qualifying_laps = models.IntegerField('Lap count', default=0)
    qualifying_time = models.FloatField('Total time', default=0)
    finalized = models.BooleanField(default=False)
    car = models.CharField(max_length=25, blank=True)
    car_class = models.CharField(max_length=25, blank=True)
    points_multiplier = models.FloatField('Points Multiplier', default=1)
    points_multiplier_description = models.CharField('Multiplier Description', max_length=250, blank=True)
    race_penalty_time = models.IntegerField('Time', default=0)
    race_penalty_positions = models.IntegerField('Positions', default=0)
    race_penalty_description = models.CharField('Description', max_length=100, blank=True)
    qualifying_penalty_grid = models.IntegerField('Grid Positions', default=0)
    qualifying_penalty_bog = models.BooleanField('Back of grid', default=False)
    qualifying_penalty_sfp = models.BooleanField('Start from pits', default=False)
    qualifying_penalty_description = models.CharField('Description', max_length=100, blank=True)
    dnf_reason = models.CharField('DNF Reason', max_length=50, blank=True)
    points = models.IntegerField(default=0)
    gap = models.CharField(default='-', max_length=25)
    fastest_lap_value = models.FloatField('Fastest lap', default=0)

    class Meta:
        ordering = ['position']

    def has_notes(self):
        return (self.note != '' and self.note is not None) \
               or self.subbed_by is not None \
               or self.allocate_points is not None

    def __str__(self):
        return "{race} ({driver}, {position})".format(
            race=self.race.name,
            driver=self.driver.name,
            position=self.position
        )


class Lap(models.Model):
    result = models.ForeignKey(Result, on_delete=models.CASCADE)
    session = models.CharField(max_length=10)
    lap_number = models.IntegerField(default=1)
    position = models.IntegerField(default=1)
    pitstop = models.BooleanField(default=False)
    sector_1 = models.FloatField(default=0)
    sector_2 = models.FloatField(default=0)
    sector_3 = models.FloatField(default=0)
    lap_time = models.FloatField(default=0)
    race_time = models.FloatField(default=0)


class LogFile(models.Model):
    file = models.FileField(upload_to='log_files/%Y/%m/%d')
    race = models.ForeignKey(Race, on_delete=models.CASCADE)

    @staticmethod
    def get_float(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def __str__(self):
        return '{} ({})'.format(os.path.basename(self.file.path), self.race)

    def process(self, request):
        with open(self.file.name) as infile:
            tree = etree.XML(infile.read().encode('utf-8'))

        duplicates = []
        drivers = tree.xpath('//Driver')
        for driver in drivers:
            driver_name = driver.xpath('./Name')[0].text.strip()
            try:
                driver_obj = Driver.objects.get(name__unaccent=driver_name)
            except Driver.DoesNotExist:
                driver_obj = Driver.objects.create(name=driver_name)
            except Driver.MultipleObjectsReturned:
                if driver_name not in duplicates:
                    duplicates.append(driver_name)
                continue

            team_name = driver.xpath('./CarType')[0].text
            (team_obj, created) = Team.objects.get_or_create(name=team_name)

            (result, created) = Result.objects.get_or_create(
                race=self.race, driver=driver_obj, team=team_obj, dnf_reason=''
            )

            result.fastest_lap = driver.xpath('./LapRankIncludingDiscos')[0].text == '1'
            result.car_class = driver.xpath('./CarClass')[0].text
            result.car = driver.xpath('./VehFile')[0].text
            result.qualifying = driver.xpath('./GridPos')[0].text
            result.position = driver.xpath('./Position')[0].text
            result.race_laps = driver.xpath('./Laps')[0].text
            if driver.xpath('./FinishStatus')[0].text == 'Finished Normally':
                result.race_time = driver.xpath('./FinishTime')[0].text
            else:
                result.race_time = 0
                try:
                    result.dnf_reason = driver.xpath('./DNFReason')[0].text
                except IndexError:
                    result.dnf_reason = ''

            result.save()

            race_time = 0
            fastest_lap = 0

            laps = driver.xpath('.//Lap')
            for lap in laps:
                lap_number = int(lap.get('num'))
                (lap_obj, created) = Lap.objects.get_or_create(result=result, lap_number=lap_number)

                lap_obj.position = int(lap.get('p'))
                lap_obj.sector_1 = self.get_float(lap.get('s1'))
                lap_obj.sector_2 = self.get_float(lap.get('s2'))
                lap_obj.sector_3 = self.get_float(lap.get('s3'))
                lap_obj.pitstop = lap.get('pit') == '1'
                lap_obj.lap_time = self.get_float(lap.text)

                lap_obj.save()

                race_time += lap_obj.lap_time
                if lap_obj.lap_time > 0 and (lap_obj.lap_time < fastest_lap or fastest_lap == 0):
                    fastest_lap = lap_obj.lap_time

            if result.race_time == 0:
                result.race_time = race_time

            result.fastest_lap_value = fastest_lap
            result.save()

        if duplicates:
            msg = 'The following drivers had duplicate records, please delete or merge into one driver - {}'.format(
                ', '.join(duplicates)
            )

            messages.add_message(request, messages.WARNING, msg)

        self.race.fill_attributes()
