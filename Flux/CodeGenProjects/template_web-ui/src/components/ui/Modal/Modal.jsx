import React from 'react';
import PropTypes from 'prop-types';
import { Dialog, Slide } from '@mui/material';
import classes from './Modal.module.css';

/**
 * @function SlideUpTransition
 * @description Custom transition component for MUI Dialog, providing a slide-up animation.
 * @param {object} props - The properties passed to the component.
 * @param {React.Ref} ref - The ref to forward to the underlying component.
 * @returns {React.ReactElement} The Slide component with direction set to 'up'.
 */
const SlideUpTransition = React.forwardRef(function Transition(props, ref) {
    return <Slide direction="up" ref={ref} {...props} />;
});

/**
 * @function Modal
 * @description A reusable modal component with a backdrop and slide-up transition, built using Material-UI Dialog.
 * @param {object} props - The properties for the component.
 * @param {React.ReactNode} props.children - The content to be displayed inside the modal.
 * @param {boolean} [props.fullScreen=false] - If true, the modal will take up the full screen.
 * @param {string} props.id - A unique identifier for the modal.
 * @param {boolean} props.open - If true, the modal is open.
 * @param {function} props.onClose - Callback function fired when the modal is requested to be closed.
 * @returns {React.ReactElement} The rendered Modal component.
 */
const Modal = (props) => {
    const { children, fullScreen, id, open, onClose } = props;

    return (
        <Dialog
            id={id}
            className={classes.modal}
            fullScreen={fullScreen}
            open={open}
            onClose={onClose}
            TransitionComponent={SlideUpTransition}
        >
            {children}
        </Dialog>
    );
};

Modal.propTypes = {
    children: PropTypes.any,
    fullScreen: PropTypes.bool,
    id: PropTypes.string.isRequired,
    open: PropTypes.bool.isRequired,
    onClose: PropTypes.func.isRequired,
};

Modal.defaultProps = {
    children: <></>,
    fullScreen: false,
};

const FullScreenModal = Modal;
export default FullScreenModal;

/**
 * @function FullScreenModalOptional
 * @description A component that conditionally renders its children inside a full-screen modal if `open` is true,
 * otherwise renders the children directly.
 * @param {object} props - The properties for the component.
 * @param {React.ReactNode} props.children - The content to be displayed.
 * @param {string} props.id - A unique identifier for the modal.
 * @param {boolean} props.open - If true, the modal is open; otherwise, children are rendered directly.
 * @param {function} props.onClose - Callback function fired when the modal is requested to be closed.
 * @returns {React.ReactElement} The rendered FullScreenModal or its children.
 */
export const FullScreenModalOptional = (props) => {
    const { id, open, children, onClose } = props;

    if (open) {
        return (
            <FullScreenModal
                id={id}
                fullScreen={true}
                open={open}
                onClose={onClose}
            >
                {children}
            </FullScreenModal>
        );
    } else {
        return children;
    }
};

FullScreenModalOptional.propTypes = {
    children: PropTypes.any,
    id: PropTypes.string.isRequired,
    open: PropTypes.bool.isRequired,
    onClose: PropTypes.func.isRequired,
};

FullScreenModalOptional.defaultProps = {
    children: <></>,
};