For extra data, PsychoPy logs were not recorded, so 'beh' files needed to be created manually. The stimuli could be found using the EEG event codes, and details corresponding to these (attendance conditions, oddballs) are available in other metadata.

Various files were added into the dataset manually, such as 'dataset_notes.xlsx' (in 'misc'), and 'CITATION.cff'. Additionally, the code relating to event errors (in the 'code' folder) must be run to calculate and tabulate those statistics.

The 'behFileCleaner' function has been observed to fail sometimes when the dataset is saved to OneDrive, due to sync conflicts. We recommend pausing syncing before running the code, to avoid this.