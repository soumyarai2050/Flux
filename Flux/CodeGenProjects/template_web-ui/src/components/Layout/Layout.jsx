import React, { useEffect, useState, useCallback } from 'react';
import PropTypes from 'prop-types';
import { useSelector, useDispatch } from 'react-redux';
import { Responsive, WidthProvider } from 'react-grid-layout';
import { Grid, Popover } from '@mui/material';
import { Brightness4, Brightness7, DashboardCustomize, DoNotTouch, PanTool, SaveAs, ViewComfy } from '@mui/icons-material';
import { defaultLayouts } from '../../projectSpecificUtils';
import { actions as LayoutActions } from '../../features/uiLayoutSlice';
import * as Selectors from '../../selectors';
import { getModelComponent } from '../../utils/modelComponentLoader';
import { getIconText, snakeToTitle } from '../../utils';
import 'react-grid-layout/css/styles.css';
import 'react-resizable/css/styles.css';
import styles from './Layout.module.css'; // Import CSS module
import Icon, { ToggleIcon } from '../Icon';
import { LoadLayoutPopup, SaveLayoutPopup } from '../Popup';
import { COOKIE_NAME } from '../../config';
import { DB_ID } from '../../constants';
import { useURLParams } from '../../hooks';
import { cloneDeep } from 'lodash';

const defaultGridProps = {
  className: 'layout',
  breakpoints: { lg: 1200, md: 996, sm: 768, xs: 480, xxs: 0 },
  cols: { lg: 18, md: 10, sm: 6, xs: 4, xxs: 2 },
  margin: { lg: [8, 8], md: [5, 5] },
  rowHeight: 25,
  autoSize: true,
  responsive: true,
  compactType: 'vertical',
  resizeHandles: ['se']
};

const ResponsiveGridLayout = WidthProvider(Responsive);

/**
 * Layout component renders a responsive grid layout with draggable and resizable items.
 * It uses a navbar to display the project logo (with project name)
 * and a toggle button that opens a popover for selecting visible components.
 * The navbar hides when the page is scrolled away from the top.
 *
 * @component
 * @param {Object} props - Component properties.
 * @param {string} props.projectName - The name of the project to display as a logo.
 * @returns {JSX.Element} The Layout component.
 */
const Layout = ({ projectName, theme, onThemeToggle }) => {
  const { storedArray, storedObj, isLoading } = useSelector(Selectors.selectUILayout);
  const [layout, setLayout] = useState(null);
  const [visibleComponents, setVisibleComponents] = useState([]);
  const [isDraggable, setIsDraggable] = useState(false);
  const [anchorEl, setAnchorEl] = useState(null);
  const [isNavbarVisible, setIsNavbarVisible] = useState(true);
  const [isSaveLayoutPopupOpen, setIsSaveLayoutPopupOpen] = useState(false);
  const [isLoadLayoutPopupOpen, setIsLoadLayoutPopupOpen] = useState(false);
  const [searchValue, setSearchValue] = useState(''); // load layout by profile search input
  const [profileId, setProfileId] = useState(''); // save layout by profile input
  const dispatch = useDispatch();

  const urlParams = useURLParams();

  /**
   * Fetch the layout data on mount and update the loading state.
   */
  useEffect(() => {
    dispatch(LayoutActions.getAll());
  }, [dispatch]);

  /**
   * Update layout and visible components when layout data is loaded.
   */
  useEffect(() => {
    if (isLoading) return;

    // Retrieve the active layout ID from sessionStorage.
    const activeLayoutId = urlParams?.layout ?? sessionStorage.getItem(COOKIE_NAME);
    let newLayout;
    let newVisibleComponents;

    // Check if we have an active layout in the stored array.
    if (activeLayoutId) {
      const activeLayout = cloneDeep(storedArray?.find(o => o.profile_id === activeLayoutId));
      if (activeLayout) {
        const updatedDataElememts = activeLayout.widget_ui_data_elements.map((item) => {
          const { x, y, w, h, widget_ui_data, chart_data, filters, join_sort } = item;
          const defaultElement = defaultLayouts.find((o) => o.i === item.i);
          return { ...defaultElement, x, y, w, h, widget_ui_data, chart_data, filters, join_sort };
        })
        activeLayout.widget_ui_data_elements = updatedDataElememts;
        newLayout = updatedDataElememts;
        newVisibleComponents = newLayout.map(item => item.i);
        dispatch(LayoutActions.setStoredObj(activeLayout));
        setProfileId(activeLayout.profile_id);
      }
    }

    // If no active layout was found and storedObjDict is empty, fall back to defaults.
    if (!newLayout) {
      // Clean up sessionStorage if the active layout no longer exists.
      if (activeLayoutId) sessionStorage.removeItem(COOKIE_NAME);
      newLayout = defaultLayouts;
      newVisibleComponents = defaultLayouts.map(item => item.i);
    }

    // Update state if a new layout is determined.
    if (newLayout && newVisibleComponents) {
      setLayout(newLayout);
      setVisibleComponents(newVisibleComponents);
    }
  }, [isLoading]);

  /**
   * Computes the maximum y-coordinate among the current layout items.
   *
   * @returns {number} The maximum y-coordinate value.
   */
  const getMaxY = useCallback(() => {
    return (layout || []).reduce((max, item) => Math.max(max, item.y + item.h), 0);
  }, [layout]);

  /**
   * Toggles the visibility of a component in the layout.
   *
   * @param {string} component - The identifier of the component to toggle.
   */
  const toggleComponent = useCallback(
    (component) => {
      setVisibleComponents((prev) => {
        if (prev.includes(component)) {
          setLayout((prevLayout) => prevLayout.filter((item) => item.i !== component));
          return prev.filter((item) => item !== component);
        } else {
          const defaultPosition = defaultLayouts.find((item) => item.i === component);
          const currentPosition = layout?.find((item) => item.i === component);
          const newPosition = currentPosition
            ? currentPosition
            : { ...defaultPosition, x: 0, y: getMaxY() };
          setLayout((prevLayout) => [...(prevLayout || []), newPosition]);
          dispatch(LayoutActions.setStoredObj({ ...storedObj, widget_ui_data_elements: [...storedObj.widget_ui_data_elements, newPosition] }));
          return [...prev, component];
        }
      });
    },
    [layout, getMaxY, storedObj]
  );

  /**
   * Handles changes in the grid layout.
   *
   * @param {Array} newLayout - The updated layout array.
   */
  const handleLayoutChange = useCallback((newLayout) => {
    if (isDraggable) {
      setLayout(newLayout);
    }
  }, [isDraggable]);

  /**
   * Opens the popover for toggling components.
   *
   * @param {Object} event - The event object.
   */
  const handlePopoverOpen = (event) => {
    setAnchorEl(event.currentTarget);
  };

  /**
   * Closes the popover for toggling components.
   */
  const handlePopoverClose = () => {
    setAnchorEl(null);
  };

  /**
   * Listens to scroll events and hides the navbar when the page is scrolled away from the top.
   */
  useEffect(() => {
    const handleScroll = () => {
      // Hide the navbar if the scroll position is greater than zero.
      setIsNavbarVisible(window.scrollY === 0);
    };

    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  if (isLoading) return <div>Loading layout...</div>;
  if (!layout && !storedObj.widget_ui_data_elements) return null;

  const popoverId = Boolean(anchorEl) ? 'toggle-popover' : undefined;

  const DraggableIcon = isDraggable ? DoNotTouch : PanTool;
  const ThemeIcon = theme === 'light' ? Brightness7 : Brightness4;

  const handleDraggableToggle = () => {
    setIsDraggable((prev) => !prev);
  }

  const handleThemeToggle = () => {
    onThemeToggle();
  }

  const handleSaveLayoutPopupToggle = () => {
    setIsSaveLayoutPopupOpen((prev) => !prev);
  }

  const handleLoadLayoutPopupToggle = () => {
    setIsLoadLayoutPopupOpen((prev) => !prev);
  }

  const handleProfileIdChange = (e) => {
    setProfileId(e.target.value);
  }

  const handleSearchValueChange = (_, value) => {
    setSearchValue(value);
  }

  const handleSave = () => {
    // Ensure profileId exists (add additional checks if needed)
    if (!profileId) return;

    // Build a map for quick lookup of layout items by their key "i"
    const layoutMap = layout.reduce((acc, curr) => {
      acc[curr.i] = curr;
      return acc;
    }, {});

    // Retrieve an existing profile from storedArray, or use storedObj as a fallback.
    // let profileData = storedArray.find((item) => item.profile_id === profileId);
    // if (!profileData) {
    //   profileData = {
    //     profile_id: profileId,
    //     widget_ui_data_elements: storedObj?.widget_ui_data_elements || [],
    //   };
    // }

    // Deep clone to avoid accidental mutations of the original object.
    let newProfileData = cloneDeep(storedObj);
    newProfileData.profile_id = profileId;

    // Filter out widget elements that do not exist in the current layout,
    // then map each widget to include updated position/size properties.
    const updatedWidgets = newProfileData.widget_ui_data_elements
      .filter((widget) => layoutMap[widget.i])
      .map((widget) => {
        const { x, y, w, h } = layoutMap[widget.i];
        return { ...widget, x, y, w, h };
      });

    newProfileData.widget_ui_data_elements = updatedWidgets;

    // Dispatch appropriate action based on whether the profile exists in the database.
    if (newProfileData[DB_ID]) {
      dispatch(LayoutActions.update({ data: newProfileData }));
    } else {
      dispatch(LayoutActions.create({ data: newProfileData }));
    }

    // Persist the active profile ID in session storage.
    sessionStorage.setItem(COOKIE_NAME, profileId);

    // Toggle the layout save popup.
    handleSaveLayoutPopupToggle();
  };

  const handleLoad = () => {
    const loadedObj = storedArray.find((o) => o[DB_ID] === searchValue[DB_ID]);
    if (loadedObj) {
      dispatch(LayoutActions.setObjId(loadedObj[DB_ID]));
      dispatch(LayoutActions.setStoredObj(loadedObj));
      setLayout(loadedObj.widget_ui_data_elements);
      const newVisibleComponents = loadedObj.widget_ui_data_elements.map(item => item.i);
      setVisibleComponents(newVisibleComponents);
      setProfileId(loadedObj.profile_id);
      sessionStorage.setItem(COOKIE_NAME, loadedObj.profile_id);
    }
    setSearchValue(null);
    handleLoadLayoutPopupToggle();
  }

  const handleReset = () => {
    sessionStorage.removeItem(COOKIE_NAME);
    setLayout(defaultLayouts);
    dispatch(LayoutActions.setStoredObj({ profile_id: 'default', widget_ui_data_elements: defaultLayouts }));
    handleLoadLayoutPopupToggle();
  }

  return (
    <div>
      {/* Enhanced Navbar with hide-on-scroll functionality */}
      <nav className={`${styles.navbar} ${!isNavbarVisible ? styles.hidden : ''}`}>
        <div className={styles.navbarLogo}>{snakeToTitle(projectName)}</div>
        <Icon name='drag' title='drag' onClick={handleDraggableToggle}>
          <DraggableIcon fontSize='medium' />
        </Icon>
        <Icon name='theme' title='theme' onClick={handleThemeToggle}>
          <ThemeIcon fontSize='medium' />
        </Icon>
        <Icon name='load' title='load' onClick={handleLoadLayoutPopupToggle}>
          <ViewComfy fontSize='medium' />
        </Icon>
        <Icon name='save' title='save' onClick={handleSaveLayoutPopupToggle}>
          <SaveAs fontSize='medium' />
        </Icon>
        <Icon name='customize' title='customize' onClick={handlePopoverOpen}>
          <DashboardCustomize fontSize="medium" />
        </Icon>
        <Popover
          id={popoverId}
          open={Boolean(anchorEl)}
          anchorEl={anchorEl}
          onClose={handlePopoverClose}
          anchorOrigin={{
            vertical: 'bottom',
            horizontal: 'left'
          }}
          transformOrigin={{
            vertical: 'top',
            horizontal: 'left'
          }}
        >
          <Grid container spacing={1} sx={{ padding: '5px', width: '300px' }}>
            {defaultLayouts.map((item) => (
              <Grid item key={item.i} lg={2}>
                <ToggleIcon
                  title={item.i}
                  name={item.i}
                  selected={visibleComponents.includes(item.i)}
                  onClick={() => toggleComponent(item.i)}
                >
                  {getIconText(item.i)}
                </ToggleIcon>
              </Grid>
            ))}
          </Grid>
        </Popover>
      </nav>
      <div className={styles.mainContainer}>
        <ResponsiveGridLayout
          {...defaultGridProps}
          isDraggable={isDraggable}
          isResizable={isDraggable}
          layouts={{ lg: layout ?? [] }}
          onLayoutChange={handleLayoutChange}
        >
          {visibleComponents.map((key) => (
            <div
              key={key}
              className={styles.gridItem}
              aria-label={`${key}_model`}
            // data-grid={layout.find((item) => key === item.i)}
            >
              {getModelComponent(key)}
            </div>
          ))}
        </ResponsiveGridLayout>
      </div>
      <SaveLayoutPopup
        open={isSaveLayoutPopupOpen}
        onClose={handleSaveLayoutPopupToggle}
        storedArray={storedArray}
        profileId={profileId}
        onProfileIdChange={handleProfileIdChange}
        onSave={handleSave}
      />
      <LoadLayoutPopup
        open={isLoadLayoutPopupOpen}
        onClose={handleLoadLayoutPopupToggle}
        storedArray={storedArray}
        onReset={handleReset}
        value={searchValue}
        onSearchValueChange={handleSearchValueChange}
        onLoad={handleLoad}
      />
    </div>
  );
};

Layout.propTypes = {
  /**
   * The project name to display in the navbar logo.
   */
  projectName: PropTypes.string.isRequired
};

export default React.memo(Layout);
