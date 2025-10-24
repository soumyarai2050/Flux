import React, { useRef } from 'react';
import ToggleButton from '@mui/material/ToggleButton';
import { useTheme } from '@mui/material/styles';
import PropTypes from 'prop-types';
import { getResolvedColor } from '../../../utils/ui/colorUtils';
import { getContrastColor } from '../../../utils/ui/uiUtils';
import classes from './ValueBasedToggleButton.module.css';
import ClearIcon from '@mui/icons-material/Clear';
import DeleteIcon from '@mui/icons-material/Delete';
import PauseIcon from '@mui/icons-material/Pause';
import RecyclingIcon from '@mui/icons-material/Recycling';

const ICONS = {
  Clear: ClearIcon,
  Delete: DeleteIcon,
  Pause: PauseIcon,
  Recycling: RecyclingIcon,
};

const DynamicIcon = React.memo(({ iconName }) => {
  const IconComponent = ICONS[iconName];
  if (!IconComponent) return null;

  return <IconComponent />;
});

DynamicIcon.propTypes = {
    iconName: PropTypes.string,
};

const ValueBasedToggleButton = (props) => {
    const theme = useTheme();
    let disabledClass = '';
    if (props.disabled) {
        disabledClass = classes.disabled;
    }

    // Resolve color using the centralized utility instead of CSS class lookup
    const resolvedColor = getResolvedColor(props.color, theme);
    const contrastColor = resolvedColor ? getContrastColor(resolvedColor) : 'inherit';

    // Create sx styles for the dynamic color
    const colorSx = resolvedColor ? {
        backgroundColor: `${resolvedColor} !important`,
        color: `${contrastColor} !important`,
        '&.Mui-selected': {
            backgroundColor: `${resolvedColor} !important`,
            color: `${contrastColor} !important`
        },
        '&:hover': {
            backgroundColor: `${resolvedColor} !important`,
            opacity: 0.8,
        },
    } : {};

    const clickTimeout = useRef(null);

    const handleClicks = (e) => {
        if (props.allowForceUpdate) {
            if (clickTimeout.current !== null) {
                // double click event
                props.onClick(e, props.action, props.xpath, props.value, props.dataSourceId, props.source, true);
                clearTimeout(clickTimeout.current);
                clickTimeout.current = null;
            } else {
                // single click event
                const timeout = setTimeout(() => {
                    if (clickTimeout.current !== null) {
                        props.onClick(e, props.action, props.xpath, props.value, props.dataSourceId, props.source);
                        clearTimeout(clickTimeout.current)
                        clickTimeout.current = null;
                    }
                }, 300);
                clickTimeout.current = timeout;
            }
        } else {
            props.onClick(e, props.action, props.xpath, props.value, props.dataSourceId, props.source);
        }
    }

    return (
        <ToggleButton
            className={`${classes.button} ${disabledClass}`}
            sx={colorSx}
            name={props.name}
            size={props.size}
            selected={true}
            disabled={props.disabled ? props.disabled : false}
            value={props.caption}
            onClick={handleClicks}>
            {props.iconName && <DynamicIcon iconName={props.iconName} />}
            {!props.hideCaption && props.caption}
        </ToggleButton>
    )
}

ValueBasedToggleButton.propTypes = {

}

export default ValueBasedToggleButton;