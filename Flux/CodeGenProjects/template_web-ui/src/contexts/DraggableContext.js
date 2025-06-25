import React, { createContext, useContext, useState } from 'react';

const DraggableContext = createContext();

export const DraggableProvider = ({ children }) => {
    const [isDraggable, setIsDraggable] = useState(false);

    return (
        <DraggableContext.Provider value={{ isDraggable, setIsDraggable }}>
            {children}
        </DraggableContext.Provider>
    )
}

export const useDraggableContext = () => useContext(DraggableContext);