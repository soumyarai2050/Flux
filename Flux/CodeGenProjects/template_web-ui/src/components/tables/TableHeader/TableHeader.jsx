import React, { useCallback, useEffect, useMemo, useState } from 'react';
import PropTypes from 'prop-types';
import { SortableContext, useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { TableHead, TableRow, TableCell } from '@mui/material';
import { useTheme } from '@emotion/react';
import { useDraggableContext } from '../../../contexts/DraggableContext';
import { getFilterDict } from '../../../utils/core/dataFiltering';
import { getSortOrderDict } from '../../../utils/core/dataSorting';
import FilterSortPopup from '../../FilterSortPopup';
import styles from './TableHeader.module.css';


const SortableHeaderCell = ({
    isDraggable = false,
    column,
    columnId,
    theme,
    stickyPosition,
    columnRefs,
    uniqueValues,
    selectedFilters,
    textFilter,
    textFilterType,
    sortDirection,
    absoluteSort,
    sortLevel,
    onApply,
    onCopy,
    clipboardText
}) => {
    const { attributes, listeners, setNodeRef, transform, transition } = useSortable({
        id: columnId,
    });

    const style = {
        transform: isDraggable ? CSS.Transform.toString(transform) : undefined,
        transition: isDraggable ? transition : undefined,
        cursor: isDraggable ? 'grab' : 'default',
    };

    const handleDragStart = (e) => {
        e.stopPropagation();
    };

    const mergeRefs = (...refs) => {
        return (el) => {
            refs.forEach((ref) => {
                if (!ref) return;
                if (typeof ref === 'function') {
                    ref(el);
                } else {
                    ref.current = el;
                }
            });
        };
    };

    let tableHeadColor = 'white';
    if (column.nameColor) {
        const color = column.nameColor.toLowerCase();
        tableHeadColor = theme.palette.text[color];
    }

    let columnName = column.title ?? column.key;
    if (column.displayName) {
        columnName = column.displayName;
    } else if (column.elaborateTitle) {
        columnName = column.tableTitle;
    }

    return (
        <TableCell
            className={styles.cell}
            sx={{
                color: tableHeadColor,
                position: column.frozenColumn ? 'sticky' : 'static',
                zIndex: column.frozenColumn ? 2 : 1,
                left: stickyPosition,
                background: column.frozenColumn ? theme.palette.background.nodeHeader : 'inherit'
            }}
            align='center'
            padding='normal'
            ref={mergeRefs(setNodeRef, (el) => columnRefs.current[columnId] = el)}
            style={style}
            {...(isDraggable ? attributes : {})}
            {...(isDraggable ? listeners : {})}
            onMouseDown={handleDragStart}
        >
            <span>
                {absoluteSort && '| '}
                {columnName}
                {absoluteSort && ' |'}
            </span>
            <FilterSortPopup
                columnId={columnId}
                columnName={columnName}
                valueCounts={uniqueValues ?? new Map()}
                uniqueValues={Array.from(uniqueValues?.keys() || [])}
                selectedFilters={selectedFilters}
                textFilter={textFilter}
                textFilterType={textFilterType}
                sortDirection={sortDirection}
                absoluteSort={absoluteSort}
                sortLevel={sortLevel}
                onApply={onApply}
                onCopy={onCopy}
                filterEnable={column.filterEnable ?? false}
                clipboardText={clipboardText}
            />
        </TableCell>
    );
};

const TableHeader = ({
    columns = [],
    uniqueValues = [],
    filters = [],
    sortOrders = [],
    onFiltersChange,
    onSortOrdersChange,
    collectionView = false,
    columnRefs,
    stickyHeader = true,
    getStickyPosition,
    groupedRows = []
}) => {
    const { isDraggable } = useDraggableContext();
    const theme = useTheme();

    // Lazy initializer for filterDict to avoid recomputation on every render.
    const [filterDict, setFilterDict] = useState(getFilterDict(filters));
    const [sortOrderDict, setSortOrderDict] = useState(getSortOrderDict(sortOrders));
    const [clipboardText, setClipboardText] = useState(null);

    const keyField = collectionView ? 'key' : 'tableTitle';

    // Update filterDict whenever the filters prop changes.
    useEffect(() => {
        const updatedFilterDict = getFilterDict(filters);
        setFilterDict(updatedFilterDict);
    }, [filters]);

    useEffect(() => {
        const updatedSortOrderDict = getSortOrderDict(sortOrders);
        setSortOrderDict(updatedSortOrderDict);
    }, [sortOrders]);

    const handleApply = useCallback((filterName, values, textFilter, textFilterType, sortDirection, isAbsoluteSort, multiSort = false) => {
        let updatedFilterDict = {};
        let updatedSortOrderDict = {};

        setFilterDict((prev) => {
            updatedFilterDict = {
                ...prev,
                [filterName]: {
                    ...prev[filterName],
                    column_name: filterName,
                    filtered_values: values,
                    text_filter: textFilter,
                    text_filter_type: textFilterType
                }
            };
            return updatedFilterDict;
        });

        setSortOrderDict((prev) => {
            updatedSortOrderDict = multiSort ? {
                ...prev,
                [filterName]: {
                    ...prev[filterName],
                    sort_direction: sortDirection,
                    is_absolute_sort: isAbsoluteSort
                }
            } : { [filterName]: {
                ...prev[filterName],
                sort_direction: sortDirection,
                is_absolute_sort: isAbsoluteSort
            } };
            if (!sortDirection) {
                delete updatedSortOrderDict[filterName];
            }

            const updatedFilters = Object.keys(updatedFilterDict).map((filterName) => ({
                ...updatedFilterDict[filterName],
                filtered_values: updatedFilterDict[filterName].filtered_values?.join(',') ?? null,
            }));
            const updatedSortOrders = Object.keys(updatedSortOrderDict).map((sortBy) => ({
                sort_by: sortBy,
                sort_direction: updatedSortOrderDict[sortBy].sort_direction,
                is_absolute_sort: updatedSortOrderDict[sortBy].is_absolute_sort
            }));
            onFiltersChange(updatedFilters);
            onSortOrdersChange(updatedSortOrders);

            return updatedSortOrderDict;
        });
    }, [onFiltersChange, onSortOrdersChange]);

    const handleCopy = (columnId, columnName) => {
        const column = columns.find((meta) => meta[keyField] === columnId);

        if (!column) {
            console.error(`handleCopy failed, no column found with columnId: ${columnId}`);
            return;
        }

        let sourceIndex = column.sourceIndex;
        if (sourceIndex == null) {
            sourceIndex = 0;
        }
        const values = [columnName];
        groupedRows.forEach((groupedRow) => {
            const row = groupedRow[sourceIndex];
            values.push(row[columnId]);
        });

        const text = values.join('\n');
        setClipboardText(text);
        setTimeout(() => {
            // to allow same column to be copied again even if there is no text change
            setClipboardText(null);
        }, 2000);
    };

    let tableHeadClasses = styles.head;
    if (stickyHeader) {
        tableHeadClasses += ` ${styles.sticky}`;
    }

    const sortableItems = useMemo(() => columns.map((column) => column[keyField]), [columns]);

    return (
        <TableHead className={tableHeadClasses}>
            <SortableContext items={sortableItems}>
                <TableRow>
                    {columns.map((column) => {
                        const columnKey = column[keyField];
                        const uniqueColumnKey = columnKey + column.sourceIndex;
                        const columnFilter = filterDict[columnKey];
                        const columnSort = sortOrderDict[columnKey];
                        const columnUniqueValues = uniqueValues[columnKey];
                        return (
                            <SortableHeaderCell
                                key={uniqueColumnKey}
                                column={column}
                                columnId={columnKey}
                                isDraggable={isDraggable}
                                theme={theme}
                                stickyPosition={getStickyPosition(columnKey)}
                                columnRefs={columnRefs}
                                uniqueValues={columnUniqueValues ?? []}
                                selectedFilters={columnFilter?.filtered_values ?? []}
                                textFilter={columnFilter?.text_filter ?? null}
                                textFilterType={columnFilter?.text_filter_type ?? 'contains'}
                                sortDirection={columnSort?.sort_direction ?? null}
                                absoluteSort={columnSort?.is_absolute_sort ?? null}
                                sortLevel={columnSort?.sort_level ?? null}
                                onApply={handleApply}
                                onCopy={handleCopy}
                                clipboardText={clipboardText}
                            />
                        );
                    })}
                </TableRow>
            </SortableContext>
        </TableHead>
    );
};

TableHeader.propTypes = {
    columns: PropTypes.array,
    uniqueValues: PropTypes.object,
    filters: PropTypes.array,
    sortOrders: PropTypes.array,
    onFiltersChange: PropTypes.func,
    onSortOrdersChange: PropTypes.func,
    collectionView: PropTypes.bool,
    stickyHeader: PropTypes.bool,
    getStickyPosition: PropTypes.func,
    groupedRows: PropTypes.array
};

export default TableHeader;