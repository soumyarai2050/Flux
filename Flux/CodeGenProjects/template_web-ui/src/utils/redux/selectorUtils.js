import { shallowEqual } from 'react-redux';
import { MODES } from '../../constants';
import { snakeToPascal } from '../core/stringUtils';

/**
 * @function getDataSourceSelector
 * @description Generates a structured object containing various state properties for a given data source.
 * This function dynamically constructs property names based on the `dataSourceName`.
 * @param {string} dataSourceName - The name of the data source in snake_case (e.g., 'admin_control').
 * @param {object} selector - The Redux state slice object for the data source.
 * @returns {object} An object containing the `storedArray`, `storedObjDict`, `storedObj`, `objId`, `mode`, `isCreating`, `isLoading`, `error`, and `popupStatus` for the specified data source.
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
        allowUpdates: selector?.allowUpdates ?? true,
        isCreating: selector?.isCreating ?? false,
        isLoading: selector?.isLoading ?? false,
        error: selector?.error ?? null,
        popupStatus: selector?.popupStatus ?? {}
    };
}

/**
 * @function getModelLayoutOption
 * @description Retrieves the layout option for a specific model from the UI layout state.
 * It searches within `storedUILayoutObj.widget_ui_data_elements` for a matching model name.
 * @param {string} modelName - The name of the model to find the layout option for.
 * @param {object} selector - The UI layout state slice object.
 * @returns {object} The matching widget UI data element, or a default empty object if not found.
 */
export function getModelLayoutOption(modelName, selector) {
    return selector.storedUILayoutObj.widget_ui_data_elements.find(o => o.i === modelName);
}

/**
 * @function dataSourcesSelectorEquality
 * @description A custom equality function for `reselect` selectors that compares dictionaries of data sources.
 * It performs a shallow comparison of `storedArrayDict`, `storedObjDict`, `updatedObjDict`, and `objIdDict`.
 * @param {object} prev - The previous result of the selector.
 * @param {object} next - The current result of the selector.
 * @returns {boolean} True if the relevant parts of the data source dictionaries are shallowly equal, false otherwise.
 */
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
