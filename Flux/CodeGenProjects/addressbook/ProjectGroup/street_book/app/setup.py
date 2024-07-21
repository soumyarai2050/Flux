from setuptools import setup, Extension
from Cython.Build import cythonize

ext_modules = [
    Extension(
        "mobile_book_cache",
        sources=["mobile_book_cache.pyx"],
        language="c++",
        extra_compile_args=["-std=c++17",
                            "-I/home/subham/Documents/GitHub/FluxCodeGenEngine/Flux/CodeGenProjects/AddressBook/ProjectGroup/mobile_book/cpp_app/replay",
                            "-I/home/subham/cpp_libs/libs_13/quill/include", "-L/home/subham/cpp_libs/libs_13/quill/lib"]
    )
]

setup(
    ext_modules=cythonize(ext_modules)
)
