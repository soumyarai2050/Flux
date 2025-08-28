import React from 'react';
import { Skeleton as SkeletonBox, Box } from '@mui/material';
import { ModelCard, ModelCardHeader, ModelCardContent } from '../../utility/cards';
import styles from './Skeleton.module.css';

const Skeleton = ({
    name
}) => {

    return (
        <ModelCard>
            <ModelCardHeader name={name} />
            <ModelCardContent>
                <Box className={styles.skeleton_body}>
                    <Box className={styles.menu_container}>
                        <SkeletonBox className={styles.skeleton} variant='circular' width={35} height={35} />
                        <SkeletonBox className={styles.skeleton} variant='circular' width={35} height={35} />
                    </Box>
                    <SkeletonBox className={styles.skeleton} animation='wave' width={240} height={40} />
                    <SkeletonBox style={{ marginLeft: 20 }} className={styles.skeleton} width={140} height={30} />
                    <SkeletonBox style={{ marginLeft: 20 }} animation='wave' className={styles.skeleton} width={240} height={40} />
                    <SkeletonBox style={{ marginLeft: 40 }} className={styles.skeleton} width={140} height={30} />
                    <SkeletonBox style={{ marginLeft: 40 }} className={styles.skeleton} width={140} height={30} />
                    <SkeletonBox style={{ marginLeft: 20 }} className={styles.skeleton} width={140} height={30} />
                </Box>
            </ModelCardContent>
        </ModelCard>
    )
}

export default Skeleton;