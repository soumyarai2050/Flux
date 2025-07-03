import React, { createContext, useContext, useState } from 'react';

const ScrollableContext = createContext();

/**
 * @function ScrollableProvider
 * @description Provides a context for managing the name of a currently active scrollable area.
 * @param {object} props - The properties for the component.
 * @param {React.ReactNode} props.children - The child components to be rendered within the provider's scope.
 * @returns {React.ReactElement} The ScrollableContext Provider.
 */
export const ScrollableProvider = ({ children }) => {
    const [scrollableName, setScrollableName] = useState(null);

    return (
        <ScrollableContext.Provider value={{ scrollableName, setScrollableName }}>
            {children}
        </ScrollableContext.Provider>
    );
};

/**
 * @function useScrollableContext
 * @description A custom hook to access the scrollable name state and its setter from the ScrollableContext.
 * @returns {{scrollableName: string|null, setScrollableName: function}} The scrollable name state and its setter.
 */
export const useScrollableContext = () => useContext(ScrollableContext);