var width = 360;
var height = 360;
var cx = (width / 2);
var cy = (height / 2);
var outerRadius = 30;
var elementWidth = width * Math.sqrt(2);
var xOffset = -(elementWidth - 360) / 2;
var lineWidth = 5;
var pitchScaleFactor = (width - (2 * outerRadius)) / width;

/* SVG.js 2.7
var attitudeDisplay = SVG('attitude').size(width, height);
$("#SvgjsSvg1003").appendTo($("#attitude"));
*/

/* SVG.js 3.0 */
var attitudeDisplay = SVG().addTo("#attitude").size(width, height);

var groundInner = attitudeDisplay.rect(elementWidth, height).attr({ fill: '#654321' }).stroke({ color: "#ffffff", width: lineWidth / 2 });
var skyInner = attitudeDisplay.rect(elementWidth, height).attr({ fill: '#87ceeb' }).stroke({ color: "#ffffff", width: lineWidth / 2 });

var pitchMarkings = [
    attitudeDisplay.line(cx - 30, cy, cx + 30, cy).center(cx, cy + (120 * pitchScaleFactor)).stroke({ color: "#ffffff", width: lineWidth / 2 }),
    attitudeDisplay.text("120").center(cx - 50, cy + (120 * pitchScaleFactor)).fill("#ffffff"), attitudeDisplay.text("120").center(cx + 50, cy + (120 * pitchScaleFactor)).fill("#ffffff"),
    attitudeDisplay.line(cx - 10, cy, cx + 10, cy).center(cx, cy + (90 * pitchScaleFactor)).stroke({ color: "#ffffff", width: lineWidth / 3 }),
    attitudeDisplay.line(cx - 35, cy, cx + 35, cy).center(cx, cy + (60 * pitchScaleFactor)).stroke({ color: "#ffffff", width: lineWidth / 2 }),
    attitudeDisplay.text("60").center(cx - 50, cy + (60 * pitchScaleFactor)).fill("#ffffff"), attitudeDisplay.text("60").center(cx + 50, cy + (60 * pitchScaleFactor)).fill("#ffffff"),
    attitudeDisplay.line(cx - 15, cy, cx + 15, cy).center(cx, cy + (45 * pitchScaleFactor)).stroke({ color: "#ffffff", width: lineWidth / 3 }),
    attitudeDisplay.line(cx - 30, cy, cx + 30, cy).center(cx, cy + (30 * pitchScaleFactor)).stroke({ color: "#ffffff", width: lineWidth / 2 }),
    attitudeDisplay.text("30").center(cx - 45, cy + (30 * pitchScaleFactor)).fill("#ffffff"), attitudeDisplay.text("30").center(cx + 45, cy + (30 * pitchScaleFactor)).fill("#ffffff"),
    attitudeDisplay.line(cx - 15, cy, cx + 15, cy).center(cx, cy + (20 * pitchScaleFactor)).stroke({ color: "#ffffff", width: lineWidth / 2 }),
    attitudeDisplay.line(cx - 10, cy, cx + 10, cy).center(cx, cy + (10 * pitchScaleFactor)).stroke({ color: "#ffffff", width: lineWidth / 3 }),
    attitudeDisplay.line(cx - 10, cy, cx + 10, cy).center(cx, cy + (-10 * pitchScaleFactor)).stroke({ color: "#ffffff", width: lineWidth / 3 }),
    attitudeDisplay.line(cx - 15, cy, cx + 15, cy).center(cx, cy + (-20 * pitchScaleFactor)).stroke({ color: "#ffffff", width: lineWidth / 2 }),
    attitudeDisplay.line(cx - 30, cy, cx + 30, cy).center(cx, cy + (-30 * pitchScaleFactor)).stroke({ color: "#ffffff", width: lineWidth / 2 }),
    attitudeDisplay.text("30").center(cx - 45, cy + (-30 * pitchScaleFactor)).fill("#ffffff"), attitudeDisplay.text("30").center(cx + 45, cy + (-30 * pitchScaleFactor)).fill("#ffffff"),
    attitudeDisplay.line(cx - 15, cy, cx + 15, cy).center(cx, cy + (-45 * pitchScaleFactor)).stroke({ color: "#ffffff", width: lineWidth / 3 }),
    attitudeDisplay.line(cx - 35, cy, cx + 35, cy).center(cx, cy + (-60 * pitchScaleFactor)).stroke({ color: "#ffffff", width: lineWidth / 2 }),
    attitudeDisplay.text("60").center(cx - 50, cy + (-60 * pitchScaleFactor)).fill("#ffffff"), attitudeDisplay.text("60").center(cx + 50, cy + (-60 * pitchScaleFactor)).fill("#ffffff"),
    attitudeDisplay.line(cx - 10, cy, cx + 10, cy).center(cx, cy + (-90 * pitchScaleFactor)).stroke({ color: "#ffffff", width: lineWidth / 3 }),
    attitudeDisplay.line(cx - 30, cy, cx + 30, cy).center(cx, cy + (-120 * pitchScaleFactor)).stroke({ color: "#ffffff", width: lineWidth / 2 }),
    attitudeDisplay.text("120").center(cx - 50, cy + (-120 * pitchScaleFactor)).fill("#ffffff"), attitudeDisplay.text("120").center(cx + 50, cy + (-120 * pitchScaleFactor)).fill("#ffffff")];
var pitchMarkingLocs = [120, 120, 120, 90, 60, 60, 60, 45, 30, 30, 30, 20, 10, -10, -20, -30, -30, -30, -45, -60, -60, -60, -90, -120, -120, -120];

var groundOuter = attitudeDisplay.rect(elementWidth, height).attr({ fill: '#654321' }).stroke({ color: "#ffffff", width: lineWidth });
var skyOuter = attitudeDisplay.rect(elementWidth, height).attr({ fill: '#87ceeb' }).stroke({ color: "#ffffff", width: lineWidth });

groundInner.move(xOffset, 180);
skyInner.move(xOffset, -180);
groundOuter.move(xOffset, 180);
skyOuter.move(xOffset, -180);

var rollMarkings = [[-60, attitudeDisplay.line(cx, outerRadius / 10, cx, outerRadius).stroke({ color: "#ffffff", width: lineWidth })],
[-45, attitudeDisplay.circle(lineWidth * 1.25).center(cx, outerRadius / 2).fill("#ffffff")],
[-30, attitudeDisplay.line(cx, outerRadius / 10, cx, outerRadius).stroke({ color: "#ffffff", width: lineWidth })],
[-20, attitudeDisplay.line(cx, outerRadius / 2, cx, outerRadius).stroke({ color: "#ffffff", width: lineWidth / 2 })],
[-10, attitudeDisplay.line(cx, outerRadius / 2, cx, outerRadius).stroke({ color: "#ffffff", width: lineWidth / 2 })],
[0, attitudeDisplay.polyline([[cx - (outerRadius / 2.5), outerRadius / 10], [cx, outerRadius], [cx + (outerRadius / 2.5), outerRadius / 10], [cx - (outerRadius / 2), outerRadius / 10]]).fill("#ffffff").stroke({ width: 0, color: "#ffffff" })],
[10, attitudeDisplay.line(cx, outerRadius / 2, cx, outerRadius).stroke({ color: "#ffffff", width: lineWidth / 2 })],
[20, attitudeDisplay.line(cx, outerRadius / 2, cx, outerRadius).stroke({ color: "#ffffff", width: lineWidth / 2 })],
[30, attitudeDisplay.line(cx, outerRadius / 10, cx, outerRadius).stroke({ color: "#ffffff", width: lineWidth })],
[45, attitudeDisplay.circle(lineWidth * 1.25).center(cx, outerRadius / 2).fill("#ffffff")],
[60, attitudeDisplay.line(cx, outerRadius / 10, cx, outerRadius).stroke({ color: "#ffffff", width: lineWidth })]];

updateMarkers(0);

var maskOuter = attitudeDisplay.mask();
maskOuter.add(attitudeDisplay.circle(360).fill("#ffffff"));
maskOuter.add(attitudeDisplay.circle(width - (2 * outerRadius)).dmove(outerRadius, outerRadius).fill("#000000"));
groundOuter.maskWith(maskOuter);
skyOuter.maskWith(maskOuter);

var maskInner = attitudeDisplay.mask();
maskInner.add(attitudeDisplay.circle(360).fill("#ffffff"));
groundInner.maskWith(maskInner);
skyInner.maskWith(maskInner);

var shadowGradient = attitudeDisplay.gradient('radial', function (add) {
    add.stop({ offset: 0, color: "#000000", opacity: 0 })
    add.stop({ offset: 0.5, color: "#000000", opacity: 0.1 })
    add.stop({ offset: 0.75, color: "#000000", opacity: 0.3 })
    add.stop({ offset: 1, color: "#000000", opacity: 1 })
})

var lightGradient = attitudeDisplay.gradient('radial', function (add) {
    add.stop({ offset: 1 - (2 * outerRadius / width), color: "#ffffff", opacity: 1 })
    add.stop({ offset: (1 - (2 * outerRadius / width)) * 1.07, color: "#ffffff", opacity: 0.3 })
    add.stop({ offset: 1, color: "#ffffff", opacity: 0 })
})

var shadow = attitudeDisplay.circle(width - (2 * outerRadius)).dmove(outerRadius, outerRadius).fill(shadowGradient).opacity(0.4);
var light = attitudeDisplay.circle(width).fill(lightGradient).opacity(0.5);
light.maskWith(maskOuter);

var markerStand = attitudeDisplay.polyline([[cx - 10, height], [cx - 1, cy + 40], [cx + 1, cy + 40], [cx + 10, height]]).fill("#ffff00").stroke({ color: "#ffff00", width: lineWidth });
var markerLine = attitudeDisplay.line(cx, cy, cx, height).stroke({ color: "#ffff00", width: lineWidth / 1.5 });
var markerCircle = attitudeDisplay.circle(lineWidth * 2).center(cx, cy).fill("#ffff00");
var orientationGuide = attitudeDisplay.path("M 31.427734,270.96094 H 265.25781 c -4.4e-4,65.73748 53.28987,119.02865 119.02735,119.02929 65.73824,4.4e-4 119.02973,-53.29105 119.02929,-119.02929 h 233.82813").attr({ 'fill-opacity': 0, stroke: "#ffff00", 'stroke-width': lineWidth * 3.33 }).center(cx, cy + 18).scale(0.3);

function updateAttitude(gyroData) {
    var roll = gyroData.x; // -180 to 180 (Data from the gyro will probably be 0-360. Check if # is > 180, if so subtract 180 and multiply by -1)
    var pitch = gyroData.y; // ''
    var pScale = 3; // 1-3 (Take max of circular array *1.2? should automatically adjust based on the pitch values)

    pitchScaleFactor = ((width - (2 * outerRadius)) / width) * pScale;
    pitch *= pitchScaleFactor;

    groundInner.rotate(roll, cx, cy);
    skyInner.rotate(roll, cx, cy);
    groundInner.y(pitch + 180);
    skyInner.y(pitch - 180);
    groundOuter.rotate(roll, cx, cy);
    skyOuter.rotate(roll, cx, cy);

    updateMarkers(roll);
}

function updateMarkers(roll) {
    for (var i = 0; i < rollMarkings.length; i++) {
        rollMarkings[i][1].rotate(rollMarkings[i][0] + roll, cx, cy);
    }

    for (var i = 0; i < pitchMarkings.length; i++) {
        pitchMarkings[i].cy(cy + (pitchMarkingLocs[i] * pitchScaleFactor));
    }

    for (var i = 0; i < pitchMarkings.length; i++) {
        pitchMarkings[i].rotate(roll, cx, cy)
    }
}