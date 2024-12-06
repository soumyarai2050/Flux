#pragma once

#include "md_container.h"

template<size_t N>
struct ShmSymbolCache {
    MDContainer<N> m_leg_1_data_shm_cache_;
    MDContainer<N> m_leg_2_data_shm_cache_;

    [[nodiscard]] bool is_data_set() const {
        return m_leg_2_data_shm_cache_.update_counter != 0 || m_leg_1_data_shm_cache_.update_counter!= 0;
    }
};

