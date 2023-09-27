import React, { useEffect, useRef } from 'react';
import { init, getInstanceByDom } from 'echarts';

function EChart({ option, theme, loading, setSelectedData, isCollectionType }) {
    const chartRef = useRef(null);

    useEffect(() => {
        function onChartClick(data) {
            setSelectedData(data.data);
        }
        let chart;
        if (chartRef.current !== null) {
            chart = init(chartRef.current, theme);
            if (isCollectionType) {
                chart.on('click', onChartClick);
            }
        }

        function resizeChart() {
            chart?.resize();
        }
        window.addEventListener('resize', resizeChart);

        return () => {
            if (isCollectionType) {
                chart?.off('click', onChartClick);
            }
            chart?.dispose();
            window.removeEventListener('resize', resizeChart);
        }
    }, [theme])

    useEffect(() => {
        // Update chart
        if (chartRef.current !== null) {
            const chart = getInstanceByDom(chartRef.current);
            chart.setOption(option, { replaceMerge: ['series', 'xAxis', 'yAxis'] });
        }
    }, [option, theme]); // Whenever theme changes we need to add option and setting due to it being deleted in cleanup function

    useEffect(() => {
        // Update chart
        if (chartRef.current !== null) {
            const chart = getInstanceByDom(chartRef.current);
            loading === true ? chart.showLoading() : chart.hideLoading();
        }
    }, [loading, theme]);

    return <div ref={chartRef} style={{ width: "100%", height: "100%" }} />;

}

export default EChart;