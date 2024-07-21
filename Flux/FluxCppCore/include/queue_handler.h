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
        typedef std::queue<T> queue_t;
        void push(const T& data)
        {
            std::unique_lock<std::mutex> lock(m_);
            q_.push(data);
            lock.unlock();
            c_.notify_all();
        }
        void push(T&& data)
        {
            std::unique_lock<std::mutex> lock(m_);
            q_.push(std::move(data));
            lock.unlock();
            c_.notify_all();
        }

        auto  size() {
            return q_.size();
        }

        QueueStatus pop(T& val)
        {
            std::unique_lock<std::mutex> lock(m_);
            if(q_.empty())
            {
                std::cv_status wakeup_status = c_.wait_for(lock, std::chrono::seconds(60));
                if (wakeup_status == std::cv_status::timeout) {return QueueStatus::TIMEOUT;}
            }
            if(!q_.empty())
            {
                val = q_.front();
                q_.pop();
                return QueueStatus::DATA_CONSUMED;
            }
            return QueueStatus::SPURIOUS_WAKEUP;
        }
    private:
        queue_t q_;
        mutable std::mutex m_;
        mutable std::condition_variable c_;
    };
}


