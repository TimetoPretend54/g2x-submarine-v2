class Sensitivity {
    constructor() {
        this.t = 0.7;
        this.power = 3;
    }

    valueAtIndex(index) {
        // clamp value
        index = Math.max(-1, Math.min(index, 1));

        // first line is odd number polynomial >= 3
        // second line is a line or polynomial === 1
        return (
            this.t * Math.pow(index, this.power) +
            (1.0 - this.t) * index
        );
    }
}
