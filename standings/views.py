from django.views.decorators.cache import cache_page
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, render
from .models import Season, Driver, Team, League, Division, Race, Track, Result, SeasonStats, SeasonPenalty, Lap
from standings.utils import sort_counter, calculate_average, truncate_point_system, grouper
from collections import Counter
from django_countries.fields import Country
from django.utils.text import slugify


def index_view(request):
    leagues = League.objects.annotate(div_count=Count('division')).\
        values('id', 'name', 'div_count').order_by('-div_count', 'name')

    context = {
        'leagues': leagues,
    }

    return render(request, 'standings/index.html', context)


@cache_page(None)
def season_view(request, season_id):
    season = get_object_or_404(Season, pk=season_id)

    upto = request.GET.get('upto', None)
    standings_driver, standings_team = season.get_standings(upto=upto)

    ps = season.point_system
    point_system = {
        'race': truncate_point_system(ps.to_dict()),
        'qualifying': truncate_point_system(ps.to_dict(False)),
        'pole': ps.pole_position,
        'lead_lap': ps.lead_lap,
        'fastest_lap': ps.fastest_lap,
        'most_laps_lead': ps.most_laps_lead,
        'extras_present': ps.extras_present()
    }

    context = {
        "upto": int(upto or season.race_set.count()),
        "season": season,
        "drivers": standings_driver,
        "teams": standings_team,
        "point_system": point_system
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
    seasons = {}
    team = get_object_or_404(Team, pk=team_id)

    season_list = Season.objects.filter(race__result__team_id=team_id).distinct()
    for season in season_list:
        seasons[season.id] = {
            "season": season,
            "drivers": {},
            "penalties": SeasonPenalty.objects.filter(season=season, team=team)
        }

        for result in team.result_set.filter(race__season_id=season.id).distinct().order_by('driver_id').\
                values('driver_id'):
            if season.id not in seasons:
                seasons[season.id] = {
                    "season": season,
                    "drivers": {},
                    "penalties": SeasonPenalty.objects.filter(season=season, team=team)
                }

            if result['driver_id'] not in seasons[season.id]['drivers']:
                results = Result.objects.filter(
                    race__season_id=season.id,
                    team_id=team.id,
                    driver_id=result['driver_id']).all()

                driver = Driver.objects.get(pk=result['driver_id'])
                seasons[season.id]['drivers'][result['driver_id']] = {
                    "driver": driver,
                    "results": results,
                    "points": results.aggregate(sum=Sum('points'))['sum']
                }

                for penalty in seasons[season.id]['penalties'].filter(driver=driver):
                    seasons[season.id]['drivers'][result['driver_id']]['points'] -= penalty.points

    for td in seasons:
        sorted_drivers = []
        for driver in sorted(seasons[td]['drivers'],
                             key=lambda item: seasons[td]['drivers'][item]['points'],
                             reverse=True):
            sorted_drivers.append(seasons[td]['drivers'][driver])
        seasons[td]['drivers'] = sorted_drivers

    team_stats = {}
    counter_keys = ['race_positions', 'dnf_reasons', 'qualifying_positions']
    td = list(set([x[0] for x in Result.objects.filter(team_id=team_id).values_list('driver_id')]))

    stats = SeasonStats.objects.filter(driver_id__in=td).prefetch_related('season__division')
    divisions = Division.objects.filter(season__race__result__team_id=team_id).distinct()
    for division in divisions:
        team_stats[division.id] = {
            'name': division.name,
            'stats': SeasonStats.collate(stats.filter(season__division_id=division.id), focus='team')
        }
        team_stats[division.id]['stats']['avg_qualifying'] = calculate_average(
            team_stats[division.id]['stats'],
            'qualifying_positions'
        )
        team_stats[division.id]['stats']['avg_race'] = calculate_average(
            team_stats[division.id]['stats'],
            'race_positions'
        )

        for key in counter_keys:
            if key in team_stats[division.id]['stats']:
                if key == 'dnf_reasons':
                    team_stats[division.id]['stats'][key] = ', '.join(
                        sort_counter(Counter(team_stats[division.id]['stats'][key]), ordinal=False, convert_int=False)
                    )
                else:
                    positions = list(grouper(sort_counter(Counter(team_stats[division.id]['stats'][key])), 3, ''))
                    team_stats[division.id]['stats'][key] = positions

    sorted_seasons = {}
    seasons_sort = sorted(seasons, key=lambda item: seasons[item]['season'].start_date)
    seasons_sort = sorted(seasons_sort, key=lambda item: seasons[item]['season'].division.order)
    for season_id, season in enumerate(seasons_sort):
        sorted_seasons[season_id] = seasons[season]

    context = {
        'team': team,
        'seasons': sorted_seasons,
        'stats': team_stats
    }

    return render(request, 'standings/team.html', context)


def driver_view_slug(request, slug):
    driver = get_object_or_404(Driver, slug=slug)
    return driver_view(request, driver.id, from_slug=True)


def driver_view(request, driver_id, from_slug=False):
    seasons = {}
    driver = get_object_or_404(Driver, pk=driver_id)
    stats = SeasonStats.objects.filter(driver=driver).prefetch_related('season__division')

    season_list = Season.objects.filter(race__result__driver_id=driver_id).distinct()
    for season in season_list:
        seasons[season.id] = {
            "season": season,
            "teams": {},
            "penalties": SeasonPenalty.objects.filter(season=season, driver=driver)
        }

        results = driver.result_set.filter(race__season__id=season.id).prefetch_related('team')
        for result in results:
            team_results = results.filter(team=result.team)
            if result.team.id not in seasons[season.id]['teams']:
                seasons[season.id]['teams'][result.team.id] = {
                    "team": result.team,
                    "results": team_results,
                    "points": team_results.aggregate(sum=Sum('points'))['sum']
                }

            for penalty in seasons[season.id]['penalties'].filter(team=result.team):
                seasons[season.id]['teams'][result.team.id]['points'] -= penalty.points

    driver_stats = {}
    counter_keys = ['race_positions', 'dnf_reasons', 'qualifying_positions']

    divisions = Division.objects.filter(season__race__result__driver_id=driver_id).distinct()
    for division in divisions:
        driver_stats[division.id] = {
            'name': division.name,
            'stats': SeasonStats.collate(stats.filter(season__division_id=division.id))
        }
        driver_stats[division.id]['stats']['avg_qualifying'] = calculate_average(
            driver_stats[division.id]['stats'],
            'qualifying_positions'
        )
        driver_stats[division.id]['stats']['avg_race'] = calculate_average(
            driver_stats[division.id]['stats'],
            'race_positions'
        )

        for key in counter_keys:
            if key in driver_stats[division.id]['stats']:
                if key == 'dnf_reasons':
                    driver_stats[division.id]['stats'][key] = ', '.join(
                        sort_counter(Counter(driver_stats[division.id]['stats'][key]), ordinal=False, convert_int=False)
                    )
                else:
                    positions = list(grouper(sort_counter(Counter(driver_stats[division.id]['stats'][key])), 3, ''))
                    driver_stats[division.id]['stats'][key] = positions

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

    if from_slug:
        slug_check = slugify(driver.name)
        see_also = Driver.objects.filter(slug__startswith=slug_check).exclude(id=driver.id)

        context['see_also'] = see_also

    return render(request, 'standings/driver.html', context)


def league_view(request, league_id):
    league = get_object_or_404(League, pk=league_id)
    divisions = league.division_set.annotate(season_count=Count('season')).values('id', 'name', 'season_count')

    context = {
        'league': league,
        'divisions': divisions
    }

    return render(request, 'standings/league.html', context)


def division_view(request, division_id):
    division = get_object_or_404(Division, pk=division_id)
    seasons = division.season_set.annotate(race_count=Count('race', distinct=True)).\
        annotate(incomplete=Count('race', filter=Q(race__result__isnull=True))).\
        values('id', 'name', 'race_count', 'incomplete')

    context = {
        'division': division,
        'seasons': seasons
    }

    return render(request, 'standings/division.html', context)


def race_view(request, race_id):
    race = get_object_or_404(Race, pk=race_id)

    try:
        labels = [lap[0] for lap in race.result_set.get(position=1).race_lap_set().values_list('lap_number')]
        winner_laps = [lap[0] for lap in race.result_set.get(position=1).race_lap_set().values_list('lap_time')]
    except (Result.DoesNotExist, Lap.DoesNotExist):
        labels = []
        winner_laps = []

    q_first = 0
    q_laps = {x.driver_id: {'time': x.qualifying_fastest_lap, 'diff': 0, 'pos': x.qualifying} for x in
              Result.objects.filter(race_id=race_id, qualifying_fastest_lap__gt=0).order_by('qualifying')}
    for driver_id, lap in q_laps.items():
        if lap['pos'] == 1:
            q_first = lap['time']
        lap['diff'] = lap['time'] - q_first

    lap_times = {}
    drivers = {}
    for result in race.result_set.all():
        lap_times[result.driver_id] = [lap[0] for lap in result.race_lap_set().values_list('lap_time')]
        drivers[result.driver_id] = result.driver.name

    compounds = {}
    compound_list = Lap.objects.filter(result__race_id=race_id, session='race').\
        values('result__driver_id', 'compound', 'lap_number', 'pitstop').order_by('lap_number')
    for result in compound_list:
        if result['result__driver_id'] not in compounds:
            compounds[result['result__driver_id']] = [{'lap_count': 0}]

        compounds[result['result__driver_id']][-1]['lap_count'] += 1
        compounds[result['result__driver_id']][-1]['compound'] = result['compound']
        if result['pitstop'] == 1:
            compounds[result['result__driver_id']].append({'lap_count': 0})

    q_compounds = {}
    compound_list = Lap.objects.filter(result__race_id=race_id, session='qualify', lap_time__gt=0).\
        values('result__driver_id', 'compound', 'lap_time').order_by('result__driver_id', 'lap_time')
    for result in compound_list:
        if result['result__driver_id'] not in q_compounds or \
                result['lap_time'] < q_compounds[result['result__driver_id']]['lap_time']:
            q_compounds[result['result__driver_id']] = {
                'compound': result['compound'],
                'lap_time': result['lap_time']
            }

    context = {
        'race': race,
        'drivers': drivers,
        'labels': labels,
        'lap_times': lap_times,
        'winner_laps': winner_laps,
        'disable_charts': 'true' if len(labels) == 0 else 'false',
        'compounds': compounds,
        'q_compounds': q_compounds,
        'qualifying_gaps': q_laps
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


def countries_view(request, division=None):
    if division is None:
        division = Division.objects.first().id

    stats = {}
    query = Result.objects.filter(position__range=[1, 10], race__season__division_id=division).\
        exclude(driver__country='').values('driver__country', 'position').\
        annotate(Count('position')).order_by('position', '-position__count')

    for row in query:
        country = Country(row['driver__country'])
        if country.code not in stats:
            stats[country.code] = {i: 0 for i in range(1, 11)}
            stats[country.code]['country'] = country
        stats[country.code][row['position']] = row['position__count']

    sorted_stats = {}
    stats_sort = sorted(stats, key=lambda item: stats[item][10], reverse=True)
    for pos in list(reversed([x for x in range(1, 10)])):
        stats_sort = sorted(stats_sort, key=lambda item: stats[item][pos], reverse=True)

    for country in stats_sort:
        sorted_stats[country] = stats[country]

    current_division = None
    divisions = {}
    for div in Division.objects.prefetch_related('league'):
        if div.league_id not in divisions:
            divisions[div.league_id] = {'name': div.league.name, 'divisions': []}
        divisions[div.league_id]['divisions'].append({
            'id': div.id, 'name': div.name, 'selected': div.id == int(division)
        })

        if div.id == int(division):
            current_division = div

    context = {
        'stats': sorted_stats,
        'positions': [x for x in range(1, 11)],
        'divisions': divisions,
        'current_division': current_division
    }

    return render(request, 'standings/countries.html', context)


def country_view(request, country_id, division=None):
    if division is None:
        division = Division.objects.first().id

    country = Country(country_id)
    drivers = Driver.objects.filter(country=country_id).distinct()
    teams = Team.objects.filter(country=country_id).distinct()

    stats = {}
    query = Result.objects.filter(position__range=[1, 10], driver_id__in=drivers, race__season__division_id=division).\
        values('driver_id', 'position').annotate(Count('position')).order_by('position', '-position__count')

    for row in query:
        if row['driver_id'] not in stats:
            stats[row['driver_id']] = {i: 0 for i in range(1, 11)}
            stats[row['driver_id']]['name'] = drivers.get(pk=row['driver_id']).name
        stats[row['driver_id']][row['position']] = row['position__count']

    sorted_stats = {}
    stats_sort = sorted(stats, key=lambda item: stats[item][10], reverse=True)
    for pos in list(reversed([x for x in range(1, 10)])):
        stats_sort = sorted(stats_sort, key=lambda item: stats[item][pos], reverse=True)

    for driver_id in stats_sort:
        sorted_stats[driver_id] = stats[driver_id]

    current_division = None
    divisions = {}
    for div in Division.objects.prefetch_related('league'):
        if div.league_id not in divisions:
            divisions[div.league_id] = {'name': div.league.name, 'divisions': []}
        divisions[div.league_id]['divisions'].append({
            'id': div.id, 'name': div.name, 'selected': div.id == int(division)
        })

        if div.id == int(division):
            current_division = div

    context = {
        'country': country,
        'drivers': drivers,
        'teams': teams,
        'stats': sorted_stats,
        'positions': [x for x in range(1, 11)],
        'divisions': divisions,
        'current_division': current_division
    }

    return render(request, 'standings/country.html', context)
