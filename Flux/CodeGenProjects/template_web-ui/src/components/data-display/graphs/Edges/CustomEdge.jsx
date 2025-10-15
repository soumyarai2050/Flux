import React from 'react';
import { BaseEdge, EdgeLabelRenderer, getBezierPath } from '@xyflow/react';
import TroubleshootOutlined from '@mui/icons-material/TroubleshootOutlined';
import SendOutlined from '@mui/icons-material/SendOutlined';
import styles from './CustomEdge.module.css';

const CustomEdge = ({ sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, style = {}, data, markerEnd }) => {
    const [edgePath, labelX, labelY] = getBezierPath({
        sourceX,
        sourceY,
        sourcePosition,
        targetX,
        targetY,
        targetPosition,
    });

    return (
        <>
            <BaseEdge path={edgePath} markerEnd={markerEnd} style={style} />
            <EdgeLabelRenderer>
                <div
                    style={{
                        position: 'absolute',
                        transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
                        fontSize: 12,
                        pointerEvents: 'all',
                    }}
                    className="nodrag nopan"
                >
                    <div className={styles.iconContainer}>
                        <div
                            className={`${styles.edgeButton} ${data?.isSelected ? styles.selected : ''}`}
                            title="Analyze"
                        >
                            <TroubleshootOutlined sx={{ fontSize: 18 }} />
                        </div>
                        <div
                            className={`${styles.edgeButton}`}
                            title="Publish"
                        >
                            <SendOutlined sx={{ fontSize: 18 }} />
                        </div>
                    </div>
                </div>
            </EdgeLabelRenderer>
        </>
    );
};

export default CustomEdge;
