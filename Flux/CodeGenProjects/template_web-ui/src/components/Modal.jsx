import React from 'react';
import PropTypes from 'prop-types';
import { Dialog, Slide } from '@mui/material';
import classes from './Modal.module.css';

// slide up transition for modal
const SlideUpTransition = React.forwardRef(function Transition(props, ref) {
    return <Slide direction="up" ref={ref} {...props} />;
});

const Modal = (props) => {
    /* 
    modal component with backdrop and slide up transition using material ui Dialog.
    props:
        children: React child component
        fullScreen: to set the modal to full screen, default false
        id: unique id for modal
        open: to identify if modal is open
        onClose: close handler for the modal
    */

    // required props
    const { children, fullScreen, id, open, onClose } = props;

    return (
        <Dialog
            id={id}
            className={classes.modal}
            fullScreen={fullScreen}
            open={open}
            onClose={onClose}
            TransitionComponent={SlideUpTransition}>
            {children}
        </Dialog>
    )
}

Modal.propTypes = {
    children: PropTypes.any,
    fullScreen: PropTypes.bool,
    id: PropTypes.string.isRequired,
    open: PropTypes.bool.isRequired,
    onClose: PropTypes.func.isRequired,
}

Modal.defaultProps = {
    children: <></>,
    fullScreen: false,
}

const FullScreenModal = Modal;
export default FullScreenModal;

export const FullScreenModalOptional = (props) => {
    /* 
    optional full screen modal component. 
    if modal is open, it wraps the children inside full screen modal. 
    otherwise returns the children
    props:
        children: React child component
        id: unique id for modal
        open: to identify if modal is open
        onClose: close handler for the modal
    */

    // required props
    const { id, open, children, onClose } = props;

    if (open) {
        // modal is open, wrap inside full screen modal
        return (
            <FullScreenModal
                id={id}
                fullScreen={true}
                open={open}
                onClose={onClose}>
                {children}
            </FullScreenModal>
        )
    } else {
        // return children as it is
        return children;
    }
}

FullScreenModalOptional.propTypes = {
    children: PropTypes.any,
    id: PropTypes.string.isRequired,
    open: PropTypes.bool.isRequired,
    onClose: PropTypes.func.isRequired,
}

FullScreenModalOptional.defaultProps = {
    children: <></>,
}
