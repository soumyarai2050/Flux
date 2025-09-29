import {
    Box,
    Typography,
    Paper,
    Grid,
    Card,
    CardContent,
    IconButton,
} from '@mui/material';
import { alpha } from '@mui/material/styles';
import {
    ArrowBack,
    ShowChart,
    BarChart,
    ScatterPlot,
} from '@mui/icons-material';
import EChart from '../../components/data-display/charts/EChart';
import styles from './ChartGallery.module.css';
import useClickIntent from '../../hooks/useClickIntent';

const chartTypeStyles = {
    line: {
        icon: <ShowChart fontSize="inherit" />,
        color: '#2196f3',
    },
    bar: {
        icon: <BarChart fontSize="inherit" />,
        color: '#4caf50',
    },
    scatter: {
        icon: <ScatterPlot fontSize="inherit" />,
        color: '#ff9800',
    },
};

const ChartGallery = ({
    detailedView,
    selectedChart,
    handleBackToList,
    chartData,
    handleChartDataFetch,
    handleChartView,
    finalOption,
    theme,
    onDataPointMultiSelect,
    selectedDataPointIds,
    lastSelectedDataPointId,
    isLoading,
    schemaLoading,
    schemaError
}) => {

    const chartClickHandler = useClickIntent(
        (chart) => handleChartDataFetch(chart),
        (chart) => handleChartView(chart)
    );

    return (
        <>
            {detailedView && selectedChart ? (
                <Box className={styles.detailedViewContainer}>
                    <Box className={styles.detailedViewHeader} sx={{ borderColor: 'divider' }}>
                        <IconButton onClick={handleBackToList} color="primary">
                            <ArrowBack />
                        </IconButton>
                        <Typography variant="h6" component="h2">
                            {selectedChart.chart_name}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                            ({selectedChart.series[0]?.type || 'Unknown'} chart)
                        </Typography>
                    </Box>
                    <Box className={styles.detailedViewChartArea}>
                        <EChart
                            loading={false}
                            theme={theme.palette.mode}
                            option={finalOption}
                            selectedSeriesIdx={0}
                            selectedData={selectedDataPointIds || []}
                            onSelectDataChange={onDataPointMultiSelect}
                            activeDataId={lastSelectedDataPointId}
                        />
                    </Box>
                </Box>
            ) : (
                <Box className={styles.galleryContainer}>
                    {chartData.length > 0 ? (
                        <Box className={styles.autoGridContainer}>
                            {chartData.map((chart) => {
                                const chartType = chart.series[0]?.type;
                                const styleInfo = chartTypeStyles[chartType];
                                const iconColor = styleInfo?.color || theme.palette.grey[500];
                                const glowColor = alpha(iconColor, 0.4);

                                return (
                                    <Card
                                        key={chart._id}
                                        className={styles.chartCard}
                                        style={{
                                            '--chart-color': iconColor,
                                            '--chart-color-glow': glowColor,
                                        }}
                                        onClick={() => chartClickHandler(chart)}
                                    >
                                        {styleInfo && (
                                            <Box className={styles.cardIcon}>
                                                {styleInfo.icon}
                                            </Box>
                                        )}
                                        <CardContent className={styles.cardContent}>
                                            <Typography variant="h6" component="h3" gutterBottom color="primary">
                                                {chart.chart_name}
                                            </Typography>
                                            <Typography variant="body2" color="text.secondary">
                                                Type: {chart.series[0]?.type || 'Unknown'}
                                            </Typography>
                                            <Typography variant="body2" color="text.secondary">
                                                Time Series: {chart.time_series ? 'Yes' : 'No'}
                                            </Typography>
                                            <Typography variant="caption" display="block" sx={{ mt: 1, fontStyle: 'italic' }}>
                                                Double-click to view chart
                                            </Typography>
                                        </CardContent>
                                    </Card>
                                );
                            })}
                        </Box>
                    ) : (
                        <Paper className={styles.noChartsPaper}>
                            <Typography variant="body1" color="text.secondary">
                                {isLoading ? 'Loading charts...' : 'No chart data available to display'}
                            </Typography>
                        </Paper>
                    )}
                </Box>
            )}
        </>
    );
};

export default ChartGallery;