import React, { useEffect, useRef } from 'react';
import { init, getInstanceByDom } from 'echarts';

function EChart({ option, theme, loading }) {
    const chartRef = useRef(null);

    useEffect(() => {
        let chart;
        if (chartRef.current !== null) {
            chart = init(chartRef.current, theme);
        }

        function resizeChart() {
            chart?.resize();
        }
        window.addEventListener('resize', resizeChart);

        return () => {
            chart?.dispose();
            window.removeEventListener('resize', resizeChart);
        }
    }, [theme])

    useEffect(() => {
        // Update chart
        if (chartRef.current !== null) {
            const chart = getInstanceByDom(chartRef.current);
            chart.setOption(option);
        }
    }, [option, theme]); // Whenever theme changes we need to add option and setting due to it being deleted in cleanup function

    useEffect(() => {
        // Update chart
        if (chartRef.current !== null) {
            const chart = getInstanceByDom(chartRef.current);
            // eslint-disable-next-line @typescript-eslint/no-unused-expressions
            loading === true ? chart.showLoading() : chart.hideLoading();
        }
    }, [loading, theme]);

    return <div ref={chartRef} style={{ width: "100%", height: "100%" }} />;

}

export default EChart;