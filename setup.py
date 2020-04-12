# Always prefer setuptools over distutils
from setuptools import setup, find_packages

setup(
    name='kyles-feedreader',
    version='1.0.0',
    description='Feed Reader based around pony orm, gevent and aciimatics',
    url='https://github.com/kmonson/kyles_feedreader',
    author='Kyle Monson',
    python_requires='>=3.7, <4',
    package_dir={'': 'src'},
    packages=find_packages(where='src'),
    install_requires=[
        "pony",
        "gevent",
        "asciimatics",
        "feedparser @ git+git://github.com/kurtmckee/feedparser.git",
        "click",
        "requests",
        "grequests",
        "pytest",
        "beautifulsoup4",
        "dateparser",
        "python-dateutil",
    ],
    extras_require={
        'test': ['pytest'],
    },
    entry_points={
        'console_scripts': [
            'kfr-cli=kyles_feedreader.cli:cli',
        ],
    }
)