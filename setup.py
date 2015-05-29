from setuptools import setup, find_packages

with open('README.rst', 'r') as infile:
    read_me = infile.read()

setup(
    name='spry',
    version='0.3.0',
    description='Multi-part download accelerator',
    long_description=read_me,
    author='Ofek Lev',
    author_email='ofekmeister@gmail.com',
    maintainer='Ofek Lev',
    maintainer_email='ofekmeister@gmail.com',
    url='https://github.com/Ofekmeister/spry',
    download_url='https://github.com/Ofekmeister/spry',
    license='MIT',
    platforms=None,

    keywords=[
        'file downloader',
        'download accelerator',
        'multi-part downloader',
        'download manager',
    ],

    classifiers=[
        'Development Status :: 1 - Planning',
        'Intended Audience :: Developers',
        'Intended Audience :: End Users/Desktop',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
    ],

    setup_requires=['requests==2.7.0'],
    install_requires=['requests==2.7.0'],
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'spry = spry.cli:main',
        ],
    },
)
