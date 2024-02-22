from setuptools import setup, Extension
from Cython.Build import cythonize

ext_modules = [
    Extension(
        "market_data_cache",
        sources=["market_data_cache.pyx"],
        language="c++",
        extra_compile_args=["-std=c++11"]
    )
]

setup(
    ext_modules=cythonize(ext_modules)
)
