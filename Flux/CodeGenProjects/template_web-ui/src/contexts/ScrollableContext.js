import React, { createContext, useContext, useState } from 'react';

const ScrollableContext = createContext();

export const ScrollableProvider = ({ children }) => {
    const [isScrollable, setIsScrollable] = useState(false);

    return (
        <ScrollableContext.Provider value={{ isScrollable, setIsScrollable }}>
            {children}
        </ScrollableContext.Provider>
    )
}

export const useScrollableContext = () => useContext(ScrollableContext);