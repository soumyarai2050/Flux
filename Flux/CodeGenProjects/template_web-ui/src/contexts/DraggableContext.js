import React, { createContext, useContext, useState } from 'react';

const DraggableContext = createContext();

/**
 * @function DraggableProvider
 * @description Provides a context for managing a draggable state throughout the application.
 * @param {object} props - The properties for the component.
 * @param {React.ReactNode} props.children - The child components to be rendered within the provider's scope.
 * @returns {React.ReactElement} The DraggableContext Provider.
 */
export const DraggableProvider = ({ children }) => {
    const [isDraggable, setIsDraggable] = useState(false);

    return (
        <DraggableContext.Provider value={{ isDraggable, setIsDraggable }}>
            {children}
        </DraggableContext.Provider>
    );
};

/**
 * @function useDraggableContext
 * @description A custom hook to access the draggable state and its setter from the DraggableContext.
 * @returns {{isDraggable: boolean, setIsDraggable: function}} The draggable state and its setter.
 */
export const useDraggableContext = () => useContext(DraggableContext);