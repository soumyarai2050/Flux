# Poco build
1. git clone -b master https://github.com/pocoproject/poco.git
   - The official POCO C++ Libraries repository is on GitHub. The master branch always reflects the latest release (1.12.4).
2. cd poco
3. mkdir cmake-build
4. cd cmake-build
5. cmake .. && cmake --build .
6. sudo cmake --build . --target install
    - in the cmake-build directory to install POCO to /usr/local.