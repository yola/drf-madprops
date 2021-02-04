from setuptools import setup

import madprops

with open('README.md') as readme_file:
    long_description = readme_file.read()

setup(
    name='drf-madprops',
    version=madprops.__version__,
    description=madprops.__doc__,
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Yola',
    author_email='engineers@yola.com',
    license='MIT',
    url=madprops.__url__,
    packages=['madprops'],
    install_requires=[
        'django >= 1.11, < 3.3',
        'djangorestframework >= 3.5, < 3.13'
    ],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Framework :: Django :: 1.11',
        'Framework :: Django :: 2.0',
        'Framework :: Django :: 2.1',
        'Framework :: Django :: 2.2',
        'Framework :: Django :: 3.0',
        'Framework :: Django :: 3.1',
        'Framework :: Django :: 3.2',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
)
