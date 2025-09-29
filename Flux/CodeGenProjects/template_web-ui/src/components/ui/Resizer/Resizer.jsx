import React, { useCallback, useEffect, useRef, useState } from 'react';
import styles from './Resizer.module.css';

const Resizer = ({
    direction = 'horizontal',
    onResize,
    minSize = 100,
    maxSize = null,
    className = '',
    ...props
}) => {
    const [isDragging, setIsDragging] = useState(false);
    const resizerRef = useRef(null);
    const startPos = useRef(0);
    const startSize = useRef(0);

    const handleMouseDown = useCallback((e) => {
        e.preventDefault();
        setIsDragging(true);
        startPos.current = direction === 'horizontal' ? e.clientY : e.clientX;

        const parentElement = resizerRef.current?.parentElement;
        if (parentElement) {
            const firstChild = parentElement.firstElementChild;
            if (firstChild) {
                const rect = firstChild.getBoundingClientRect();
                startSize.current = direction === 'horizontal' ? rect.height : rect.width;
            }
        }
    }, [direction]);

    const handleMouseMove = useCallback((e) => {
        if (!isDragging) return;

        const currentPos = direction === 'horizontal' ? e.clientY : e.clientX;
        const delta = currentPos - startPos.current;
        let newSize = startSize.current + delta;

        if (newSize < minSize) {
            newSize = minSize;
        }

        if (maxSize && newSize > maxSize) {
            newSize = maxSize;
        }

        if (onResize) {
            onResize(newSize);
        }
    }, [isDragging, direction, minSize, maxSize, onResize]);

    const handleMouseUp = useCallback(() => {
        setIsDragging(false);
    }, []);

    useEffect(() => {
        if (isDragging) {
            document.addEventListener('mousemove', handleMouseMove);
            document.addEventListener('mouseup', handleMouseUp);
            document.body.style.cursor = direction === 'horizontal' ? 'ns-resize' : 'ew-resize';
            document.body.style.userSelect = 'none';

            return () => {
                document.removeEventListener('mousemove', handleMouseMove);
                document.removeEventListener('mouseup', handleMouseUp);
                document.body.style.cursor = '';
                document.body.style.userSelect = '';
            };
        }
    }, [isDragging, handleMouseMove, handleMouseUp, direction]);

    const resizerClasses = `
        ${styles.resizer}
        ${direction === 'horizontal' ? styles.horizontal : styles.vertical}
        ${isDragging ? styles.dragging : ''}
        ${className}
    `.trim();

    return (
        <div
            ref={resizerRef}
            className={resizerClasses}
            onMouseDown={handleMouseDown}
            {...props}
        >
            <div className={styles.handle}>
                {direction === 'horizontal' ? (
                    <div className={styles.dots}>
                        <div className={styles.dot}></div>
                        <div className={styles.dot}></div>
                        <div className={styles.dot}></div>
                    </div>
                ) : (
                    <div className={styles.line}></div>
                )}
            </div>
        </div>
    );
};

export default Resizer;