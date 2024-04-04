## StreetBook

init_params: 
* bartering_data_manager: instance of bartering_data_manager
* strat_cache: instance of strat_cache

# important points:
* Each pair is having its own executor running in different thread - this thread 
  needs to be changed to each process
* thread replacement means we need process locks instead of thread locks
* executor + bartering_data_manager - one per pair
* beanie server running asynchronously on one thread
* Even if executors are running separately for each pair, 
  when calling server interfaces these processes needs 
  to be dependent on single threaded async executor

Important links:
* Async multiprocess module: 
  https://github.com/dano/aioprocessing
* To share resources between multiple processes:
  https://stackoverflow.com/questions/55004267/sharing-resources-between-python-processes
* 