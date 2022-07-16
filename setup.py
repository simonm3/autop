"""
This file is automatically generated by the autogen package.
Please edit the marked area only. Other areas will be
overwritten when autogen is rerun.
"""

from setuptools import setup

params = dict(
    name='autogen',
    description='Automate development tasks',
    version='1.0.14',
    url='https://gitlab.com/simonm3/autogen.git',
    install_requires=['setuptools', 'docopt',
                      'PyYAML', 'pypiwin32', 'autopep8'],
    packages=['autogen'],
    package_data={'autogen': ['import2pypi.txt']},
    include_package_data=True,
    py_modules=[],
    scripts=None)

########## EDIT BELOW THIS LINE ONLY ##########

# prevent vscode moving this to top
if True:
    import sys

if sys.platform != "win32":
    print("warning. must install pypiwin32")
params["install_requires"].remove("pypiwin32")

# enable command line
params.update(entry_points={"console_scripts": [
              "autogen = autogen.autogen:main"]})

########## EDIT ABOVE THIS LINE ONLY ##########

setup(**params)
