## Requirements

- EEGLAB (tested with v2023.0)
- MATLAB (tested with R2023b)
- MATLAB Engine for Python (tested with 23.2.3)
- MNE-Python (tested with v1.7.0)
- MNE-BIDS (tested with v0.14)
- NumPy (tested with v1.26.4)
- Pandas (tested with v2.2.2)
- pybv (tested with v0.7.5)
- Python (3.8+; at the time of writing, December 2025, 3.13 is incompatible with the MATLAB engine)

To install the MATLAB Engine for Python:

1. Open MATLAB
2. Run:

   cd(fullfile(matlabroot,'extern','engines','python'))
   system('python setup.py install')

## Setup
For those who are less experienced with pip, to set up the software simply navigate into the main directory (the upper poly52bids folder), and run the following command:
pip install .

Installation should only take a few seconds, and then you'll be good to go!

## Additional Tips
                      
For extra data, PsychoPy logs were not recorded, so 'beh' files needed to be created manually. The stimuli could be found using the EEG event codes, and details corresponding to these (attendance conditions, oddballs) are available in other metadata.

Various files were added into the dataset manually, such as 'dataset_notes.xlsx' (in 'misc'), and 'CITATION.cff'. Additionally, the code relating to event errors (in the 'code' folder) must be run to calculate and tabulate those statistics.


The 'behFileCleaner' function has been observed to fail sometimes when the dataset is saved to OneDrive, due to sync conflicts. We recommend pausing syncing before running the code, to avoid this.

