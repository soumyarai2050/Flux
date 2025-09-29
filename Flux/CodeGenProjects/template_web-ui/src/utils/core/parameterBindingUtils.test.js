/**
 * @module parameterBindingUtils.test
 * @description Test suite for parameter binding utilities used with FluxFldQueryParamBind.
 */

import {
    createAutoBoundParams,
    getEditableParams,
    mergeQueryParams,
    validateRequiredParams,
    getParameterBindingSummary
} from './parameterBindingUtils';

describe('Parameter Binding Utils', () => {
    describe('createAutoBoundParams', () => {
        it('should create auto-bound parameters from schema and current data', () => {
            const schema = {
                properties: {
                    id: { query_param_bind: "order_id", type: "string" },
                    user_id: { query_param_bind: "user_id", type: "string" },
                    symbol: { type: "string" }  // No binding
                }
            };
            const currentData = {
                id: "ORDER_123",
                user_id: "USER_456",
                symbol: "AAPL"
            };

            const result = createAutoBoundParams(schema, currentData);

            expect(result).toEqual({
                order_id: "ORDER_123",
                user_id: "USER_456"
                // symbol should not be included since it has no query_param_bind
            });
        });

        it('should handle missing or null data', () => {
            const schema = {
                properties: {
                    id: { query_param_bind: "order_id", type: "string" },
                    missing_field: { query_param_bind: "missing_param", type: "string" }
                }
            };
            const currentData = {
                id: "ORDER_123",
                other_field: "value"
            };

            const result = createAutoBoundParams(schema, currentData);

            expect(result).toEqual({
                order_id: "ORDER_123"
                // missing_param should not be included since missing_field is undefined
            });
        });

        it('should return empty object for invalid inputs', () => {
            expect(createAutoBoundParams(null, {})).toEqual({});
            expect(createAutoBoundParams({}, null)).toEqual({});
            expect(createAutoBoundParams(undefined, {})).toEqual({});
        });
    });

    describe('getEditableParams', () => {
        it('should filter out auto-bound parameters', () => {
            const queryParams = [
                { QueryParamName: "order_id", QueryParamDataType: "str" },
                { QueryParamName: "user_id", QueryParamDataType: "str" },
                { QueryParamName: "reason", QueryParamDataType: "str" }
            ];
            const autoBoundParams = {
                order_id: "ORDER_123",
                user_id: "USER_456"
            };

            const result = getEditableParams(queryParams, autoBoundParams);

            expect(result).toEqual({
                reason: { type: "str" }
            });
        });

        it('should return all parameters when none are auto-bound', () => {
            const queryParams = [
                { QueryParamName: "reason", QueryParamDataType: "str" },
                { QueryParamName: "priority", QueryParamDataType: "int" }
            ];
            const autoBoundParams = {};

            const result = getEditableParams(queryParams, autoBoundParams);

            expect(result).toEqual({
                reason: { type: "str" },
                priority: { type: "int" }
            });
        });

        it('should handle empty inputs', () => {
            expect(getEditableParams([], {})).toEqual({});
            expect(getEditableParams(undefined, {})).toEqual({});
        });
    });

    describe('mergeQueryParams', () => {
        it('should merge auto-bound and user parameters', () => {
            const autoBoundParams = {
                order_id: "ORDER_123",
                user_id: "USER_456"
            };
            const userParams = {
                reason: "Customer request",
                priority: "high"
            };

            const result = mergeQueryParams(autoBoundParams, userParams);

            expect(result).toEqual({
                order_id: "ORDER_123",
                user_id: "USER_456",
                reason: "Customer request",
                priority: "high"
            });
        });

        it('should allow user params to override auto-bound params', () => {
            const autoBoundParams = {
                order_id: "ORDER_123",
                status: "pending"
            };
            const userParams = {
                order_id: "ORDER_456",  // Override
                reason: "Manual override"
            };

            const result = mergeQueryParams(autoBoundParams, userParams);

            expect(result).toEqual({
                order_id: "ORDER_456",  // User value takes precedence
                status: "pending",
                reason: "Manual override"
            });
        });

        it('should handle empty inputs', () => {
            expect(mergeQueryParams({}, {})).toEqual({});
            expect(mergeQueryParams({ a: 1 }, {})).toEqual({ a: 1 });
            expect(mergeQueryParams({}, { b: 2 })).toEqual({ b: 2 });
        });
    });

    describe('validateRequiredParams', () => {
        it('should validate that all required params are present', () => {
            const requiredParams = ["order_id", "user_id", "reason"];
            const finalParams = {
                order_id: "ORDER_123",
                user_id: "USER_456",
                reason: "Customer request"
            };

            const result = validateRequiredParams(requiredParams, finalParams);

            expect(result).toEqual({
                isValid: true,
                missingParams: []
            });
        });

        it('should detect missing required params', () => {
            const requiredParams = ["order_id", "user_id", "reason"];
            const finalParams = {
                order_id: "ORDER_123"
                // user_id and reason are missing
            };

            const result = validateRequiredParams(requiredParams, finalParams);

            expect(result).toEqual({
                isValid: false,
                missingParams: ["user_id", "reason"]
            });
        });

        it('should consider empty strings as missing', () => {
            const requiredParams = ["order_id", "reason"];
            const finalParams = {
                order_id: "ORDER_123",
                reason: ""
            };

            const result = validateRequiredParams(requiredParams, finalParams);

            expect(result).toEqual({
                isValid: false,
                missingParams: ["reason"]
            });
        });
    });

    describe('getParameterBindingSummary', () => {
        it('should provide a summary of parameter binding', () => {
            const autoBoundParams = {
                order_id: "ORDER_123",
                user_id: "USER_456"
            };
            const userParams = {
                reason: "Customer request"
            };
            const schema = {
                properties: {
                    id: { query_param_bind: "order_id", type: "string" },
                    user_id: { query_param_bind: "user_id", type: "string" },
                    reason: { type: "string" }
                }
            };

            const result = getParameterBindingSummary(autoBoundParams, userParams, schema);

            expect(result).toEqual({
                autoBound: [
                    { paramName: "order_id", value: "ORDER_123", sourceField: "id" },
                    { paramName: "user_id", value: "USER_456", sourceField: "user_id" }
                ],
                userProvided: [
                    { paramName: "reason", value: "Customer request" }
                ],
                total: 3
            });
        });
    });
});

// Example usage scenarios for documentation
describe('Integration Examples', () => {
    it('should handle a complete TradeOrder scenario', () => {
        // Example proto definition:
        // message TradeOrder {
        //   option (FluxMsgButtonQuery) = {
        //     query_data: {
        //       QueryName: "cancel_order",
        //       QueryParams: [
        //         { QueryParamName: "order_id", QueryParamDataType: "str" },
        //         { QueryParamName: "user_id", QueryParamDataType: "str" },
        //         { QueryParamName: "reason", QueryParamDataType: "str" }
        //       ]
        //     }
        //   };
        //   required string id = 1 [(FluxFldQueryParamBind) = "order_id"];
        //   required string user_id = 2 [(FluxFldQueryParamBind) = "user_id"];
        //   required string symbol = 3;
        // }

        const schema = {
            properties: {
                id: { query_param_bind: "order_id", type: "string" },
                user_id: { query_param_bind: "user_id", type: "string" },
                symbol: { type: "string" }
            }
        };

        const currentTradeOrder = {
            id: "ORDER_123",
            user_id: "USER_456",
            symbol: "AAPL"
        };

        const queryParams = [
            { QueryParamName: "order_id", QueryParamDataType: "str" },
            { QueryParamName: "user_id", QueryParamDataType: "str" },
            { QueryParamName: "reason", QueryParamDataType: "str" }
        ];

        // Step 1: Create auto-bound parameters
        const autoBoundParams = createAutoBoundParams(schema, currentTradeOrder);
        expect(autoBoundParams).toEqual({
            order_id: "ORDER_123",
            user_id: "USER_456"
        });

        // Step 2: Get editable parameters (only reason should be shown to user)
        const editableParams = getEditableParams(queryParams, autoBoundParams);
        expect(editableParams).toEqual({
            reason: { type: "str" }
        });

        // Step 3: User provides only the reason
        const userInput = { reason: "Customer requested cancellation" };

        // Step 4: Merge for final execution
        const finalParams = mergeQueryParams(autoBoundParams, userInput);
        expect(finalParams).toEqual({
            order_id: "ORDER_123",
            user_id: "USER_456",
            reason: "Customer requested cancellation"
        });

        // Result: User only had to input "reason", order_id and user_id were auto-filled
        expect(Object.keys(editableParams)).toHaveLength(1);
        expect(Object.keys(finalParams)).toHaveLength(3);
    });
});