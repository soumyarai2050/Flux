import React from 'react';
import { Dialog, Slide } from '@mui/material';
import PropTypes from 'prop-types';
import classes from './Modal.module.css';

const Transition = React.forwardRef(function Transition(props, ref) {
    return <Slide direction="up" ref={ref} {...props} />;
});

const FullScreenModal = (props) => {

    return (
        <Dialog
            id={props.id}
            className={classes.modal}
            // fullScreen
            open={props.open}
            onClose={props.onClose}
            TransitionComponent={Transition}
        >
            {props.children}
        </Dialog>
    )
}

FullScreenModal.defaultProps = {
    open: false
}

FullScreenModal.propTypes = {
    open: PropTypes.bool.isRequired,
    onClose: PropTypes.func.isRequired,
    children: PropTypes.any.isRequired
}

export default FullScreenModal;