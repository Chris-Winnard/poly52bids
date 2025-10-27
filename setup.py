from setuptools import setup, find_packages

setup(name="poly52bids",
      version="1.0.0",
      packages=find_packages(),
      install_requires=["matlabengineforpython",
                        "matplotlib",
                        "mne",
                        "mne_bids",
                        "numpy",
                        "pandas",
                        "pybv"],
    entry_points={"console_scripts": ["poly52bids = poly52bids.__main__:main"]},
    author="Chris Winnard",
    description="""Package to convert from .poly5 EEG and .csv behavioural data
                to BIDS formatting. This is individualised for the sourcedata of
                the Decoding Auditory Attention and Musical Emotions with EarEEG
                (DAAMEE) dataset; adjustment for work with other datasets is advised""",
    license="MIT",
    classifiers=["Programming Language :: Python :: 3"],
    include_package_data=True)