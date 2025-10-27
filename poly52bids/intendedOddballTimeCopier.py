import os
import shutil

def intendedOddballTimeCopier(basePath,participantNumber):
    originalFilePath = basePath + 'sourcedata/P' + participantNumber + '/Oddball Start Times.txt'
    
    #Convert e.g., "P01" to BIDS format "sub-01"
    target_participant_path = basePath + f"bids_dataset/sub-{participantNumber}/eeg/"
    
    #New file name in BIDS format
    new_filename = f"sub-{participantNumber}_attnMultInstOBs_intendedOBonsets.txt"
    target_file_path = target_participant_path + new_filename

    #Check if Oddball Start Times.txt exists in sourcedata
    if os.path.exists(originalFilePath):
        #Ensure target directory exists
        os.makedirs(target_participant_path, exist_ok=True)
        
        #Copy and rename file to BIDS dataset
        shutil.copy(originalFilePath, target_file_path)
        print(f"Copied and renamed oddball file from sourcedata to BIDS for {participantNumber}.")
    else:
        print(f"No Oddball Start Times.txt found for {originalFilePath}.")