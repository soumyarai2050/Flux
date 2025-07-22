import { useCallback, useRef, useState, useEffect } from 'react';

/**
 * Custom hook for managing tree expansion animations
 * 
 * This hook enhances the existing tree expansion functionality by:
 * - Tracking animation states for individual nodes
 * - Providing smooth expand/collapse animations
 * - Managing animation timing and coordination
 * - Handling multiple concurrent animations
 */
const useTreeAnimations = (expandedNodeXPaths, handleNodeToggle) => {
    const [animatingNodes, setAnimatingNodes] = useState(new Set());
    const [pendingAnimations, setPendingAnimations] = useState(new Map());
    const [isInitializing, setIsInitializing] = useState(true);
    const animationTimeoutRefs = useRef(new Map());

    // Animation duration in milliseconds
    const ANIMATION_DURATION = 300;

    // Disable animations during initial tree setup
    useEffect(() => {
        const initTimer = setTimeout(() => {
            setIsInitializing(false);
        }, 500); // Longer delay to allow initial tree setup

        return () => clearTimeout(initTimer);
    }, []);

    // Reset initialization flag when tree structure changes significantly
    useEffect(() => {
        const nodeCount = Object.keys(expandedNodeXPaths).length;
        if (nodeCount === 0) {
            setIsInitializing(true);
            const resetTimer = setTimeout(() => {
                setIsInitializing(false);
            }, 500);
            return () => clearTimeout(resetTimer);
        }
    }, [expandedNodeXPaths]);

    /**
     * Enhanced node toggle with animation support
     */
    const animatedNodeToggle = useCallback((nodeXPath, shouldExpand, skipAnimation = false) => {
        // Safety check
        if (!nodeXPath || !handleNodeToggle) {
            return;
        }

        // Skip animation during initialization or when explicitly requested
        if (isInitializing || skipAnimation) {
            handleNodeToggle(nodeXPath, shouldExpand);
            return;
        }

        // Prevent too many simultaneous animations
        if (animatingNodes.size > 10) {
            handleNodeToggle(nodeXPath, shouldExpand);
            return;
        }

        // Clear any existing timeout for this node
        if (animationTimeoutRefs.current.has(nodeXPath)) {
            clearTimeout(animationTimeoutRefs.current.get(nodeXPath));
        }

        // Add to animating nodes
        setAnimatingNodes(prev => new Set([...prev, nodeXPath]));

        // Store pending animation state
        setPendingAnimations(prev => new Map([...prev, [nodeXPath, shouldExpand]]));

        // Set timeout to complete the animation
        const timeoutId = setTimeout(() => {
            try {
                // Execute the actual toggle
                handleNodeToggle(nodeXPath, shouldExpand);
                
                // Clean up animation state
                setAnimatingNodes(prev => {
                    const next = new Set(prev);
                    next.delete(nodeXPath);
                    return next;
                });

                setPendingAnimations(prev => {
                    const next = new Map(prev);
                    next.delete(nodeXPath);
                    return next;
                });

                animationTimeoutRefs.current.delete(nodeXPath);
            } catch (error) {
                console.warn('Error during animated node toggle:', error);
                // Clean up on error
                setAnimatingNodes(prev => {
                    const next = new Set(prev);
                    next.delete(nodeXPath);
                    return next;
                });
                setPendingAnimations(prev => {
                    const next = new Map(prev);
                    next.delete(nodeXPath);
                    return next;
                });
                animationTimeoutRefs.current.delete(nodeXPath);
            }
        }, ANIMATION_DURATION);

        animationTimeoutRefs.current.set(nodeXPath, timeoutId);
    }, [handleNodeToggle, isInitializing, animatingNodes.size]);

    /**
     * Check if a node is currently animating
     */
    const isNodeAnimating = useCallback((nodeXPath) => {
        return animatingNodes.has(nodeXPath);
    }, [animatingNodes]);

    /**
     * Get the target state for a node (what it's animating towards)
     */
    const getNodeTargetState = useCallback((nodeXPath) => {
        if (pendingAnimations.has(nodeXPath)) {
            return pendingAnimations.get(nodeXPath);
        }
        return expandedNodeXPaths[nodeXPath];
    }, [pendingAnimations, expandedNodeXPaths]);

    /**
     * Get animation props for a node
     */
    const getNodeAnimationProps = useCallback((nodeXPath) => {
        const isAnimating = isNodeAnimating(nodeXPath);
        const currentState = expandedNodeXPaths[nodeXPath];
        const targetState = getNodeTargetState(nodeXPath);

        return {
            isAnimating,
            currentState,
            targetState,
            animationDuration: ANIMATION_DURATION,
        };
    }, [isNodeAnimating, getNodeTargetState, expandedNodeXPaths]);

    /**
     * Batch toggle multiple nodes with staggered animations
     */
    const batchAnimatedToggle = useCallback((nodeXPaths, shouldExpand, staggerDelay = 50) => {
        nodeXPaths.forEach((nodeXPath, index) => {
            setTimeout(() => {
                animatedNodeToggle(nodeXPath, shouldExpand);
            }, index * staggerDelay);
        });
    }, [animatedNodeToggle]);

    /**
     * Clean up timeouts on unmount
     */
    useEffect(() => {
        return () => {
            animationTimeoutRefs.current.forEach(timeoutId => {
                clearTimeout(timeoutId);
            });
            animationTimeoutRefs.current.clear();
        };
    }, []);

    return {
        animatedNodeToggle,
        isNodeAnimating,
        getNodeTargetState,
        getNodeAnimationProps,
        batchAnimatedToggle,
        animatingNodes,
        isInitializing, // Export for debugging
    };
};

export default useTreeAnimations; 