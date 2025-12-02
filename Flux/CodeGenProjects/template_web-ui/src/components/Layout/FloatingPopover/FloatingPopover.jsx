import React, { useState, useCallback, useMemo, useRef } from 'react';
import PropTypes from 'prop-types';
import { motion, useMotionValue, useTransform } from 'framer-motion';
import { Responsive, WidthProvider } from 'react-grid-layout';
import PictureInPictureAltIcon from '@mui/icons-material/PictureInPictureAlt';
import DoNotTouch from '@mui/icons-material/DoNotTouch';
import PanTool from '@mui/icons-material/PanTool';
import PopoverWidgetWrapper from './PopoverWidgetWrapper';
import { componentMapWithFallback as componentMap } from '../../../models/componentMap';
import Icon from '../../ui/Icon';
import styles from './FloatingPopover.module.css';
import 'react-grid-layout/css/styles.css';
import 'react-resizable/css/styles.css';

const ResponsiveGridLayout = WidthProvider(Responsive);

const popoverGridProps = {
  className: 'popover-layout',
  breakpoints: { lg: 1200 },
  cols: { lg: 8 }, // 8 columns instead of 18
  margin: { lg: [8, 8] },
  rowHeight: 25,
  autoSize: true,
  responsive: true,
  compactType: 'vertical',
  resizeHandles: ['se']
};

/**
 * FloatingPopover Component
 * A floating workspace overlay that displays disabled widgets in a 50% width/height popover.
 * Widgets can be dragged, resized, and maximized within the popover.
 * The entire popover window can also be dragged around.
 */
const FloatingPopover = ({
  open,
  widgets,
  layout,
  onLayoutChange,
  onRemoveWidget,
  onMaximizeToggle
}) => {
  const [popoverWidgetsDraggable, setPopoverWidgetsDraggable] = useState(false);
  const [isDraggingPopover, setIsDraggingPopover] = useState(false);
  const [enablePopoverDrag, setEnablePopoverDrag] = useState(false);
  const [popoverSize, setPopoverSize] = useState({ width: 50, height: 50 }); // vw, vh
  const [isResizing, setIsResizing] = useState(false);
  const resizeStartRef = useRef({ width: 0, height: 0, startX: 0, startY: 0 });
  const dragStartElement = useRef(null);
  const widthMotion = useMotionValue(50);
  const heightMotion = useMotionValue(50);
  const widthTransform = useTransform(widthMotion, (w) => `${w}vw`);
  const heightTransform = useTransform(heightMotion, (h) => `${h}vh`);

  const handlePopoverWidgetsDragToggle = useCallback(() => {
    setPopoverWidgetsDraggable(prev => !prev);
  }, []);

  const DraggableIcon = useMemo(() =>
    popoverWidgetsDraggable ? DoNotTouch : PanTool,
    [popoverWidgetsDraggable]
  );

  const iconTitle = useMemo(() =>
    popoverWidgetsDraggable ? 'Disable drag' : 'Enable drag',
    [popoverWidgetsDraggable]
  );

  const cursorClass = useMemo(() => {
    if (!popoverWidgetsDraggable) return styles.default;
    return isDraggingPopover ? styles.grabbing : styles.grab;
  }, [popoverWidgetsDraggable, isDraggingPopover]);

  const handlePointerDown = useCallback((e) => {
    // Capture which element initiated the pointer down
    dragStartElement.current = e.target;

    const isFromHeader = e.target.closest(`.${styles.popover_header}`);
    const isInteractive = e.target.closest('[data-interactive]');

    // Only allow drag if pointer started from header and not interactive
    const canDrag = isFromHeader && !isInteractive;
    setEnablePopoverDrag(canDrag);
  }, []);

  const handleDragStart = useCallback(() => {
    setIsDraggingPopover(true);
  }, []);

  const handleDragEnd = useCallback(() => {
    dragStartElement.current = null;
    setIsDraggingPopover(false);
    setEnablePopoverDrag(false);
  }, []);

  const handleResizeStart = useCallback((e) => {
    // Only resize from bottom-right corner
    if (!e.target.closest(`.${styles.popover_resizer}`)) {
      return;
    }

    e.preventDefault();
    setIsResizing(true);

    resizeStartRef.current = {
      width: popoverSize.width,
      height: popoverSize.height,
      startX: e.clientX,
      startY: e.clientY
    };

    const handleMouseMove = (e) => {
      const deltaX = e.clientX - resizeStartRef.current.startX;
      const deltaY = e.clientY - resizeStartRef.current.startY;

      // Convert pixels to viewport units
      const deltaVw = (deltaX / window.innerWidth) * 100;
      const deltaVh = (deltaY / window.innerHeight) * 100;

      // Set minimum size (20vw x 20vh) and maximum (90vw x 90vh)
      const newWidth = Math.max(20, Math.min(90, resizeStartRef.current.width + deltaVw));
      const newHeight = Math.max(20, Math.min(90, resizeStartRef.current.height + deltaVh));

      widthMotion.set(newWidth);
      heightMotion.set(newHeight);
      setPopoverSize({ width: newWidth, height: newHeight });
    };

    const handleMouseUp = () => {
      setIsResizing(false);
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
  }, [popoverSize, widthMotion, heightMotion]);

  if (!open) return null;

  return (
    <motion.div
      drag={enablePopoverDrag}
      dragMomentum={false}
      initial={{ x: 0, y: 0 }}
      onPointerDown={handlePointerDown}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
      className={`${styles.popover_overlay} ${cursorClass}`}
      style={{
        left: 'calc(25%)',
        top: 'calc(25%)',
        width: widthTransform,
        height: heightTransform
      }}
    >
      <div className={styles.popover_container}>
        <div
          className={styles.popover_resizer}
          onMouseDown={handleResizeStart}
          title="Drag to resize"
        />
        <div className={styles.popover_header}>
          <PictureInPictureAltIcon fontSize="small" style={{ marginLeft: '4px', flexShrink: 0 }} />
          <span className={styles.popover_title}>
            Floating Workspace
          </span>
          <Icon
            name='drag'
            title={iconTitle}
            onClick={handlePopoverWidgetsDragToggle}
            data-interactive
          >
            <DraggableIcon fontSize="small" />
          </Icon>
        </div>
        <div className={styles.popover_content}>
          {widgets.length > 0 ? (
            <ResponsiveGridLayout
              {...popoverGridProps}
              isDraggable={popoverWidgetsDraggable}
              isResizable={popoverWidgetsDraggable}
              layouts={{ lg: layout }}
              onLayoutChange={onLayoutChange}
            >
              {widgets.map((widget) => {
                const Component = componentMap[widget.i];
                if (!Component) {
                  console.warn(`Component not found for widget: ${widget.i}`);
                  return null;
                }
                return (
                  <div key={widget.i} className={styles.popover_grid_item}>
                    <PopoverWidgetWrapper
                      widgetId={widget.i}
                      isMaximized={widget.isMaximized || false}
                      onRemove={onRemoveWidget}
                      onMaximizeToggle={onMaximizeToggle}
                    >
                      <Component />
                    </PopoverWidgetWrapper>
                  </div>
                );
              })}
            </ResponsiveGridLayout>
          ) : (
            <div className={styles.empty_message}>No widgets in popover</div>
          )}
        </div>
      </div>
    </motion.div>
  );
};

FloatingPopover.propTypes = {
  open: PropTypes.bool.isRequired,
  widgets: PropTypes.arrayOf(PropTypes.shape({
    i: PropTypes.string.isRequired,
    isMaximized: PropTypes.bool,
    w: PropTypes.number,
    h: PropTypes.number,
    x: PropTypes.number,
    y: PropTypes.number,
  })).isRequired,
  layout: PropTypes.arrayOf(PropTypes.shape({
    x: PropTypes.number,
    y: PropTypes.number,
    w: PropTypes.number,
    h: PropTypes.number,
    i: PropTypes.string,
  })).isRequired,
  onLayoutChange: PropTypes.func.isRequired,
  onRemoveWidget: PropTypes.func.isRequired,
  onMaximizeToggle: PropTypes.func.isRequired,
};

export default FloatingPopover;