import React from 'react';
import { motion } from 'framer-motion';
import PropTypes from 'prop-types';

/**
 * AnimatedTreeNode - A wrapper component that provides smooth accordion-style animations
 * for tree node content using framer-motion.
 */
const AnimatedTreeNode = ({ 
    children, 
    animationKey, 
    className = '',
    style = {},
    ...props 
}) => {
    // Accordion animation variants
    const accordionVariants = {
        hidden: {
            height: 0,
            opacity: 0,
            transition: {
                height: { duration: 0.3, ease: "easeInOut" },
                opacity: { duration: 0.2, ease: "easeOut" }
            }
        },
        visible: {
            height: "auto",
            opacity: 1,
            transition: {
                height: { duration: 0.3, ease: "easeInOut" },
                opacity: { duration: 0.2, delay: 0.1 }
            }
        }
    };

    return (
        <motion.div
            key={animationKey}
            className={`animated-tree-node ${className}`}
            style={{ 
                ...style, 
                overflow: 'hidden', // This is the fix for the collapse glitch
                transformOrigin: 'top'
            }}
            initial="hidden"
            animate="visible"
            exit="hidden"
            variants={accordionVariants}
            layout
            {...props}
        >
            {children}
        </motion.div>
    );
};

AnimatedTreeNode.propTypes = {
    children: PropTypes.node.isRequired,
    isExpanded: PropTypes.bool,
    animationKey: PropTypes.string,
    level: PropTypes.number,
    isContainer: PropTypes.bool,
    className: PropTypes.string,
    style: PropTypes.object,
};

AnimatedTreeNode.defaultProps = {
    isExpanded: false,
    animationKey: 'default',
    level: 0,
    isContainer: false,
    className: '',
    style: {},
};

export default AnimatedTreeNode; 