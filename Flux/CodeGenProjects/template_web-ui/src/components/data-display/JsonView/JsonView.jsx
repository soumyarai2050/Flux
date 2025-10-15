import React, { useState } from 'react';
import ClickAwayListener from '@mui/material/ClickAwayListener';
import Tooltip from '@mui/material/Tooltip';
import { JsonViewer } from '@textea/json-viewer';
import PropTypes from 'prop-types';
import { useTheme } from '@mui/material/styles';
import styles from './JsonView.module.css';
import ClipboardCopier from '../../utility/ClipboardCopier';

const JsonView = (props) => {
    const theme = useTheme();
    const [clipboardText, setClipboardText] = useState(null);
    const isDarkMode = theme.palette.mode === 'dark';

    // Custom copy handler that uses ClipboardCopier instead of navigator API
    const handleCopy = (path, value) => {
        setClipboardText(JSON.stringify(value, null, 2));
        // Return false to prevent default @textea/json-viewer copy behavior
        return false;
    };

    const jsonViewerComponent = (
        <div className={styles.jsonViewerContainer}>
            <JsonViewer
                value={props.src}
                theme={isDarkMode ? 'dark' : 'light'}
                displayDataTypes={false}
                displayObjectSize={false}
                enableClipboard={props.enableClipboard}
                onCopy={props.enableClipboard ? handleCopy : undefined}
                indentWidth={6}
                rootName={false}
                defaultInspectDepth={props.collapsed !== undefined ? props.collapsed : 0}
                style={{
                    padding: '5px',
                    borderRadius: '5px',
                }}
            />
        </div>
    );

    // Standalone mode: just return the JSON viewer component
    if (!props.showWrapper) {
        return (
            <>
                {props.enableClipboard && <ClipboardCopier text={clipboardText} />}
                {jsonViewerComponent}
            </>
        );
    }

    // Tooltip mode: wrap with ClickAwayListener and Tooltip
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
                    title={jsonViewerComponent}>
                    <span>{JSON.stringify(props.src)}</span>
                </Tooltip>
            </div>
        </ClickAwayListener>
    );
};

JsonView.propTypes = {
    src: PropTypes.oneOfType([PropTypes.array, PropTypes.object]).isRequired,
    open: PropTypes.bool,
    onClose: PropTypes.func,
    collapsed: PropTypes.number,
    showWrapper: PropTypes.bool,
    enableClipboard: PropTypes.bool
};

JsonView.defaultProps = {
    open: false,
    src: {},
    collapsed: 0,
    showWrapper: true,
    enableClipboard: true
};

export default JsonView;
