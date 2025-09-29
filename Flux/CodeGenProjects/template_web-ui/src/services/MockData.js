// Mock table schemas
export const NODE_DATA_SCHEMAS = {
    "strat_collection": {
        columns: [
            { name: "_id", type: "number", primary: true },
            { name: "loaded_strat_keys", type: "array" },
            { name: "buffered_strat_keys", type: "array" }
        ],
        sample_data: [
            
        ]
    },
    "pair_strat": {
        columns: [
            { name: "strat_mode", type: "enum", primary: false },
            { name: "strat_type", type: "enum", primary: false },
            { name: "strat_leg1", type: "object", primary: false },
            { name: "strat_leg2", type: "object", primary: false },
            { name: "common_premium", type: "number", primary: false },
            { name: "hedge_ratio", type: "number", primary: false },
            { name: "mstrat", type: "string", primary: false }
        ],
        sample_data: [
          
        ]
    },
    "order_journal": {
        columns: [
            { name: "_id", type: "number", primary: true },
            { name: "order", type: "object", primary: false },
            { name: "order_event_date_time", type: "date-time", primary: false },
            { name: "order_event", type: "enum", primary: false },
            { name: "current_period_order_count", type: "number", primary: false }
        ],
        sample_data: [
            
        ]
    },
    "order_limits": {
        columns: [
            { name: "_id", type: "number", primary: true },
            { name: "order", type: "object", primary: false },
            { name: "order_event_date_time", type: "date-time", primary: false },
            { name: "order_event", type: "enum", primary: false },
            { name: "current_period_order_count", type: "number", primary: false }
        ],
        sample_data: [
            
        ]
    },
    "portfolio_limits": {
        columns: [
            { name: "_id", type: "number", primary: true },
            { name: "order", type: "object", primary: false },
            { name: "order_event_date_time", type: "date-time", primary: false },
            { name: "order_event", type: "enum", primary: false },
            { name: "current_period_order_count", type: "number", primary: false }
        ],
        sample_data: [
            
        ]
    },
    "strat_limits":{
         columns: [
            { name: "_id", type: "number", primary: true },
            { name: "strat_order", type: "object", primary: false },
            { name: "strat_event_date_time", type: "date-time", primary: false },
            { name: "strat_event", type: "enum", primary: false },
            { name: "current_period_order_count", type: "number", primary: false }
        ],
        sample_data: [
            
        ]

    },
    "strat_status":{
            columns: [
            { name: "_id", type: "number", primary: true },
            { name: "stats_thing", type: "object", primary: false },
            { name: "status_event_date_time", type: "date-time", primary: false },
            { name: "strat_event", type: "enum", primary: false },
            { name: "current_period_order_count", type: "number", primary: false }
        ],
        sample_data: [
            
        ]

    }
};

export const DUMMY_CHART_DATA =  [
    [
        {
            "_id": 1,
            "chart_data": {
                "_id": "68cd288d8caac588d6982cf3",
                "chart_name": "FX-1",
                "time_series": false,
                "filters": [],
                "partition_fld": null,
                "series": [
                    {
                        "_id": "68cd288d8caac588d6982cf2",
                        "type": "line",
                        "encode": {
                            "x": "limit_dn_px",
                            "y": "closing_px"
                        },
                        "stack": false,
                        "y_min": null,
                        "y_max": null
                    }
                ]
            },
            "source_model_name": "fx_symbol_overview",
            "source_model_base_url": "http://127.0.0.1:8020/pair_strat_engine"
        },
        {
            "_id": "68cd288d8caac588d6982cf5",
            "chart_name": "FX-2",
            "time_series": false,
            "filters": [],
            "partition_fld": null,
            "series": [
                {
                    "_id": "68cd288d8caac588d6982cf4",
                    "type": "bar",
                    "encode": {
                        "x": "open_px",
                        "y": "conv_px"
                    },
                    "stack": false,
                    "y_min": null,
                    "y_max": null
                }
            ]
        }
    ],
    [
        {
            "_id": "68cd292e8caac588d6982cf7",
            "chart_name": "PL-1",
            "time_series": false,
            "filters": [],
            "partition_fld": null,
            "series": [
                {
                    "_id": "68cd292e8caac588d6982cf6",
                    "type": "scatter",
                    "encode": {
                        "x": "alert_count",
                        "y": "alert_meta"
                    },
                    "stack": false,
                    "y_min": null,
                    "y_max": null
                }
            ]
        }
    ]
];