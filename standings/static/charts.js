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
    { 'name': '#7cb5ec', 'used': false, 'rgb': [124, 181, 236] },
    { 'name': '#434348', 'used': false, 'rgb': [67, 67, 72] },
    { 'name': '#90ed7d', 'used': false, 'rgb': [144, 237, 125] },
    { 'name': '#f7a35c', 'used': false, 'rgb': [247, 163, 92] },
    { 'name': '#8085e9', 'used': false, 'rgb': [128, 133, 233] },
    { 'name': '#f15c80', 'used': false, 'rgb': [241, 92, 128] },
    { 'name': '#e4d354', 'used': false, 'rgb': [228, 211, 84] },
    { 'name': '#2b908f', 'used': false, 'rgb': [43, 144, 143] },
    { 'name': '#f45b5b', 'used': false, 'rgb': [141, 70, 83] },
    { 'name': '#91e8e1', 'used': false, 'rgb': [145, 232, 225] },
];

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

function pick_colour(name) {
    if (typeof name === 'undefined') {
        let pick = colours.filter(colour => colour.used === false);
        pick[0].used = true;

        return pick[0];
    }

    let pick = colours.filter(colour => colour.used === true && colour.name === name);
    pick[0].used = false;
}

function add_driver(driver_id, driver_name, checkbox) {
    let colour = pick_colour();

    $('[data-chart=true]').each(function(i, element) {
        let name = element.id.replace('-chart', '');
        let chart = charts[name];

        let data = times[name][driver_id];
        let dataset = {
            "data": data,
            "fill": false,
            "driver": driver_id,
            "borderColor": "rgb(" + colour['rgb'][0] + "," + colour['rgb'][1] + "," + colour['rgb'][2] + ")",
            "colour": colour['name'],
            "label": driver_name
        };

        chart.data.datasets.push(dataset);
        chart.update();

        if (chart.data.datasets.length === 10) {
            $('.add-to-charts:not(:checked)').attr('disabled', 'disabled').attr('title', titles['max'])
        }

        $(checkbox).attr('title', titles['del']);
    });

    return false;
}

function remove_driver(driver_id) {
    $('[data-chart=true]').each(function(i, element) {
        let name = element.id.replace('-chart', '');
        let chart = charts[name];

        let found = chart.data.datasets.filter(dataset => dataset.driver === driver_id);
        if (found.length > 0) {
            pick_colour(found.colour);
            $('.add-to-charts:not(:checked)').attr('disabled', null).attr('title', titles['add']);

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

