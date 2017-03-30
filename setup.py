import glob
from setuptools import setup

setup(
    name='edxcut',
    version='0.2',
    author='I. Chuang and G. Lopez',
    author_email='ichuang@mit.edu',
    packages=['edxcut'],
    scripts=[],
    url='http://pypi.python.org/pypi/edxcut/',
    license='LICENSE.txt',
    description='edX course unit tester',
    long_description=open('README.md').read(),
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
                      ],
    package_dir={'edxcut': 'edxcut'},
    package_data={},
    # data_files = data_files,
    # test_suite="edxcut.test",
)
