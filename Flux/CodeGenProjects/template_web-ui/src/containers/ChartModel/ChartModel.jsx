import React, { useState, useEffect, useMemo } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useWebSocketWorker, useModelLayout } from '../../hooks';
import { getWidgetTitle, toCamelCase } from '../../utils';
import { MODEL_TYPES } from '../../constants';
import { useTheme } from '@emotion/react';
import { generateChartOption, packageChartDataWithSchema, fetchChartSchema, transformChartTileData } from '../../utils/core/serviceUtils';
import { sliceMap } from '../../models/sliceMap';
import ChartGallery from './ChartGallery';
import { FullScreenModalOptional } from '../../components/ui/Modal';
import { ModelCard, ModelCardHeader, ModelCardContent } from '../../components/utility/cards';


function ChartModel({ modelName, modelDataSource }) {
    const dispatch = useDispatch();
    const { actions, selector, url } = modelDataSource;
    const { storedArray, error, isLoading } = useSelector(selector);
    const [reconnectCounter, setReconnectCounter] = useState(0);
    const [detailedView, setDetailedView] = useState(false);
    const [selectedChart, setSelectedChart] = useState(null);
    const [selectedChartData, setSelectedChartData] = useState([]);
    const [selectedChartFields, setSelectedChartFields] = useState([]);
    const [schemaLoading, setSchemaLoading] = useState(false);
    const [schemaError, setSchemaError] = useState(null);
    const [fetchedChartSchemaData, setFetchedChartSchemaData] = useState({});
    const theme = useTheme();

    const { actions: nodeActions, selector: nodeSelector } = useMemo(() => sliceMap[`${modelName}_node`]);
    const {
        selectedDataPoints,
        lastSelectedDataPoint,
    } = useSelector(state => state[toCamelCase(modelName) + 'Node'] || {});

    const { storedArray: storedNodeArray } = useSelector(nodeSelector);

    const selectedDataPointIds = useMemo(() =>
        selectedDataPoints?.map(point => point['_id']) || [],
        [selectedDataPoints]
    );

    const lastSelectedDataPointId = useMemo(() =>
        lastSelectedDataPoint?.['_id'] || null,
        [lastSelectedDataPoint]
    );

    useEffect(() => {
        if (detailedView && storedNodeArray && storedNodeArray.length > 0) {
            const realChartData = transformChartTileData(storedNodeArray);
            console.log("this time useEffect set the data", realChartData)
            setSelectedChartData(realChartData);
        } else if (detailedView && (!storedNodeArray || storedNodeArray.length === 0)) {
            setSelectedChartData([]);
        }
    }, [storedNodeArray, detailedView]);

    const {
        modelLayoutOption,
        isMaximized,
        handleFullScreenToggle,
    } = useModelLayout(modelName, null, MODEL_TYPES.CHART, () => { }, 'read');

    const handleChartDataUpdate = (updatedArray) => {
        dispatch(actions.setStoredArray(updatedArray));
    }

    const handleReconnect = () => {
        setReconnectCounter((prev) => prev + 1);
    }

    useEffect(() => {
        dispatch(actions.getAll());
    }, [dispatch]);

    useWebSocketWorker({
        url: url,
        modelName: modelName,
        reconnectCounter,
        selector,
        onWorkerUpdate: handleChartDataUpdate,
        onReconnect: handleReconnect,
    });

    const modelTitle = getWidgetTitle(modelLayoutOption, {}, modelName, {});
    let rawData = storedArray.flat();
    let chartData = rawData.map(item => item.chart_data || item);


    const handleErrorClear = () => {
        dispatch(actions.setError(null));
    };


    const handleChartDataFetch = async (chart) => {
        setSchemaLoading(true);
        setSchemaError(null);

        // Check if we have cached schema data for this chart
        if (fetchedChartSchemaData[chart.chart_name]) {
            const chartNodeData = fetchedChartSchemaData[chart.chart_name];
            setSelectedChartFields(chartNodeData.fieldsMetadata || []);

            if (nodeActions) {
                dispatch(nodeActions.setNode(chartNodeData));
            }

            setSchemaLoading(false);
            return;
        }

        // Fetch schema if not cached
        try {
            const chartItem = rawData.find(item => {
                const chartData = item.chart_data || item;
                return chartData.chart_name === chart.chart_name;
            });

            if (!chartItem) {
                throw new Error(`Configuration for chart "${chart.chart_name}" not found.`);
            }

            const sourceModelName = chartItem?.source_model_name;
            const sourceModelBaseUrl = chartItem?.source_model_base_url || '';

            // Fetch live schema from API
            const schemaData = await fetchChartSchema(sourceModelName, sourceModelBaseUrl);
            const chartNodeData = packageChartDataWithSchema(
                schemaData,
                sourceModelName,
                sourceModelBaseUrl
            );

            // Cache the schema data
            setFetchedChartSchemaData(prevData => ({
                ...prevData,
                [chart.chart_name]: chartNodeData
            }));

            setSelectedChartFields(chartNodeData.fieldsMetadata || []);

            if (nodeActions) {
                dispatch(nodeActions.setNode(chartNodeData));
            }

        } catch (error) {
            console.error('Error fetching chart schema:', error);
            setSchemaError(`Failed to load chart schema: ${error.message}`);

            setSelectedChartData([]);
            setSelectedChartFields([]);

            if (nodeActions) {
                dispatch(nodeActions.setNode(null));
                dispatch(nodeActions.setStoredArray([]));
            }
        } finally {
            setSchemaLoading(false);
        }
    };


    const handleChartView = async (chart) => {

        await handleChartDataFetch(chart);
        setSelectedChart(chart);
        setDetailedView(true);
    };


    const handleBackToList = () => {
        setDetailedView(false);
        setSelectedChart(null);
        setSelectedChartData([]);
        setSelectedChartFields([]);
        setSchemaError(null);
        setSchemaLoading(false);

        if (nodeActions) {
            dispatch(nodeActions.setNode(null));
            dispatch(nodeActions.setStoredArray([]));
            dispatch(nodeActions.setSelectedDataPoints());
            dispatch(nodeActions.setLastSelectedDataPoint());
        }
    };

    const handleDataPointMultiSelect = (event, dataId) => {
        const currentPoints = selectedDataPoints || [];
        const clickedPoint = selectedChartData.find(p => p['data-id'] === dataId);

        if (!clickedPoint) {
            return;
        }

        const isAlreadySelected = currentPoints.some(p => p['data-id'] === dataId);
        let newSelectedPoints = [];

        if (event?.ctrlKey) {
            if (isAlreadySelected) {
                newSelectedPoints = currentPoints.filter(p => p['data-id'] !== dataId);
            } else {
                newSelectedPoints = [...currentPoints, clickedPoint];
            }
        } else {
            if (isAlreadySelected && currentPoints.length === 1) {
                newSelectedPoints = [];
            } else {
                newSelectedPoints = [clickedPoint];
            }
        }

        let mostRecentPoint = null;
        if (newSelectedPoints.length > 0) {
            if (newSelectedPoints.some(p => p['data-id'] === dataId)) {
                mostRecentPoint = clickedPoint;
            } else {
                mostRecentPoint = newSelectedPoints[newSelectedPoints.length - 1];
            }
        }

        if (nodeActions) {
            dispatch(nodeActions.setSelectedDataPoints(newSelectedPoints));
            dispatch(nodeActions.setLastSelectedDataPoint(mostRecentPoint));
        }
    };


    const { chartOptions, datasets } = generateChartOption(selectedChart, selectedChartData, selectedChartFields);



    const finalOption = {
        legend: {},
        tooltip: {
            trigger: 'axis',
            axisPointer: {
                type: 'cross'
            }
        },
        dataZoom: [
            {
                type: 'inside',
                filterMode: 'filter'
            },
            {
                type: 'slider',
                filterMode: 'filter'
            }
        ],
        dataset: datasets,
        ...chartOptions
    };

    return (
        <FullScreenModalOptional
            id={modelName}
            open={isMaximized}
            onClose={handleFullScreenToggle}
        >
            <ModelCard id={modelName}>
                <ModelCardHeader
                    name={modelTitle}
                    isMaximized={isMaximized}
                    onMaximizeToggle={handleFullScreenToggle}
                />
                <ModelCardContent
                    isDisabled={isLoading}
                    error={error}
                    onClear={handleErrorClear}
                >
                    <ChartGallery
                        detailedView={detailedView}
                        selectedChart={selectedChart}
                        handleBackToList={handleBackToList}
                        chartData={chartData}
                        handleChartDataFetch={handleChartDataFetch}
                        handleChartView={handleChartView}
                        finalOption={finalOption}
                        theme={theme}
                        onDataPointMultiSelect={handleDataPointMultiSelect}
                        selectedDataPointIds={selectedDataPointIds}
                        lastSelectedDataPointId={lastSelectedDataPointId}
                        isLoading={isLoading}
                        schemaLoading={schemaLoading}
                        schemaError={schemaError}
                    />
                </ModelCardContent>
            </ModelCard>
        </FullScreenModalOptional>
    );
}

export default ChartModel;