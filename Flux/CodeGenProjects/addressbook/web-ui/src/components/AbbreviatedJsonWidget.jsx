import React from 'react';
import { Dialog } from '@mui/material';
import { makeStyles } from '@mui/styles';
import ReactJson from 'react-json-view'
import PropTypes from 'prop-types';
import { ClickAwayListener, Tooltip } from '@mui/material';

const useStyles = makeStyles({
    abbreviated: {
        maxWidth: 150,
        overflow: 'hidden',
        textOverflow: 'ellipsis'
    },
    tooltip: {
        maxWidth: 'none !important'
    }
})

const AbbreviatedJsonWidget = (props) => {

    const classes = useStyles();

    return (
        <Dialog open={props.open} onClose={props.onClose}>
            <ReactJson
                style={{ minHeight: 500, minWidth: 450, width: 'max-content' }}
                theme='tube'
                displayDataTypes={false}
                displayObjectSize={false}
                indentWidth={6}
                enableClipboard={false}
                name={false}
                iconStyle='square'
                src={props.json}
            />
        </Dialog>
    )
}

AbbreviatedJsonWidget.defaultProps = {
    open: false,
    json: {}
}

AbbreviatedJsonWidget.propTypes = {
    open: PropTypes.bool.isRequired,
    onClose: PropTypes.func.isRequired
}

export const AbbreviatedJsonTooltip = (props) => {
    const classes = useStyles();

    let value = JSON.stringify(props.src);

    return (
        <ClickAwayListener onClickAway={props.onClose}>
            <div className={classes.abbreviated}>
                <Tooltip
                    componentsProps={{ tooltip: { className: classes.tooltip } }}
                    open={props.open}
                    onClose={props.onClose}
                    disableFocusListener
                    disableHoverListener
                    disableTouchListener
                    placement='bottom-start'
                    title={
                        <ReactJson
                            theme='tube'
                            displayDataTypes={false}
                            displayObjectSize={false}
                            indentWidth={6}
                            enableClipboard={false}
                            name={false}
                            iconStyle='square'
                            src={props.src}
                        />
                    }>
                    <span>{value}</span>
                </Tooltip>
            </div>
        </ClickAwayListener>
    )
}

export default AbbreviatedJsonWidget;

