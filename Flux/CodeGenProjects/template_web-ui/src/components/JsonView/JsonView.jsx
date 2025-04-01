import React, { useState } from 'react';
import { ClickAwayListener, Tooltip } from '@mui/material';
import ReactJson from 'react-json-view'
import PropTypes from 'prop-types';
import { useTheme } from '@emotion/react';
import styles from './JsonView.module.css';
import ClipboardCopier from '../ClipboardCopier';

const JsonView = (props) => {
    const theme = useTheme();
    const [clipboardText, setClipboardText] = useState(null);
    const jsonViewTheme = theme.palette.mode === 'dark' ? 'tube' : 'rjv-default';

    return (
        <ClickAwayListener onClickAway={props.onClose}>
            <div className={styles.text}>
                <ClipboardCopier text={clipboardText} />
                <Tooltip
                    componentsProps={{ tooltip: { className: styles.popup } }}
                    open={props.open}
                    disableFocusListener
                    disableHoverListener
                    disableTouchListener
                    placement='bottom-start'
                    onClose={props.onClose}
                    title={
                        <ReactJson
                            theme={jsonViewTheme}
                            displayDataTypes={false}
                            displayObjectSize={false}
                            enableClipboard={(o) => setClipboardText(JSON.stringify(o.src, null, 2))}
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

JsonView.propTypes = {
    text: PropTypes.string.isRequired,
    open: PropTypes.bool.isRequired,
    src: PropTypes.oneOfType([PropTypes.array, PropTypes.object]).isRequired,
    onClose: PropTypes.func.isRequired
}

JsonView.defaultProps = {
    text: JSON.stringify({}),
    open: false,
    src: {}
}

export default JsonView;

