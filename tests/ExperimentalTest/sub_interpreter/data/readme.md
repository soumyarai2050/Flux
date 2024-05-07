# Sub-Interpreter Sample impl

### Dirs:
* cpp: holds all cpp related files
* py: holds python files
* data: contains so file and readme file

```
command used to create so file:
- g++ -std=c++17 -fPIC -c main.cpp -I/usr/include/python3.12/
- g++ -shared -o libmain.so main.o -L/lib/x86_64-linux-gnu/ -lpython3.12
```

## Run:
Move to py directory and run `python sub_interpreter_sample.py`

note: run this with python3.12 and avoid using env(s) like anaconda, since so file fails with env(s)

