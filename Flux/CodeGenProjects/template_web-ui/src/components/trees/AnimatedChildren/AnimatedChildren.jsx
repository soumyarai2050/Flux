import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import PropTypes from 'prop-types';

/**
 * AnimatedChildren - A specialized component for animating the children container
 * in an accordion-style fashion when tree nodes expand/collapse.
 * 
 * This component provides smooth height transitions for the children content area.
 */
const AnimatedChildren = ({ 
    children, 
    isExpanded, 
    nodeXPath,
    level = 0,
    className = '',
    style = {},
    ...props 
}) => {
    // Animation variants for the children container
    const childrenVariants = {
        collapsed: {
            height: 0,
            opacity: 0,
            overflow: 'hidden',
            transition: {
                height: { duration: 0.3, ease: "easeInOut" },
                opacity: { duration: 0.2, ease: "easeInOut" }
            }
        },
        expanded: {
            height: "auto",
            opacity: 1,
            overflow: 'visible',
            transition: {
                height: { duration: 0.3, ease: "easeInOut" },
                opacity: { duration: 0.2, ease: "easeInOut", delay: 0.1 }
            }
        }
    };

    // Don't render anything if there are no children
    if (!children || (Array.isArray(children) && children.length === 0)) {
        return null;
    }

    return (
        <AnimatePresence initial={false}>
            {isExpanded && (
                <motion.div
                    key={`children-${nodeXPath}`}
                    className={`animated-children ${className}`}
                    style={{
                        marginLeft: `${level * 20}px`,
                        ...style
                    }}
                    initial="collapsed"
                    animate="expanded"
                    exit="collapsed"
                    variants={childrenVariants}
                    layout
                    {...props}
                >
                    {children}
                </motion.div>
            )}
        </AnimatePresence>
    );
};

AnimatedChildren.propTypes = {
    children: PropTypes.node,
    isExpanded: PropTypes.bool.isRequired,
    nodeXPath: PropTypes.string.isRequired,
    level: PropTypes.number,
    className: PropTypes.string,
    style: PropTypes.object,
};

AnimatedChildren.defaultProps = {
    level: 0,
    className: '',
    style: {},
};

export default AnimatedChildren; 