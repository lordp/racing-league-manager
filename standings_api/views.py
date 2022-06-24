from standings.models import Driver, Result, Race, Team, SeasonStats, Season, Division, SeasonCarNumber, PointSystem
from standings_api.serializers import DriverSerializer, ResultSerializer, RaceSerializer, TeamSerializer
from standings.utils import calculate_average
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import mixins, generics
from datetime import datetime, timezone
from django.db.models import Q
from django.forms.models import model_to_dict
from collections import Counter
from django.utils.text import slugify


class DriverList(mixins.ListModelMixin, generics.GenericAPIView):
    queryset = Driver.objects.all().order_by('name')
    serializer_class = DriverSerializer

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class TeamList(mixins.ListModelMixin, generics.GenericAPIView):
    queryset = Team.objects.all().order_by('name')
    serializer_class = TeamSerializer

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class ResultList(generics.ListAPIView):
    serializer_class = ResultSerializer

    def get_queryset(self):
        queryset = Result.objects.order_by('race__round_number')

        driver_name = self.request.query_params.get('name', None)
        if driver_name is not None:
            queryset = queryset.filter(driver__name__icontains=driver_name)

        season = self.request.query_params.get('season', None)
        if season is not None:
            queryset = queryset.filter(race__season__id=season)

        return queryset

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class RaceList(generics.ListAPIView):
    serializer_class = RaceSerializer

    def get_queryset(self):
        queryset = Race.objects.order_by('start_time', 'round_number')

        start_date = self.request.query_params.get('start_date', None)
        if start_date is not None:
            queryset = queryset.filter(start_time__gte=start_date)

        end_date = self.request.query_params.get('end_date', None)
        if end_date is not None:
            queryset = queryset.filter(start_time__lt=end_date)

        season = self.request.query_params.get('season', None)
        if season is not None:
            queryset = queryset.filter(season__id=season)

        division = self.request.query_params.get('division', None)
        if division is not None:
            queryset = queryset.filter(season__division_id=division)

        return queryset

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class DriverDetail(APIView):
    @staticmethod
    def get(request, number, season_id):
        try:
            driver = SeasonCarNumber.objects.get(car_number=number, season_id=season_id).driver
            standings = Season.objects.get(pk=season_id).get_standings(use_position=True)
            standings = [x for x in standings[0] if x['driver'].id == driver.id][0]
            detail = {
                'id': driver.id,
                'name': driver.name,
                'team': {
                    'id': standings['team'].id,
                    'name': standings['team'].name,
                },
                'points': standings['points'],
                'position': standings['position'],
                'best_finish': standings['best_finish']
            }

            return Response(detail)
        except (Driver.DoesNotExist, Season.DoesNotExist, IndexError):
            return Response({'error': 'Driver or season not found'}, status=404)


class TeamDetail(mixins.RetrieveModelMixin, generics.GenericAPIView):
    queryset = Team.objects.all()
    serializer_class = TeamSerializer

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)


class SeasonDetail(mixins.RetrieveModelMixin, generics.GenericAPIView):
    @staticmethod
    def get(request, season_id):
        try:
            season = Season.objects.get(pk=season_id)
            races = []
            for race in season.race_set.order_by('round_number'):
                this_race = {
                    'id': race.id,
                    'name': race.name,
                    'round_number': race.round_number,
                    'start_time': race.start_time,
                    'point_system': None
                }

                if race.point_system:
                    ps = race.point_system
                    this_race['point_system'] = slugify(ps.name)

                races.append(this_race)

                point_systems = {}
                ps = season.point_system
                point_systems[slugify(ps.name)] = {
                    'name': ps.name,
                    'race': ps.to_dict(),
                    'qualifying': ps.to_dict(False),
                    'pole': ps.pole_position,
                    'lead_lap': ps.lead_lap,
                    'fastest_lap': ps.fastest_lap,
                    'most_laps_lead': ps.most_laps_lead,
                    'extras_present': ps.extras_present()
                }

                for ps in PointSystem.objects.filter(race__season_id=season.id).exclude(id=ps.id).distinct():
                    point_systems[slugify(ps.name)] = {
                        'name': ps.name,
                        'race': ps.to_dict(),
                        'qualifying': ps.to_dict(False),
                        'pole': ps.pole_position,
                        'lead_lap': ps.lead_lap,
                        'fastest_lap': ps.fastest_lap,
                        'most_laps_lead': ps.most_laps_lead,
                        'extras_present': ps.extras_present()
                    }


            detail = {
                "name": season.name,
                "division": season.division.name,
                "race_count": season.race_set.count(),
                "races": races,
                "point_systems": point_systems
            }
            return Response(detail)
        except (Season.DoesNotExist, IndexError):
            return Response({'error': 'Season not found'}, status=404)


class RaceDetail(APIView):
    queryset = Race.objects.all()
    serializer_class = RaceSerializer

    @staticmethod
    def get(request, race_id, format=None):
        race = Race.objects.get(pk=race_id)
        if race:
            results = []
            for result in race.result_set.all():
                results.append({
                    'driver': {
                        'id': result.driver_id,
                        'name': result.driver.name,
                        'country': result.driver.country.name
                    },
                    'team': {
                        'id': result.team_id,
                        'name': result.team.name,
                        'country': result.team.country.name
                    },
                    'qualifying': result.qualifying,
                    'position': result.position,
                    'points': result.points,
                    'dnf': result.dnf_reason,
                    'fastest_lap': result.fastest_lap,
                    'laps': result.race_laps,
                    'penalty': result.race_penalty_description,
                    'time': result.race_time
                })
            race_detail = {
                'name': race.name,
                'round_number': race.round_number,
                'start_time': race.start_time,
                'results': results
            }

            return Response(race_detail)
        else:
            return Response({}, status=404)


class NextRaceDetail(APIView):
    @staticmethod
    def get(request):
        now = datetime.now(timezone.utc)
        queryset = Race.objects.filter(start_time__gte=now).order_by('start_time')
        division = request.query_params.get('division', None)
        if division:
            queryset = queryset.filter(season__division__name__icontains=division)

        race = queryset.first()

        detail = {
            "round_number": race.round_number,
            "name": race.name,
            "start_time": race.start_time,
            "division": race.season.division.name
        }

        return Response(detail)


class DriverStats(APIView):
    @staticmethod
    def get(request):
        stats = SeasonStats.objects
        driver = request.query_params.get('driver', None)
        if driver:
            stats = stats.filter(driver__name__icontains=driver)

        season = request.query_params.get('season', None)
        if season:
            stats = stats.filter(season__name__icontains=season)

        division = request.query_params.get('division', None)
        if division:
            stats = stats.filter(season__division__name__icontains=division)

        driver_stats = SeasonStats.collate(stats)
        if 'error' in driver_stats:
            return Response(driver_stats)

        driver_stats['race_positions'] = Counter(driver_stats['race_positions'])
        driver_stats['qualifying_positions'] = Counter(driver_stats['qualifying_positions'])

        driver_stats['avg_qualifying'] = calculate_average(driver_stats, 'qualifying_positions')
        driver_stats['avg_race'] = calculate_average(driver_stats, 'race_positions')

        return Response(driver_stats)


class Standings(APIView):
    @staticmethod
    def get(request, season_id, team):
        season = Season.objects.get(pk=season_id)
        if season:
            data = []
            standings = season.get_standings(use_position=True)
            if team:
                standings = standings[1]
            else:
                standings = standings[0]

            for row in standings:
                if team:
                    data.append({
                        'name': row['team'].name,
                        'position': row['position'],
                        'points': row['points'],
                    })
                else:
                    tmp = {
                        'name': row['driver'].name,
                        'id': row['driver'].id,
                        'position': row['position'],
                        'points': row['points'],
                        'best_finish': row['best_finish']
                    }

                    if not season.teams_disabled:
                        tmp['teams'] = []
                        for tmp_team in row['teams']:
                            try:
                                tmp['teams'].append({
                                    'name': tmp_team.name,
                                    'id': tmp_team.id,
                                })
                            except AttributeError:
                                tmp['teams'].append({
                                    'name': 'Unknown',
                                    'id': 0,
                                })

                    data.append(tmp)
            return Response(data)
        else:
            return Response({}, status=404)


class DivisionInfo(APIView):
    @staticmethod
    def get(request, division_name):
        try:
            division = Division.objects.filter(
                Q(name__icontains=division_name) | Q(league__name__icontains=division_name)
            ).first()
            season = division.season_set.order_by('-start_date').first()

            return Response({
                'name': division.name,
                'league': division.league.name,
                'season': model_to_dict(season)
            })
        except (IndexError, AttributeError):
            return Response({}, status=404)
