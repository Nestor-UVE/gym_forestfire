from setuptools import setup
import sys

assert sys.version_info.major == 3 and sys.version_info.minor >= 6, \
    "The gym_forestfire package is designed to work with Python 3.6 " \
    "and greater Please install it before proceeding."

setup(
    name='gym_forestfire',
    py_modules=['gym_forestfire'],
    install_requires=[
        'gym',
        'numpy',
        'matplotlib',
    ],
    description="Forest fire Gym environment.",
    author="Sahand Rezaei-Shoshtari",
)
