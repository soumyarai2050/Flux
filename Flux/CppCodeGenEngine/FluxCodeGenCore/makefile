CXX=g++
CXXFLAGS =  -fPIC -Wall -g -shared

INCLUDES =
LFLAGS   =
LIBS     = 

SRCS = flux_options.pb.cc strutil.cc 
OBJS = $(SRCS:.cc=.o)

MAIN = FluxCodeGenCore.so

SHELL = /bin/sh
.SUFFIXES:
.SUFFIXES: .cc .o .proto

.PHONY: all clean depend Makefile

all:    $(MAIN)
$(MAIN): $(OBJS)
	$(CXX) $(CXXFLAGS) $(INCLUDES) -o $(MAIN) $(OBJS) $(LFLAGS) $(LIBS)

flux_options.pb.cc flux_options.pb.h: flux_options.proto
	protoc flux_options.proto --cpp_out=. -I. -I/usr/include -I/usr/local/include
	protoc flux_options.proto --java_out=. -I. -I/usr/include -I/usr/local/include

.cc.o:
	$(CXX) $(CXXFLAGS) $(INCLUDES) -c $<  -o $@

clean:
	$(RM) *.o $(MAIN) $(GENTESTS) flux_options.pb.cc flux_options.pb.h

depend: $(SRCS)
	makedepend $(INCLUDES) $^


