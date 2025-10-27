import pathlib
import matlab.engine
from poly52trigs_allVersions import *
from setAndTrigs2bids_allVersions import *
from additionalDataReader import *

"""Alternate versions of the main poly52bids workflow. In order, these are for dealing with:
-Participants with only partial ceegrid data, and trigger corrections added.
-Participants with no ceegrid data.
-Extra data. Only for converting the extra data, not other data from the chosen participant."""

def poly52bids_partial_ceegrid_addCorrections(basePath, eeglabPath, participantNumber, handedness, filterBufferPeriod):
    """For a recording where cEEGrid ground came loose (only P1 FULLY recorded), and also trigs needed corrections."""
    
    eng = matlab.engine.start_matlab()
    eng.addpath(eeglabPath, nargout=0)
    eng.poly52set(basePath, participantNumber, "baseline","","", nargout=0) #3rd arg is recordingProperty
    eng.quit()   
    print("cEEGrid arrays OK for " + participantNumber + ".")
    print("Stage 1 of conversion complete.")
    
    partStartEndLatencies_scalp, partStartEndLatencies_ceegrid = poly52trigs_partial_ceegrid_addCorrections(basePath, participantNumber,
                                                                                                            filterBufferPeriod)
    print("This file had missing or incorrect triggers, which have been corrected manually. These may be a little less precise than"
          + " otherwise.")
    print("Stage 2 of conversion complete.")
    
    additionalData = additionalDataReader(basePath, participantNumber, handedness)
    print("Stage 3 of conversion complete.")
    
    setAndTrigs2bids_partial_ceegrid(basePath, participantNumber, partStartEndLatencies_scalp, partStartEndLatencies_ceegrid,
                                     additionalData)
    print("Stage 4 of conversion complete.")
    
    
def poly52bids_no_ceegrid(basePath, eeglabPath, participantNumber, handedness, filterBufferPeriod):
    """For a few recordings where cEEGrid data was not recorded/was of insufficient quality."""
    
    eng = matlab.engine.start_matlab()
    eng.addpath(eeglabPath, nargout=0)
    eng.poly52set(basePath, participantNumber, "noCeegrid","","", nargout=0)
    eng.quit()   
    print("cEEGrid arrays OK for " + participantNumber + ".")
    print("Stage 1 of conversion complete.")
    
    partStartEndLatencies_scalp = poly52trigs_no_ceegrid(basePath, participantNumber,
                                                         filterBufferPeriod)
    print("Stage 2 of conversion complete.")
    
    additionalData = additionalDataReader(basePath, participantNumber, handedness)
    print("Stage 3 of conversion complete.")
    
    setAndTrigs2bids_no_ceegrid(basePath, participantNumber, partStartEndLatencies_scalp,
                                additionalData)
    print("Stage 4 of conversion complete.")
    
    
def poly52bids_extraData(basePath, participantNumber, handedness, filterBufferPeriod): #eeglab path not needed
    #Stage one has already been completed. Below are stages 2-4. Stages 5-6 completed after,
    #in poly52bids.py.
        
    partStartEndLatencies_scalp, partStartEndLatencies_ceegrid = poly52trigs_extraData(basePath, participantNumber,
                                                                                       filterBufferPeriod)
        
    additionalData = additionalDataReader(basePath, participantNumber, handedness)
    
    setAndTrigs2bids_extraData(basePath, participantNumber, partStartEndLatencies_scalp, partStartEndLatencies_ceegrid,
                               additionalData)