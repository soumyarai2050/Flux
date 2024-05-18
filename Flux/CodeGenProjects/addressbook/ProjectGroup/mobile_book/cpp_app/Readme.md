# C++ App External Modules Installation Guide

## Prerequisites

Before proceeding with the installation, ensure that you have the following prerequisites installed:

- `build-essential`: This package contains important tools like gcc, g++, make, etc.

```bash
sudo apt install build-essential
```

## Install gcc g++ version 12 and 13
```
sudo apt update
sudo apt install software-properties-common
sudo add-apt-repository ppa:ubuntu-toolchain-r/test
sudo apt update
sudo apt install gcc-12 g++-12 gcc-13 g++-13 -y
sudo update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-13 13 --slave /usr/bin/g++ g++ /usr/bin/g++-13

```

## To Change gcc version
``
sudo update-alternatives --config gcc
``

## Boost
### Boost provides free peer-reviewed portable C++ source libraries.

```
wget https://boostorg.jfrog.io/artifactory/main/release/1.81.0/source/boost_1_81_0.tar.gz
tar -xf boost_1_81_0.tar.gz
cd boost_1_81_0
./bootstrap.sh --prefix=/home/subham/cpp_libs/libs_12/boost
sudo ./b2 install
```

[//]: # (## MongoC)

[//]: # (### MongoC is the C driver for MongoDB.)

[//]: # (```)

[//]: # (sudo apt install libbson-dev)

[//]: # (sudo apt install libmongoc-dev)

[//]: # (```)

## Mongocxx
### Mongocxx is the official MongoDB C++ driver.
```
curl -OL https://github.com/mongodb/mongo-cxx-driver/releases/download/r3.10.1/mongo-cxx-driver-r3.10.1.tar.gz
tar -xzf mongo-cxx-driver-r3.10.1.tar.gz
cd mongo-cxx-driver-r3.10.1/build
cmake .. -DCMAKE_BUILD_TYPE=Release -DMONGOCXX_OVERRIDE_DEFAULT_INSTALL_PREFIX=OFF -DCMAKE_INSTALL_PREFIX=/usr/local
cmake --build .
sudo cmake --build . --target install
```

## Quill
### Quill is a C++ logging library.
```
git clone https://github.com/odygrd/quill.git
cd quill
mkdir cmake_build
cd cmake_build
cmake ..
sudo make install
```

## Protobuf
### Protocol Buffers (protobuf) is a method of serializing structured data.
```
git clone --recursive https://github.com/protocolbuffers/protobuf.git
cd protobuf
mkdir cmake-out
git checkout v25.0
cmake -S. -Bcmake-out -DCMAKE_INSTALL_PREFIX=/home/subham/cpp_libs/libs/protobuf_25.2 -DCMAKE_CXX_STANDARD=17 -Dprotobuf_ABSL_PROVIDER=module -DCMAKE_PREFIX_PATH=/home/subham/cpp_libs/libs/protobuf_25.2
cd cmake-out
make -j8
sudo make install
```

