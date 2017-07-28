class Interpolator {
    constructor() {
        this.data = [];
    }

    addIndexValue(index, value) {
        this.data.push({index: index, value: value});

        // make sure items are in ascdending order by index
        //this.data.sort((a, b) => a.index - b.index);
    }

    valueAtIndex(target_index) {
        if (target_index < this.data[0].index || this.data[this.data.length - 1].index < target_index) {
            return null;
        }
        else {
            var start = null
            var end = null;

            for (var i = 0; i < this.data.length; i++) {
                let current = this.data[i];

                if (current.index === target_index) {
                    return current.value;
                }
                else {
                    if (current.index <= target_index) {
                        start = current;
                    }
                    else if (target_index < current.index) {
                        end = current;
                        break;
                    }
                }
            }

            let index_delta = end.index - start.index;
            let percent = (target_index - start.index) / index_delta;
            let value_delta = end.value - start.value;

            return start.value + value_delta * percent;
        }
    }
}
