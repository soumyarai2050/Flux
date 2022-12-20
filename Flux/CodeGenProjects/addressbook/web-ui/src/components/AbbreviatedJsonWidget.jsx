import React from 'react';
import { Dialog } from '@mui/material';
import { makeStyles } from '@mui/styles';
import ReactJson from 'react-json-view'
import PropTypes from 'prop-types';

const useStyles = makeStyles({})

const AbbreviatedJsonWidget = (props) => {

    const classes = useStyles();

    return (
        <Dialog open={props.open} onClose={props.onClose}>
            <ReactJson
                style={{minHeight: 500, minWidth: 450, width: 'max-content'}}
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

export default AbbreviatedJsonWidget;