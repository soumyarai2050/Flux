import React from 'react';
import classes from './AbbreviatedJson.module.css';
import { ClickAwayListener, Tooltip } from '@mui/material';
import ReactJson from 'react-json-view'
import PropTypes from 'prop-types';

const AbbreviatedJson = (props) => {
    return (
        <ClickAwayListener onClickAway={props.onClose}>
            <div className={classes.text}>
                <Tooltip
                    componentsProps={{ tooltip: { className: classes.popup } }}
                    open={props.open}
                    disableFocusListener
                    disableHoverListener
                    disableTouchListener
                    placement='bottom-start'
                    onClose={props.onClose}
                    title={
                        <ReactJson
                            theme='tube'
                            displayDataTypes={false}
                            displayObjectSize={false}
                            enableClipboard={true}
                            iconStyle='square'
                            indentWidth={6}
                            name={false}
                            src={props.src}
                        />
                    }>
                    <span>{JSON.stringify(props.src)}</span>
                </Tooltip>
            </div>
        </ClickAwayListener>
    )
}

export default AbbreviatedJson;

