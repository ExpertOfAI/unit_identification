https://packaging.python.org/en/latest/tutorials/packaging-projects/

pip install twine		
python setup.py sdist

twine upload dist/*
<Enter API token , created from pypi account "create api token">