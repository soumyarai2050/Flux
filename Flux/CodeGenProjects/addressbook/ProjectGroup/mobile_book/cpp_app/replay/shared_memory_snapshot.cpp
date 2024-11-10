
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

        // Set the size of shared memory
        if (ftruncate(m_shm_fd_, m_shm_size_) != 0) {
            shm_unlink(m_shm_name_.c_str()); // Cleanup on error
            throw std::runtime_error(std::format("Error truncating shared memory: {}, shared memory name: {}, size: {}",
                strerror(errno), m_shm_name_, m_shm_size_));
        }

        // Map shared memory
        ptr_ = mmap(nullptr, m_shm_size_, PROT_READ | PROT_WRITE, MAP_SHARED, m_shm_fd_, 0);
        if (m_shm_data_ == MAP_FAILED) {
            shm_unlink(m_shm_name_.c_str()); // Cleanup on error
            throw std::runtime_error(std::format("Error mapping shared memory: {}, shared memory name: {}",
                strerror(errno), m_shm_name_));
        }

        m_shm_data_ = new (ptr_) ShmStruct;

        // Open semaphore
        mp_sem_ = sem_open(m_sem_name_.c_str(), O_CREAT, SHM_PERMISSIONS, 0);
        if (mp_sem_ == SEM_FAILED) {
            munmap(m_shm_data_, m_shm_size_); // Cleanup on error
            shm_unlink(m_shm_name_.c_str());
            throw std::runtime_error(std::format("Error opening semaphore: {}, semaphore name: {}",
                strerror(errno), m_sem_name_));
        }

        // Initialize mutex attributes
        pthread_mutexattr_t mutex_attr;
        pthread_mutexattr_init(&mutex_attr);
        pthread_mutexattr_setpshared(&mutex_attr, PTHREAD_PROCESS_SHARED);

        // Initialize mutex
        if (pthread_mutex_init(&m_shm_data_->mutex, &mutex_attr) != 0) {
            munmap(m_shm_data_, m_shm_size_); // Cleanup on error
            shm_unlink(m_shm_name_.c_str());
            throw std::runtime_error(std::format("Error initializing mutex: {}, shm name: {}, sem name: {}",
                strerror(errno), m_shm_name_, m_sem_name_));
        }
    }

    // Destructor to clean up resources
    ~SharedMemoryManager() {
        pthread_mutex_destroy(&m_shm_data_->mutex); // Destroy mutex
        munmap(m_shm_data_, m_shm_size_); // Unmap shared memory
        sem_close(mp_sem_); // Close semaphore
        shm_unlink(m_shm_name_.c_str()); // Unlink shared memory
    }

    // Write data to shared memory
    void write_to_shared_memory(const T& new_data) {
        if (try_lock()) [[likely]] {  // Attempt to acquire the lock without blocking
            std::memcpy(&m_shm_data_->data, &new_data, sizeof(T)); // Copy data to shared memory
            if(!m_shm_signature_set) [[unlikely]] {
                auto signature = new_data.is_data_set() ? k_shm_signature : 0;
                m_shm_data_->shm_update_signature = signature;
                m_shm_signature_set = signature == k_shm_signature ? true : false;
            }
            unlock(); // Release the lock
            sem_post(mp_sem_); // Signal that data is available

        } else {
            std::cerr << "Error writing to shared memory, lock not found\n";
            // LOG_DEBUG_IMPL(GetCppAppLogger(), "Skipping write as shared memory is locked by another process.");
        }
    }

    // Read data from shared memory
    T read_from_shared_memory() {
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

        auto d =shmManager.read_from_shared_memory();
        d.m_leg_1_data_shm_cache_.print();
        sleep(50);
        std::cout << "Mutex unlocked, press any key to start cleaning up..." << std::endl;
        std::cin.get();
    } catch (const std::exception& ex) {
        std::cerr << ex.what() << std::endl;
        return 1;
    }

    std::cout << "Cleanup completed" << std::endl;
    return 0;
}


