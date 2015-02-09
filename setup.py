import os
from setuptools import setup, find_packages

version = "0.1"
url = 'https://github.com/denniskempin/safetynet'
description = ("Type documentation and checking for python")

script_dir = os.path.dirname(__file__)
long_description = open(os.path.join(script_dir, "README.md")).read()

setup(name='safetynet',
      author="Dennis Kempin",
      author_email="denniskempin@chromium.org",
      url=url,
      description=description,
      long_description=long_description,
      keywords="type checking, documentation",
      license="MIT",

      classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Topic :: Software Development :: Documentation',
        'Topic :: Software Development :: Testing',
        'Programming Language :: Python :: 2.7',
      ],

      version=version,
      download_url='%s/tarball/%s' % (url, version),

      packages=find_packages('.'),
      install_requires=[],
      tests_require=['nose2'],
      entry_points={},
)
