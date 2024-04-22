# C++ App External Modules Installation Guide

## Prerequisites

Before proceeding with the installation, ensure that you have the following prerequisites installed:

- `build-essential`: This package contains important tools like gcc, g++, make, etc.

```bash
sudo apt install build-essential
```

## Boost
### Boost provides free peer-reviewed portable C++ source libraries.

```
wget https://boostorg.jfrog.io/artifactory/main/release/1.81.0/source/boost_1_81_0.tar.gz
tar -xf boost_1_81_0.tar.gz
cd boost_1_81_0
./bootstrap.sh --prefix=/usr/local
sudo ./b2 install
```

## MongoC
### MongoC is the C driver for MongoDB.
```
- apt install libbson-dev
- apt install libmongoc-dev
```

## Mongocxx
### Mongocxx is the official MongoDB C++ driver.
```
curl -OL https://github.com/mongodb/mongo-cxx-driver/releases/download/r3.7.0/mongo-cxx-driver-r3.7.0.tar.gz
tar -xzf mongo-cxx-driver-r3.7.0.tar.gz
cd mongo-cxx-driver-r3.7.0/build
cmake .. -DCMAKE_BUILD_TYPE=Release -DBSONCXX_POLY_USE_BOOST=1 -DMONGOCXX_OVERRIDE_DEFAULT_INSTALL_PREFIX=OFF -DCMAKE_INSTALL_PREFIX=/usr/local
cmake --build .
sudo cmake --build . --target install
```

## Quill
### Quill is a C++ logging library.
```
git clone https://github.com/odygrd/quill.git
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
cmake -S. -Bcmake-out -DCMAKE_INSTALL_PREFIX=/usr/local -DCMAKE_CXX_STANDARD=17 -Dprotobuf_ABSL_PROVIDER=module -DCMAKE_PREFIX_PATH=/usr/local
cd cmake-out
make -j4
sudo make install
```

