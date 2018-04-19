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

    standings_driver, standings_team = season.get_standings()

    context = {
        "season": season,
        "drivers": standings_driver,
        "teams": standings_team
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
