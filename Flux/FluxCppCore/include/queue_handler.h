#pragma once

#include <condition_variable>
#include <queue>
#include <mutex>

namespace FluxCppCore {

    enum QueueStatus
    {
        DATA_CONSUMED,
        TIMEOUT,
        SPURIOUS_WAKEUP

    };


    template <class T> struct Monitor
    {
        void push(const T& data)
        {
            {
                std::unique_lock<std::mutex> lock(mutex_);
                queue_.push(data);
            }
            condition_.notify_one(); // Notify all waiting threads
        }

        void push(T&& data)
        {
            {
                std::unique_lock<std::mutex> lock(mutex_);
                queue_.push(std::move(data));
            }
            condition_.notify_one(); // Notify all waiting threads
        }

        size_t size()
        {
            std::unique_lock<std::mutex> lock(mutex_);
            return queue_.size();
        }

        QueueStatus pop(T& val, std::chrono::milliseconds timeout = std::chrono::seconds(300))
        {
            std::unique_lock<std::mutex> lock(mutex_);
            while (queue_.empty()) // Loop to handle spurious wakeups
            {
                if (condition_.wait_for(lock, timeout) == std::cv_status::timeout)
                {
                    return QueueStatus::TIMEOUT;
                }
            }

            if (!queue_.empty())
            {
                val = std::move(queue_.front());
                queue_.pop();
                return QueueStatus::DATA_CONSUMED;
            }
            return QueueStatus::SPURIOUS_WAKEUP;
        }

    private:
        std::queue<T> queue_;
        std::mutex mutex_;
        std::condition_variable condition_;
    };
}


