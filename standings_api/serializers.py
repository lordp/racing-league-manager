from standings.models import *
from rest_framework import serializers
from django_countries.serializer_fields import CountryField


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
    country = CountryField(country_dict=True)

    class Meta:
        model = Driver
        fields = ['name', 'country']


class ParentTeamSerializer(serializers.ModelSerializer):
    country = CountryField(country_dict=True)

    class Meta:
        model = Team
        fields = ['id', 'name', 'country', 'url']


class TeamSerializer(serializers.ModelSerializer):
    country = CountryField(country_dict=True)
    parent = ParentTeamSerializer()

    class Meta:
        model = Team
        fields = ['name', 'country', 'url', 'parent']


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
