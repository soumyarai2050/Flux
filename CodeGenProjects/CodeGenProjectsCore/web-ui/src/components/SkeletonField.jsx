import React from 'react'
import { Skeleton, Box } from '@mui/material'
import { makeStyles } from '@mui/styles'
import WidgetContainer from './WidgetContainer'

const useStyles = makeStyles({
    skeletonContainer: {
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
    },
    skeletionMenuContainer: {
        display: 'flex',
        margin: '20px 0',
    },
    skeletonBody: {
        padding: '0 20px'
    },
    skeleton: {
        margin: 2,
        borderRadius: 5
    }
})

const SkeletonField = (props) => {

    const classes = useStyles();

    return (
        <Box className={classes.skeletonContainer}>
            <WidgetContainer title={props.title}>
                <Box className={classes.skeletonBody}>
                    <Box className={classes.skeletionMenuContainer}>
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
        </Box>
    )
}

export default SkeletonField