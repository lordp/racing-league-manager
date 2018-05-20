from standings.models import *
from rest_framework import serializers


class LeagueSerializer(serializers.ModelSerializer):
    class Meta:
        model = League
        fields = ['name']


class DivisionSerializer(serializers.ModelSerializer):
    league = LeagueSerializer(read_only=True)

    class Meta:
        model = Division
        fields = ['name', 'league']


class SeasonSerializer(serializers.ModelSerializer):
    division = DivisionSerializer(read_only=True)

    class Meta:
        model = Season
        fields = ['name', 'division']


class DriverSerializer(serializers.ModelSerializer):
    class Meta:
        model = Driver
        fields = ['name']


class TeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = ['name']


class RaceSerializer(serializers.ModelSerializer):
    season = SeasonSerializer(read_only=True)

    class Meta:
        model = Race
        fields = ['name', 'season', 'round_number', 'start_time']


class ResultSerializer(serializers.ModelSerializer):
    race = RaceSerializer(read_only=True)
    driver = DriverSerializer(read_only=True)
    team = TeamSerializer(read_only=True)

    class Meta:
        model = Result
        fields = ['race', 'driver', 'team', 'qualifying', 'position', 'fastest_lap']
