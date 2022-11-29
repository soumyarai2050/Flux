import { NEW_ITEM_ID } from "./constants";

export const defaultItem = {
    'pair_strat.pair_strat_params.leg2_sec.sec_id': 'YYYY',
    'pair_strat.pair_strat_params.leg2_sec.sec_id': 'XXXX',
    'pair_strat.pair_strat_params.leg1_side': 'SIDE_UNSPECIFIED',
    'pair_strat._id': NEW_ITEM_ID
}

export function getLayout() {
    const layout = [
        { i: "strat_collection", x: 0, y: 0, w: 3, h: 13 },
        { i: "pair_strat_params", x: 3, y: 0, w: 7, h: 13 },
        { i: "strat_status", x: 0, y: 13, w: 10, h: 6 },
        { i: "strat_limits", x: 10, y: 0, w: 8, h: 3 },
        { i: "order_limits", x: 10, y: 3, w: 8, h: 3 },
        { i: "portfolio_limits", x: 10, y: 6, w: 8, h: 6 },
        { i: "portfolio_status", x: 10, y: 12, w: 8, h: 7 }
    ]
    return layout;
}
