
#include <Python.h>
#include <iostream>
#include <thread>
#include <chrono>

class TopOfBook {};
class LastTrade {};

class MarketDataService
{
public:
    MarketDataService(TopOfBook &top_of_book, LastTrade& last_trade) : t_(top_of_book), l_(last_trade) {}
    void process_last_trade() {/*relevent code*/}   // locks and unlocks gil internally in recursive calls for instance while updating pycache
    void process_top() {/*relevent code*/}          // locks and unlocks gil internally in recursive calls for instance while updating pycache


    void replay()
    {
        // creat thread and pass process_last_trade() as thread function
        // creat thread and pass process_top() as thread function
        // detatch threads
        // it suppose to call python specific code but to keep minimal i am not calling any python code
        return;
    }

protected:
    TopOfBook& t_;
    LastTrade& l_;
};

void launch()
{
    PyEval_InitThreads(); // locks GIL
    std::thread launcher_impl {[]() {

        // create  TopOfBook, LastTradeHandler objects
        // create MarketDataService object and pass TopOfBook and LastTradeHandler references
        TopOfBook top_book;
        LastTrade last_trade;
        MarketDataService mds {top_book, last_trade};
        mds.replay();	  // will creates further threads
    }};

    launcher_impl.detach(); // must detatch because the control has to be raturned to main/()py main()
    PyEval_ReleaseLock(); // as per documents it has to be callede why? because pyeval_initthreads() locks gil.
    std::cout << __func__ << ":" << __LINE__ << std::endl;
    // but we observed that if we call this it creats sev fault
    // but if we coment out pyeval_releselock() it works. but we are not sure if this(i.e commenting out) could lead to any other issues as we are not releasing gil.
}

int main()   // this will be def main():
{
    Py_Initialize(); // init python interpreter

    std::thread launch_thread(launch);
    std::cout << __func__ << ":" << __LINE__ << std::endl;
    while(1) {
        sleep(1);
    }
    launch_thread.join();

    // the control returns here for other processing.
}
