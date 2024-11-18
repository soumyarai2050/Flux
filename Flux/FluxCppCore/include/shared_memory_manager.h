/*
 * This code defines a template class `SharedMemoryManager` for managing shared memory and synchronization between
 * processes using POSIX shared memory and semaphores. The class provides methods to write to and read
 * from shared memory while ensuring thread safety with a mutex. It handles the creation, mapping,
 * and cleanup of shared memory and semaphores, as well as error handling for various operations.
 * The shared memory structure includes a mutex and a data field of type T.
 */

#pragma once

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

#include "binary_file_writer.h"

constexpr mode_t SHM_PERMISSIONS = 0666; // Permissions for shared memory

template<typename T>
class SharedMemoryManager {
public:
    // Constructor to initialize shared memory and semaphore
    explicit SharedMemoryManager(const std::string& shm_name, const std::string& sem_name,
        const std::string& r_binary_file_)
    : m_shm_name_(shm_name), m_sem_name_(sem_name), m_binary_file_(r_binary_file_),
    m_binary_file_writer_(m_binary_file_),
    m_shm_size_(sizeof(ShmStruct)) {

        // Open shared memory
        m_shm_fd_ = shm_open(m_shm_name_.c_str(), O_RDWR, SHM_PERMISSIONS);
        if (m_shm_fd_ < 0) {
            m_shm_already_exists_ = false;
            m_shm_fd_ = shm_open(m_shm_name_.c_str(), O_CREAT | O_RDWR, SHM_PERMISSIONS);
            if (m_shm_fd_ < 0) {
                throw std::runtime_error(std::format("Error opening shared memory: {}, shared memory name: {}",
                    strerror(errno), m_shm_name_));
            }
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

        if (m_shm_already_exists_) {
            m_shm_data_->shm_update_signature = 0;
            for (size_t i = 0; i < 5; ++i) {
                sem_post(mp_sem_);
                sleep(1);
            }
            initialize_mutex();
        } else {
            // Initialize mutex attributes
            initialize_mutex();
        }
    }

    // Destructor to clean up resources
    ~SharedMemoryManager() {
        pthread_mutex_destroy(&m_shm_data_->mutex); // Destroy mutex
        munmap(m_shm_data_, m_shm_size_); // Unmap shared memory
        sem_close(mp_sem_); // Close semaphore
        sem_unlink(m_sem_name_.c_str()); // Unlink semaphore
        shm_unlink(m_shm_name_.c_str()); // Unlink shared memory
    }

    // Write data to shared memory
    void write_to_shared_memory(const T& new_data) {
        if (try_lock()) {  // Attempt to acquire the lock without blocking
            std::memcpy(&m_shm_data_->data, &new_data, sizeof(T)); // Copy data to shared memory
            if(!m_shm_signature_set){
                auto signature = new_data.is_data_set() ? k_shm_signature : 0;
                m_shm_data_->shm_update_signature = signature;
                m_shm_signature_set = signature == k_shm_signature ? true : false;
            }
            unlock(); // Release the lock
            sem_post(mp_sem_); // Signal that data is available
            m_binary_file_writer_.write(m_shm_data_->data);
        } else {
            LOG_DEBUG_IMPL(GetCppAppLogger(), "Skipping write as shared memory is locked by another process.");
        }
    }

    // Read data from shared memory
    T read_from_shared_memory() {
        sem_wait(mp_sem_); // Wait for data to be available
        lock(); // Acquire the lock
        T data_copy = m_shm_data_->data; // Copy data from shared memory
        unlock(); // Release the lock
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
    std::string m_binary_file_;
    BinaryFileWriter m_binary_file_writer_;
    size_t m_shm_size_; // Size of the shared memory
    // control variable helps set shm_signature if found false during a shm write, reader will not read shm until sig is set
    bool m_shm_signature_set = false;
    const uint64_t k_shm_signature = 0xFAFAFAFAFAFAFAFA;
    bool m_shm_already_exists_ = true;
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

    void initialize_mutex() {
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
};
