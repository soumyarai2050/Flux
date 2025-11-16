import { useState, useEffect, useRef } from 'react';
import { HIGHLIGHT_STATES } from '../../../../constants';
import styles from './PivotTable.module.css';

/**
 * PivotTableCell - Renders a table cell in pivot table with value change highlighting
 * Mimics the highlight behavior of Cell.jsx (DataTable cells)
 *
 * Props:
 *   - value: Current cell value
 *   - children: Cell content to render
 *   - fieldName: Name of the field for lookup in fieldsMetadata
 *   - fieldsMetadata: Array of field metadata objects with highlightUpdate property
 *   - highlightDuration: Duration in seconds for the highlight (default: 1)
 *   - ...props: Other props passed to <td> element
 */
export const PivotTableCell = ({
  value,
  children,
  fieldName,
  fieldsMetadata,
  highlightDuration = 1,
  ...props
}) => {
  // State to track the previous value and old value for comparison
  const [oldValue, setOldValue] = useState(null);
  const [newUpdateClass, setNewUpdateClass] = useState('');
  const timeoutRef = useRef(null);

  // Get the collection metadata for this field
  const collection = fieldsMetadata?.find(f => f.key === fieldName);

  useEffect(() => {
    // Only apply highlighting if:
    // 1. Collection has highlightUpdate property set
    // 2. highlightUpdate is not NONE
    // 3. Value has changed from old value
    if (
      collection?.highlightUpdate &&
      collection.highlightUpdate !== HIGHLIGHT_STATES.NONE &&
      value !== oldValue
    ) {
      // Apply highlight based on the type of highlight update
      if (collection.highlightUpdate === HIGHLIGHT_STATES.HIGH_LOW) {
        // For HIGH_LOW: show increase vs decrease
        if (value > oldValue) {
          setNewUpdateClass(styles.new_update_increase);
        } else if (value < oldValue) {
          setNewUpdateClass(styles.new_update_decrease);
        }
      } else if (collection.highlightUpdate === HIGHLIGHT_STATES.CHANGE) {
        // For CHANGE: just show that it changed
        setNewUpdateClass(styles.new_update);
      }

      // Clear any existing timeout
      if (timeoutRef.current !== null) {
        clearTimeout(timeoutRef.current);
      }

      // Set timeout to remove highlight after duration
      timeoutRef.current = setTimeout(() => {
        setNewUpdateClass("");
      }, highlightDuration * 1000);

      // Update oldValue for next comparison
      setOldValue(value);
    }
  }, [value, oldValue, collection, highlightDuration]);

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (timeoutRef.current !== null) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  // Combine original className with highlight class
  const className = `${props.className || ''} ${newUpdateClass}`;

  // Render the table cell
  return (
    <td {...props} className={className}>
      {children}
    </td>
  );
};