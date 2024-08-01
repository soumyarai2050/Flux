import React, { Fragment, useEffect, useRef, useState } from 'react';
import _ from 'lodash';
import { Typography, Box, ToggleButtonGroup, ToggleButton, ClickAwayListener, Tooltip } from '@mui/material';
import { Save, Cached, Edit, AccountTree, GridView, TableChartSharp, PivotTableChartSharp, FormatListNumberedSharp, BarChart } from '@mui/icons-material';
import { Icon } from './Icon';
import { Modes, Layouts } from '../constants';
import PropTypes from 'prop-types';
import CommonKeyWidget from './CommonKeyWidget';
import classes from './WidgetContainer.module.css';
import { useTheme } from '@emotion/react';

const WidgetContainer = (props) => {
    const commonkeyRef = useRef(null);
    const [showLayoutOptions, setShowLayoutOptions] = useState(false);
    const [isBouncing, setIsBouncing] = useState(false);
    const scrollContainerRef = useRef(null);
    const theme = useTheme();

    const handleScroll = () => {
        const element = scrollContainerRef.current;
        const scrollTop = element.scrollTop;
        const maxScrollTop = element.scrollHeight - element.clientHeight;

        if (scrollTop === 0 || scrollTop > (maxScrollTop * 0.95)) {
            // Scrolling at the top or bottom, apply bounce class
            setIsBouncing(true);
        } else {
            // Not at the top or bottom, remove bounce class
            setIsBouncing(false);
        }
    }

    useEffect(() => {
        const element = scrollContainerRef.current;
        element.addEventListener('scroll', handleScroll);

        return () => {
            element.removeEventListener('scroll', handleScroll);
        };
    }, []);


    let modeMenu = '';
    if (props.onSave && props.mode === Modes.EDIT_MODE) {
        modeMenu = <Icon className={classes.icon} name="Save" title="Save" onClick={props.onSave}><Save fontSize='small' /></Icon>
    } else if (props.onChangeMode && props.mode === Modes.READ_MODE) {
        modeMenu = <Icon className={classes.icon} name="Edit" title="Edit" onClick={props.onChangeMode}><Edit fontSize='small' /></Icon>
    }

    const onChangeLayout = (layout) => {
        onToggleShowLayoutOptions();
        props.onChangeLayout(layout);
    }

    const onToggleShowLayoutOptions = () => {
        setShowLayoutOptions(prevState => !prevState);
    }

    const onDoubleClick = (e) => {
        if (props.nestedTree) {
            e.stopPropagation();
        }
    }

    const layoutMenu = showLayoutOptions ? (
        <ClickAwayListener onClickAway={onToggleShowLayoutOptions}>
            <ToggleButtonGroup className={classes.toggle_button_group} value={props.layout ? props.layout : Layouts.TABLE_LAYOUT} size='small'>
                {props.supportedLayouts?.map(layout => {
                    return (
                        <ToggleButton key={layout} className={classes.toggle_button} name={layout} value={layout} onClick={() => onChangeLayout(layout)}>
                            <Tooltip title={layout} disableInteractive>
                                <span>
                                    {layout === Layouts.TABLE_LAYOUT && <TableChartSharp fontSize='medium' />}
                                    {layout === Layouts.TREE_LAYOUT && <AccountTree fontSize='medium' />}
                                    {layout === Layouts.PIVOT_TABLE && <PivotTableChartSharp fontSize='medium' />}
                                    {layout === Layouts.ABBREVIATED_FILTER_LAYOUT && <FormatListNumberedSharp fontSize='medium' />}
                                    {layout === Layouts.CHART && <BarChart fontSize='medium' />}
                                </span>
                            </Tooltip>
                        </ToggleButton>
                    )
                })}
            </ToggleButtonGroup>
        </ClickAwayListener >
    ) : (
        <Icon className={classes.icon} name="Layout" title={`Layout: ${props.layout}`} onClick={onToggleShowLayoutOptions}><GridView fontSize='small' /></Icon>
    )

    let commonkeys = props.commonkeys ? props.commonkeys.filter(commonkey => {
        if (commonkey.value === null || commonkey.value === undefined) return false;
        else if (_.isObject(commonkey.value) && _.keys(commonkey.value).length === 0) return false;
        else if (Array.isArray(commonkey.value) && commonkey.value.length === 0) return false;
        else if (Number.isInteger(commonkey.value) && commonkey.value === 0) {
            if (commonkey.displayZero) return true;
            return false;
        }
        return true;
    }) : [];

    let height = 0;
    if (commonkeyRef.current !== null) {
        height = commonkeyRef.current.offsetHeight;
    }

    const backgroundColor = theme.palette.primary.dark;
    let widgetBodyClasses = `${classes.widget_body}`;
    if (props.mode === Modes.EDIT_MODE) {
        widgetBodyClasses += ` ${classes.edit}`;
    }
    if (props.scrollLock) {
        widgetBodyClasses += ` ${classes.no_scroll}`;
    }
    if (isBouncing) {
        widgetBodyClasses += ` ${classes.bounce}`;
    }

    return (
        <Box onDoubleClick={onDoubleClick}>
            <Typography variant='h6'>
                <div className={classes.widget_header} style={{ background: backgroundColor }}>
                    <span>{props.title}</span>
                    <span>{props.centerText}</span>
                    <div className={classes.menu_container}>
                        {props.menu}
                        {modeMenu}
                        {layoutMenu}
                        {props.onReload && <Icon className={classes.icon} name="Reload" title="Reload" onClick={props.onReload}><Cached fontSize='small' /></Icon>}
                        {props.menuRight}
                    </div>
                </div>
            </Typography>
            {commonkeys.length > 0 && props.mode !== Modes.EDIT_MODE &&
                <CommonKeyWidget
                    ref={commonkeyRef}
                    commonkeys={commonkeys}
                    lineBreakStart={props.lineBreakStart}
                    lineBreakEnd={props.lineBreakEnd}
                    truncateDateTime={props.truncateDateTime}
                />
            }
            <Box style={{ height: `calc(100% - 42px - ${height}px` }} ref={scrollContainerRef} className={widgetBodyClasses}>
                {props.children}
            </Box>
        </Box >
    )
}

WidgetContainer.propTypes = {
    title: PropTypes.string,
    centerText: PropTypes.string,
    menu: PropTypes.oneOfType([PropTypes.element, PropTypes.string]),
    mode: PropTypes.string,
    layout: PropTypes.string,
    commonkeys: PropTypes.array.isRequired,
    onChangeMode: PropTypes.func,
    onChangeLayout: PropTypes.func,
    onSave: PropTypes.func,
    children: PropTypes.any,
    lineBreakStart: PropTypes.bool,
    lineBreakEnd: PropTypes.bool,
    scrollLock: PropTypes.bool,
}

WidgetContainer.defaultProps = {
    commonkeys: [],
    lineBreakStart: true,
    lineBreakEnd: true,
    scrollLock: true,
}

export default WidgetContainer;