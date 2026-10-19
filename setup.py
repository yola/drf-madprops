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
        'django >= 1.11, < 6',
        'djangorestframework >= 3.5, < 4'
    ],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
    ],
)
