# standard imports
from libc.stdint cimport int64_t


cdef class SecurityC:
    cdef public str sec_id

cpdef enum SideC:
    BUY = 1,
    SELL = 2

cdef class StratLegC:
    cdef public SecurityC sec
    cdef public SideC side

cdef class PairStratParamsC:
    cdef public StratLegC strat_leg1
    cdef public StratLegC strat_leg2
    cdef public float hedge_ratio
    cdef public int64_t exch_response_max_seconds

cdef class PairStratCython:
    cdef public PairStratParamsC pair_strat_params
    cdef public object last_active_date_time