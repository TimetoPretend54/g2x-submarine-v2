import React, { Component } from 'react';
import './App.css';
import LineChart from './components/LineChart';
import Compass from './components/Compass';

class App extends Component {
    constructor(props) {
        super(props);
        this.state = {
            depth: [],
            temperature: [],
            compass: []
        };
    }

    componentDidMount() {
        this.intervalId = setInterval(
            () => this.tick(),
            1000
        );
    }

    componentWillUnount() {
        clearInterval(this.intervalId);
    }

    tick() {
        var t = Date.now();
        var depth = [];
        var temperature = [];
        var i, value;

        for (i = 10; i < 100; i += 10) {
            value = ((i + t * 0.25) % 80) + 10;

            depth.push([i, value]);
        }

        for (i = 10; i < 100; i += 10) {
            value = ((i + t * 0.25) % 80) + 10;

            temperature.push([i, value]);
        }

        this.setState({
            depth: depth,
            temperature: temperature,
            compass: (t / 100) % 360.0
        });
    }

    render() {
        var depth = this.state.depth;
        var temperature = this.state.temperature;
        var direction = `rotate(${-this.state.compass})`;
        var depthLabel = depth.length > 0
            ? depth[depth.length - 1][1] + " ft"
            : "-- ft";
        var temperatureLabel = temperature.length > 0
            ? temperature[temperature.length - 1][1] + " °F"
            : "-- °F";

        return (
            <div className="App">
                <LineChart label={depthLabel} data={depth}/>
                <LineChart label={temperatureLabel} data={temperature}/>
                <Compass direction={direction}/>
            </div>
        );
    }
}

export default App;
