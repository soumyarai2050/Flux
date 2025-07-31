import React, { useEffect, useRef } from 'react';
import { init, getInstanceByDom } from 'echarts';
import { useTheme } from '@emotion/react';
import { cssVar } from '../theme';

function EChart({ option, theme, loading, selectedData, selectedSeriesIdx, onSelectDataChange, activeDataId, isCollectionType }) {
    const chartRef = useRef(null);
    const onSelectDataChangeRef = useRef();
    onSelectDataChangeRef.current = onSelectDataChange;
    const themeStore = useTheme();

    useEffect(() => {
        function onChartClick(params) {
            onSelectDataChangeRef.current(params.event.event, params.data['data-id'], params.seriesIndex);
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

            // Deep copy option to avoid mutating original
            const modifiedOption = JSON.parse(JSON.stringify(option));

            const series = modifiedOption.series?.[selectedSeriesIdx];
            if (series) {
                series.itemStyle = series.itemStyle || {};
                series.itemStyle.color = (params) => {
                    const dataId = params.data['data-id'];
                    return dataId === activeDataId
                        ? themeStore.palette.primary.dark
                        : selectedData.includes(dataId)
                            ? themeStore.palette.primary.main
                            : '#5470C6';
                }
            }
            chart.setOption(modifiedOption, { replaceMerge: ['series', 'xAxis', 'yAxis'] });
        }
    }, [option, theme, selectedData, selectedSeriesIdx, activeDataId]); // Whenever theme changes we need to add option and setting due to it being deleted in cleanup function

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