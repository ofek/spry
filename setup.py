from setuptools import setup, find_packages

with open('README.rst', 'r') as infile:
    read_me = infile.read()

setup(
    name='spry',
    version='0.5.0',
    description='Modern file transfer utility supporting HTTPS & SFTP.',
    long_description=read_me,
    author='Ofek Lev',
    author_email='ofekmeister@gmail.com',
    maintainer='Ofek Lev',
    maintainer_email='ofekmeister@gmail.com',
    url='https://github.com/Ofekmeister/spry',
    download_url='https://github.com/Ofekmeister/spry',
    license='MIT',
    platforms=None,

    keywords=(
        'file transfer',
        'accelerator',
        'download manager',
    ),

    classifiers=(
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy'
    ),

    install_requires=['appdirs', 'click', 'requests', 'SQLAlchemy'],

    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'spry = spry.cli:spry',
        ],
    },
)
