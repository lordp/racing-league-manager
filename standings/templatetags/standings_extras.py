from django import template
import standings.utils
from django.conf import settings
from django.utils.safestring import mark_safe
import textwrap

register = template.Library()


def position_display(result):
    if result is None:
        return '-'

    special_positions = {
        None: '-',
        0: '-',
        -1: 'Ret',
        -2: 'DSQ',
        -3: 'DNS'
    }

    return special_positions.get(result.position, result.position)


def position_colour(result, season):
    colours = {
        '-': 'default',
        0: 'default',
        1: 'yellow',
        2: 'gray',
        3: 'orange',
        'Ret': 'retired',
        'DSQ': 'black',
        'DNS': 'default'
    }

    if result.race.point_system:
        ps = result.race.point_system.to_dict()
    else:
        ps = season.point_system.to_dict()

    colours.update({x: 'green' for x in range(4, len(ps) + 1)})

    return "pos-{}".format(str(colours.get(result.position, 'blue')))


@register.filter(name='find_result')
def find_result(results, race):
    try:
        result = [result for result in results if result.race_id == race.id][0]
    except IndexError:
        result = None
    return result


@register.filter(name='find_driver')
def find_driver(results, driver):
    try:
        result = [result for result in results if result.driver_id == driver.id][0]
    except IndexError:
        result = None
    return result


@register.filter(name='find_results')
def find_results(results, race):
    return [result for result in results if result.race_id == race.id]


@register.filter(name='get_position')
def get_position(result):
    return position_display(result)


@register.filter(name='get_points')
def get_points(results, season):
    if len(results) == 0:
        return 0

    points = 0
    ps = season.point_system.to_dict()
    for result in results:
        if result.race.point_system:
            ps = result.race.point_system.to_dict()
        points += ps.get(result.position, 0)

    return points


@register.filter(name='format_time')
def format_time(seconds):
    return standings.utils.format_time(seconds)


@register.filter(name='format_float')
def format_float(num):
    return standings.utils.format_float(num)


@register.filter(name='get_css_classes')
def get_css_classes(result, season):
    ret = []

    if result is not None:
        ret.append(position_colour(result, season))
        if result.qualifying == 1:
            ret.append("pole-position")
        if result.fastest_lap:
            ret.append("fastest-lap")
    else:
        ret.append('pos-default')

    return " ".join(ret)


@register.filter(name='collate_notes')
def collate_notes(result):
    notes = []

    if result is not None:
        if result.note != '' and result.note is not None:
            notes.append(result.note)

        if result.race_penalty_description != '' and result.race_penalty_description is not None:
            notes.append("R: {}".format(result.race_penalty_description))

        if result.qualifying_penalty_description != '' and result.qualifying_penalty_description is not None:
            notes.append("Q: {}".format(result.qualifying_penalty_description))

        if result.subbed_by is not None:
            notes.append(
                '{} reserved for {}'.format(result.subbed_by.name, result.driver.name)
            )

        if result.allocate_points is not None:
            notes.append(
                'WCC points allocated to {}'.format(result.allocate_points.name)
            )

    note = textwrap.shorten('; '.join([n for n in notes if n is not None]), width=100)
    return note


@register.filter(name='admin_breadcrumb')
def admin_breadcrumb(breadcrumb):
    return 'admin:standings_{}_changelist'.format(breadcrumb['url'])


@register.filter(name='show_flag')
def show_flag(country):
    if country in settings.COUNTRIES_OVERRIDE:
        return mark_safe('<img src="{}" title="{}"/>'.format(country.flag, country.name))
    else:
        return mark_safe('<i class="{}" title="{}"></i>'.format(country.flag_css, country.name))
