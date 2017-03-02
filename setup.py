from setuptools import setup

import madprops


setup(
    name='drf-madprops',
    version=madprops.__version__,
    description=madprops.__doc__,
    author='Yola',
    author_email='engineers@yola.com',
    license='MIT (Expat)',
    url=madprops.__url__,
    packages=['madprops'],
    install_requires=[
        'django >= 1.4.11, < 1.12',
        'djangorestframework >= 3.0.1, < 3.6.0'
    ]
)
