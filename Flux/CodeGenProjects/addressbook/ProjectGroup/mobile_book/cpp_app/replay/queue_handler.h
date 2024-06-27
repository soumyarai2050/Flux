#pragma once

#include <condition_variable>
#include <functional>
#include <queue>
#include <iostream>
#include <mutex>
#include <thread>
#include "mobile_book_service.pb.h"


namespace mobile_book_handler {

    struct DataHandler {
        mobile_book::LastBarter m_last_barter_obj_;
		int i;
    };
}

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

    bool pop(T& val)
    {
        std::unique_lock<std::mutex> lock(m_);
        if(q_.empty()) {c_.wait(lock);}
        if(!q_.empty())
        {
            val = q_.front();
            q_.pop();
            return true;
        }
        return false;
    }
private:
    queue_t q_;
    mutable std::mutex m_;
    mutable std::condition_variable c_;
};

