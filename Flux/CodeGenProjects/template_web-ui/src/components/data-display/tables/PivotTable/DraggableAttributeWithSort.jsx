import React from 'react';
import PropTypes from 'prop-types';
import Draggable from 'react-draggable';
import styles from './DraggableAttributeWithSort.module.css';

export class DraggableAttributeWithSort extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      open: false,
      filterText: '',
      baseSort: null,      // 'asc' or 'desc' - base direction
      useAbsolute: false   // whether to apply absolute value modifier
    };
  }

  toggleValue(value) {
    if (value in this.props.valueFilter) {
      this.props.removeValuesFromFilter(this.props.name, [value]);
    } else {
      this.props.addValuesToFilter(this.props.name, [value]);
    }
  }

  matchesFilter(x) {
    return x
      .toLowerCase()
      .trim()
      .includes(this.state.filterText.toLowerCase().trim());
  }

  selectOnly(e, value) {
    e.stopPropagation();
    this.props.setValuesInFilter(
      this.props.name,
      Object.keys(this.props.attrValues).filter(y => y !== value)
    );
  }

  handleSortClick(sortType) {
    const { baseSort, useAbsolute } = this.state;
    const sortPrefix = this.props.sortPrefix || ''; // Get prefix (row_ or col_)

    if (sortType === 'abs') {
      // Abs button: toggle absolute value modifier (only works if baseSort is set)
      if (!baseSort) {
        // Can't use Abs without selecting Asc or Desc first
        return;
      }
      const newUseAbsolute = !useAbsolute;
      this.setState({ useAbsolute: newUseAbsolute });

      // Calculate final sort type based on baseSort + useAbsolute
      const finalSortType = newUseAbsolute ? `${baseSort}_abs` : baseSort;
      if (this.props.sortCallback) {
        // Pass attribute name with prefix so row and column sorts are independent
        this.props.sortCallback(`${sortPrefix}${this.props.name}`, finalSortType, true);
      }
    } else {
      // Asc or Desc: select base sort
      const newBaseSort = baseSort === sortType ? null : sortType;
      const newUseAbsolute = newBaseSort ? useAbsolute : false; // Reset abs if clearing base sort

      this.setState({ baseSort: newBaseSort, useAbsolute: newUseAbsolute });

      if (this.props.sortCallback) {
        if (!newBaseSort) {
          // Clear all sorts
          this.props.sortCallback(`${sortPrefix}${this.props.name}`, null, true);
        } else {
          // Apply base sort + absolute modifier if active
          const finalSortType = newUseAbsolute ? `${newBaseSort}_abs` : newBaseSort;
          this.props.sortCallback(`${sortPrefix}${this.props.name}`, finalSortType, true);
        }
      }
    }
  }

  getFilterBox() {
    const showMenu =
      Object.keys(this.props.attrValues).length < this.props.menuLimit;

    const values = Object.keys(this.props.attrValues);
    const shown = values
      .filter(this.matchesFilter.bind(this))
      .sort(this.props.sorter);

    return (
      <Draggable handle=".pvtDragHandle">
        <div
          className="pvtFilterBox"
          style={{
            display: 'block',
            cursor: 'initial',
            zIndex: this.props.zIndex,
          }}
          onClick={() => this.props.moveFilterBoxToTop(this.props.name)}
        >
          <a onClick={() => this.setState({ open: false })} className="pvtCloseX">
            ×
          </a>
          <span className="pvtDragHandle">☰</span>
          <h4>{this.props.name}</h4>

          {/* Sort buttons section - only render if sortCallback exists */}
          {this.props.sortCallback && (
            <div className={styles.pvtSortButtonContainer}>
              <button
                className={`${styles.pvtSortButton} ${
                  this.state.baseSort === 'asc' ? styles.selected : ''
                }`}
                onClick={() => this.handleSortClick('asc')}
                title="Sort A-Z"
              >
                ↓ Asc
              </button>
              <button
                className={`${styles.pvtSortButton} ${
                  this.state.baseSort === 'desc' ? styles.selected : ''
                }`}
                onClick={() => this.handleSortClick('desc')}
                title="Sort Z-A"
              >
                ↑ Desc
              </button>
              <button
                className={`${styles.pvtSortButton} ${
                  this.state.useAbsolute ? styles.selected : ''
                } ${!this.state.baseSort ? styles.disabled : ''}`}
                onClick={() => this.handleSortClick('abs')}
                disabled={!this.state.baseSort}
                title={this.state.baseSort ? 'Apply Absolute Value Modifier' : 'Select Asc or Desc first'}
              >
                ± Abs
              </button>
            </div>
          )}

          {showMenu || <p>(too many values to show)</p>}

          {showMenu && (
            <p>
              <input
                type="text"
                placeholder="Filter values"
                className="pvtSearch"
                value={this.state.filterText}
                onChange={e =>
                  this.setState({
                    filterText: e.target.value,
                  })
                }
              />
              <br />
              <a
                role="button"
                className="pvtButton"
                onClick={() =>
                  this.props.removeValuesFromFilter(
                    this.props.name,
                    Object.keys(this.props.attrValues).filter(
                      this.matchesFilter.bind(this)
                    )
                  )
                }
              >
                Select {values.length === shown.length ? 'All' : shown.length}
              </a>{' '}
              <a
                role="button"
                className="pvtButton"
                onClick={() =>
                  this.props.addValuesToFilter(
                    this.props.name,
                    Object.keys(this.props.attrValues).filter(
                      this.matchesFilter.bind(this)
                    )
                  )
                }
              >
                Deselect {values.length === shown.length ? 'All' : shown.length}
              </a>
            </p>
          )}

          {showMenu && (
            <div className="pvtCheckContainer">
              {shown.map(x => (
                <p
                  key={x}
                  onClick={() => this.toggleValue(x)}
                  className={x in this.props.valueFilter ? '' : 'selected'}
                >
                  <a className="pvtOnly" onClick={e => this.selectOnly(e, x)}>
                    only
                  </a>
                  <a className="pvtOnlySpacer">&nbsp;</a>

                  {x === '' ? <em>null</em> : x}
                </p>
              ))}
            </div>
          )}
        </div>
      </Draggable>
    );
  }

  toggleFilterBox() {
    this.setState({ open: !this.state.open });
    this.props.moveFilterBoxToTop(this.props.name);
  }

  render() {
    const filtered =
      Object.keys(this.props.valueFilter).length !== 0
        ? 'pvtFilteredAttribute'
        : '';
    return (
      <li data-id={this.props.name}>
        <span className={'pvtAttr ' + filtered}>
          {this.props.name}
          <span
            className="pvtTriangle"
            onClick={this.toggleFilterBox.bind(this)}
          >
            {' '}
            ▾
          </span>
        </span>

        {this.state.open ? this.getFilterBox() : null}
      </li>
    );
  }
}

DraggableAttributeWithSort.defaultProps = {
  valueFilter: {},
};

DraggableAttributeWithSort.propTypes = {
  name: PropTypes.string.isRequired,
  addValuesToFilter: PropTypes.func.isRequired,
  removeValuesFromFilter: PropTypes.func.isRequired,
  attrValues: PropTypes.objectOf(PropTypes.number).isRequired,
  valueFilter: PropTypes.objectOf(PropTypes.bool),
  moveFilterBoxToTop: PropTypes.func.isRequired,
  sorter: PropTypes.func.isRequired,
  menuLimit: PropTypes.number,
  zIndex: PropTypes.number,
  sortCallback: PropTypes.func,
};

export default DraggableAttributeWithSort;