import glob
from pathlib import Path
from setuptools import setup

# read the contents of README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name='edxcut',
    version='0.4',
    author='I. Chuang and G. Lopez',
    author_email='ichuang@mit.edu',
    packages=['edxcut'],
    scripts=[],
    url='http://pypi.python.org/pypi/edxcut/',
    license='LICENSE.txt',
    description='edX course unit tester',
    long_description=long_description,
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'edxcut = edxcut.main:CommandLine',
            ],
        },
    install_requires=['lxml',
                      'requests',
                      'pyyaml',
                      'pytest',
                      'pysrt',
                      ],
    package_dir={'edxcut': 'edxcut'},
    package_data={},
    # data_files = data_files,
    # test_suite="edxcut.test",
)
