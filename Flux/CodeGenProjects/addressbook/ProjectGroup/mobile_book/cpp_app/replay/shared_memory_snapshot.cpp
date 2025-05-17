// g++ -std=c++20 -o shared_memory_manager shared_memory_snapshot.cpp -lpthread -I../../../../../../FluxCppCore/include/


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

#include "../include/shm_symbol_cache.h"
#include "../include/md_utility_functions.h"


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
    if (argc != 4) {
        std::cout << "Usage: " << argv[0] << " no. of level(1, 5, 10, 15, 20), /street_book_1_shm /street_book_1_sem\n";
        return 0;
    }

    int level = std::stoi(argv[1]);
    std::cout << level << "\n";
    if (level != 1 && level != 5 && level != 10 && level != 15 && level != 20) {
        std::cout << "Invalid level provided. Supported levels are 1, 5, 10, 15, 20.\n";
        throw std::runtime_error("Invalid level provided. Supported levels are 1, 5, 10, 15, 20.\n");
        return 0;
    }

    std::string shm_name = argv[2];
    std::string sem_name = argv[3];

    try {
        switch (level) {
            case 1: {
                SharedMemoryManager<ShmSymbolCache<1>> shmManager(shm_name, sem_name);
                while (1) {
                    std::cout << "------------------------------------ S N A P S H O T ------------------------------------\n";
                    auto shm_cache =shmManager.read_from_shared_memory();
                    std::cout << mobile_book_handler::shm_snapshot(shm_cache);
                }
                break;
            }
            case 5: {
                SharedMemoryManager<ShmSymbolCache<5>> shmManager(shm_name, sem_name);
                while (1) {
                    std::cout << "------------------------------------ S N A P S H O T ------------------------------------\n";
                    auto shm_cache =shmManager.read_from_shared_memory();
                    std::cout << mobile_book_handler::shm_snapshot(shm_cache);
                }
                break;
            }
            case 10: {
                SharedMemoryManager<ShmSymbolCache<10>> shmManager(shm_name, sem_name);
                while (1) {
                    std::cout << "------------------------------------ S N A P S H O T ------------------------------------\n";
                    auto shm_cache =shmManager.read_from_shared_memory();
                    std::cout << mobile_book_handler::shm_snapshot(shm_cache);
                }
                break;
            }
            case 15: {
                SharedMemoryManager<ShmSymbolCache<15>> shmManager(shm_name, sem_name);
                while (1) {
                    std::cout << "------------------------------------ S N A P S H O T ------------------------------------\n";
                    auto shm_cache =shmManager.read_from_shared_memory();
                    std::cout << mobile_book_handler::shm_snapshot(shm_cache);
                }
                break;
            }
            case 20: {
                SharedMemoryManager<ShmSymbolCache<20>> shmManager(shm_name, sem_name);
                while (1) {
                    std::cout << "------------------------------------ S N A P S H O T ------------------------------------\n";
                    auto shm_cache =shmManager.read_from_shared_memory();
                    std::cout << mobile_book_handler::shm_snapshot(shm_cache);
                }
                break;
            }
            default:
                throw std::runtime_error("Invalid level provided. Supported levels are 1, 5, 10, 15, 20.\n");
        }
    } catch (const std::exception& ex) {
        std::cerr << ex.what() << std::endl;
        return 1;
    }
}


