import { configureStore } from '@reduxjs/toolkit';
import orderLimitsSlice from './features/orderLimitsSlice';
import portfolioLimitsSlice from './features/portfolioLimitsSlice';
import portfolioStatusSlice from './features/portfolioStatusSlice';
import pairStratSlice from './features/pairStratSlice';
import stratCollectionSlice from './features/stratCollectionSlice';
import uiLayoutSlice from './features/uiLayoutSlice';
import schemaSlice from './features/schemaSlice';

export const store = configureStore({
    reducer: {
        schema: schemaSlice,
        orderLimits: orderLimitsSlice,
        portfolioLimits: portfolioLimitsSlice,
        portfolioStatus: portfolioStatusSlice,
        pairStrat: pairStratSlice,
        stratCollection: stratCollectionSlice,
        uiLayout: uiLayoutSlice
    }
});
