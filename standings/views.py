from django.shortcuts import render
from .models import Season, Driver, Team, League, Division, Result, Race, SortCriteria, SeasonPenalty


def index_view(request):
    leagues = League.objects.all()

    context = {
        'leagues': leagues,
    }

    return render(request, 'standings/index.html', context)


def season_view(request, season_id):
    season = Season.objects.prefetch_related('point_system').get(pk=season_id)
    season_penalty = SeasonPenalty.objects.filter(season=season)

    drivers = {}
    teams = {}

    results = Result.objects.filter(race__season=season).prefetch_related('race').prefetch_related(
        'driver').prefetch_related('team').prefetch_related('race__track')

    for result in results:
        if result.driver_id not in drivers:
            try:
                best_finish = SortCriteria.objects.get(season=season, driver=result.driver).best_finish
            except SortCriteria.DoesNotExist:
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

        if not season.teams_disabled:
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
                    'position': 0,
                    'season_penalty': sp
                }
            else:
                teams[result.team_id]['results'].append(result)
                teams[result.team_id]['points'] += result.points

    sorted_drivers = []
    driver_sort = sorted(drivers, key=lambda item: drivers[item]['best_finish'])
    driver_sort = sorted(driver_sort, key=lambda item: drivers[item]['points'], reverse=True)
    for pos, driver in enumerate(driver_sort):
        drivers[driver]["position"] = pos + 1
        sorted_drivers.append(drivers[driver])

    sorted_teams = []
    team_sort = sorted(teams, key=lambda item: teams[item]['season_penalty'] is None, reverse=True)
    team_sort = sorted(team_sort, key=lambda item: teams[item]['points'], reverse=True)
    for pos, team in enumerate(team_sort):
        teams[team]["position"] = pos + 1
        sorted_teams.append(teams[team])

    context = {
        "season": season,
        "drivers": sorted_drivers,
        "teams": sorted_teams
    }

    return render(request, 'standings/season.html', context)


def team_view(request, team_id):
    team_drivers = {}
    team = Team.objects.get(pk=team_id)
    for res in team.result_set.all():
        season = res.race.season    
        ps = season.point_system.to_dict()
        if season.id not in team_drivers:
            team_drivers[season.id] = {
                "season": season,
                "drivers": {}
            }

        if res.driver.id not in team_drivers[season.id]['drivers']:
            results = res.driver.result_set.filter(race__season__id=season.id, team__id=team.id).all()
            team_drivers[season.id]['drivers'][res.driver.id] = {
                "driver": res.driver,
                "results": results,
                "points": sum([ps.get(x.position, 0) for x in results])
            }

    for td in team_drivers:
        sorted_drivers = []
        for driver in sorted(team_drivers[td]['drivers'],
                             key=lambda item: team_drivers[td]['drivers'][item]['points'],
                             reverse=True):
            sorted_drivers.append(team_drivers[td]['drivers'][driver])
        team_drivers[td]['drivers'] = sorted_drivers

    context = {
        'team': team,
        'seasons': team_drivers,
    }

    return render(request, 'standings/team.html', context)


def driver_view(request, driver_id):
    seasons = {}
    driver = Driver.objects.get(pk=driver_id)
    for res in driver.result_set.all():
        season = res.race.season
        ps = season.point_system.to_dict()
        if season.id not in seasons:
            seasons[season.id] = {
                "season": season,
                "teams": {}
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

    context = {
        'driver': driver,
        'seasons': seasons,
    }

    return render(request, 'standings/driver.html', context)


def league_view(request, league_id):
    league = League.objects.get(pk=league_id)

    context = {
        'league': league,
    }

    return render(request, 'standings/league.html', context)


def division_view(request, division_id):
    division = Division.objects.get(pk=division_id)

    context = {
        'division': division,
    }

    return render(request, 'standings/division.html', context)


def race_view(request, race_id):
    race = Race.objects.get(pk=race_id)

    context = {
        'race': race,
    }

    return render(request, 'standings/race.html', context)
