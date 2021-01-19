//Initialize socket timeout
let socketTimeout;
let url;

const chartMap = new Map();
const resizeCharts = function () {
    chartMap.forEach(function (chart) {
        window.echarts.getInstanceByDom(chart).resize();
    });
};

const updateChart = function (json) {
    const id = 'chart-' + json.name;
    let chartElement = document.querySelector('#' + id);
    let chart;
    if(!chartElement) {
        const chartTemplate = document.querySelector('#chart-template').content.cloneNode(true);
        chartTemplate.querySelector('.chart').id = id;
        document.body.appendChild(chartTemplate);
        chartElement = document.querySelector('#' + id);
        chart = echarts.init(chartElement);
    } else {
        chart = echarts.getInstanceByDom(chartElement);
    }

    const series = [];
    for(let i = 1; i < json.columns.length; i++) {
        series.push({
            type: 'line',
            areaStyle: {},
            encode: {
                y: i,
                seriesName: json.columns[i]
            }
        });
    }
    chart.setOption({
        title: {
            text: json.name,
        },
        legend: {},
        grid: {
            show: true,
        },
        tooltip: {
            trigger: 'axis',
        },
        xAxis: {
            type: 'time',
            boundaryGap: false,
            axisLabel: {
                rotate: 30,
                formatter: function (value) {
                    return echarts.format.formatTime('hh:mm:ss', value);
                }
            },
        },
        yAxis: {
            type: 'value',
            max: json.max,
            axisLabel: {
                formatter: json.suffix ? '{value}' + json.suffix : '{value}'
            }
        },
        dataset: {
            dimensions: json.columns,
            source: json.values
        },
        series: series,
        toolbox: {
            show: true,
            feature: {
                dataZoom: {
                    yAxisIndex: 'none'
                },
                dataView: {
                    readOnly: false
                },
                restore: {},
                saveAsImage: {}
            }
        },
    });
}

window.addEventListener('DOMContentLoaded', function () {
    const hostname = window.location.hostname;
    if (window.location.protocol === 'https:') {
        url = `wss://${hostname}/websocket`;
    } else {
        url = `ws://${hostname}:8081/websocket`;
    }
    start();
});

window.onresize = function () {
    resizeCharts();
};

const start = function () {
    const socket = new WebSocket(url);
    socket.onopen = function () {
        clearSocketTimeout();
    };

    socket.onclose = function () {
        setSocketTimeout();
    };

    socket.onerror = function () {
        socket.close();
    };

    socket.onmessage = function (event) {
        try {
            if(event.data === 'heartbeat') {
                return;
            }
            const json = JSON.parse(event.data);
            updateChart(json);
        } catch (error) {
            console.log(error);
        }
    };
};

const clearSocketTimeout = function () {
    if (socketTimeout) {
        clearTimeout(socketTimeout);
    }
};

const setSocketTimeout = function () {
    console.log('Socket closed. Attempting reconnect in 5 seconds.');
    socketTimeout = setTimeout(function () {
        start();
    }, 5000);
};