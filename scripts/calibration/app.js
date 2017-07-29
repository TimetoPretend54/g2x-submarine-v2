let svgns = "http://www.w3.org/2000/svg";

var sensitivity, iWithS;
var iGraph, sGraph, iwsGraph;

var data;
var activeThruster = 0;

function go() {
    createCharts();
    Data.getData(applyToCharts);
}

function applyToCharts(error, data) {
    // convert thruster data providers
    data.thrusters = data.thrusters.map(values => {
        let interpolator = new Interpolator();

        for (var i = 0; i < values.length; i += 2) {
            interpolator.addIndexValue(values[i], values[i+1]);
        }

        return interpolator;
    });

    // create sensitivity data provider
    sensitivity = new Sensitivity(data.sensitivity.strength, data.sensitivity.power);

    // create thruster with sensitivity provider
    iWithS = new InterpolatorWithSensitivity(data.thrusters[activeThruster], sensitivity);

    // apply data providers to graphs
    iGraph.dataProvider = data.thrusters[activeThruster];
    sGraph.dataProvider = sensitivity;
    iwsGraph.dataProvider = iWithS;

    // update all graphs
    iGraph.drawData();
    sGraph.drawData();
    iwsGraph.drawData();
}

function createCharts() {
    let chart = document.getElementById("chart");

    let margin = 35;
    let padding = 15;
    let width = 600;
    let height = 200;

    iGraph = new Graph(
        margin,
        margin + 0 * (200 + padding),
        width,
        height,
        0, 360,
        -1, 1,
        4,
        10,
        360,
        10,
        null
    );

    sGraph = new Graph(
        margin,
        margin + 1 * (200 + padding),
        width,
        height,
        -1, 1,
        -1, 1,
        4,
        8,
        360,
        10,
        null
    );

    iwsGraph = new Graph(
        margin,
        margin + 2 * (200 + padding),
        width,
        height,
        0, 360,
        -1, 1,
        4,
        8,
        360,
        10,
        null
    );

    iGraph.attach(chart);
    sGraph.attach(chart);
    iwsGraph.attach(chart);
}

function createInterpolator() {
    let interpolator = new Interpolator();

    interpolator.addIndexValue(0.0, -1.0)
    interpolator.addIndexValue(90.0, 1.0)
    interpolator.addIndexValue(180.0, 1.0)
    interpolator.addIndexValue(270.0, -1.0)
    interpolator.addIndexValue(360.0, -1.0)

    return interpolator;
}

function updateT(value) {
    sensitivity.t = value;

    document.getElementById("tLabel").innerHTML = value;

    sGraph.drawData();
    iwsGraph.drawData();
}

function updatePower(value) {
    sensitivity.power = value;

    document.getElementById("powerLabel").innerHTML = value;

    sGraph.drawData();
    iwsGraph.drawData();
}