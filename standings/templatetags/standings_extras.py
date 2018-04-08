from django import template
import standings.utils

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


def position_colour(position, season):
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

    ps = season.point_system.to_dict()
    colours.update({x: 'green' for x in range(4, len(ps) + 1)})

    return "pos-{}".format(str(colours.get(position['position'], 'blue')))


@register.filter(name='find_result')
def find_result(results, race):
    return results.filter(race__id=race.id).first()


@register.filter(name='find_results')
def find_results(results, race):
    return results.filter(race__id=race.id)


@register.filter(name='get_position')
def get_position(result):
    return position_display(result)


@register.filter(name='get_points')
def get_points(results, season):
    if results.count() == 0:
        return 0

    points = 0
    ps = season.point_system.to_dict()
    for result in results:
        # ps = result.race.season.point_system.to_dict()
        points += ps.get(result.position, 0)

    return points


@register.filter(name='get_result_points')
def get_result_points(result, season):
    points = 0
    ps = season.point_system.to_dict()
    points += ps.get(result.position, 0)

    return points


@register.filter(name='format_time')
def format_time(seconds):
    return standings.utils.format_time(seconds)


@register.filter(name='get_css_classes')
def get_css_classes(result, season):
    ret = []

    if result is not None:
        ret.append(position_colour({"position": result.position}, season))
        if result.position == 1:
            ret.append("pole-position")
        if result.fastest_lap:
            ret.append("fastest-lap")
    else:
        ret.append('pos-default')

    return " ".join(ret)


@register.filter(name='collate_notes')
def collate_notes(result):
    notes = []
    if result.note != '' and result.note is not None:
        notes.append(result.note)

    if result.subbed_by is not None:
        notes.append(
            '{} reserved for {}'.format(result.subbed_by.name, result.driver.name)
        )

    if result.allocate_points is not None:
        notes.append(
            'WCC points allocated to {}'.format(result.allocate_points.name)
        )

    note = '; '.join([n for n in notes if n is not None])
    return note
