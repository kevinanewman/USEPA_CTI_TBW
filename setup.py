import pathlib
from setuptools import setup

# The directory containing this file
HERE = pathlib.Path(__file__).parent

# The text of the README file
README = (HERE / "README.md").read_text()

# This call to setup() does all the work
setup(
    name="usepa-cti",
    version="0.0.1",
    description="USEPA Cleaner Trucks Initiative",
    long_description=README,
    long_description_content_type="text/x-md",
    url="https://github.com/kevinanewman/USEPA_CTI_TBW",
    project_urls={'Documentation': 'https://https://github.com/kevinanewman/USEPA_CTI_TBW/blob/master/USEPA_CTI%200.0.1%20documentation.pdf',
                  'Bug Tracker': 'https://github.com/kevinanewman/USEPA_CTI_TBW/issues',
                  'Source Code': 'https://github.com/kevinanewman/USEPA_CTI_TBW',
    },
    author="US EPA",
    author_email="newman.kevin@epa.gov",
    license="",
    classifiers=[
        # "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
    ],
    packages=["usepa_cti"],                # or something like packages=find_packages(exclude=("tests",)),
    include_package_data=True,
    install_requires=["numpy", "matplotlib", "pandas", "scipy"],
    # entry_points={
    #     "console_scripts": [
    #         "omega2=usepa_omega2.__main__:main",
    #     ]
    # },
)