import React, { Fragment, useRef, useState } from 'react';
import Box from '@mui/material/Box';
import Tooltip from '@mui/material/Tooltip';
import ClickAwayListener from '@mui/material/ClickAwayListener';
import IconButton from '@mui/material/IconButton';
import Collapse from '@mui/material/Collapse';
import PropTypes from 'prop-types';
import { clearxpath } from '../../../utils/core/dataAccess';
import { getColorFromMapping, getResolvedColor } from '../../../utils/ui/colorUtils';
import { isValidJsonString } from '../../../utils/core/stringUtils';
import { floatToInt, getLocalizedValueAndSuffix } from '../../../utils/formatters/numberUtils';
import { groupCommonKeys } from '../../../utils/core/dataGrouping';
import { excludeNullFromObject, formatJSONObjectOrArray } from '../../../utils/core/objectUtils';
import { getDateTimeFromInt } from '../../../utils/formatters/dateUtils';
import { DATA_TYPES, DATE_TIME_FORMATS, MODES } from '../../../constants';
import JsonView from '../JsonView';
import VerticalDataTable from '../tables/VerticalDataTable';
import _, { cloneDeep, isObject } from 'lodash';
import classes from './CommonKeyWidget.module.css';
import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
import timezone from 'dayjs/plugin/timezone';
import { useTheme } from '@mui/material/styles';
import ClipboardCopier from '../../utility/ClipboardCopier';
import ContentCopy from '@mui/icons-material/ContentCopy';
dayjs.extend(utc);
dayjs.extend(timezone);

const localTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;

const CommonKeyWidget = React.forwardRef((props, ref) => {
    const theme = useTheme();
    const { collapse = false } = props;

    if (props.mode === MODES.EDIT || props.commonkeys.length === 0) return null;
    // filter unset or null values from common keys
    let commonkeys = props.commonkeys.filter((obj) => {
        const { value } = obj;
        if (value === undefined || value === null) return false;
        if (Array.isArray(value) && value.length === 0) return false;
        if (isObject(value) && Object.keys(value) === 0) return false;
        if (!obj.displayZero && value === 0) return false;
        if (obj.type === 'button') return false;

        return true;
    })

    if (commonkeys.length === 0) return null;

    // sort the common keys based on sequence in ascending order
    commonkeys = commonkeys.sort(function (a, b) {
        if (a.sequenceNumber < b.sequenceNumber) return -1;
        return 1;
    })

    // group the common keys with same parent
    commonkeys = groupCommonKeys(commonkeys);

    return (
        <Collapse in={!collapse} timeout="auto" unmountOnExit sx={{ minHeight: 'auto !important', backgroundColor: theme.palette.background.commonKey }}>
            <Box ref={ref} className={classes.container} sx={{ bgcolor: 'background.commonKey' }}>
                {commonkeys.map((collection, i) => {
                    return (
                        <Fragment key={i}>
                            {props.lineBreakStart && collection.groupStart && <div className={classes.break_line} />}
                            <CommonKey collection={collection} />
                            {props.lineBreakEnd && collection.groupEnd && <div className={classes.break_line} />}
                        </Fragment>
                    )
                })}
            </Box>
        </Collapse>
    )
})

CommonKeyWidget.propTypes = {
    commonkeys: PropTypes.array.isRequired
};

const CommonKey = (props) => {
    const [open, setOpen] = useState(false);
    const [clipboardText, setClipboardText] = useState(null);
    const jsonTableRef = useRef(null);
    const { collection } = props;

    const theme = useTheme();

    const onOpenAbbreviatedField = () => {
        setOpen(true);
    }

    const onCloseAbbreviatedField = () => {
        setOpen(false);
    }

    const copyHandler = (text) => {
        setClipboardText(text);
    }

    let abbreviatedJsonClass = '';
    if (collection.abbreviated && collection.abbreviated === "JSON") {
        abbreviatedJsonClass = classes.abbreviated_json;
    }

    let abbreviatedField;
    if (collection.abbreviated && collection.abbreviated === "JSON") {
        let updatedData = collection.value;
        if (collection.type === DATA_TYPES.OBJECT || collection.type === DATA_TYPES.ARRAY || (collection.type === DATA_TYPES.STRING && isValidJsonString(updatedData))) {
            if (collection.type === DATA_TYPES.OBJECT || collection.type === DATA_TYPES.ARRAY) {
                updatedData = updatedData ? cloneDeep(updatedData) : null;
                if (updatedData) {
                    formatJSONObjectOrArray(updatedData, collection.subCollections);
                    updatedData = clearxpath(updatedData);
                }
            } else {
                updatedData = updatedData.replace(/\\/g, '');
                updatedData = JSON.parse(updatedData);
            }
            excludeNullFromObject(updatedData);
            abbreviatedField = updatedData ? (
                <div className={classes.abbreviated_json} ref={jsonTableRef}>
                    <span>{JSON.stringify(updatedData)}</span>
                    <VerticalDataTable
                        isOpen={open}
                        data={updatedData}
                        onClose={onCloseAbbreviatedField}
                        anchorEl={jsonTableRef.current}
                        usePopover={true}
                        fieldsMetadata={collection.subCollections || []}
                    />
                </div>
                // <JsonView open={open} onClose={onCloseAbbreviatedField} src={updatedData} />
            ) : null;
        } else if (collection.type === DATA_TYPES.STRING && !isValidJsonString(updatedData)) {
            let tooltipText = "";
            if (updatedData !== null && updatedData !== undefined) {
                let lines = updatedData.replace(/\\n/g, '\n').split('\n');
                tooltipText = (
                    <>
                        {lines.map((line, idx) => (
                            <p key={idx}>
                                {idx === 0 && (
                                    <IconButton className={classes.icon} size='small' onClick={() => copyHandler(updatedData)}>
                                        <ContentCopy fontSize='small' />
                                    </IconButton>
                                )}
                                {line}
                            </p>
                        ))}
                    </>
                )
            }
            abbreviatedField = (
                <>
                    <ClipboardCopier text={clipboardText} />
                    <ClickAwayListener onClickAway={onCloseAbbreviatedField}>
                        <div className={classes.abbreviated_json}>
                            <Tooltip
                                title={tooltipText}
                                placement="bottom-start"
                                open={open}
                                onClose={onCloseAbbreviatedField}
                                disableFocusListener
                                disableHoverListener
                                disableTouchListener>
                                <span>{updatedData}</span>
                            </Tooltip >
                        </div>
                    </ClickAwayListener>
                </>
            )
        }
    }

    let commonkeyColor = 'var(--dark-text-primary)';

    if (collection.color && !collection.progressBar && !collection.button) {
        const colorValue = getColorFromMapping(collection, collection.value, null, theme);
        if (colorValue && colorValue.toLowerCase() === 'default') {
            commonkeyColor = 'var(--dark-text-primary)';
        } else {
            commonkeyColor = getResolvedColor(colorValue, theme, 'var(--dark-text-primary)');
        }
    }

    let commonkeyTitleColor = theme.palette.text.tertiary;
    if (collection.nameColor) {
        const nameColor = collection.nameColor.toLowerCase();
        if (theme.palette.text[nameColor]) {
            commonkeyTitleColor = theme.palette.text[nameColor];
        }
    }

    let value = collection.value;
    if (collection.type === DATA_TYPES.DATE_TIME && value) {
        const dateTimeWithTimezone = getDateTimeFromInt(value);
        if (collection.displayType === 'date') {
            value = dateTimeWithTimezone.format(DATE_TIME_FORMATS.DATE);
        } else if (collection.displayType === 'datetime') {
            value = dateTimeWithTimezone.format(DATE_TIME_FORMATS.DATETIME);
        } else {
            value = dateTimeWithTimezone.isSame(dayjs(), 'day') ? dateTimeWithTimezone.format(DATE_TIME_FORMATS.TIME) : dateTimeWithTimezone.format(DATE_TIME_FORMATS.DATETIME);
        }
    } else if (value && (collection.type === DATA_TYPES.NUMBER || typeof (value) === DATA_TYPES.NUMBER)) {
        if (collection.displayType === DATA_TYPES.INTEGER) {
            value = floatToInt(value);
        }
    } else {
        value = String(value);
    }

    let [numberSuffix, v] = getLocalizedValueAndSuffix(collection, value);
    value = v;
    if (typeof value === DATA_TYPES.NUMBER) {
        value = value.toLocaleString();
    }

    const groupIndicatorColor = theme.palette.text.tertiary;

    let columnName = collection.title ?? collection.key;
    if (collection.displayName) {
        columnName = collection.displayName;
    } else if (collection.elaborateTitle) {
        columnName = collection.tableTitle;
    }

    return (
        <Box className={classes.item}>
            {collection.groupStart && (
                <span style={{ color: `${groupIndicatorColor}` }} className={classes.group_indicator}>
                    {collection.tableTitle?.substring(0, collection.tableTitle?.lastIndexOf('.'))}: [
                </span>
            )}
            <span style={{ color: `${commonkeyTitleColor}` }}>
                {columnName}:
            </span>
            {collection.abbreviated && collection.abbreviated === "JSON" ? (
                <span className={abbreviatedJsonClass} onClick={onOpenAbbreviatedField}>
                    {abbreviatedField}
                </span>
            ) : (
                <span style={{ color: `${commonkeyColor}` }}>
                    {value}{numberSuffix}
                </span>
            )}
            {collection.groupEnd && <span style={{ color: `${groupIndicatorColor}` }} className={classes.group_indicator}> ]</span>}
        </Box>
    )
}

export default CommonKeyWidget;

