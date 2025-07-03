import { SEVERITY_TYPES } from '../constants';

/**
 * @class AlertCache
 * @description Manages the caching of alert severity indices and positions.
 * It helps in maintaining the order and counts of alerts based on their severity.
 */
export class AlertCache {
    /**
     * @property {object} severityFirstNLastIdxDict - Stores severity cache data.
     * Format: `{ modelName: { id: { severity: { first: number, last: number } } } }`
     */
    static severityFirstNLastIdxDict = {};

    /**
     * Retrieves the severity cache for a given model name and optional ID.
     * Initializes the cache if it doesn't exist.
     * @param {string} name - The name of the model.
     * @param {string|null} [id=null] - The ID of the alert (optional).
     * @returns {object} The severity cache object.
     */
    static getSeverityCache(name, id = null) {
        if (id) {
            if (!AlertCache.severityFirstNLastIdxDict?.[name]?.[id]) {
                AlertCache.setSeverityCache(name, id, {});
            }
            return AlertCache.severityFirstNLastIdxDict[name][id];
        } else {
            if (!AlertCache.severityFirstNLastIdxDict?.[name]) {
                AlertCache.setSeverityCache(name, null, {});
            }
            return AlertCache.severityFirstNLastIdxDict[name];
        }
    }

    /**
     * Sets the severity cache for a given model name and optional ID.
     * @param {string} name - The name of the model.
     * @param {string|null} [id=null] - The ID of the alert (optional).
     * @param {object} severityCache - The severity cache object to set.
     */
    static setSeverityCache(name, id = null, severityCache) {
        if (id) {
            if (!AlertCache.severityFirstNLastIdxDict[name]) {
                AlertCache.severityFirstNLastIdxDict[name] = {};
            }
            AlertCache.severityFirstNLastIdxDict[name][id] = severityCache;
        } else {
            AlertCache.severityFirstNLastIdxDict[name] = severityCache;
        }
    }

    /**
     * Updates the severity cache based on a severity type and a delta.
     * This method adjusts the `first` and `last` indices for severities.
     * @param {string} name - The name of the model.
     * @param {string|null} [id=null] - The ID of the alert (optional).
     * @param {string} severity - The severity type (e.g., 'Severity_CRITICAL').
     * @param {number} delta - The change in count (-1 for removal, 1 for addition).
     */
    static updateSeverityCache(name, id = null, severity, delta) {
        const severityCache = AlertCache.getSeverityCache(name, id);
        const severityPriority = SEVERITY_TYPES[severity];

        if (severityCache.hasOwnProperty(severity)) {
            const { first, last } = severityCache[severity];
            if (delta === -1) {
                if (first === last) {
                    delete severityCache[severity];
                } else {
                    severityCache[severity].last += delta;
                }
            } else {  // delta is 1
                severityCache[severity].last += delta;
            }
        } else {
            if (delta === 1) {
                let higherPrioritySeverityIdx;
                Object.keys(SEVERITY_TYPES).forEach(k => {
                    if (SEVERITY_TYPES[k] > severityPriority) {
                        if (severityCache.hasOwnProperty(k) && (severityCache[k].last || severityCache[k].last === 0)) {
                            higherPrioritySeverityIdx = severityCache[k].last;
                        }
                    }
                });
                if (higherPrioritySeverityIdx || higherPrioritySeverityIdx === 0) {
                    higherPrioritySeverityIdx += 1;
                } else {
                    higherPrioritySeverityIdx = 0;
                }
                severityCache[severity] = {};
                severityCache[severity].first = higherPrioritySeverityIdx;
                severityCache[severity].last = higherPrioritySeverityIdx;
            } else {
                console.error('updateSeverityCache failed for name: ' + name + ', id: ' + id + ', severity: ' + severity + ', delta: ' + delta);
            }
        }

        Object.keys(SEVERITY_TYPES).forEach(k => {
            if (severityCache.hasOwnProperty(k) && SEVERITY_TYPES[k] < severityPriority) {
                severityCache[k].first += delta;
                severityCache[k].last += delta;
            }
        });
    }

    /**
     * Retrieves the index for a given severity type within the cached alerts.
     * This index is used to determine the insertion point for new alerts to maintain order.
     * @param {string} name - The name of the model.
     * @param {string|null} [id=null] - The ID of the alert (optional).
     * @param {string} severity - The severity type (e.g., 'Severity_INFO').
     * @returns {number} The calculated index for the severity.
     */
    static getSeverityIndex(name, id = null, severity) {
        const severityCache = AlertCache.getSeverityCache(name, id);
        if (severityCache.hasOwnProperty(severity)) {
            return severityCache[severity].first;
        } else {
            const severityPriority = SEVERITY_TYPES[severity];
            let lowerPrioritySeverityIdx;
            Object.keys(SEVERITY_TYPES).some(k => {
                if (SEVERITY_TYPES[k] < severityPriority) {
                    if (severityCache.hasOwnProperty(k) && (severityCache[k].first || severityCache[k].first === 0)) {
                        lowerPrioritySeverityIdx = severityCache[k].first;
                        return true;
                    }
                }
                return false; // Added return for some function
            });
            if (lowerPrioritySeverityIdx || lowerPrioritySeverityIdx === 0) {
                return lowerPrioritySeverityIdx;
            }
            let higherPrioritySeverityIdx;
            Object.keys(SEVERITY_TYPES).some(k => {
                if (SEVERITY_TYPES[k] > severityPriority) {
                    if (severityCache.hasOwnProperty(k) && (severityCache[k].last || severityCache[k].last === 0)) {
                        higherPrioritySeverityIdx = severityCache[k].last;
                    }
                }
                return false; // Added return for some function
            });
            if (higherPrioritySeverityIdx || higherPrioritySeverityIdx === 0) {
                return higherPrioritySeverityIdx + 1;
            }
            return 0;
        }
    }
}