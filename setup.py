#!/usr/bin/env python2
from distutils.command.build_py import build_py
from distutils.command.clean import clean
from setuptools import setup
from pdfminer import __version__
import errno
import os
import shutil
from tools import conv_cmap


cmapdir = 'pdfminer/cmap'
samplesdir = 'samples'


class CustomBuild(build_py):
    def run(self):
        # Build cmap directory
        try:
            os.makedirs(cmapdir)
        except OSError as exception:
            if exception.errno != errno.EEXIST:
                raise
        conv_cmap.convert(cmapdir, 'Adobe-CNS1', 'cmaprsrc/cid2code_Adobe_CNS1.txt', ['cp950', 'big5'])
        conv_cmap.convert(cmapdir, 'Adobe-GB1', 'cmaprsrc/cid2code_Adobe_GB1.txt', ['cp936', 'gb2312'])
        conv_cmap.convert(cmapdir, 'Adobe-Japan1', 'cmaprsrc/cid2code_Adobe_Japan1.txt', ['cp932', 'euc-jp'])
        conv_cmap.convert(cmapdir, 'Adobe-Korea1', 'cmaprsrc/cid2code_Adobe_Korea1.txt', ['cp949', 'euc-kr'])
        build_py.run(self)  # Continue with regular build


class CustomClean(clean):
    def run(self):
        # Remove cmap directory in source directory (not build directory)
        shutil.rmtree(cmapdir, ignore_errors=True)
        # Remove files produced when running unit tests
        for root, dirs, files in os.walk(samplesdir):
            for fn in files:
                if fn.endswith('.txt') or fn.endswith('.xml') or fn.endswith('.html'):
                    os.remove(os.path.join(root, fn))
        clean.run(self)  # Continue with regular clean

setup(
    name='pdfminer',
    version=__version__,
    description='PDF parser and analyzer',
    long_description='''PDFMiner is a tool for extracting information from PDF documents.
Unlike other PDF-related tools, it focuses entirely on getting 
and analyzing text data. PDFMiner allows to obtain
the exact location of texts in a page, as well as 
other information such as fonts or lines.
It includes a PDF converter that can transform PDF files
into other text formats (such as HTML). It has an extensible
PDF parser that can be used for other purposes instead of text analysis.''',
    license='MIT/X',
    author='Yusuke Shinyama',
    author_email='yusuke at cs dot nyu dot edu',
    maintainer='Matt Swain',
    maintainer_email='m.swain@me.com',
    url='http://www.unixuser.org/~euske/python/pdfminer/index.html',
    cmdclass={'build_py': CustomBuild, 'clean': CustomClean},
    packages=[
    'pdfminer',
    ],
    package_data={
    'pdfminer': ['cmap/*.pickle.gz']
    },
    entry_points={
        'console_scripts': [
            'pdf2txt = pdfminer.pdf2txt:main',
            'dumppdf = pdfminer.dumppdf:main',
            'latin2ascii = pdfminer.latin2ascii:main',
        ]
    },
    test_suite='tests',
    keywords=['pdf parser', 'pdf converter', 'layout analysis', 'text mining'],
    classifiers=[
    'Development Status :: 4 - Beta',
    'Environment :: Console',
    'Intended Audience :: Developers',
    'Intended Audience :: Science/Research',
    'License :: OSI Approved :: MIT License',
    'Topic :: Text Processing',
    ],
)
