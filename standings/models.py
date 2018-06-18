from django.db import models
from django.db.models import Count, Min
from django_countries.fields import CountryField
from django.contrib import messages
from datetime import date
from lxml import etree
import os
import standings.utils
from .utils import apply_positions
import json


class PointSystem(models.Model):
    name = models.CharField(max_length=25)
    race_points = models.CharField(max_length=100)
    qualifying_points = models.CharField(max_length=100, blank=True)
    pole_position = models.FloatField(default=0)
    lead_lap = models.FloatField(default=0)
    fastest_lap = models.FloatField(default=0)
    most_laps_lead = models.FloatField(default=0)

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
        return '{} ({}, {})'.format(self.name, self.country, self.version)

    def collate_results(self, session_type):
        best = {}

        if session_type == 'race':
            results = Result.objects.filter(race__track=self, race_fastest_lap__gt=0).\
                values('race__season_id', 'driver_id', 'race_id').annotate(
                Min('race_fastest_lap')).order_by('race_fastest_lap')
            key = 'race_fastest_lap__min'
        else:
            results = Result.objects.filter(race__track=self, qualifying_fastest_lap__gt=0).\
                values('race__season_id', 'driver_id', 'race_id').annotate(
                Min('qualifying_fastest_lap')).order_by('qualifying_fastest_lap')
            key = 'qualifying_fastest_lap__min'

        for result in results:
            if result['race__season_id'] not in best:
                best[result['race__season_id']] = {
                    'driver': result['driver_id'],
                    'race': result['race_id'],
                    'lap_time': result[key],
                    'update': True
                }
            elif result[key] < best[result['race__season_id']]['lap_time']:
                best[result['race__season_id']] = {
                    'new_driver': result['driver_id'],
                    'new_race': result['race_id'],
                    'lap_time': result[key],
                    'update': True
                }

        return best

    def update_records(self):
        best = {
            'race': self.collate_results('race'),
            'qualifying': self.collate_results('qualifying')
        }

        for session_type, session_best in best.items():
            for season, record in session_best.items():
                if record['update']:
                    (tr, created) = TrackRecord.objects.get_or_create(
                        driver_id=record['driver'],
                        race_id=record['race'],
                        season_id=season,
                        track=self
                    )

                    if 'new_driver' in record:
                        tr.driver_id = record['new_driver'],
                        tr.race_id = record['new_race']

                    tr.lap_time = record['lap_time']
                    tr.session_type = session_type
                    tr.save()


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
    teams_disabled = models.BooleanField(default=False)

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

    def get_standings(self):
        season_penalty = self.seasonpenalty_set

        drivers = {}
        teams = {}

        results = Result.objects.filter(race__season=self).prefetch_related('race').prefetch_related(
            'driver').prefetch_related('team').prefetch_related('race__track')

        for result in results:
            if result.driver_id not in drivers:
                try:
                    best_finish = self.seasonstats_set.get(driver=result.driver).best_finish
                except SeasonStats.DoesNotExist:
                    best_finish = 0

                try:
                    sp = season_penalty.get(driver=result.driver)
                    result.points -= sp.points
                except SeasonPenalty.DoesNotExist:
                    sp = None

                drivers[result.driver_id] = {
                    'driver': result.driver,
                    'points': result.points,
                    'results': [result],
                    'position': 0,
                    'best_finish': best_finish,
                    'season_penalty': sp
                }
            else:
                drivers[result.driver_id]['results'].append(result)
                drivers[result.driver_id]['points'] += result.points

            if not self.teams_disabled:
                if result.team.id not in teams:
                    try:
                        sp = season_penalty.get(team=result.team)
                        result.points -= sp.points
                    except SeasonPenalty.DoesNotExist:
                        sp = None

                    teams[result.team.id] = {
                        'team': result.team,
                        'points': result.points,
                        'results': [result],
                        'drivers': {result.driver},
                        'season_penalty': sp
                    }
                else:
                    teams[result.team_id]['results'].append(result)
                    teams[result.team_id]['points'] += result.points
                    teams[result.team_id]['drivers'].add(result.driver)

                teams[result.team.id]['driver_count'] = len(teams[result.team.id]['drivers'])

        sorted_drivers = []
        driver_sort = sorted(drivers, key=lambda item: drivers[item]['best_finish'])
        driver_sort = sorted(driver_sort, key=lambda item: drivers[item]['points'], reverse=True)
        for pos, driver in enumerate(driver_sort):
            sorted_drivers.append(drivers[driver])

        sorted_teams = []
        team_sort = sorted(teams, key=lambda item: teams[item]['season_penalty'] is None, reverse=True)
        team_sort = sorted(team_sort, key=lambda item: teams[item]['points'], reverse=True)
        for pos, team in enumerate(team_sort):
            sorted_teams.append(teams[team])

        return apply_positions(sorted_drivers), apply_positions(sorted_teams)

    def generate_image(self, mode, data):
        from PIL import Image, ImageDraw, ImageFont
        from django.core.files.storage import get_storage_class
        from django.conf import settings
        from standings.utils import format_float

        static_storage = get_storage_class(settings.STATICFILES_STORAGE)()

        division = self.division.name.lower().replace(' ', '_')
        top = Image.open(static_storage.open("top10/fsr-top-{}.png".format(division)))
        bottom = Image.open(static_storage.open("top10/fsr-bottom.png"))
        row_left = Image.open(static_storage.open("top10/fsr-row-left.png"))
        row_mid = Image.open(static_storage.open("top10/fsr-row-mid.png"))
        row_right = Image.open(static_storage.open("top10/fsr-row-right.png"))

        standings_image = Image.new('RGB', (300, 555))

        standings_image.paste(top, (0, 0))
        standings_image.paste(bottom, (0, standings_image.height - bottom.height))

        draw = ImageDraw.Draw(standings_image)
        font = ImageFont.truetype(static_storage.open('top10/DINPro-CondBlack.otf'), 22)
        height = top.size[1]

        for row in range(0, 10):
            for num in range(0, top.size[0]):
                if num < 45:
                    standings_image.paste(row_left, (num, height))
                elif num < 238:
                    standings_image.paste(row_mid, (num, height))
                else:
                    standings_image.paste(row_right, (num, height))

            pos_text = str(row + 1)
            (pos_width, _) = font.getsize(text=pos_text)
            draw.text(((45 - pos_width) / 2, height + 5), pos_text, font=font)

            name_text = data[row][mode].name
            (_, name_height) = font.getsize(text=name_text)
            draw.text((50, height + 5), name_text, font=font)

            pts_text = format_float(data[row]["points"])
            (pts_width, _) = font.getsize(text=pts_text)
            draw.text((238 + ((62 - pts_width) / 2), height + 5), pts_text, fill=(0, 0, 0), font=font)

            height += 40

        standings_image.save(static_storage.path('top10/standings-{}-{}-{}.png'.format(mode, division, self.name)))

    def generate_top10(self):
        standings_driver, standings_team = self.get_standings()

        self.generate_image('driver', standings_driver)
        self.generate_image('team', standings_team)

    def update_stats(self):
        for driver in Driver.objects.filter(result__race__season=self).distinct():
            (stat, _) = SeasonStats.objects.get_or_create(season=self, driver=driver)
            stat.update_stats()


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

    @property
    def qualifying_order(self):
        return self.result_set.order_by('qualifying')

    @property
    def race_order(self):
        return self.result_set.order_by('position')

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
        ll = self.laps_lead()
        ml = ll.first()
        season_penalty = SeasonPenalty.objects.filter(season=self.season)

        for result in self.result_set.all():
            if result.position == 1:
                result.gap = '-'
                total_lap_count = result.race_laps
                total_race_time = result.race_time

            if result.race_laps < total_lap_count:
                result.gap = '{} laps down'.format(total_lap_count - result.race_laps)
            else:
                result.gap = standings.utils.format_time(result.race_time - total_race_time)

            # check classification rules
            if self.season.allocate_points(total_lap_count, result.race_laps):
                result.points = ps.to_dict().get(result.position, 0)
                if result.fastest_lap:
                    result.points += ps.fastest_lap
            else:
                result.points = 0

            # pole position
            if result.qualifying == 1:
                result.points += ps.pole_position

            # most laps lead
            if ml['driver_id'] == result.driver_id:
                result.points += ps.most_laps_lead

            # points per lap lead
            for driver in ll:
                if driver['driver_id'] == result.driver_id:
                    result.points += (ps.lead_lap * driver['first_place'])

            # multiplier
            result.points *= result.points_multiplier

            try:
                sp = season_penalty.get(driver=result.driver)
            except SeasonPenalty.DoesNotExist:
                sp = None

            if sp and sp.disqualified:
                result.points = 0

            result.save()

            (season_stats, _) = SeasonStats.objects.get_or_create(season=self.season, driver=result.driver)
            if result.position < season_stats.best_finish or season_stats.best_finish == 0:
                season_stats.best_finish = result.position
            if sp and sp.disqualified:
                season_stats.best_finish = 99

            season_stats.save()

    def tooltip(self):
        tooltip = "{name}<br/>{time}".format(
            time=self.start_time.strftime('%B %d %Y @ %H:%M'),
            name=self.name,
        )
        return tooltip

    def laps_lead(self):
        return Result.objects.values('driver_id').filter(race=self, lap__position=1).annotate(
            first_place=Count('lap__position')).order_by('-first_place')


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


class TrackRecord(models.Model):
    track = models.ForeignKey(Track, on_delete=models.CASCADE)
    season = models.ForeignKey(Season, on_delete=models.CASCADE)
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE)
    race = models.ForeignKey(Race, on_delete=models.CASCADE)
    session_type = models.CharField(max_length=10)
    lap_time = models.FloatField(default=0)


class SeasonStats(models.Model):
    season = models.ForeignKey(Season, on_delete=models.CASCADE)
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE)
    best_finish = models.IntegerField(default=0)
    attendance = models.IntegerField(default=0)
    wins = models.IntegerField(default=0)
    podiums = models.IntegerField(default=0)
    points_finishes = models.IntegerField(default=0)
    pole_positions = models.IntegerField(default=0)
    fastest_laps = models.IntegerField(default=0)
    laps_lead = models.IntegerField(default=0)
    laps_completed = models.IntegerField(default=0)
    winner = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = 'Season stats'

    def update_stats(self):
        self.wins = 0
        self.podiums = 0
        self.points_finishes = 0
        self.pole_positions = 0
        self.fastest_laps = 0
        self.laps_lead = 0
        self.laps_completed = 0
        self.winner = False
        self.best_finish = 0

        for result in Result.objects.filter(race__season=self.season, driver=self.driver):
            self.attendance += 1

            if self.best_finish == 0 or self.best_finish > result.position:
                self.best_finish = result.position

            if (result.race.point_system and result.position <= len(
                    result.race.point_system.to_dict())) or result.position <= len(
                    self.season.point_system.to_dict()):
                self.points_finishes += 1

            if result.position == 1:
                self.wins += 1

            if 1 <= result.position <= 3:
                self.podiums += 1

            if result.qualifying == 1:
                self.pole_positions += 1

            if result.fastest_lap:
                self.fastest_laps += 1

            self.laps_lead += result.lap_set.filter(position=1, session='race').aggregate(Count('id'))['id__count']
            self.laps_completed += result.lap_set.filter(session='race').aggregate(Count('id'))['id__count']

        self.save()


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
    dnf_reason = models.CharField('DNF Reason', max_length=50, blank=True, default='')
    points = models.FloatField(default=0)
    gap = models.CharField(default='-', max_length=25)
    race_fastest_lap = models.FloatField('Fastest lap (R)', default=0)
    qualifying_fastest_lap = models.FloatField('Fastest lap (Q)', default=0)
    penalty_points = models.IntegerField(default=0)
    race_penalty_dsq = models.BooleanField(default=False)
    qualifying_penalty_dsq = models.BooleanField(default=False)

    class Meta:
        ordering = ['position']

    def has_notes(self):
        return (self.note != '' and self.note is not None) \
               or self.subbed_by is not None \
               or self.allocate_points is not None \
               or (self.race_penalty_description != '' and self.race_penalty_description is not None) \
               or (self.qualifying_penalty_description != '' and self.qualifying_penalty_description is not None)

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
    summary = models.TextField(default='', blank=True)

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

        qualify = len(tree.xpath('//Qualify'))
        if qualify > 0:
            session = 'qualify'
        else:
            session = 'race'

        duplicates = []
        lap_errors = {}
        drivers = tree.xpath('//Driver')
        for driver in drivers:
            driver_name = driver.xpath('./Name')[0].text.strip()
            try:
                driver_obj = Driver.objects.get(name__unaccent=driver_name)
            except Driver.DoesNotExist:
                driver_obj = Driver.objects.create(name=driver_name)
            except Driver.MultipleObjectsReturned:
                driver_obj = Driver.objects.filter(name__unaccent=driver_name).annotate(
                    result_count=Count('result')).order_by('-result_count').first()
                if driver_name not in duplicates:
                    duplicates.append(driver_obj.id)

            team_name = driver.xpath('./CarType')[0].text
            (team_obj, created) = Team.objects.get_or_create(name=team_name)

            (result, created) = Result.objects.get_or_create(
                race=self.race, driver=driver_obj, team=team_obj
            )

            result.fastest_lap = driver.xpath('./LapRankIncludingDiscos')[0].text == '1'
            result.car_class = driver.xpath('./CarClass')[0].text
            result.car = driver.xpath('./VehFile')[0].text
            if session == 'race':
                result.qualifying = driver.xpath('./GridPos')[0].text
                result.position = driver.xpath('./Position')[0].text
                result.race_laps = driver.xpath('./Laps')[0].text
            else:
                result.qualifying_laps = driver.xpath('./Laps')[0].text
                result.qualifying = driver.xpath('./Position')[0].text

            if driver.xpath('./FinishStatus')[0].text == 'Finished Normally':
                try:
                    result.race_time = driver.xpath('./FinishTime')[0].text
                except IndexError:
                    result.race_time = 0
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
                (lap_obj, created) = Lap.objects.get_or_create(result=result, lap_number=lap_number, session=session)

                lap_obj.position = int(lap.get('p'))
                lap_obj.sector_1 = self.get_float(lap.get('s1'))
                lap_obj.sector_2 = self.get_float(lap.get('s2'))
                lap_obj.sector_3 = self.get_float(lap.get('s3'))
                lap_obj.pitstop = lap.get('pit') == '1'
                lap_obj.lap_time = self.get_float(lap.text)

                lap_obj.save()

                if lap.text == '--.----':
                    if driver_obj.name not in lap_errors:
                        lap_errors[driver_obj.name] = []
                    tmp_lap = {"number": lap_obj.lap_number, "id": lap_obj.id}
                    lap_errors[driver_obj.name].append(tmp_lap)

                race_time += lap_obj.lap_time
                if lap_obj.lap_time > 0 and (lap_obj.lap_time < fastest_lap or fastest_lap == 0):
                    fastest_lap = lap_obj.lap_time

            if session == 'race':
                result.race_fastest_lap = fastest_lap
                if result.race_time == 0:
                    result.race_time = race_time
            else:
                result.qualifying_fastest_lap = fastest_lap
                if result.qualifying_time == 0:
                    result.qualifying_time = race_time

            result.save()

        self.summary = json.dumps({'duplicates': duplicates, 'lap_errors': lap_errors})
        self.save()

        self.race.fill_attributes()


class SeasonPenalty(models.Model):
    season = models.ForeignKey(Season, on_delete=models.CASCADE)
    driver = models.ForeignKey(Driver, null=True, blank=True, on_delete=models.SET_NULL)
    team = models.ForeignKey(Team, null=True, blank=True, on_delete=models.SET_NULL)
    points = models.IntegerField(default=0)
    disqualified = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = 'Season Penalties'

    def process(self):
        qs = None
        if self.disqualified:
            if self.driver:
                qs = Result.objects.filter(driver=self.driver)
            elif self.team:
                qs = Result.objects.filter(team=self.team)

            if qs:
                qs.update(points=0)

    def __str__(self):
        string = '{}'.format(self.season)
        if self.driver:
            string = '{}, {}'.format(string, self.driver)
        if self.team:
            string = '{}, {}'.format(string, self.team)
        if self.points > 0:
            string = '{}, docked {} points'.format(string, self.points)
        if self.disqualified:
            string = '{}, disqualified'.format(string)

        return string
