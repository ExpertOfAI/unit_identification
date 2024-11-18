from setuptools import setup, find_packages

setup(name='unit_identification_cpu',
		version='1.7',
		description='UOM identification_cpu',
		url='https://github.com/ExpertOfAI/unit_identification',
		author='ExpertOfAI1',
		license='MIT',
		packages=find_packages(),
		data_files=[
				('', ['unit_identification/units.json', 'unit_identification/entities.json']),
				('_lang/en_US',['unit_identification/_lang/en_US/clf.joblib', 'unit_identification/_lang/en_US/common-words.json', 'unit_identification/_lang/en_US/entities.json', 'unit_identification/_lang/en_US/units.json']),
				('_lang/en_US/train',['unit_identification/_lang/en_US/train/similars.json', 'unit_identification/_lang/en_US/train/train.json', 'unit_identification/_lang/en_US/train/wiki.json']),
					],
		include_package_data=True,
		classifiers=[
		'Programming Language :: Python :: 3',
		'License :: OSI Approved :: MIT License',
		'Operating System :: OS Independent',
		],
		python_requires='>=3.6',
		install_requires = ["quantulum3", "stemming", "cryptography"]
		)
