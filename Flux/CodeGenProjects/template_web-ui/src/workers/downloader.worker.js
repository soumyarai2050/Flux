import { getTableRowsFromData } from '../utils';
import { DATA_TYPES, MODEL_TYPES } from '../constants';

onmessage = (e) => {
  const { fieldsMetadata, data, xpath = null, modelType = null } = e.data;

  // Generate the entire rows dataset (CPU intensive)
  let rows;
  if (modelType === MODEL_TYPES.ABBREVIATION_MERGE) {
    rows = data;
  } else {
    rows = getTableRowsFromData(fieldsMetadata, data, xpath);
  }
  const totalRows = rows.length;

  rows.forEach((row) => {
    delete row['data-id'];
  })

  // Create header row if rows exist.
  let header = "";
  if (totalRows > 0) {
    header = Object.keys(rows[0]).join(",") + "\n";
  }

  const chunkSize = 5000;
  let csvChunk = header;

  for (let i = 0; i < totalRows; i++) {
    const row = rows[i];
    // Process each field in the row.
    const keys = Object.keys(row);
    const values = keys.map((key) => {
      let value = row[key];
      if (value !== null && typeof value === DATA_TYPES.OBJECT) {
        value = JSON.stringify(value);
      }
      if (value == null) value = "";
      // Escape double quotes.
      value = value.toString().replace(/"/g, '""');
      return `"${value}"`;
    });
    csvChunk += values.join(",") + "\n";

    // When the chunk reaches the specified size, post it and reset the buffer.
    if ((i + 1) % chunkSize === 0) {
      postMessage({ csvChunk, currentRow: i + 1, totalRows, done: false });
      csvChunk = "";
    }
  }

  // Send any remaining CSV content and mark as done.
  postMessage({ csvChunk, currentRow: totalRows, totalRows, done: true });
};

export { };