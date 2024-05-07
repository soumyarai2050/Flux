from pendulum import DateTime
from threading import Thread
from ctypes import CDLL
from pathlib import PurePath

so_file_path = PurePath(__file__).parent.parent / "data" / "libmain.so"
interpreter_handler = CDLL(str(so_file_path))


def cpu_intensive_task():
    for _ in range(200000000):
        pass


strat_time = DateTime.utcnow()
t1 = Thread(target=cpu_intensive_task)
t2 = Thread(target=cpu_intensive_task)
t3 = Thread(target=cpu_intensive_task)
t1.start()
t2.start()
t3.start()
t1.join()
t2.join()
t3.join()
end_time = DateTime.utcnow()

elapsed_time = (end_time - strat_time).total_seconds()
print("Time Taken by Threads =", elapsed_time)


def cpu_intensive_task_wrapper():
    interpreter_handler.initialize_new_interpreter()
    cpu_intensive_task()
    interpreter_handler.end_interpreter()


strat_time = DateTime.utcnow()
t1 = Thread(target=cpu_intensive_task_wrapper)
t2 = Thread(target=cpu_intensive_task_wrapper)
t3 = Thread(target=cpu_intensive_task_wrapper)
t1.start()
t2.start()
t3.start()
t1.join()
t2.join()
t3.join()
end_time = DateTime.utcnow()

elapsed_time = (end_time - strat_time).total_seconds()
print("Time Taken by Interpreters =", elapsed_time)
