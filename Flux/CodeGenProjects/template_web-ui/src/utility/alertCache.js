import { SEVERITY_TYPES } from '../constants';

export class AlertCache {
    static severityFirstNLastIdxDict = {};

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

    static setSeverityCache(name, id = null, severityCache) {
        if (id) {
            AlertCache.severityFirstNLastIdxDict[name][id] = severityCache;
        } else {
            AlertCache.severityFirstNLastIdxDict[name] = severityCache;
        }
    }

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
                })
                if (higherPrioritySeverityIdx || higherPrioritySeverityIdx === 0) {
                    higherPrioritySeverityIdx += 1;
                } else {
                    higherPrioritySeverityIdx = 0
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
        })
    }

    static getSeverityIndex(name, id = null, severity) {
        const severityCache = AlertCache.getSeverityCache(name, id);
        if (severityCache.hasOwnProperty(severity)) {
            return severityCache[severity].first;
        } else {
            const severityProirity = SEVERITY_TYPES[severity];
            let lowerPrioritySeverityIdx;
            Object.keys(SEVERITY_TYPES).some(k => {
                if (SEVERITY_TYPES[k] < severityProirity) {
                    if (severityCache.hasOwnProperty(k) && (severityCache[k].first || severityCache[k].first === 0)) {
                        lowerPrioritySeverityIdx = severityCache[k].first;
                        return true;
                    }
                }
            })
            if (lowerPrioritySeverityIdx || lowerPrioritySeverityIdx === 0) {
                return lowerPrioritySeverityIdx;
            }
            let higherPrioritySeverityIdx;
            Object.keys(SEVERITY_TYPES).some(k => {
                if (SEVERITY_TYPES[k] > severityProirity) {
                    if (severityCache.hasOwnProperty(k) && (severityCache[k].last || severityCache[k].last === 0)) {
                        higherPrioritySeverityIdx = severityCache[k].last;
                    }
                }
            })
            if (higherPrioritySeverityIdx || higherPrioritySeverityIdx === 0) {
                return higherPrioritySeverityIdx + 1;
            }
            return 0;
        }
    }
}