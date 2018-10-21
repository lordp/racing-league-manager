function convert_seconds_to_lap(seconds, include_micro) {
    let t1 = Math.floor(seconds / 60);
    let t2;
    if (include_micro) {
        t2 = (seconds % 60).toFixed(3);
    }
    else {
        t2 = (seconds % 60).toFixed(0);
    }
    return (t1 > 0 ? t1 + ":" : '') + (t2.padStart(2, '0'));
}

const colours = [
    [124, 181, 236],
    [67, 67, 72],
    [144, 237, 125],
    [247, 163, 92],
    [128, 133, 233],
    [241, 92, 128],
    [228, 211, 84],
    [128, 133, 232],
    [141, 70, 83],
    [145, 232, 225],
];

const colour_regex = /rgb\((\d+),(\d+),(\d+)\)/;
const titles = {
    'add': 'Add driver to charts.',
    'del': 'Remove driver from charts.',
    'max': 'The maximum number of drivers (10) have been added.',
};

// Helper method to return a total time for an array or array slice
function array_sum(array) {
    let race = 0;
    if (array.length > 0) {
        race = array.reduce(function (a, b) {
            return a + b;
        });
    }

    return race;
}

function add_driver(driver_id, driver_name, checkbox) {
    $('[data-chart=true]').each(function(i, element) {
        let name = element.id.replace('-chart', '');
        let chart = charts[name];
        let colours = colour_lists[name];

        let found = false;
        $.each(chart.data.datasets, function () {
            found = this.driver === driver_id;
        });

        if (!found) {
            let data = times[name][driver_id];
            let pick = colours.pop();
            if (colours.length === 0) {
                $('.add-to-charts:not(:checked)').attr('disabled', 'disabled').attr('title', titles['max'])
            }

            $(checkbox).attr('title', titles['del']);

            let dataset = {
                "data": data,
                "fill": false,
                "driver": driver_id,
                "borderColor": "rgb(" + pick[0] + "," + pick[1] + "," + pick[2] + ")",
                "label": driver_name
            };

            chart.data.datasets.push(dataset);
            chart.update();
        }
    });

    return false;
}

function remove_driver(driver_id, checkbox) {
    $('[data-chart=true]').each(function(i, element) {
        let name = element.id.replace('-chart', '');
        let chart = charts[name];
        let colours = colour_lists[name];

        let found = chart.data.datasets.filter(dataset => dataset.driver === driver_id);
        if (found.length > 0) {
            let found_colour = found[0].borderColor.split(colour_regex);
            colours.push([found_colour[1], found_colour[2], found_colour[3]]);
            if (colours.length > 0) {
                // $('#' + element + '-chart .add-driver').attr('disabled', null).removeClass('disabled');
                $('.add-to-charts:not(:checked)').attr('disabled', null).attr('title', titles['add'])
            }

            chart.data.datasets = chart.data.datasets.filter(dataset => dataset.driver !== driver_id);
            chart.update();
        }
    });

    return false;
}

function calculate_gaps() {
    let gap_data = {};
    let winner_average = array_sum(winner_laps) / winner_laps.length;

    $.each(times['lap'], function (driver_id, laps) {
        let data = [];
        let average = [];
        $.each(laps, function (i, lap) {
            // First lap is handled separately
            if (i === 0) {
                average.push(lap);
            }

            // Other laps are added together as you go
            else {
                let laps_slice = [];
                $.each(laps.slice(0, i + 1), function (i, lap) {
                    laps_slice.push(lap);
                });
                average.push(array_sum(laps_slice));
            }

            // Keep a track of the difference
            data.push(((winner_average * (i + 1)) - average[i]));
        });

        // data.unshift(0);
         gap_data[driver_id] = data;
    });

    return gap_data;
}

