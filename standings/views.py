from django.views.decorators.cache import cache_page
from django.shortcuts import get_object_or_404, render
from .models import Season, Driver, Team, League, Division, Race, Track, Result, SeasonStats, SeasonPenalty
from standings.utils import sort_counter, calculate_average
from collections import Counter


def index_view(request):
    leagues = League.objects.all()

    context = {
        'leagues': leagues,
    }

    return render(request, 'standings/index.html', context)


@cache_page(None)
def season_view(request, season_id):
    season = get_object_or_404(Season, pk=season_id)

    standings_driver, standings_team = season.get_standings()

    context = {
        "season": season,
        "drivers": standings_driver,
        "teams": standings_team
    }

    return render(request, 'standings/season.html', context)


def season_stats_view(request, season_id):
    season = get_object_or_404(Season, pk=season_id)
    stats = season.seasonstats_set.order_by('-wins')

    context = {
        "season": season,
        "stats": stats
    }

    return render(request, 'standings/season_stats.html', context)


def team_view(request, team_id):
    team_drivers = {}
    team = get_object_or_404(Team, pk=team_id)
    for res in team.result_set.all():
        season = res.race.season    

        if res.race.point_system:
            ps = res.race.point_system.to_dict()
        else:
            ps = season.point_system.to_dict()

        if season.id not in team_drivers:
            team_drivers[season.id] = {
                "season": season,
                "drivers": {},
                "penalties": SeasonPenalty.objects.filter(season=season, team=res.team)
            }

        if res.driver.id not in team_drivers[season.id]['drivers']:
            results = res.driver.result_set.filter(race__season__id=season.id, team__id=team.id).all()
            team_drivers[season.id]['drivers'][res.driver.id] = {
                "driver": res.driver,
                "results": results,
                "points": sum([ps.get(x.position, 0) for x in results])
            }

            for penalty in team_drivers[season.id]['penalties'].filter(driver=res.driver):
                team_drivers[season.id]['drivers'][res.driver.id]['points'] -= penalty.points

    for td in team_drivers:
        sorted_drivers = []
        for driver in sorted(team_drivers[td]['drivers'],
                             key=lambda item: team_drivers[td]['drivers'][item]['points'],
                             reverse=True):
            sorted_drivers.append(team_drivers[td]['drivers'][driver])
        team_drivers[td]['drivers'] = sorted_drivers

    sorted_seasons = {}
    seasons_sort = sorted(team_drivers, key=lambda item: team_drivers[item]['season'].start_date)
    seasons_sort = sorted(seasons_sort, key=lambda item: team_drivers[item]['season'].division.order)
    for season_id, season in enumerate(seasons_sort):
        sorted_seasons[season_id] = team_drivers[season]

    context = {
        'team': team,
        'seasons': sorted_seasons,
    }

    return render(request, 'standings/team.html', context)


def driver_view(request, driver_id):
    seasons = {}
    driver = get_object_or_404(Driver, pk=driver_id)
    stats = SeasonStats.objects.filter(driver=driver)
    for res in driver.result_set.all():
        season = res.race.season

        if res.race.point_system:
            ps = res.race.point_system.to_dict()
        else:
            ps = season.point_system.to_dict()

        if season.id not in seasons:
            seasons[season.id] = {
                "season": season,
                "teams": {},
                "penalties": SeasonPenalty.objects.filter(season=season, driver=driver)
            }

            for result in driver.result_set.filter(race__season__id=season.id):
                if result.team.id not in seasons[season.id]['teams']:
                    seasons[season.id]['teams'][result.team.id] = {
                        "team": result.team,
                        "results": driver.result_set.filter(race__season__id=season.id, team__id=result.team.id)
                    }

                seasons[season.id]['teams'][result.team.id]["points"] = sum(
                    [ps.get(x.position, 0) for x in seasons[season.id]['teams'][result.team.id]["results"]]
                )

                for penalty in seasons[season.id]['penalties'].filter(team=res.team):
                    seasons[season.id]['teams'][res.team.id]['points'] -= penalty.points

    driver_stats = SeasonStats.collate(stats)
    counter_keys = ['race_positions', 'dnf_reasons', 'qualifying_positions']

    driver_stats['avg_qualifying'] = calculate_average(driver_stats, 'qualifying_positions')
    driver_stats['avg_race'] = calculate_average(driver_stats, 'race_positions')

    for key in counter_keys:
        if key == 'dnf_reasons':
            driver_stats[key] = ', '.join(
                sort_counter(Counter(driver_stats[key]), ordinal=False, convert_int=False)
            )
        else:
            driver_stats[key] = ', '.join(sort_counter(Counter(driver_stats[key])))

    sorted_seasons = {}
    seasons_sort = sorted(seasons, key=lambda item: seasons[item]['season'].start_date)
    seasons_sort = sorted(seasons_sort, key=lambda item: seasons[item]['season'].division.order)
    for season_id, season in enumerate(seasons_sort):
        sorted_seasons[season_id] = seasons[season]
        try:
            stats = SeasonStats.objects.get(season_id=season, driver_id=driver_id)
            sorted_seasons[season_id]['position'] = stats.season_position
        except SeasonStats.DoesNotExist:
            pass

    context = {
        'driver': driver,
        'seasons': sorted_seasons,
        'stats': driver_stats,
    }

    return render(request, 'standings/driver.html', context)


def league_view(request, league_id):
    league = get_object_or_404(League, pk=league_id)

    context = {
        'league': league,
    }

    return render(request, 'standings/league.html', context)


def division_view(request, division_id):
    division = get_object_or_404(Division, pk=division_id)

    context = {
        'division': division,
    }

    return render(request, 'standings/division.html', context)


def race_view(request, race_id):
    race = get_object_or_404(Race, pk=race_id)

    context = {
        'race': race,
    }

    return render(request, 'standings/race.html', context)


def track_view(request, track_id):
    track = get_object_or_404(Track, pk=track_id)
    track_records = track.trackrecord_set.order_by('season', 'race')

    context = {
        "track": track,
        "records": track_records
    }

    return render(request, 'standings/track.html', context)


def laps_view(request, result_id):
    result = get_object_or_404(Result, pk=result_id)
    laps = result.lap_set.filter(session='race').order_by('lap_number')

    context = {
        'result': result,
        'laps': laps,
    }

    return render(request, 'standings/laps.html', context)
