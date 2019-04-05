function to_hex(d) {
    return ("0" + (Number(d).toString(16))).slice(-2)
}

function fill_style(num, type) {
    if (type === 'line') {
        num = to_hex((70 + (num * 170)).toFixed());
    } else if (type === 'box') {
        num = to_hex((255 - (num * 170) / 5.0).toFixed());
    }

    return "#CC" + num + "33";
}

function draw_wear_line(ctx, tyre, offset) {
    ctx.fillStyle = fill_style(tyre, 'line');
    ctx.fillRect(0, offset, 60 * tyre, 5);
    ctx.strokeRect(0, offset, 60 * tyre, 5);
}

function tyre_wear_line(canvas) {
    var ctx = canvas.getContext("2d");

    ctx.strokeStyle = "#999";
    ctx.fillStyle = "#FFF";
    ctx.fillRect(0, 0, 60, 20);

    draw_wear_line(ctx, canvas.parentElement.getAttribute("data-twfl"), 0);
    draw_wear_line(ctx, canvas.parentElement.getAttribute("data-twfr"), 5);
    draw_wear_line(ctx, canvas.parentElement.getAttribute("data-twrl"), 10);
    draw_wear_line(ctx, canvas.parentElement.getAttribute("data-twrr"), 15);
}

var offsets = {
    "twfl": {
        "text": {
            "x": 18, "y": 7
        },
        "box": {
            "x": 21, "y": 0
        }
    },
    "twfr": {
        "text": {
            "x": 50, "y": 7
        },
        "box": {
            "x": 53, "y": 0
        }
    },
    "twrl": {
        "text": {
            "x": 18, "y": 19
        },
        "box": {
            "x": 21, "y": 13
        }
    },
    "twrr": {
        "text": {
            "x": 50, "y": 19
        },
        "box": {
            "x": 53, "y": 13
        }
    },
};

function draw_wear_box(ctx, tyre, value) {
    ctx.fillStyle = "#000";

    var wear_display;
    var lap = Number(ctx.canvas.parentElement.getAttribute('data-lap'));
    if (lap === 1) {
        wear_display = ((1 - value) * 100).toFixed(1);
    } else {
        wear_display = (($('td[data-lap="' + (lap - 1) + '"').attr('data-' + tyre) - value) * 100).toFixed(1);
    }

    if (Number(wear_display) < 0) {
        wear_display = "0";
    }

    ctx.fillText(wear_display, offsets[tyre]['text']['x'], offsets[tyre]['text']['y']);

    ctx.fillStyle = fill_style(check_diff(wear_display), 'box');
    ctx.fillRect(offsets[tyre]['box']['x'], offsets[tyre]['box']['y'], 7, 7);
}

function check_diff(diff) {
    diff = parseFloat(diff);
    if (isNaN(diff)) {
        diff = 0;
    } else if (diff > 5) {
        diff = 5;
    }

    return diff;
}

function tyre_wear_box(canvas) {
    var ctx = canvas.getContext("2d");
    ctx.textAlign = "right";

    draw_wear_box(ctx, 'twfl', canvas.parentElement.getAttribute("data-twfl"));
    draw_wear_box(ctx, 'twfr', canvas.parentElement.getAttribute("data-twfr"));
    draw_wear_box(ctx, 'twrl', canvas.parentElement.getAttribute("data-twrl"));
    draw_wear_box(ctx, 'twrr', canvas.parentElement.getAttribute("data-twrr"));
}