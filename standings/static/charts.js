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

function dynamicColours(name) {
    let pick = colours.pop();
    let r = pick[0];
    let g = pick[1];
    let b = pick[2];

    if (colours.length === 0) {
        $('#' + name + '-chart .add-driver').attr('disabled', 'disabled').addClass('disabled');
    }

    return "rgb(" + r + "," + g + "," + b + ")";
}

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

function add_driver(event) {
    let driver_list = $('#' + event.data.name + '-driver-list');
    let driver_id = driver_list[0][driver_list[0].selectedIndex].value;

    let found = false;
    $.each(event.data.chart.data.datasets, function () {
        found = this.driver === driver_id;
    });

    if (!found) {
        let data = [];
        if (event.data.name === 'lap') {
            data = lap_times[driver_id];
        }
        else {
            data = gap_times[driver_id];
        }

        let dataset = {
            "data": data,
            "fill": false,
            "driver": driver_id,
            "borderColor": dynamicColours(event.data.name),
            "label": driver_list[0][driver_list[0].selectedIndex].text
        };

        event.data.chart.data.datasets.push(dataset);
        event.data.chart.update();
    }

    return false;
}

function remove_driver(event) {
    let driver_list = $('#' + event.data.name + '-driver-list');
    let driver_id = driver_list[0][driver_list[0].selectedIndex].value;

    let found = event.data.chart.data.datasets.filter(dataset => dataset.driver === driver_id);
    if (found.length > 0) {
        let found_colour = found[0].borderColor.split(colour_regex);
        colours.push([found_colour[1], found_colour[2], found_colour[3]]);
        if (colours.length > 0) {
            $('#' + event.data.name + '-chart .add-driver').attr('disabled', null).removeClass('disabled');
        }


        event.data.chart.data.datasets = event.data.chart.data.datasets.filter(dataset => dataset.driver !== driver_id);
        event.data.chart.update();
    }

    return false;
}

function calculate_gaps() {
    let gap_data = {};
    let winner_average = array_sum(winner_laps) / winner_laps.length;

    $.each(lap_times, function (driver_id, laps) {
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

