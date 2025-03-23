import { shallowEqual } from 'react-redux';
import { MODES } from '../constants';
import { snakeToPascal } from '../utils';

/**
 * Generates selectors for a given data source.
 * @param {string} dataSourceName - The name of the data source in snake case.
 * @param {object} selector - The Redux state slice.
 * @returns {object} - Object containing selectors.
 */
export function getDataSourceSelector(dataSourceName, selector) {
    const capDataSourceName = snakeToPascal(dataSourceName);

    return {
        storedArray: selector?.[`stored${capDataSourceName}Array`] ?? [],
        storedObjDict: selector?.[`stored${capDataSourceName}ObjDict`] ?? {},
        storedObj: selector?.[`stored${capDataSourceName}Obj`] ?? {},
        updatedObj: selector?.[`updated${capDataSourceName}Obj`] ?? {},
        objId: selector?.[`selected${capDataSourceName}Id`] ?? null,
        mode: selector?.mode ?? MODES.READ,
        isLoading: selector?.isLoading ?? false,
        error: selector?.error ?? null,
        isConfirmSavePopupOpen: selector?.isConfirmSavePopupOpen ?? false,
        isWsPopupOpen: selector?.isWsPopupOpen ?? false
    };
}

export function getModelLayoutOption(modelName, selector) {
    return selector.storedUILayoutObj.widget_ui_data_elements.find(o => o.i === modelName);
}

export function dataSourcesSelectorEquality(prev, next) {
    if (!shallowEqual(prev.storedArrayDict, next.storedArrayDict)) {
        return false;
    }
    if (!shallowEqual(prev.storedObjDict, next.storedObjDict)) {
        return false;
    }
    if (!shallowEqual(prev.updatedObjDict, next.updatedObjDict)) {
        return false;
    }
    if (!shallowEqual(prev.objIdDict, next.objIdDict)) {
        return false;
    }
    return true;
};
