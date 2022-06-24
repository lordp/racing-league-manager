from django.test import TestCase

from .models import Season


class SeasonModelTests(TestCase):
    fixtures = ["division", "driver", "league", "point_system", "race", "result", "season", "team", "track"]

    def test_standings_show_correct_position(self):
        s = Season.objects.get(pk=1)
        ss = s.get_standings(use_position=True)

        drivers = {
            99: {"name": "Tom Oldenmenger", "points": 96, "position": 1},
            100: {"name": "Luca D Amelio", "points": 79, "position": 2},
            91: {"name": "Cameron Rodger", "points": 79, "position": 3},
            174: {"name": "Bojan Bogdanov", "points": 13, "position": 14},
            304: {"name": "Kostas Galanomatis", "points": 13, "position": 13},
            244: {"name": "Eduard Batalla", "points": 11, "position": 18},
            93: {"name": "Matthew Tuson", "points": 11, "position": 17},
            292: {"name": "Francesco Morante", "points": 11, "position": 16},
            92: {"name": "Mirko Lupini", "points": 11, "position": 15}
        }

        for driver_id, driver_info in drivers.items():
            position = ss[0][driver_info["position"] - 1]
            assert position["driver"].id == driver_id
            assert position["points"] == driver_info["points"]
            assert position["position"] == driver_info["position"]
