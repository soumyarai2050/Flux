/**
 * plotlyClickMapper.js
 *
 * Utility for mapping Plotly click events to pivot table cell selections.
 * Provides a pure, testable function for event translation and a binding helper.
 */

// Symbol key to track if a handler is already bound
const PLOTLY_CLICK_BOUND = Symbol('plotlyClickBound');

/**
 * Maps a Plotly click event to pivot-compatible label/title pairs.
 *
 * @param {Object} ev - Plotly click event object
 * @returns {{label: string, title: string}} - Mapped label and title for pivot filtering
 *
 * Supports:
 * - Dot charts: trace has no type and mode === 'markers'; use trace.name as title, empty label
 * - Regular scatter: use trace.name as label, point.x as title
 * - Pie charts: use slice label from event if available; otherwise derive from event payload
 */
export function mapPlotlyClickToPivot(ev) {
  // Defensive null checks
  if (!ev || !ev.points || ev.points.length === 0) {
    console.warn('No points in event:', ev);
    return { label: '', title: '' };
  }

  const point = ev.points[0];


  // Use fullData for complete trace info, fallback to data for basic info
  const trace = point.fullData || point.data;

  if (!trace) {
    console.warn('No trace data in point:', point);
    return { label: '', title: '' };
  }
  const pointNumber = point.pointNumber;
  let result = { label: '', title: '' };


  // PIE CHART: check if trace.type is 'pie'
  if (trace.type === 'pie') {
    // Pie slices have label in point.label and trace title in trace.title.text

    const label = point.label ?? '';
    const title = trace.title?.text ?? '';
    return { label, title };
  }

  // BAR & COLUMN CHARTS (FINAL, SIMPLE LOGIC)
  if (trace.type === 'bar') {
    const isHorizontal = trace.orientation === 'h';

    const axisValue = isHorizontal
      ? (point.y ?? trace.y?.[pointNumber])
      : (point.x ?? trace.x?.[pointNumber]);

    const legendValue = trace.name ?? '';

    // SPECIAL RULE for VERTICAL/COLUMN charts
    if (!isHorizontal) {
      // In Vertical Column charts, the library flips the logic.
      // Legend contains the ROW dimensions.
      // X-Axis contains the COLUMN dimensions.
      result = {
        label: legendValue,  // label (rows) comes from Legend
        title: axisValue != null ? String(axisValue).trim() : '' // title (cols) comes from X-Axis
      };
    }
    //  RULE for HORIZONTAL/BAR charts
    else {
      // In Horizontal Bar charts, the logic is normal.
      // Y-Axis contains the ROW dimensions.
      // Legend contains the COLUMN dimensions.
      result = {
        label: axisValue != null ? String(axisValue).trim() : '',
        title: legendValue
      };
    }

    // Final cleanup for simple charts where legend is just "Count"
    if (result.title.toLowerCase() === 'count' && result.label) {
      // This is a simple horizontal bar chart like `Count vs Company`
      // In this case, `label` has the company and `title` is just 'Count' so it should be empty.
      result.title = '';
    }

    return result;
  }

  // SCATTER-FAMILY CHARTS
  if (trace.type === 'scatter') {
    // SUB-CASE 3A: LINE CHART (It has 'lines' in mode)
    if (trace.mode?.includes('lines')) {
      const rowValue = trace.name ?? '';
      const colValue = point.x ?? trace.x?.[pointNumber];
      result = {
        label: rowValue,
        title: colValue != null ? String(colValue).trim() : ''
      };
    }
    // DOT or SCATTER CHART (mode is just 'markers')
    else if (trace.mode === 'markers') {
      const junkNames = ['count', 'trace 0']; // Given by chart library ,count as "no legend"

      //  DOT chart with legend
      if (!junkNames.includes(trace.name.toLowerCase())) {
        const rowValue = point.y ?? trace.y?.[pointNumber];
        const colValue = trace.name ?? ''; // Title comes from Legend
        result = {
          label: rowValue != null ? String(rowValue).trim() : '',
          title: colValue
        };
      }
      // if legend IS junk, it's a SCATTER chart or Dot without Legend
      else {
        const rowValue = point.y ?? trace.y?.[pointNumber];
        const colValue = point.x ?? trace.x?.[pointNumber]; // Title comes from X-axis
        result = {
          label: rowValue != null ? String(rowValue).trim() : '',
          title: colValue != null ? String(colValue).trim() : ''
        };
      }
    }
    return result;
  }

  // Fallback for unknown chart types
  console.warn('Unknown chart type - trace.type:', trace.type, 'trace.mode:', trace.mode);
  return { label: '', title: '' };
}

/**
 * Binds a single plotly_click listener to the given div element.
 *
 * @param {HTMLElement} div - The Plotly plot div (with .on method)
 * @param {Function} onMapped - Callback that receives {label, title}
 * @returns {Function} - Unbind function to remove the listener
 *
 * Uses a symbol key on the div to avoid duplicate bindings.
 * Returns an unbind function that removes the handler to prevent leaks.
 */
export function bindPlotlyClick(div, onMapped) {
  if (!div) {
    return () => { }; // No-op unbind if no div
  }

  // Check if already bound - if so, unbind first to avoid duplicates
  if (div[PLOTLY_CLICK_BOUND]) {
    div[PLOTLY_CLICK_BOUND](); // Unbind previous handler
  }

  // Define the click handler
  const clickHandler = (ev) => {
    const mapped = mapPlotlyClickToPivot(ev);
    onMapped(mapped);
  };

  const hoverHandler = () => {
    const dragLayer = div.querySelector('.draglayer');
    if (dragLayer) {
      dragLayer.style.cursor = 'pointer';
    }
  };

  const unhoverHandler = () => {
    const dragLayer = div.querySelector('.draglayer');
    if (dragLayer) {
      dragLayer.style.cursor = '';
    }
  };

  // Bind using Plotly's event emitter API
  if (div.on && typeof div.on === 'function') {
    div.on('plotly_click', clickHandler);
    div.on('plotly_hover', hoverHandler);
    div.on('plotly_unhover', unhoverHandler);
  } else {
    console.warn('bindPlotlyClick: div does not have .on method', div);
    return () => { }; // No-op unbind
  }

  // Create unbind function
  const unbind = () => {
    if (div.removeListener && typeof div.removeListener === 'function') {
      div.removeListener('plotly_click', clickHandler);
      div.removeListener('plotly_hover', hoverHandler);
      div.removeListener('plotly_unhover', unhoverHandler);
    } else if (div.removeAllListeners && typeof div.removeAllListeners === 'function') {
      // Fallback: remove all listeners for these events
      div.removeAllListeners('plotly_click');
      div.removeAllListeners('plotly_hover');
      div.removeAllListeners('plotly_unhover');
    }
    delete div[PLOTLY_CLICK_BOUND];
  };

  // Store unbind function on the div
  div[PLOTLY_CLICK_BOUND] = unbind;

  return unbind;
}