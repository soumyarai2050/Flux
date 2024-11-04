

#include <iostream>
#include <fstream>
#include <sys/mman.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <pthread.h>
#include <cstring>

const char* shm_name = "/my_shared_memory";

int main() {
    // Create shared memory
    int shm_fd = shm_open(shm_name, O_RDWR | O_CREAT, 0666);
    ftruncate(shm_fd, 1024);

    // Map shared memory
    void* shm_ptr = mmap(NULL, 1024, PROT_READ | PROT_WRITE, MAP_SHARED, shm_fd, 0);

    // Initialize mutex attributes
    pthread_mutexattr_t mutex_attr;
    pthread_mutexattr_init(&mutex_attr);
    pthread_mutexattr_setpshared(&mutex_attr, PTHREAD_PROCESS_SHARED);

    // Store mutex size
    int64_t* mutex_size = (int64_t*)shm_ptr;
    *mutex_size = sizeof(pthread_mutex_t);

    // Create mutex in shared memory
    pthread_mutex_t* mutex = new((char*)shm_ptr + sizeof(int64_t)) pthread_mutex_t;
    std::cout << mutex << "\n";
    pthread_mutex_init(mutex, &mutex_attr);
    pthread_mutexattr_destroy(&mutex_attr);

    // Lock mutex
    pthread_mutex_lock(mutex);

    // Critical section
    std::cout << "C++: Writing to shared memory..." << std::endl;
    char* data = (char*)shm_ptr + sizeof(pthread_mutex_t) + sizeof(int64_t);
    std::cout << ">>> " << data << std::endl;
    strcpy(data, "Hello from C++!");
    pthread_mutex_unlock(mutex);

    sleep(50);
    return 0;
}