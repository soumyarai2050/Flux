
#include <iostream>
#include <cstring>
#include <iomanip>
#include <chrono>
#include <sys/mman.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <semaphore.h>
#include <cerrno>
#include <format>
#include <stdexcept>
#include "mobile_book_shared_memory_data_structure.h"

// #define SHM_NAME "/my_shm"
// #define SEM_NAME "/my_sem"

inline void format_data(MobileBookShmCache const& cache, std::vector<char>& buffer) {
    // std::format_to(std::back_inserter(buffer), "{:*^40}\n{:5} {:10.5f}  {:10.5f} {:5}\n", "GOOG", 1202, 22.86, 22.9, 1386);

    std::format_to(std::back_inserter(buffer), "{:*^40}\n", std::string_view(cache.symbol_));

    std::format_to(std::back_inserter(buffer), "Last Barter: {} {}@{} CumQty: {} ExchTs: {} ArrTs: {}\n\n",
        std::string_view(cache.last_barter_.symbol_n_exch_id_.symbol_), cache.last_barter_.qty_, cache.last_barter_.px_,
        cache.last_barter_.market_barter_volume_.participation_period_last_barter_qty_sum_, cache.last_barter_.exch_time_,
        cache.last_barter_.arrival_time_);

    const auto top_bid_qty = (int)cache.top_of_book_.bid_quote_.qty_; // cache.top_of_book_.is_bid_quote_set_ ? cache.top_of_book_.bid_quote_.qty_ : 0;
    const auto top_bid_px = (float)cache.top_of_book_.bid_quote_.px_; //cache.top_of_book_.is_bid_quote_set_? cache.top_of_book_.bid_quote_.px_ : 0;

    const auto top_ask_qty = (int)cache.top_of_book_.ask_quote_.qty_; //cache.top_of_book_.is_ask_quote_set_? cache.top_of_book_.ask_quote_.qty_ : 0;
    const auto top_ask_px = (float)cache.top_of_book_.ask_quote_.px_; //cache.top_of_book_.is_ask_quote_set_? cache.top_of_book_.ask_quote_.px_ : 0;

    const auto last_barter_qty = (int)cache.top_of_book_.last_barter_.qty_; //cache.last_barter_.is_qty_set_? cache.last_barter_.qty
    const auto last_barter_px = (float)cache.top_of_book_.last_barter_.px_; //cache.last_barter_.is_px_set_? cache.last_barter_.px_ : 0;

    std::format_to(std::back_inserter(buffer), "Top of Book: {:6} {:10.5f}  {:10.5f} {:6}\n", top_bid_qty, top_bid_px, top_ask_px, top_ask_qty );
    std::format_to(std::back_inserter(buffer), "Last Price: {}@{} cumQty: {} updateTs: {}\n\n", last_barter_px, last_barter_qty,
        "Not Set", cache.top_of_book_.last_barter_.last_update_date_time_);

    std::format_to(std::back_inserter(buffer), "{:*^40}\n", "Market Depth");
    for (size_t i{0}; i < MARKET_DEPTH_LEVEL; ++i) {
        const auto& bid = cache.bid_market_depths_[i];
        const auto& ask = cache.ask_market_depths_[i];
        auto bid_qty = bid.qty_ ; //bid.is_qty_set_ ? bid.qty_ : 0;
        auto bid_px = bid.px_; //bid.is_px_set_? bid.px_ : 0;

        auto ask_qty = ask.qty_; //ask.is_qty_set_? ask.qty_ : 0;
        auto ask_px = ask.px_; // ask.is_px_set_? ask.px_ : 0;

        std::format_to(std::back_inserter(buffer), "{:6} {:10.5f}  {:10.5f} {:6}\n", bid_qty, bid_px, ask_px, ask_qty);
    }
}


constexpr mode_t SHM_PERMISSIONS = 0666; // Permissions for shared memory

template<typename T>
class SharedMemoryManager {
public:
    // Constructor to initialize shared memory and semaphore
    explicit SharedMemoryManager(const std::string& shm_name, const std::string& sem_name)
        : m_shm_name_(shm_name), m_sem_name_(sem_name), m_shm_size_(sizeof(ShmStruct)) {

        // Open shared memory
        m_shm_fd_ = shm_open(m_shm_name_.c_str(), O_RDWR, SHM_PERMISSIONS);
        if (m_shm_fd_ < 0) {
            throw std::runtime_error(std::format("Error opening shared memory: {}, shared memory name: {}",
                strerror(errno), m_shm_name_));
        }

        // Map shared memory
        ptr_ = mmap(nullptr, m_shm_size_, PROT_READ | PROT_WRITE, MAP_SHARED, m_shm_fd_, 0);
        if (m_shm_data_ == MAP_FAILED) {
            throw std::runtime_error(std::format("Error mapping shared memory: {}, shared memory name: {}",
                strerror(errno), m_shm_name_));
        }

        m_shm_data_ = new (ptr_) ShmStruct;

        // Initialize mutex attributes
        pthread_mutexattr_t mutex_attr;
        pthread_mutexattr_init(&mutex_attr);
        pthread_mutexattr_setpshared(&mutex_attr, PTHREAD_PROCESS_SHARED);

        // Initialize mutex
        if (pthread_mutex_init(&m_shm_data_->mutex, &mutex_attr) != 0) {
            throw std::runtime_error(std::format("Error initializing mutex: {}, shm name: {}, sem name: {}",
                strerror(errno), m_shm_name_, m_sem_name_));
        }
    }
    struct LockGuard {
        LockGuard(SharedMemoryManager* manager) : manager_(manager) {
            manager_->lock();
        }

        ~LockGuard() {
            manager_->unlock();
        }
        SharedMemoryManager* manager_;
    };
    // Read data from shared memory
    T read_from_shared_memory() {
        LockGuard lock(this);
        T data_copy = m_shm_data_->data; // Copy data from shared memory
        return data_copy; // Return the copied data
    }

protected:
    // Structure to hold shared memory data and mutex
    struct ShmStruct {
        uint64_t shm_update_signature;
        pthread_mutex_t mutex;
        T data;
    };

    std::string m_shm_name_; // Name of the shared memory
    std::string m_sem_name_; // Name of the semaphore
    size_t m_shm_size_; // Size of the shared memory
    // control variable helps set shm_signature if found false during a shm write, reader will not read shm until sig is set
    bool m_shm_signature_set = false;
    const uint64_t k_shm_signature = 0xFAFAFAFAFAFAFAFA;
    int m_shm_fd_; // File descriptor for shared memory
    void* ptr_;
    ShmStruct* m_shm_data_; // Pointer to shared memory data
    sem_t* mp_sem_; // Pointer to semaphore

    // Lock the mutex
    int lock() {
        if (pthread_mutex_lock(&m_shm_data_->mutex) != 0) {
            std::cerr << "Error locking mutex: " << strerror(errno) << '\n';
            throw std::runtime_error("Error locking mutex!");
        }
        return 0;
    }

    // Unlock the mutex
    void unlock() {
        pthread_mutex_unlock(&m_shm_data_->mutex);
    }

    // Attempt to lock the mutex without blocking
    bool try_lock() {
        return pthread_mutex_trylock(&m_shm_data_->mutex) == 0; // Return true if lock was acquired
    }
};


int main(int argc, char* argv[]) {
    if (argc != 3) {
        std::cout << "Usage: " << argv[0] << " /street_book_1_shm /street_book_1_sem\n";
        return 0;
    }

    try {
        SharedMemoryManager<ShmSymbolCache> shmManager(argv[1], argv[2]);

        while (1) {
        //     // Read data from shared memory
            std::cout << "------------------------------------ S N A P S H O T ------------------------------------\n";
            auto d =shmManager.read_from_shared_memory();
            std::vector<char> buffer;
            format_data(d.m_leg_1_data_shm_cache_, buffer);
            std::cout << std::string_view{buffer.begin(), buffer.end()} << '\n';
            buffer.clear();
            std::cout << "------------------------------------ LEG 2 ------------------------------------\n";
            format_data(d.m_leg_2_data_shm_cache_, buffer);
            std::cout << std::string_view{buffer.begin(), buffer.end()} << '\n';
        }

    } catch (const std::exception& ex) {
        std::cerr << ex.what() << std::endl;
        return 1;
    }
}


