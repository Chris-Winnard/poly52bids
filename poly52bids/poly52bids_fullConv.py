from poly52bids_fullConv_altWfsImport import *
import pathlib
import matlab.engine
from poly52trigs_allVersions import *
from setAndTrigs2bids_allVersions import *
from additionalDataReader import *
from intendedOddballTimeCopier import *
from fileFormatter import *
import os
import shutil

"""For converting from sourcedata to the EEG-BIDS format for the DAAMEE dataset (and the code may be of interest to anyone working with data
from EEG experiments generally, particularly TMSi .poly5 files).

Note, for each output file we use 7s of surrounding data on each side (sometimes includes padding), to give filter buffers plus a little extra
data for ICA training etc.

For some participants/recordings there were minor tech issues, so we have had to implement adaptations of the main workflow (with the more
substantial ones imported from "poly52bids_altWorkflowsImport"). These are all handled automatically, so the user will not need to do anything.

The overall conversion has seven stages:
1- Conversion from .poly5 to .set.
2- Converting triggers to BIDS events files. These will either be straight from the .poly5 files, or, where necessary, from manually corrected
.txt files (in some cases there were errors in trigger recordings).
3- Reading additional metadata from the questionnaire file.
4- Converting the above three into the remaining BIDS files for that participant. Also, converting data from the PsychoPy log .csvs into
BIDS _beh.tsv files.
5- Copying the oddball metadata for part 2/attnMultInstOBs from sourcedata to BIDS.
6- Finally, reading through and formatting the _eeg.json and _beh.tsv files. This is done across the dataset so only needs to be done once,
after steps 1-5 are finished for all participants.
7. OPTIONAL: Copy, or move, sourcedata to the bids_dataset folder.
Note also that some parts of the BIDS dataset were added/adapted manually, e.g., dataset_description.json."""


def poly52bids_fullConv(subjects, filterBufferPeriod, basePath, eeglabPath, processExtraData, sourcedataTransfer):
    """Now we begin:"""
        
    if processExtraData == "exclusively":
        print("Extra data is available for these participants (e.g., due to issues where the experiment had to be restarted, and will " +
              "also be converted now (behaviour files must be completed manually, and you may want to move all files into the main 'misc'"+
              " directory).")
        assert all(s in [9, 28] for s in subjects), "subjects contains values other than 9 or 28- please check as these are the only two with"
        + " extra data."
        for participantNumber in [f'{i:02d}' for i in subjects]:
            
            handedness = "right"
                
            participantNumber = '%02d' % participantNumber
            
            eng = matlab.engine.start_matlab()
            eng.addpath(eeglabPath, nargout=0)
            eng.poly52set(basePath, participantNumber, "baseline","","", nargout=0) #3rd arg is recordingProperty
            eng.quit()   
            poly52bids_extraData(basePath, participantNumber, handedness, filterBufferPeriod)

    ############################################################################################################################################
    ############################################################################################################################################


    elif processExtraData == "additionally":
        for participantNumber in subjects:
            
            if participantNumber in [12, 14, 23]:
                handedness = "left"
            else:
                handedness = "right"
            
            if participantNumber == 4:
                continue
            
            participantNumber = '%02d' % participantNumber
            
            if participantNumber == "06":
                poly52bids_partial_ceegrid_addCorrections(basePath, eeglabPath, participantNumber, handedness, filterBufferPeriod)
            
            elif participantNumber in ["16","21"]:
                print("Running the '_no_ceegrid' conversion workflow.")
                poly52bids_no_ceegrid(basePath, eeglabPath, participantNumber, handedness, filterBufferPeriod)
    ############################################################################################################################################
            #P05 was split into a couple of recordings, so the set files and trigs must be processed in their own workflow:
            elif participantNumber == "05":
                print("Running the workflow for split recordings.")
                "Recordings - e.g if first recording covered part 1 ('P1'), second covered parts 2+3:"
                rec1 = "P1"
                rec2 = "P2+P3"
                            
                eng = matlab.engine.start_matlab()
                eng.addpath(eeglabPath, nargout=0)
                eng.poly52set(basePath, participantNumber,"splitRecs", rec1, rec2, nargout=0)
                eng.quit()   
                print("cEEGrid arrays OK for " + participantNumber + ".")
                print("Stage 1 of conversion complete.")
                
                #Note this function adds a cEEGrid P3 end trig, to account for missing one.
                partStartEndLatencies_scalp, partStartEndLatencies_ceegrid = poly52trigs_splitRecs(basePath, participantNumber, rec1, rec2, filterBufferPeriod)
                print("Stage 2 of conversion complete.")
                
                additionalData = additionalDataReader(basePath, participantNumber, handedness)
                print("Stage 3 of conversion complete.")
            
                setAndTrigs2bids(basePath, participantNumber, partStartEndLatencies_scalp, partStartEndLatencies_ceegrid, additionalData)
                print("Stage 4 of conversion complete.")

    ############################################################################################################################################
            
            else:
                if participantNumber in ["01", "02", "22"]: #For these participants, cEEGrid chans were mistakenly inverted
                    eng = matlab.engine.start_matlab()
                    eng.addpath(eeglabPath, nargout=0)
                    eng.poly52set(basePath, participantNumber, "invertedCeegrid","","", nargout=0)
                    eng.quit()
                    print("Note: cEEGrid arrays were mistakenly reversed for P" + participantNumber + " so we have corrected for this. You do not need to"
                      + " do anything.")
                elif participantNumber in ["29", "30", "31", "32"]:
                    eng = matlab.engine.start_matlab()
                    eng.addpath(eeglabPath, nargout=0)
                    eng.poly52set(basePath, participantNumber, "cER10switched","","", nargout=0)
                    eng.quit()
                    print("The cER10 electrode was broken and another electrode from the set had to be moved to replace it for " + participantNumber + " so we have corrected for this. You do not need to"
                          + " do anything.")
                    print("Stage 1 of conversion complete.")
                else:
                    eng = matlab.engine.start_matlab()
                    eng.addpath(eeglabPath, nargout=0)
                    eng.poly52set(basePath, participantNumber, "baseline","","", nargout=0)
                    eng.quit()
                    print("cEEGrid arrays OK for " + participantNumber + ".")
                    print("Stage 1 of conversion complete.")
            
                #Stage 2:
                if participantNumber in ["02", "03", "08", "09", "10", "28", "29", "30"]:
                    partStartEndLatencies_scalp, partStartEndLatencies_ceegrid = poly52trigs_addCorrections(basePath, participantNumber, filterBufferPeriod)
                    print("This file had missing or incorrect triggers, which have been corrected manually. These may be a little less precise than"
                          + " otherwise.")
                    print("Stage 2 of conversion complete.")
                else:  
                    partStartEndLatencies_scalp, partStartEndLatencies_ceegrid = poly52trigs(basePath, participantNumber, filterBufferPeriod)
                    print("Stage 2 of conversion complete.")
            
                additionalData = additionalDataReader(basePath, participantNumber, handedness)
                print("Stage 3 of conversion complete.")
            
                setAndTrigs2bids(basePath, participantNumber, partStartEndLatencies_scalp, partStartEndLatencies_ceegrid, additionalData)
                print("Stage 4 of conversion complete.")

            intendedOddballTimeCopier(basePath, participantNumber)
            print("Stage 5 of conversion complete.")
            
            if participantNumber in ["09","28"]:
                print("Extra data is available for this participant (e.g, due to issues where the experiment had to be restarted, and will" +
                      "also be converted now (behaviour files must be completed manually, and you may want to move all files into the main 'misc'"+
                      "directory).")
                poly52bids_extraData(basePath, participantNumber, handedness, filterBufferPeriod)
                print("The extra data has been converted and stored in a \"misc\" folder alongside that of the other participants.")
                
    else:
        for participantNumber in subjects:
            
            if participantNumber in [12, 14, 23]:
                handedness = "left"
            else:
                handedness = "right"
                
            if participantNumber == 4:
                continue
            
            participantNumber = '%02d' % participantNumber
            
            if participantNumber == "06":
                poly52bids_partial_ceegrid_addCorrections(basePath, eeglabPath, participantNumber, handedness, filterBufferPeriod)
            
            elif participantNumber in ["16","21"]:
                print("Running the '_no_ceegrid' conversion workflow.")
                poly52bids_no_ceegrid(basePath, eeglabPath, participantNumber, handedness, filterBufferPeriod)
    ############################################################################################################################################
            #P05 was split into a couple of recordings, so the set files and trigs must be processed in their own workflow:
            elif participantNumber == "05":
                print("Running the workflow for split recordings.")
                "Recordings - e.g if first recording covered part 1 ('P1'), second covered parts 2+3:"
                rec1 = "P1"
                rec2 = "P2+P3"
                
                eng = matlab.engine.start_matlab()
                eng.addpath(eeglabPath, nargout=0)
                eng.poly52set(basePath, participantNumber,"splitRecs", rec1, rec2, nargout=0)
                eng.quit()   
                print("cEEGrid arrays OK for " + participantNumber + ".")
                print("Stage 1 of conversion complete.")
                
                #Note this function adds a cEEGrid P3 end trig, to account for missing one.
                partStartEndLatencies_scalp, partStartEndLatencies_ceegrid = poly52trigs_splitRecs(basePath, participantNumber, rec1, rec2, filterBufferPeriod)
                print("Stage 2 of conversion complete.")
                
                additionalData = additionalDataReader(basePath, participantNumber, handedness)
                print("Stage 3 of conversion complete.")
            
                setAndTrigs2bids(basePath, participantNumber, partStartEndLatencies_scalp, partStartEndLatencies_ceegrid, additionalData)
                print("Stage 4 of conversion complete.")
                
    ############################################################################################################################################
            
            else:
                if participantNumber in ["01", "02", "22"]: #For these participants, cEEGrid chans were mistakenly inverted
                 eng = matlab.engine.start_matlab()
                 eng.addpath(eeglabPath, nargout=0)
                 eng.poly52set(basePath, participantNumber, "invertedCeegrid","","", nargout=0)
                 eng.quit()   
                 print("Note: cEEGrid arrays were mistakenly reversed for P" + participantNumber + " so we have corrected for this. You do not need to"
                      + " do anything.")
                 print("Stage 1 of conversion complete.")
                elif participantNumber in ["29", "30", "31", "32"]:
                    #Later ones- need to use cER10_switched
                    eng = matlab.engine.start_matlab()
                    eng.addpath(eeglabPath, nargout=0)
                    eng.poly52set(basePath, participantNumber, "cER10switched","","", nargout=0)
                    eng.quit()   
                    print("The cER10 electrode was broken and another electrode from the set had to be moved to replace it for " +
                          participantNumber + " so we have corrected for this. You do not need to do anything.")
                    print("Stage 1 of conversion complete.")
                else:
                    eng = matlab.engine.start_matlab()
                    eng.addpath(eeglabPath, nargout=0)
                    eng.poly52set(basePath, participantNumber, "baseline","","", nargout=0)
                    eng.quit()   
                    print("cEEGrid arrays OK for " + participantNumber + ".")
                    print("Stage 1 of conversion complete.")
            
                #Stage 2:
                if participantNumber in ["02", "03", "08", "09", "10", "28", "29", "30"]:
                    partStartEndLatencies_scalp, partStartEndLatencies_ceegrid = poly52trigs_addCorrections(basePath, participantNumber, filterBufferPeriod)
                    print("This file had missing or incorrect triggers, which have been corrected manually. These may be a little less precise than"
                          + " otherwise.")
                    print("Stage 2 of conversion complete.")
                else:  
                    partStartEndLatencies_scalp, partStartEndLatencies_ceegrid = poly52trigs(basePath, participantNumber, filterBufferPeriod)
                    print("Stage 2 of conversion complete.")
            
                additionalData = additionalDataReader(basePath, participantNumber, handedness)
                print("Stage 3 of conversion complete.")
            
                setAndTrigs2bids(basePath, participantNumber, partStartEndLatencies_scalp, partStartEndLatencies_ceegrid, additionalData)
                print("Stage 4 of conversion complete.")
                
            intendedOddballTimeCopier(basePath, participantNumber)
            print("Stage 5 of conversion complete.")

    bidsPath = os.path.join(basePath, "bids_dataset")
    fileFormatter(bidsPath)      
    print("Stage 6 of conversion complete.")
    
    #Stage 7- OPTIONAL:
    if sourcedataTransfer == "copy":
        sourcedataPath = os.path.join(basePath, "sourcedata")
        sourcedataCopyPath = os.path.join(bidsPath, "sourcedata")
        
        shutil.copytree(sourcedataPath, sourcedataCopyPath, dirs_exist_ok=True)
        print(f"Copied sourcedata into bids_path.")
        print("Stage 7 of conversion complete.")
    elif sourcedataTransfer == "move":
        sourcedataPath = basePath + "/sourcedata"
        shutil.move(sourcedataPath, bidsPath)
        print(f"Moved sourcedata into bids_path.")
        print("Stage 7 of conversion complete.")        
    else:
        print("Stage 7 of conversion, transferring sourcedata, has not been opted for and so has not been run.")
        