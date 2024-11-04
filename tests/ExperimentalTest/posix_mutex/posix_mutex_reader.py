
import mmap
import os
import struct
import ctypes
import threading

shm_name = "/dev/shm/my_shared_memory"

def main():
    # Open shared memory
    shm_fd = os.open(shm_name, os.O_RDWR)
    shm = mmap.mmap(shm_fd, 0, access=mmap.PROT_READ | mmap.PROT_WRITE)

    # Read mutex size from shared memory
    mutex_size = struct.unpack('q', shm.read(8))[0]

    # Get mutex from shared memory
    mutex_ptr = ctypes.c_void_p(ctypes.addressof(ctypes.c_int64.from_buffer(shm)))
    lib = ctypes.CDLL('libpthread.so.0')

    # Lock mutex
    lib.pthread_mutex_lock(mutex_ptr)

    # Critical section
    print("Python: Reading from shared memory...")
    data = shm.read(1024)[mutex_size + 4:]
    print(data.decode())

    # Unlock mutex
    lib.pthread_mutex_unlock(mutex_ptr)

    shm.close()
    os.close(shm_fd)

if __name__ == "__main__":
    main()