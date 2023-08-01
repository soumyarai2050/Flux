import React, { useState, useEffect } from 'react';
import PivotTableUI from 'react-pivottable/PivotTableUI';
import TableRenderers from 'react-pivottable/TableRenderers';
import Plot from 'react-plotly.js';
import createPlotlyRenderer from 'react-pivottable/PlotlyRenderers';
import 'react-pivottable/pivottable.css';

const PlotlyRenderers = createPlotlyRenderer(Plot);

const pivotTableDefaultProps = {
    data: [],
    rows: [],
    cols: [],
    vals: [],
    aggregatorName: "Count",
    rendererName: "Table"
}

function PivotTable({ pivotData }) {
    const [pivotTableProps, setPivotTableProps] = useState({ ...pivotTableDefaultProps, data: pivotData });

    useEffect(() => {
        setPivotTableProps({...pivotTableProps, data: pivotData});
    }, [pivotData])

    const handlePivotTableChange = (updatedPivotTableProps) => {
        const { data, rows, cols, vals, aggregatorName, rendererName } = updatedPivotTableProps;
        setPivotTableProps({ data, rows, cols, vals, aggregatorName, rendererName });
    }

    return (
        <div>
            <PivotTableUI
                {...pivotTableProps}
                onChange={handlePivotTableChange}
                renderers={Object.assign({}, TableRenderers, PlotlyRenderers)}
                unusedOrientationCutoff={Infinity}
            />
        </div>
    )
}

export default PivotTable;