import React from 'react';
import { Skeleton, Box } from '@mui/material';
import WidgetContainer from './WidgetContainer';
import classes from './SkeletonField.module.css';

const SkeletonField = (props) => {

    return (
        <WidgetContainer title={props.title}>
            <Box className={classes.skeleton_body}>
                <Box className={classes.menu_container}>
                    <Skeleton className={classes.skeleton} variant='circular' width={35} height={35} />
                    <Skeleton className={classes.skeleton} variant='circular' width={35} height={35} />
                </Box>
                <Skeleton className={classes.skeleton} animation='wave' width={240} height={40} />
                <Skeleton style={{ marginLeft: 20 }} className={classes.skeleton} width={140} height={30} />
                <Skeleton style={{ marginLeft: 20 }} animation='wave' className={classes.skeleton} width={240} height={40} />
                <Skeleton style={{ marginLeft: 40 }} className={classes.skeleton} width={140} height={30} />
                <Skeleton style={{ marginLeft: 40 }} className={classes.skeleton} width={140} height={30} />
                <Skeleton style={{ marginLeft: 20 }} className={classes.skeleton} width={140} height={30} />
            </Box>
        </WidgetContainer>
    )
}

export default SkeletonField;