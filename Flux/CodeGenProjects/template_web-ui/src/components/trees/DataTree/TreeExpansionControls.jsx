import React, { useState } from 'react';
import { Box, Tooltip, IconButton } from "@mui/material";
import { KeyboardDoubleArrowDown, KeyboardDoubleArrowUp, DragHandle } from "@mui/icons-material";
import { BeatLoader } from 'react-spinners';
import PropTypes from 'prop-types';

/**
 * Component for expand/collapse all controls
 * Shows a single toggle icon that changes based on children's expansion state
 */
const TreeExpansionControls = ({ 
    nodeXPath, 
    treeData, 
    onExpandAll, 
    onCollapseAll, 
    hasChildren,
    expandedNodeXPaths = {},
    disabled = false,
    onNodeToggle = null // Function to toggle the node itself
}) => {
    const [isLoading, setIsLoading] = useState(false);

    // Only show controls if the node has children
    if (!hasChildren) {
        return null;
    }

    // Don't show expand/collapse controls on root node or the first real data node
    // Index 0 = 'root' (dummy), Index 1 = first actual data node (portfolio_limits, strat_limits, etc.)
    const firstDataNodeId = treeData && treeData.length > 1 ? treeData[1].id : null;
    
    if (nodeXPath === 'root' || nodeXPath === firstDataNodeId) {
        return null;
    }

    // Check the expansion state of direct children
    const getChildrenExpansionState = () => {
        if (!expandedNodeXPaths || !treeData) return 'none';
        
        // Find all direct children of this node
        const directChildren = treeData.filter(node => {
            const nodeId = node.id;
            // Check if this node is a direct child of the parent we're checking
            if (nodeId.startsWith(nodeXPath + '.') || nodeId.startsWith(nodeXPath + '[')) {
                // Make sure it's a direct child, not a nested child
                const remainder = nodeId.substring(nodeXPath.length + 1);
                // Direct child should not contain additional dots or brackets (except for array indices)
                return !remainder.includes('.') || remainder.match(/^\[\d+\]$/);
            }
            return false;
        });
        
        if (directChildren.length === 0) return 'none';
        
        // Count how many children are expanded
        const expandedChildren = directChildren.filter(child => expandedNodeXPaths[child.id] === true);
        
        if (expandedChildren.length === 0) {
            return 'none'; // No children expanded
        } else if (expandedChildren.length === directChildren.length) {
            return 'all'; // All children expanded
        } else {
            return 'partial'; // Some children expanded, some not
        }
    };

    const expansionState = getChildrenExpansionState();
    
    const handleToggle = async (e) => {
        e.stopPropagation();
        
        setIsLoading(true);
        
        try {
            if (expansionState === 'all' || expansionState === 'partial') {
                // All children expanded - collapse them all
                onCollapseAll(nodeXPath);
                
                // Always collapse the parent node itself when collapsing children
                // This ensures that after collapse, only the parent header remains visible
                if (onNodeToggle) {
                    // Add a small delay to let the children collapse first
                    setTimeout(() => {
                        onNodeToggle(nodeXPath, false);
                    }, 100);
                }
            } else {
                // None or partial expansion - expand all remaining children
                // This will complete the expansion whether starting from none or partial state
                await onExpandAll(nodeXPath, treeData);
            }
            
        } finally {
            setIsLoading(false);
        }
    };

    // Show tooltip and icon based on children expansion state
    let tooltipTitle, IconComponent;
    
    switch (expansionState) {
        case 'none':
            tooltipTitle = "Expand All";
            IconComponent = KeyboardDoubleArrowDown;
            break;
        case 'partial':
            tooltipTitle = "Collapse All (Partial)";
            IconComponent = DragHandle; // Horizontal lines indicating partial state
            break;
        case 'all':
            tooltipTitle = "Collapse All";
            IconComponent = KeyboardDoubleArrowUp;
            break;
        default:
            tooltipTitle = "Expand All";
            IconComponent = KeyboardDoubleArrowDown;
    }

    return (
        <Box sx={{ display: 'flex', marginRight: '8px' }}>
            <Tooltip 
                title={tooltipTitle} 
                disableInteractive
                key={`${nodeXPath}-${isLoading}-${expansionState}`} // Force tooltip re-render
            >
                <IconButton
                    size="small"
                    onClick={handleToggle}
                    disabled={disabled || isLoading}
                    sx={{ 
                        color: 'white',
                        padding: '2px',
                        '&:hover': { backgroundColor: 'rgba(255,255,255,0.1)' },
                        '&.Mui-disabled': { color: 'rgba(255,255,255,0.3)' },
                        minWidth: '24px',
                        minHeight: '24px'
                    }}
                >
                    {isLoading ? (
                        <BeatLoader color="white" size={3} />
                    ) : (
                        <IconComponent 
                            fontSize="small" 
                            sx={expansionState === 'partial' ? { 
                                transform: 'rotate(0deg)', 
                                opacity: 0.9 
                            } : {}}
                        />
                    )}
                </IconButton>
            </Tooltip>
        </Box>
    );
};

TreeExpansionControls.propTypes = {
    nodeXPath: PropTypes.string.isRequired,
    treeData: PropTypes.array.isRequired,
    onExpandAll: PropTypes.func.isRequired,
    onCollapseAll: PropTypes.func.isRequired,
    hasChildren: PropTypes.bool.isRequired,
    expandedNodeXPaths: PropTypes.object,
    disabled: PropTypes.bool,
    onNodeToggle: PropTypes.func
};

export default TreeExpansionControls;
