#!/usr/bin/env python
import os, sys
if sys.platform=='win32' and ('install' in sys.argv or 'install_ext' in sys.argv):
	exe = sys.argv[0]
	if not os.path.isabs(exe):
		exe = os.path.join(os.getcwd(),exe)
	sys.argv.append('--install-platlib='+os.path.dirname(exe))

from distutils.core import setup, Extension

if sys.platform=="win32":
	LIBS=[]
elif sys.platform=="sunos5":
	LIBS=[]
else:
	print "Don't know about other systems"

setup(	name = "_rl_accel",
		version = "0.2",
		description = "Python Reportlab acceleretaor extensions",
		author = "Robin Becker",
		author_email = "robin@reportlab.com",
		url = "http://www.reportlab.com",
		packages = [],
		ext_modules =	[Extension(	'_rl_accel',
									['_rl_accel.c'],
									include_dirs=[],
									define_macros=[],
									library_dirs=[],
									libraries=LIBS,	# libraries to link against
									),
						Extension(	'sgmlop',
									['sgmlop.c'],
									include_dirs=[],
									define_macros=[],
									library_dirs=[],
									libraries=LIBS,	# libraries to link against
									),
						Extension(	'pyHnj',
									['pyHnjmodule.c','hyphen.c', 'hnjalloc.c'],
									include_dirs=[],
									define_macros=[],
									library_dirs=[],
									libraries=LIBS,	# libraries to link against
									),
						],
		)