import React from 'react';
import PivotTableUI from 'react-pivottable/PivotTableUI';
import { Dropdown } from 'react-pivottable/PivotTableUI';
import Sortable from 'react-sortablejs';
import { getSort } from 'react-pivottable/Utilities';
import DraggableAttributeWithSort from './DraggableAttributeWithSort';

/**
 * Custom wrapper around PivotTableUI that integrates sort callbacks
 * into the DraggableAttribute filter popup
 */
class PivotTableUIWithSort extends PivotTableUI {
  makeDnDCell(items, onChange, classes) {
    // Determine if this is a row or column cell based on CSS classes
    const isRowCell = classes.includes('pvtRows');
    const sortPrefix = isRowCell ? 'row_' : 'col_';

    return (
      <Sortable
        options={{
          group: 'shared',
          ghostClass: 'pvtPlaceholder',
          filter: '.pvtFilterBox',
          preventOnFilter: false,
        }}
        tag="td"
        className={classes}
        onChange={onChange}
      >
        {items.map(x => (
          <DraggableAttributeWithSort
            name={x}
            key={x}
            attrValues={this.state.attrValues[x]}
            valueFilter={this.props.valueFilter[x] || {}}
            sorter={getSort(this.props.sorters, x)}
            menuLimit={this.props.menuLimit}
            setValuesInFilter={this.setValuesInFilter.bind(this)}
            addValuesToFilter={this.addValuesToFilter.bind(this)}
            moveFilterBoxToTop={this.moveFilterBoxToTop.bind(this)}
            removeValuesFromFilter={this.removeValuesFromFilter.bind(this)}
            sortCallback={this.props.tableOptions?.sortCallback}
            sortPrefix={sortPrefix}
            zIndex={this.state.zIndices[x] || this.state.maxZIndex}
          />
        ))}
      </Sortable>
    );
  }
}

export default PivotTableUIWithSort;