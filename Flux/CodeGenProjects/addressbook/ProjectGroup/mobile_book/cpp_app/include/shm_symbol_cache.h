#pragma once

#include "md_container.h"

struct ShmSymbolCache {
    MDContainer m_leg_1_data_shm_cache_;
    MDContainer m_leg_2_data_shm_cache_;

    [[nodiscard]] bool is_data_set() const {
        return m_leg_2_data_shm_cache_.update_counter != 0 || m_leg_1_data_shm_cache_.update_counter!= 0;
    }
};

