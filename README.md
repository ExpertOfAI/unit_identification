https://packaging.python.org/en/latest/tutorials/packaging-projects/

from setuptools import setup, find_packages

setup(name='unit_identification',
		version='1.0',
		description='unit_identification',
		url='https://github.com/ExpertOfAI/unit_identification',
		author='ExpertOfAI',
		license='MIT',
		packages=find_packages(),
		classifiers=[
		'Programming Language :: Python :: 3',
		'License :: OSI Approved :: MIT License',
		'Operating System :: OS Independent',
		],
		python_requires='>=3.6',
		)
pip install twine		
python setup.py sdist

delete tar.gz from dist folder
twine upload dist/*
<Enter API token , created from pypi account "create api token">
pypi-AgEIcHlwaS5vcmcCJGQzZDc3NmQ4LTFhMTctNDYxOC05YWQ5LWNmYThhY2NiNGE5ZAACKlszLCJiN2ZkNTM4Ny00YTAzLTQwZWYtYTdhZS1lMjBhOWI2OTRlN2IiXQAABiAcgG04Ac5mG9mGO1LScd93dCKNfvU7LTiqvU0muSRW2A