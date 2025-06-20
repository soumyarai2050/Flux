import React, { useEffect, useState, useCallback } from 'react';
import PropTypes from 'prop-types';
import { useSelector, useDispatch } from 'react-redux';
import { Responsive, WidthProvider } from 'react-grid-layout';
import { Grid, Popover, MenuItem } from '@mui/material';
import { Brightness4, Brightness7, DashboardCustomize, DoNotTouch, PanTool, SaveAs, ViewComfy, Palette, SpaceDashboard } from '@mui/icons-material';
import { defaultLayouts } from '../../projectSpecificUtils';
import { actions as LayoutActions } from '../../features/uiLayoutSlice';
import * as Selectors from '../../selectors';
import { getModelComponent } from '../../utils/modelComponentLoader';
import { fastClone, getIconText, snakeToTitle } from '../../utils';
import 'react-grid-layout/css/styles.css';
import 'react-resizable/css/styles.css';
import styles from './Layout.module.css';
import Icon, { ToggleIcon } from '../Icon';
import { SaveLayoutPopup } from '../Popup';
import { API_ROOT_URL, API_ROOT_VIEW_URL, COOKIE_NAME } from '../../config';
import { DB_ID } from '../../constants';
import { useURLParams, useWebSocketWorker } from '../../hooks';
import { BaseColor, cssVar, baseColorPalettes, Theme, DEFAULT_BASE_COLOR } from '../../theme';
import GlobalScrollbarStyle from '../GlobalScrollbarStyle';
import DropdownButton from '../DropdownButton';

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
 * Enhanced Layout component with per-profile base color support.
 * 
 * Base Color Behavior:
 * - Each saved layout profile stores its own base color preference (base_color)
 * - When saving a layout, the current selected base color is saved with the profile
 * - When loading a profile, if it has a base_color, that color is applied; otherwise DEFAULT_BASE_COLOR is used
 * - On app startup, the layout loading process will apply the appropriate base color from the loaded profile
 * - Switching between profiles will automatically apply each profile's saved base color
 * - The Default profile always uses DEFAULT_BASE_COLOR
 * - Admin control allows changing base color, which gets saved when the layout is saved
 * 
 * Usage Flow:
 * 1. Load profile → applies saved base color (or default if none saved)
 * 2. Change base color via admin control → updates current color
 * 3. Save layout → saves current base color with profile
 * 4. Switch profiles → each profile loads with its own saved color
 */

/**
 * Layout component renders a responsive grid layout with draggable and resizable items.
 * It uses a navbar to display the project logo (with project name)
 * and a toggle button that opens a popover for selecting visible components.
 * The navbar hides when the page is scrolled away from the top.
 *
 * @component
 * @param {Object} props - Component properties.
 * @param {string} props.projectName - The name of the project to display as a logo.
 * @param {string} props.theme - The current theme mode ('light' or 'dark').
 * @param {Function} props.onThemeToggle - Callback to toggle the theme mode.
 * @param {string} props.baseColor - The current base color name.
 * @param {Function} props.onBaseColorChange - Callback to change the base color.
 * @returns {JSX.Element} The Layout component.
 */
const Layout = ({ projectName, theme, onThemeToggle, baseColor, onBaseColorChange }) => {
  const { storedArray, storedObj, isLoading } = useSelector(Selectors.selectUILayout);
  const [layout, setLayout] = useState(null);
  const [visibleComponents, setVisibleComponents] = useState([]);
  const [isDraggable, setIsDraggable] = useState(false);
  const [anchorEl, setAnchorEl] = useState(null);
  const [isNavbarVisible, setIsNavbarVisible] = useState(true);
  const [isSaveLayoutPopupOpen, setIsSaveLayoutPopupOpen] = useState(false);
  const [reconnectCounter, setReconnectCounter] = useState(0);
  const [profileId, setProfileId] = useState(''); // save layout by profile input
  const dispatch = useDispatch();

  // internal state for selected base color, synced with prop
  const [selectedBaseColor, setSelectedBaseColor] = useState(baseColor || DEFAULT_BASE_COLOR);

  const urlParams = useURLParams();

  // Check if admin_control parameter exists in URL
  const showAdminControl = urlParams && urlParams.admin_control === 'true';

  // Calculate dropdown selected index
  const profileOptions = ['reset', ...(storedArray || []).map(profile => profile.profile_id)];
  const currentProfileValue = profileId || 'reset';
  const dropdownSelectedIndex = profileOptions.indexOf(currentProfileValue);

  const handleWorkerUpdate = (updatedArray) => {
    dispatch(LayoutActions.setStoredArray(updatedArray));
  }

  const handleReconnect = () => {
    setReconnectCounter((prev) => prev + 1);
  }

  useWebSocketWorker({
    url: API_ROOT_VIEW_URL,
    modelName: 'ui_layout',
    isDisabled: false,
    reconnectCounter,
    isAbbreviationSource: false,
    selector: Selectors.selectUILayout,
    onWorkerUpdate: handleWorkerUpdate,
    onReconnect: handleReconnect
  })

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
    if (!activeLayoutId) {
      // Reset to default if no layout parameter (inline logic instead of calling handleReset)
      sessionStorage.removeItem(COOKIE_NAME);
      setLayout(defaultLayouts);
      const newVisibleComponents = defaultLayouts.map(item => item.i);
      setVisibleComponents(newVisibleComponents);
      dispatch(LayoutActions.setStoredObj({ profile_id: 'default', widget_ui_data_elements: defaultLayouts, base_color: DEFAULT_BASE_COLOR }));
      setProfileId('');
      
      // Reset base color to default
      setSelectedBaseColor(DEFAULT_BASE_COLOR);
      if (onBaseColorChange) {
        onBaseColorChange(DEFAULT_BASE_COLOR);
      }
      
      // Clear the layout parameter from URL
      const currentUrl = new URL(window.location);
      currentUrl.searchParams.delete('layout');
      window.history.pushState({}, '', currentUrl.toString());
      
      return;
    }
    let newLayout;
    let newVisibleComponents;

    // Check if we have an active layout in the stored array.
    if (activeLayoutId) {
      const activeLayout = fastClone(storedArray?.find(o => o.profile_id === activeLayoutId));
      if (activeLayout) {
        const updatedDataElememts = activeLayout.widget_ui_data_elements.map((item) => {
          const { x, y, w, h, widget_ui_data, chart_data, filters, join_sort, pivot_data } = item;
          const defaultElement = defaultLayouts.find((o) => o.i === item.i);
          return { ...defaultElement, x, y, w, h, widget_ui_data, chart_data, filters, join_sort, pivot_data };
        })
        activeLayout.widget_ui_data_elements = updatedDataElememts;
        newLayout = updatedDataElememts;
        newVisibleComponents = newLayout.map(item => item.i);
        dispatch(LayoutActions.setStoredObj(activeLayout));
        setProfileId(activeLayout.profile_id);

        // Apply saved base color if it exists, otherwise use default
        const baseColor = activeLayout.base_color || DEFAULT_BASE_COLOR;

        setSelectedBaseColor(baseColor);
        if (onBaseColorChange) {
          onBaseColorChange(baseColor);
        }
      }
    }

    // If no active layout was found and storedObjDict is empty, fall back to defaults.
    if (!newLayout) {
      // Clean up sessionStorage if the active layout no longer exists.
      if (activeLayoutId) sessionStorage.removeItem(COOKIE_NAME);
      newLayout = defaultLayouts;
      newVisibleComponents = defaultLayouts.map(item => item.i);

      // Use default base color when falling back to default layout
      setSelectedBaseColor(DEFAULT_BASE_COLOR);
      if (onBaseColorChange) {
        onBaseColorChange(DEFAULT_BASE_COLOR);
      }
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

  // Sync internal selectedBaseColor with prop baseColor only on mount
  // Profile loading will handle setting the color after that
  useEffect(() => {
    setSelectedBaseColor(baseColor || DEFAULT_BASE_COLOR);
  }, []); // Empty dependency array - only run on mount

  // Apply global CSS variables to document root
  useEffect(() => {
    // Determine navbar colors
    const currentSelectedPalette = baseColorPalettes[selectedBaseColor] || baseColorPalettes[DEFAULT_BASE_COLOR];
    const isLightMode = theme === Theme.LIGHT;
    const navbarBgColorVarName = currentSelectedPalette.dark;
    const navbarTextColorValue = cssVar('--dark-text-primary');
    const cellSelectedColorVarName = isLightMode ? currentSelectedPalette.lighter : currentSelectedPalette.darkest;

    const root = document.documentElement;
    root.style.setProperty('--dynamic-navbar-bg', `var(${navbarBgColorVarName})`);
    root.style.setProperty('--dynamic-navbar-text', navbarTextColorValue);
    root.style.setProperty('--dynamic-cell-selected', `var(${cellSelectedColorVarName})`);
  }, [selectedBaseColor, theme]);

  if (isLoading || !layout) return <div>Loading layout...</div>;
  if (!layout && !storedObj.widget_ui_data_elements) return null;

  const popoverId = Boolean(anchorEl) ? 'toggle-popover' : undefined;

  const DraggableIcon = isDraggable ? DoNotTouch : PanTool;
  const MuiThemeIcon = theme === Theme.LIGHT ? Brightness7 : Brightness4;

  const handleDraggableToggle = () => {
    setIsDraggable((prev) => !prev);
  }

  const handleThemeToggle = () => {
    onThemeToggle();
  }

  const handleBaseColorSelectorChange = (value) => {
    const newColor = value;
    setSelectedBaseColor(newColor);
    if (onBaseColorChange) {
      onBaseColorChange(newColor);
    }
  };

  const handleSaveLayoutPopupToggle = () => {
    setIsSaveLayoutPopupOpen((prev) => !prev);
  }

  const handleProfileDropdownChange = (selectedValue) => {
    if (selectedValue === 'reset') {
      handleReset();
    } else {
      const loadedObj = storedArray.find((o) => o.profile_id === selectedValue);
      if (loadedObj) {
        dispatch(LayoutActions.setObjId(loadedObj[DB_ID]));
        dispatch(LayoutActions.setStoredObj(loadedObj));
        setLayout(loadedObj.widget_ui_data_elements);
        const newVisibleComponents = loadedObj.widget_ui_data_elements.map(item => item.i);
        setVisibleComponents(newVisibleComponents);
        setProfileId(loadedObj.profile_id);
        sessionStorage.setItem(COOKIE_NAME, loadedObj.profile_id);

        // Apply saved base color if it exists, otherwise use default
        const baseColor = loadedObj.base_color || DEFAULT_BASE_COLOR;

        setSelectedBaseColor(baseColor);
        if (onBaseColorChange) {
          onBaseColorChange(baseColor);
        }

        // Update URL to reflect the selected profile
        const currentUrl = new URL(window.location);
        currentUrl.searchParams.set('layout', loadedObj.profile_id);
        window.history.pushState({}, '', currentUrl.toString());
      }
    }
  };

  const handleProfileIdChange = (e) => {
    setProfileId(e.target.value);
  };

  const handleSave = () => {
    // Ensure profileId exists (add additional checks if needed)
    if (!profileId) return;

    // Build a map for quick lookup of layout items by their key "i"
    const layoutMap = layout.reduce((acc, curr) => {
      acc[curr.i] = curr;
      return acc;
    }, {});

    // Retrieve an existing profile from storedArray, or use storedObj as a fallback.
    let profileData;
    const existingObj = storedArray.find((o) => o.profile_id === profileId);
    if (existingObj) {
      // override existing profile with current layout
      profileData = {
        ...existingObj,
        widget_ui_data_elements: storedObj?.widget_ui_data_elements || [],
      };
    } else {
      // create a new profile
      profileData = {
        profile_id: profileId,
        widget_ui_data_elements: storedObj?.widget_ui_data_elements || [],
      };
    }

    // Deep clone to avoid accidental mutations of the original object.
    profileData = fastClone(profileData);

    // Filter out widget elements that do not exist in the current layout,
    // then map each widget to include updated position/size properties.
    const updatedWidgets = profileData.widget_ui_data_elements
      .filter((widget) => layoutMap[widget.i])
      .map((widget) => {
        const { x, y, w, h } = layoutMap[widget.i];
        return { ...widget, x, y, w, h };
      });

    profileData.widget_ui_data_elements = updatedWidgets;

    // Save the current base color with the profile
    profileData.base_color = selectedBaseColor;


    // Dispatch appropriate action based on whether the profile exists in the database.
    if (profileData[DB_ID]) {
      dispatch(LayoutActions.update({ data: profileData }));
    } else {
      dispatch(LayoutActions.create({ data: profileData }));
    }

    // Persist the active profile ID in session storage.
    sessionStorage.setItem(COOKIE_NAME, profileId);

    // Toggle the layout save popup.
    handleSaveLayoutPopupToggle();
  };

  const handleReset = () => {
    sessionStorage.removeItem(COOKIE_NAME);
    setLayout(defaultLayouts);
    const newVisibleComponents = defaultLayouts.map(item => item.i);
    setVisibleComponents(newVisibleComponents);
    dispatch(LayoutActions.setStoredObj({ profile_id: 'default', widget_ui_data_elements: defaultLayouts, base_color: DEFAULT_BASE_COLOR }));
    setProfileId('');

    // Reset base color to default
    setSelectedBaseColor(DEFAULT_BASE_COLOR);
    if (onBaseColorChange) {
      onBaseColorChange(DEFAULT_BASE_COLOR);
    }

    // Clear the layout parameter from URL
    const currentUrl = new URL(window.location);
    currentUrl.searchParams.delete('layout');
    window.history.pushState({}, '', currentUrl.toString());
  }

  // Calculate navbar styling values for render
  const navbarTextColorValue = cssVar('--dark-text-primary');

  return (
    <div>
      <GlobalScrollbarStyle selectedBaseColorName={selectedBaseColor} />
      {/* Enhanced Navbar with hide-on-scroll functionality */}
      <nav className={`${styles.navbar} ${!isNavbarVisible ? styles.hidden : ''}`}>
        <div className={styles.navbarLogo}>{snakeToTitle(projectName)}</div>
        {/* Base Color Selector - only show if admin_control URL param exists */}
        {showAdminControl && (
          <DropdownButton
            options={Object.values(BaseColor)}
            renderButtonContent={(color) => (
              <span>
                {color === BaseColor.GREEN ? '🟩' : color === BaseColor.BLUE ? '🟦' : '🟫'}
              </span>
            )}
            renderOption={(color) => (
              <>
                {color === BaseColor.GREEN ? '🟩' : color === BaseColor.BLUE ? '🟦' : '🟫'}
              </>
            )}
            initialSelectedIndex={Object.values(BaseColor).indexOf(selectedBaseColor)}
            selectedIndex={Object.values(BaseColor).indexOf(selectedBaseColor)}
            onOptionSelect={handleBaseColorSelectorChange}
          />
        )}
        {/* Profile Dropdown - replacing load popup */}
        <DropdownButton
          options={['reset', ...(storedArray || []).map(profile => profile.profile_id)]}
          renderButtonContent={(option) => (
            <span style={{ fontSize: '0.75rem', color: navbarTextColorValue }}>
              <SpaceDashboard fontSize='medium' sx={{marginRight: '4px'}} />
              {option === 'reset' ? 'Default' : option}
            </span>
          )}
          renderOption={(option) => (
            <>
              {option === 'reset' ? 'Default' : option}
            </>
          )}
          initialSelectedIndex={dropdownSelectedIndex}
          selectedIndex={dropdownSelectedIndex}
          onOptionSelect={handleProfileDropdownChange}
        />
        <Icon name='drag' title='drag' onClick={handleDraggableToggle}>
          <DraggableIcon fontSize='medium' />
        </Icon>
        <Icon name='theme' title='theme' onClick={handleThemeToggle}>
          <MuiThemeIcon fontSize='medium' />
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

    </div>
  );
};

Layout.propTypes = {
  /**
   * The project name to display in the navbar logo.
   */
  projectName: PropTypes.string.isRequired,
  /**
   * The current theme mode ('light' or 'dark').
   */
  theme: PropTypes.string.isRequired,
  /**
   * Callback to toggle the theme mode.
   */
  onThemeToggle: PropTypes.func.isRequired,
  /**
   * The current base color name.
   */
  baseColor: PropTypes.string.isRequired,
  /**
   * Callback to change the base color.
   */
  onBaseColorChange: PropTypes.func.isRequired,
};

export default React.memo(Layout);
