from setuptools import setup, Extension
from Cython.Build import cythonize

ext_modules = [
    Extension(
        "mobile_book_cache",
        sources=["mobile_book_cache.pyx"],
        language="c++",
        extra_compile_args=["-std=c++17"]
    )
]

setup(
    ext_modules=cythonize(ext_modules)
)
