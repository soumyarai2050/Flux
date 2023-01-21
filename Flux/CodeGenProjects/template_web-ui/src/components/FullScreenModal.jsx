import React from 'react';
import { makeStyles } from '@mui/styles';
import { Dialog, Slide } from '@mui/material';
import PropTypes from 'prop-types';

const useStyles = makeStyles({
    modal: {
        maxHeight: '100vh',
        minWidth: '30%',
        '& .MuiDialog-container': {
            '& .MuiPaper-root': {
                margin: 0,
                minWidth: "30%",  // Set your width here
            },
        },
    }
})

const Transition = React.forwardRef(function Transition(props, ref) {
    return <Slide direction="up" ref={ref} {...props} />;
});

const FullScreenModal = (props) => {

    const classes = useStyles();

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