from SerialTriggerDecoder import *
from poly52POPO_import import *
import numpy as np
import csv
from expectedTriggerCalculator import *

"""Versions of poly52trigs (in order):
-Baseline.
-Add trigger corrections.
-No ceegrid data.
-No ceegrid/add corrections.
-Partial ceegrid data/add corrections.
-Split recordings: for one participant where recording was stopped and restarted (meaning two scalp files, two ceegrid files).
-Extra data. Only for converting the extra data, not other data from the chosen participant."""

def poly52trigs(basePath, participantNumber,filterBufferPeriod):
    rawDataPath = basePath + 'sourcedata\P' + participantNumber + '\\'
    scalpFilename = "P" + participantNumber + "_scalp.Poly5"
    ceegridFilename = "P" + participantNumber + "_ceegrid.Poly5"
    
    SCALP_EEG = rawDataPath + scalpFilename
    CEEGRID = rawDataPath + ceegridFilename
    
    subjFolder = "sub-" + participantNumber

    TRIGGER_CLK = 16
    THR_ERROR = -0.05
    TRANS_ERROR = 0.1

    #read scalp poly5
    scalp_eeg = poly52POPO(SCALP_EEG, 'scalp')
    scalp_eeg.decode_events(triggerClk=TRIGGER_CLK, thrError=THR_ERROR, transError=TRANS_ERROR)
    scalp_eegCodes = [ sub['code'] for sub in scalp_eeg.raw_events ]

    #read ceegrid poly5
    ceegrid = poly52POPO(CEEGRID, 'ceegrid')
    ceegrid.decode_events(triggerClk=TRIGGER_CLK, thrError=THR_ERROR, transError=TRANS_ERROR)
    ceegridCodes = [ sub['code'] for sub in ceegrid.raw_events ]

#####################################################################################################################################################################
    #Good to run various checks: that there are the same number of events for the scalp/ceegrid files; that these do not contradict; and separately checking that events in
    #each are sensible. These are only rough and not exhaustive

    #Check same number of trigs recorded for scalp and ceegrid:
    num_scalp_eeg_events = len(scalp_eeg.raw_events)
    num_ceegrid_events = len(ceegrid.raw_events)    
    difference = num_scalp_eeg_events - num_ceegrid_events
    if difference > 0:
        print("WARNING - MORE SCALP THAN CEEGRID EVENTS DETECTED")
        lesserEventCount = num_ceegrid_events
    elif difference < 0:
        print("WARNING - MORE CEEGRID EVENTS THAN SCALP EVENTS DETECTED")
        lesserEventCount = num_scalp_eeg_events
    else:
        print("Equal number of scalp and ceegrid events detected.")
        lesserEventCount = num_scalp_eeg_events #could use either since it's the same value
    
    #Calculate no. of expected trigs, compare to recorded:    
    expectedTrigs = expectedTriggerCalculator(basePath, participantNumber)
    if expectedTrigs > num_scalp_eeg_events:
        diff = str(expectedTrigs - num_scalp_eeg_events)
        print("WARNING - " + diff + " SCALP EVENTS MISSING")#
    if expectedTrigs < num_scalp_eeg_events:
        diff = str(num_scalp_eeg_events - expectedTrigs)
        print("WARNING - " + diff + " EXCESS SCALP EVENTS DETECTED")
    if expectedTrigs > num_ceegrid_events:
        diff = str(expectedTrigs - num_ceegrid_events)
        print("WARNING - CEEGRID EVENTS MISSING")
    if expectedTrigs < num_ceegrid_events:
        diff = str(num_ceegrid_events - expectedTrigs)
        print("WARNING - " + diff + " EXCESS CEEGRID EVENTS DETECTED")
    if expectedTrigs == num_scalp_eeg_events and difference == 0:
        print("Good news: the number of trigs detected for both scalp and cEEGrid is what should be expected.")
    

    #Finally, check individual scalp and ceegrid trigs match up:
    x = 0
    for i in range(0, lesserEventCount):
        if scalp_eegCodes[i] != ceegridCodes[i]:
            print("WARNING - EVENT CODES DISCREPENCY")
            print("This is at the following sample in the scalp data: " + str(scalp_eeg.raw_events[i].get("sample_idx")))
            print("Alternatively, this is the following sample for the ceegrid data: " + str(ceegrid.raw_events[i].get("sample_idx")))
            
            
            #Single event checks. Note, if scalp/ceegrid EEG does have one or two more triggers, then will need to check the extra ones at the end
            #separately
            scalp_pattern = scalp_eeg.raw_events[i].get("pattern")
            scalp_code = scalp_eeg.raw_events[i].get("code")
            
            if len(scalp_pattern) > 8 and int(scalp_code) > 159:
                print("Scalp pattern too long. Scalp code value is also too large.")
            elif len(scalp_pattern) > 8 and int(scalp_code) < 160:
                print("Scalp pattern too long. Scalp code value is NOT too large.")
            elif len(scalp_pattern) < 9 and int(scalp_code) > 159:
                print("Scalp pattern NOT too long. However, scalp code value is too large.")
            
            ceegrid_pattern = ceegrid.raw_events[i].get("pattern")
            ceegrid_code = ceegrid.raw_events[i].get("code")
            
            if len(ceegrid_pattern) > 8 and int(ceegrid_code) > 159:
                print("ceegrid pattern too long. ceegrid code value is also too large.")
            if len(ceegrid_pattern) > 8 and int(ceegrid_code) < 160:
                print("ceegrid pattern too long. ceegrid code value is NOT too large.")
            if len(ceegrid_pattern) < 9 and int(ceegrid_code) > 159:
                print("ceegrid pattern NOT too long. However, ceegrid code value is too large.")
                
            
            print("It is the " + str(i+1) + "th event in each data file. The scalp code is: " + str(scalp_code) + " and the ceegrid code is: " + str(ceegrid_code))
        if scalp_eegCodes[i] == ceegridCodes[i]:
            x += 1
            
    print(str(x) + " out of " + str(lesserEventCount) + " codes are the same between both data files. Note this assumes that the code numbers are the same, OR that if one file has more "
          + "events detected, these are at the end.")
    
#######################################################################################################################################################################################################
    #Save to files, in a BIDS-friendly format:
    
    outputDir = basePath + "bids_dataset\sub-" + participantNumber + "\eeg\\"
    outputDirExists = os.path.exists(outputDir)
    
    if not outputDirExists:
        os.makedirs(outputDir)
#######################################################################################################################################################################################################   
    #First, scalp:
    
    scalp_eegLatencies = [ sub['sample_idx'] for sub in scalp_eeg.raw_events ]
    sfreq = 1000
    
    #Do this "task by task", i.e emotion decoding first etc:
    task1 = "emotion"
    filename = subjFolder + "_task-" + task1 + "_acq-scalp_events.tsv"
    scalpEvents_BIDS = (outputDir + filename)

    P1practiceEnded = False
    P1ended = False
    P2practiceEnded = False
    P2ended = False
    P3practiceEnded = False
    P3ended = False
    
    P1P3trialStartVals = np.arange(1, 73, 2) #Can reuse these later
    P1P3trialEndVals = np.arange(2, 74, 2)
    
    with open(scalpEvents_BIDS, 'w', newline='') as tsvfile:
        writer = csv.writer(tsvfile, delimiter='\t', lineterminator='\n')
        writer.writerow(["onset", "duration", "value", "significance", "trial"])
        i = 0
        j = 1 #For keeping track of main trials
        
        P1startLatency_scalp = scalp_eegLatencies[i]/sfreq - filterBufferPeriod
        duration = "0" #Throughout P1
        
        while P1ended == False:
            onset = scalp_eegLatencies[i]/sfreq - P1startLatency_scalp #So that the first trigger is at t = 0 (t= 'buffer period' once that's added in)
            value = scalp_eegCodes[i]
                
            if P1practiceEnded == False:
                trial = "prac"
                if value in P1P3trialStartVals:
                    significance = "trial_start"
                else:
                    significance = "trial_end"
                    P1practiceEnded = True
                    
            elif value == 154:
                trial = "N/A"
                significance = "main_trials_start"
            elif value == 155:
                trial = "N/A"
                significance = "main_trials_end"
                
            else:
                trial = str(j)
                if value in P1P3trialStartVals:
                    significance = "trial_start"
                elif value in P1P3trialEndVals:
                    significance = "trial_end"
                    j += 1
                    
            if value == 46: #These trials were about 42.7ms too long due to an error in expt setup.
            #For simplicity/consistency we trim the difference by moving end trigs forward.
                onset -= 0.043
                
            writer.writerow([str(onset), duration, str(value), significance, trial])
            i += 1
            
            if significance == "main_trials_end":
                P1endLatency_scalp = onset + P1startLatency_scalp + filterBufferPeriod
                P1ended = True  
                         
        tsvfile.close
    
    
    #P2:
    task2 = "attnMultInstOBs"    
    filename = subjFolder + "_task-" + task2 + "_acq-scalp_events.tsv"
    scalpEvents_BIDS = (outputDir + filename)

    P2trialStartVals = np.arange(73, 144, 2) #Can reuse these later
    P2trialEndVals = np.arange(74, 145, 2)
    P2attendedOBvals = np.array([145, 149, 153])
    P2unattendedOBvals = np.array([146, 147, 148, 150, 151, 152])    
    
    with open(scalpEvents_BIDS, 'w', newline='') as tsvfile:
        writer = csv.writer(tsvfile, delimiter='\t', lineterminator='\n')
        writer.writerow(["onset", "duration", "value", "significance", "trial"])
        
        #Continue to use i from before.
        j = 1 #For keeping track of prac trials
        k = 1 #"     "       "   "   main     "
        
        P2startLatency_scalp = scalp_eegLatencies[i]/sfreq - filterBufferPeriod
        
        while P2ended == False:
            onset = scalp_eegLatencies[i]/sfreq - P2startLatency_scalp
            value = scalp_eegCodes[i]
            
            if value == 156:
                trial = "N/A"
                significance = "main_trials_start"
                P2practiceEnded = True
                
            elif P2practiceEnded == False:
                trial = "prac_" + str(j)
                if value in P2trialStartVals:
                    significance = "trial_start"
                elif value in P2attendedOBvals:
                    significance = "attended_OB"
                elif value in P2unattendedOBvals:
                    significance = "unattended_OB"
                elif value in P2trialEndVals:
                    significance = "trial_end"
                    j += 1
                    
            elif value == 157:
                trial = "N/A"
                significance = "main_trials_end"
                
            else:
                trial = str(k)
                if value in P2trialStartVals:
                    significance = "trial_start"
                elif value in P2attendedOBvals:
                    significance = "attended_OB"
                elif value in P2unattendedOBvals:
                    significance = "unattended_OB"
                elif value in P2trialEndVals:
                    significance = "trial_end"
                    k += 1
                
            if "OB" in significance: #Oddballs
                duration = "0.49197278911"
            else:
                duration = "0"
            writer.writerow([str(onset), duration, str(value), significance, trial])
            i += 1
            
            if significance == "main_trials_end":
                P2endLatency_scalp = onset + P2startLatency_scalp + filterBufferPeriod
                P2ended = True  
                
        tsvfile.close
        
    #P3:
    task3 = "attnOneInstNoOBs"
    filename = subjFolder + "_task-" + task3 + "_acq-scalp_events.tsv"
    scalpEvents_BIDS = (outputDir + filename)
        
    with open(scalpEvents_BIDS, 'w', newline='') as tsvfile:
        writer = csv.writer(tsvfile, delimiter='\t', lineterminator='\n')
        writer.writerow(["onset", "duration", "value", "significance", "trial"])
        j = 1 #For keeping track of main trials
        
        P3startLatency_scalp = scalp_eegLatencies[i]/sfreq - filterBufferPeriod
        duration = "0" #Should already be set, but if e.g triggers above are missed, this acts as a failsafe.
        
        while P3ended == False:
            onset = scalp_eegLatencies[i]/sfreq - P3startLatency_scalp #So that the first trigger is at t = 0
            value = scalp_eegCodes[i]
                
            if P3practiceEnded == False:
                trial = "prac"
                if value in P1P3trialStartVals:
                    significance = "trial_start"
                else:
                    significance = "trial_end"
                    P3practiceEnded = True
                    
            elif value == 158:
                trial = "N/A"
                significance = "main_trials_start"
            elif value == 159:
                trial = "N/A"
                significance = "main_trials_end"
                
            else:
                trial = str(j)
                if value in P1P3trialStartVals:
                    significance = "trial_start"
                elif value in P1P3trialEndVals:
                    significance = "trial_end"
                    j += 1
                    
            if value == 46: #These trials were about 42.7ms too long due to an error in expt setup.
            #For simplicity/consistency we trim the difference by moving end trigs forward.
                onset -= 0.043
                
            writer.writerow([str(onset), duration, str(value), significance, trial])
            i += 1
            
            if significance == "main_trials_end" or i == len(scalp_eegLatencies):
                P3endLatency_scalp = onset + P3startLatency_scalp + filterBufferPeriod
                P3ended = True  
                         
        tsvfile.close
    
    partStartLatencies_scalp =[P1startLatency_scalp, P2startLatency_scalp, P3startLatency_scalp]
    partEndLatencies_scalp = [P1endLatency_scalp, P2endLatency_scalp, P3endLatency_scalp]
    partStartEndLatencies_scalp = np.stack([partStartLatencies_scalp, partEndLatencies_scalp])
        
#######################################################################################################################################################################################################
    #ceegrid:
        
    ceegridLatencies = [ sub['sample_idx'] for sub in ceegrid.raw_events ]
    sfreq = 1000
    
    #Do this "task by task", i.e emotion decoding first etc:
    task1 = "emotion"
    filename = subjFolder + "_task-" + task1 + "_acq-ceegrid_events.tsv"
    ceegridEvents_BIDS = (outputDir + filename)

    P1practiceEnded = False
    P1ended = False
    P2practiceEnded = False
    P2ended = False
    P3practiceEnded = False
    P3ended = False
    
    P1P3trialStartVals = np.arange(1, 73, 2) #Can reuse these later
    P1P3trialEndVals = np.arange(2, 74, 2)
    
    with open(ceegridEvents_BIDS, 'w', newline='') as tsvfile:
        writer = csv.writer(tsvfile, delimiter='\t', lineterminator='\n')
        writer.writerow(["onset", "duration", "value", "significance", "trial"])
        i = 0
        j = 1 #For keeping track of main trials
        
        P1startLatency_ceegrid = ceegridLatencies[i]/sfreq - filterBufferPeriod
        
        while P1ended == False:
            onset = ceegridLatencies[i]/sfreq - P1startLatency_ceegrid
            value = ceegridCodes[i]
                
            if P1practiceEnded == False:
                trial = "prac"
                if value in P1P3trialStartVals:
                    significance = "trial_start"
                else:
                    significance = "trial_end"
                    P1practiceEnded = True
                    
            elif value == 154:
                trial = "N/A"
                significance = "main_trials_start"
            elif value == 155:
                trial = "N/A"
                significance = "main_trials_end"
                
            else:
                trial = str(j)
                if value in P1P3trialStartVals:
                    significance = "trial_start"
                elif value in P1P3trialEndVals:
                    significance = "trial_end"
                    j += 1

            if value == 46: #These trials were about 42.7ms too long due to an error in expt setup.
            #For simplicity/consistency we trim the difference by moving end trigs forward.
                onset -= 0.043
                
            writer.writerow([str(onset), duration, str(value), significance, trial])
            i += 1
            
            if significance == "main_trials_end":
                P1endLatency_ceegrid = onset + P1startLatency_ceegrid + filterBufferPeriod
                P1ended = True  
                         
        tsvfile.close
    
    
    #P2:
    task2 = "attnMultInstOBs"    
    filename = subjFolder + "_task-" + task2 + "_acq-ceegrid_events.tsv"
    ceegridEvents_BIDS = (outputDir + filename)

    P2trialStartVals = np.arange(73, 144, 2) #Can reuse these later
    P2trialEndVals = np.arange(74, 145, 2)
    P2attendedOBvals = np.array([145, 149, 153])
    P2unattendedOBvals = np.array([146, 147, 148, 150, 151, 152])    
    
    with open(ceegridEvents_BIDS, 'w', newline='') as tsvfile:
        writer = csv.writer(tsvfile, delimiter='\t', lineterminator='\n')
        writer.writerow(["onset", "duration", "value", "significance", "trial"])
        
        #Continue to use i from before.
        j = 1 #For keeping track of prac trials
        k = 1 #"     "       "   "   main     "
        
        P2startLatency_ceegrid = ceegridLatencies[i]/sfreq - filterBufferPeriod
        
        while P2ended == False:
            onset = ceegridLatencies[i]/sfreq - P2startLatency_ceegrid
            value = ceegridCodes[i]
            
            if value == 156:
                trial = "N/A"
                significance = "main_trials_start"
                P2practiceEnded = True
                
            elif P2practiceEnded == False:
                trial = "prac_" + str(j)
                if value in P2trialStartVals:
                    significance = "trial_start"
                elif value in P2attendedOBvals:
                    significance = "attended_OB"
                elif value in P2unattendedOBvals:
                    significance = "unattended_OB"
                elif value in P2trialEndVals:
                    significance = "trial_end"
                    j += 1
                    
                
            elif value == 157:
                trial = "N/A"
                significance = "main_trials_end"
                
            else:
                trial = str(k)
                if value in P2trialStartVals:
                    significance = "trial_start"
                elif value in P2attendedOBvals:
                    significance = "attended_OB"
                elif value in P2unattendedOBvals:
                    significance = "unattended_OB"
                elif value in P2trialEndVals:
                    significance = "trial_end"
                    k += 1
                    
            if "OB" in significance: #Oddballs
                duration = "0.49197278911"
            else:
                duration = "0"
                
            writer.writerow([str(onset), duration, str(value), significance, trial])
            i += 1
            
            if significance == "main_trials_end":
                P2endLatency_ceegrid = onset + P2startLatency_ceegrid + filterBufferPeriod
                P2ended = True  
                
        tsvfile.close
        
    #P3:
    task3 = "attnOneInstNoOBs"    
    filename = subjFolder + "_task-" + task3 + "_acq-ceegrid_events.tsv"
    ceegridEvents_BIDS = (outputDir + filename)
        
    with open(ceegridEvents_BIDS, 'w', newline='') as tsvfile:
        writer = csv.writer(tsvfile, delimiter='\t', lineterminator='\n')
        writer.writerow(["onset", "duration", "value", "significance", "trial"])
        j = 1 #For keeping track of main trials
        
        P3startLatency_ceegrid = ceegridLatencies[i]/sfreq - filterBufferPeriod
        duration = "0" #Should already be set, but if e.g triggers above are missed, this acts as a failsafe.
        
        while P3ended == False:
            onset = ceegridLatencies[i]/sfreq - P3startLatency_ceegrid #So that the first trigger is at t = 0
            value = ceegridCodes[i]
                
            if P3practiceEnded == False:
                trial = "prac"
                if value in P1P3trialStartVals:
                    significance = "trial_start"
                else:
                    significance = "trial_end"
                    P3practiceEnded = True
                    
            elif value == 158:
                trial = "N/A"
                significance = "main_trials_start"
            elif value == 159:
                trial = "N/A"
                significance = "main_trials_end"
                
            else:
                trial = str(j)
                if value in P1P3trialStartVals:
                    significance = "trial_start"
                elif value in P1P3trialEndVals:
                    significance = "trial_end"
                    j += 1
                    
            if value == 46: #These trials were about 42.7ms too long due to an error in expt setup.
            #For simplicity/consistency we trim the difference by moving end trigs forward.
                onset -= 0.043   
                
            writer.writerow([str(onset), duration, str(value), significance, trial])
            i += 1
            
            if significance == "main_trials_end" or i == len(ceegridLatencies):
                P3endLatency_ceegrid = onset + P3startLatency_ceegrid + filterBufferPeriod
                P3ended = True  
                         
        tsvfile.close
        
    partStartLatencies_ceegrid = [P1startLatency_ceegrid, P2startLatency_ceegrid, P3startLatency_ceegrid]
    partEndLatencies_ceegrid = [P1endLatency_ceegrid, P2endLatency_ceegrid, P3endLatency_ceegrid]
    partStartEndLatencies_ceegrid = np.stack([partStartLatencies_ceegrid, partEndLatencies_ceegrid])
        
    return partStartEndLatencies_scalp, partStartEndLatencies_ceegrid

#######################################################################################################################################################################################################
#######################################################################################################################################################################################################

#Version for using triggers from .txt file, including manually-corrected ones:
def poly52trigs_addCorrections(basePath, participantNumber,filterBufferPeriod):
    rawDataPath = basePath + 'sourcedata\P' + participantNumber + '\\'
    
    subjFolder = "sub-" + participantNumber
    
    correctionsFile_scalp = rawDataPath + 'P' + participantNumber + '_scalpCorrTrigs.txt'
    
    scalp_eegCodes = ([x.split()[0] for x in open(correctionsFile_scalp).readlines()])
    scalp_eegLatencies = ([x.split()[1] for x in open(correctionsFile_scalp).readlines()]) #Need to adjust this stuff..
    
    scalp_eegCodes.remove(scalp_eegCodes[0])
    scalp_eegLatencies.remove(scalp_eegLatencies[0])
    
    correctionsFile_ceegrid = rawDataPath + 'P' + participantNumber + '_ceegridCorrTrigs.txt'
    
    ceegridCodes = ([x.split()[0] for x in open(correctionsFile_ceegrid).readlines()])
    ceegridLatencies = ([x.split()[1] for x in open(correctionsFile_ceegrid).readlines()])
    
    ceegridCodes.remove(ceegridCodes[0])
    ceegridLatencies.remove(ceegridLatencies[0])

    #Convert all to ints:
    scalp_eegCodes = [int(i) for i in scalp_eegCodes]
    scalp_eegLatencies = [int(i) for i in scalp_eegLatencies]
    ceegridCodes = [int(i) for i in ceegridCodes]
    ceegridLatencies = [int(i) for i in ceegridLatencies]

#####################################################################################################################################################################
    #Good to run various checks: that there are the same number of events for the scalp/ceegrid files; that these do not contradict; and separately checking that events in
    #each are sensible. These are only rough and not exhaustive

    #Check same number of trigs recorded for scalp and ceegrid:
    num_scalp_eeg_events = len(scalp_eegCodes)
    num_ceegrid_events = len(ceegridCodes)
    difference = num_scalp_eeg_events - num_ceegrid_events
    if difference > 0:
        print("WARNING - MORE SCALP THAN CEEGRID EVENTS DETECTED")
        lesserEventCount = num_ceegrid_events
    elif difference < 0:
        print("WARNING - MORE CEEGRID EVENTS THAN SCALP EVENTS DETECTED")
        lesserEventCount = num_scalp_eeg_events
    else:
        print("Equal number of scalp and ceegrid events detected.")
        lesserEventCount = num_scalp_eeg_events #could use either 
        
    
    #Calculate no. of expected trigs, compare to recorded:   
    expectedTrigs = expectedTriggerCalculator(basePath, participantNumber)
    if expectedTrigs > num_scalp_eeg_events:
        diff = str(expectedTrigs - num_scalp_eeg_events)
        print("WARNING - " + diff + " SCALP EVENTS MISSING")#
    if expectedTrigs < num_scalp_eeg_events:
        diff = str(num_scalp_eeg_events - expectedTrigs)
        print("WARNING - " + diff + " EXCESS SCALP EVENTS DETECTED")
    if expectedTrigs > num_ceegrid_events:
        diff = str(expectedTrigs - num_ceegrid_events)
        print("WARNING - " + diff + " CEEGRID EVENTS MISSING")
    if expectedTrigs < num_ceegrid_events:
        diff = str(num_ceegrid_events - expectedTrigs)
        print("WARNING - " + diff + " EXCESS CEEGRID EVENTS DETECTED")
    if expectedTrigs == num_scalp_eeg_events and difference == 0:
        print("Good news: the number of trigs detected for both scalp and cEEGrid is what should be expected.")
    

    #Finally, check individual scalp and ceegrid trigs match up:
    x = 0
    for i in range(0, lesserEventCount):
        if scalp_eegCodes[i] != ceegridCodes[i]:
            print("WARNING - EVENT CODES DISCREPENCY")
            print("This is at the following sample in the scalp data: " + str(scalp_eegLatencies[i]))
            print("Alternatively, this is the following sample for the ceegrid data: " + str(ceegridLatencies[i]))
            
            
            #Single event checks. Note, if scalp/ceegrid EEG does have one or two more triggers, then will need to check the extra ones at the end
            #separately
         #  scalp_pattern = scalp_eeg.raw_events[i].get("pattern")
            scalp_code = scalp_eegCodes[i]
            
            if int(scalp_code) > 159:
                print("Scalp code value is too large.")
            
            ceegrid_code = ceegridCodes[i]
            
            if int(ceegrid_code) > 159:
                print("ceegrid code value is too large.")
                
            
            print("It is the " + str(i+1) + "th event in each data file. The scalp code is: " + str(scalp_code) + " and the ceegrid code is: " + str(ceegrid_code))
        if scalp_eegCodes[i] == ceegridCodes[i]:
            x += 1
            
    print(str(x) + " out of " + str(lesserEventCount) + " codes are the same between both data files. Note this assumes that the code numbers are the same, OR that if one file has more "
          + "events detected, these are at the end.")

#######################################################################################################################################################################################################
    #Save to files, in a BIDS-friendly format:
    
    outputDir = basePath + "bids_dataset\sub-" + participantNumber + "\eeg\\"
    outputDirExists = os.path.exists(outputDir)
    
    if not outputDirExists:
        os.makedirs(outputDir)
#######################################################################################################################################################################################################   
    #First, scalp:
    
    sfreq = 1000
    
    #Do this "task by task", i.e emotion decoding first etc:
    task1 = "emotion"
    filename = subjFolder + "_task-" + task1 + "_acq-scalp_events.tsv"
    scalpEvents_BIDS = (outputDir + filename)

    P1practiceEnded = False
    P1ended = False
    P2practiceEnded = False
    P2ended = False
    P3practiceEnded = False
    P3ended = False
    
    P1P3trialStartVals = np.arange(1, 73, 2) #Can reuse these later
    P1P3trialEndVals = np.arange(2, 74, 2)
    
    with open(scalpEvents_BIDS, 'w', newline='') as tsvfile:
        writer = csv.writer(tsvfile, delimiter='\t', lineterminator='\n')
        writer.writerow(["onset", "duration", "value", "significance", "trial"])
        i = 0
        j = 1 #For keeping track of main trials
        
        P1startLatency_scalp = scalp_eegLatencies[i]/sfreq - filterBufferPeriod
        duration = "0" #Throughout P1
        
        while P1ended == False:
            onset = scalp_eegLatencies[i]/sfreq - P1startLatency_scalp #So that the first trigger is at t = 0
            value = scalp_eegCodes[i]
                
            if P1practiceEnded == False:
                trial = "prac"
                if value in P1P3trialStartVals:
                    significance = "trial_start"
                else:
                    significance = "trial_end"
                    P1practiceEnded = True
                    
            elif value == 154:
                trial = "N/A"
                significance = "main_trials_start"
            elif value == 155:
                trial = "N/A"
                significance = "main_trials_end"
                
            else:
                trial = str(j)
                if value in P1P3trialStartVals:
                    significance = "trial_start"
                elif value in P1P3trialEndVals:
                    significance = "trial_end"
                    j += 1

            if value == 46: #These trials were about 42.7ms too long due to an error in expt setup.
            #For simplicity/consistency we trim the difference by moving end trigs forward.
                onset -= 0.043
                
            writer.writerow([str(onset), duration, str(value), significance, trial])
            i += 1
            
            if significance == "main_trials_end":
                P1endLatency_scalp = onset + P1startLatency_scalp + filterBufferPeriod
                P1ended = True  
                         
        tsvfile.close
    
    
    #P2:
    task2 = "attnMultInstOBs"    
    filename = subjFolder + "_task-" + task2 + "_acq-scalp_events.tsv"
    scalpEvents_BIDS = (outputDir + filename)

    P2trialStartVals = np.arange(73, 144, 2) #Can reuse these later
    P2trialEndVals = np.arange(74, 145, 2)
    P2attendedOBvals = np.array([145, 149, 153])
    P2unattendedOBvals = np.array([146, 147, 148, 150, 151, 152])    
    
    with open(scalpEvents_BIDS, 'w', newline='') as tsvfile:
        writer = csv.writer(tsvfile, delimiter='\t', lineterminator='\n')
        writer.writerow(["onset", "duration", "value", "significance", "trial"])
        
        #Continue to use i from before.
        j = 1 #For keeping track of prac trials
        k = 1 #"     "       "   "  main   "
        
        P2startLatency_scalp = scalp_eegLatencies[i]/sfreq - filterBufferPeriod
        
        while P2ended == False:
            onset = scalp_eegLatencies[i]/sfreq - P2startLatency_scalp
            value = scalp_eegCodes[i]
            
            if value == 156:
                trial = "N/A"
                significance = "main_trials_start"
                P2practiceEnded = True
                
            elif P2practiceEnded == False:
                trial = "prac_" + str(j)
                if value in P2trialStartVals:
                    significance = "trial_start"
                elif value in P2attendedOBvals:
                    significance = "attended_OB"
                elif value in P2unattendedOBvals:
                    significance = "unattended_OB"
                elif value in P2trialEndVals:
                    significance = "trial_end"
                    j += 1
                    
            elif value == 157:
                trial = "N/A"
                significance = "main_trials_end"
                
            else:
                trial = str(k)
                if value in P2trialStartVals:
                    significance = "trial_start"
                elif value in P2attendedOBvals:
                    significance = "attended_OB"
                elif value in P2unattendedOBvals:
                    significance = "unattended_OB"
                elif value in P2trialEndVals:
                    significance = "trial_end"
                    k += 1
                
            if "OB" in significance: #Oddballs
                duration = "0.49197278911"
            else:
                duration = "0"
            writer.writerow([str(onset), duration, str(value), significance, trial])
            i += 1
            
            if significance == "main_trials_end":
                P2endLatency_scalp = onset + P2startLatency_scalp + filterBufferPeriod
                P2ended = True  
                
        tsvfile.close
        
    #P3:
    task3 = "attnOneInstNoOBs"    
    filename = subjFolder + "_task-" + task3 + "_acq-scalp_events.tsv"
    scalpEvents_BIDS = (outputDir + filename)
        
    with open(scalpEvents_BIDS, 'w', newline='') as tsvfile:
        writer = csv.writer(tsvfile, delimiter='\t', lineterminator='\n')
        writer.writerow(["onset", "duration", "value", "significance", "trial"])
        j = 1 #For keeping track of main trials
        
        P3startLatency_scalp = scalp_eegLatencies[i]/sfreq - filterBufferPeriod
        duration = "0" #Should already be set, but if e.g triggers above are missed, this acts as a failsafe.
        
        while P3ended == False:
            onset = scalp_eegLatencies[i]/sfreq - P3startLatency_scalp #So that the first trigger is at t = 0
            value = scalp_eegCodes[i]
                
            if P3practiceEnded == False:
                trial = "prac"
                if value in P1P3trialStartVals:
                    significance = "trial_start"
                else:
                    significance = "trial_end"
                    P3practiceEnded = True
                    
            elif value == 158:
                trial = "N/A"
                significance = "main_trials_start"
            elif value == 159:
                trial = "N/A"
                significance = "main_trials_end"
                
            else:
                trial = str(j)
                if value in P1P3trialStartVals:
                    significance = "trial_start"
                elif value in P1P3trialEndVals:
                    significance = "trial_end"
                    j += 1

            if value == 46: #These trials were about 42.7ms too long due to an error in expt setup.
            #For simplicity/consistency we trim the difference by moving end trigs forward.
                onset -= 0.043
                
            writer.writerow([str(onset), duration, str(value), significance, trial])
            i += 1
            
            if significance == "main_trials_end" or i == len(scalp_eegLatencies):
                P3endLatency_scalp = onset + P3startLatency_scalp + filterBufferPeriod
                P3ended = True  
                         
        tsvfile.close
        
    partStartLatencies_scalp =[P1startLatency_scalp, P2startLatency_scalp, P3startLatency_scalp]
    partEndLatencies_scalp = [P1endLatency_scalp, P2endLatency_scalp, P3endLatency_scalp]
    partStartEndLatencies_scalp = np.stack([partStartLatencies_scalp, partEndLatencies_scalp])
        
#######################################################################################################################################################################################################
    #ceegrid:
        
    sfreq = 1000
    
    #Do this "task by task", i.e emotion decoding first etc:
    task1 = "emotion"
    filename = subjFolder + "_task-" + task1 + "_acq-ceegrid_events.tsv"
    ceegridEvents_BIDS = (outputDir + filename)

    P1practiceEnded = False
    P1ended = False
    P2practiceEnded = False
    P2ended = False
    P3practiceEnded = False
    P3ended = False
    
    P1P3trialStartVals = np.arange(1, 73, 2) #Can reuse these later
    P1P3trialEndVals = np.arange(2, 74, 2)
    
    with open(ceegridEvents_BIDS, 'w', newline='') as tsvfile:
        writer = csv.writer(tsvfile, delimiter='\t', lineterminator='\n')
        writer.writerow(["onset", "duration", "value", "significance", "trial"])
        i = 0
        j = 1 #For keeping track of main trials
        
        P1startLatency_ceegrid = ceegridLatencies[i]/sfreq - filterBufferPeriod
        
        while P1ended == False:
            onset = ceegridLatencies[i]/sfreq - P1startLatency_ceegrid #So that the first trigger is at t = 0
            value = ceegridCodes[i]
                
            if P1practiceEnded == False:
                trial = "prac"
                if value in P1P3trialStartVals:
                    significance = "trial_start"
                else:
                    significance = "trial_end"
                    P1practiceEnded = True
                    
            elif value == 154:
                trial = "N/A"
                significance = "main_trials_start"
            elif value == 155:
                trial = "N/A"
                significance = "main_trials_end"
                
            else:
                trial = str(j)
                if value in P1P3trialStartVals:
                    significance = "trial_start"
                elif value in P1P3trialEndVals:
                    significance = "trial_end"
                    j += 1

            if value == 46: #These trials were about 42.7ms too long due to an error in expt setup.
            #For simplicity/consistency we trim the difference by moving end trigs forward.
                onset -= 0.043
                
            writer.writerow([str(onset), duration, str(value), significance, trial])
            i += 1
            
            if significance == "main_trials_end":
                P1endLatency_ceegrid = onset + P1startLatency_ceegrid + filterBufferPeriod
                P1ended = True  
                         
        tsvfile.close
    
    
    #P2:
    task2 = "attnMultInstOBs"    
    filename = subjFolder + "_task-" + task2 + "_acq-ceegrid_events.tsv"
    ceegridEvents_BIDS = (outputDir + filename)

    P2trialStartVals = np.arange(73, 144, 2) #Can reuse these later
    P2trialEndVals = np.arange(74, 145, 2)
    P2attendedOBvals = np.array([145, 149, 153])
    P2unattendedOBvals = np.array([146, 147, 148, 150, 151, 152])    
    
    with open(ceegridEvents_BIDS, 'w', newline='') as tsvfile:
        writer = csv.writer(tsvfile, delimiter='\t', lineterminator='\n')
        writer.writerow(["onset", "duration", "value", "significance", "trial"])
        
        #Continue to use i from before.
        j = 1 #For keeping track of prac trials
        k = 1 #"     "       "   "  main   "
        
        P2startLatency_ceegrid = ceegridLatencies[i]/sfreq - filterBufferPeriod
        
        while P2ended == False:
            onset = ceegridLatencies[i]/sfreq - P2startLatency_ceegrid
            value = ceegridCodes[i]
            
            if value == 156:
                trial = "N/A"
                significance = "main_trials_start"
                P2practiceEnded = True
                
            elif P2practiceEnded == False:
                trial = "prac_" + str(j)
                if value in P2trialStartVals:
                    significance = "trial_start"
                elif value in P2attendedOBvals:
                    significance = "attended_OB"
                elif value in P2unattendedOBvals:
                    significance = "unattended_OB"
                elif value in P2trialEndVals:
                    significance = "trial_end"
                    j += 1
                    
                
            elif value == 157:
                trial = "N/A"
                significance = "main_trials_end"
                
            else:
                trial = str(k)
                if value in P2trialStartVals:
                    significance = "trial_start"
                elif value in P2attendedOBvals:
                    significance = "attended_OB"
                elif value in P2unattendedOBvals:
                    significance = "unattended_OB"
                elif value in P2trialEndVals:
                    significance = "trial_end"
                    k += 1
                    
            if "OB" in significance: #Oddballs
                duration = "0.49197278911"
            else:
                duration = "0"
                
            writer.writerow([str(onset), duration, str(value), significance, trial])
            i += 1
            
            if significance == "main_trials_end":
                P2endLatency_ceegrid = onset + P2startLatency_ceegrid + filterBufferPeriod
                P2ended = True  
                
        tsvfile.close
        
    #P3:
    task3 = "attnOneInstNoOBs"    
    filename = subjFolder + "_task-" + task3 + "_acq-ceegrid_events.tsv"
    ceegridEvents_BIDS = (outputDir + filename)
        
    with open(ceegridEvents_BIDS, 'w', newline='') as tsvfile:
        writer = csv.writer(tsvfile, delimiter='\t', lineterminator='\n')
        writer.writerow(["onset", "duration", "value", "significance", "trial"])
        j = 1 #For keeping track of main trials
        
        P3startLatency_ceegrid = ceegridLatencies[i]/sfreq - filterBufferPeriod
        duration = "0" #Should already be set, but if e.g triggers above are missed, this acts as a failsafe.
        
        while P3ended == False:
            onset = ceegridLatencies[i]/sfreq - P3startLatency_ceegrid #So that the first trigger is at t = 0
            value = ceegridCodes[i]
                
            if P3practiceEnded == False:
                trial = "prac"
                if value in P1P3trialStartVals:
                    significance = "trial_start"
                else:
                    significance = "trial_end"
                    P3practiceEnded = True
                    
            elif value == 158:
                trial = "N/A"
                significance = "main_trials_start"
            elif value == 159:
                trial = "N/A"
                significance = "main_trials_end"
                
            else:
                trial = str(j)
                if value in P1P3trialStartVals:
                    significance = "trial_start"
                elif value in P1P3trialEndVals:
                    significance = "trial_end"
                    j += 1
                    
            if value == 46: #These trials were about 42.7ms too long due to an error in expt setup.
            #For simplicity/consistency we trim the difference by moving end trigs forward.
                onset -= 0.043
                        
            writer.writerow([str(onset), duration, str(value), significance, trial])
            i += 1
            
            if significance == "main_trials_end" or i == len(ceegridLatencies):
                P3endLatency_ceegrid = onset + P3startLatency_ceegrid + filterBufferPeriod
                P3ended = True  
                         
        tsvfile.close
        
    partStartLatencies_ceegrid = [P1startLatency_ceegrid, P2startLatency_ceegrid, P3startLatency_ceegrid]
    partEndLatencies_ceegrid = [P1endLatency_ceegrid, P2endLatency_ceegrid, P3endLatency_ceegrid]
    partStartEndLatencies_ceegrid = np.stack([partStartLatencies_ceegrid, partEndLatencies_ceegrid])
        
    return partStartEndLatencies_scalp, partStartEndLatencies_ceegrid
    
#######################################################################################################################################################################################################
#######################################################################################################################################################################################################

#Version for converting if no ceegrid data:
def poly52trigs_no_ceegrid(basePath, participantNumber, filterBufferPeriod):
    rawDataPath = basePath + 'sourcedata\P' + participantNumber + '\\'
    scalpFilename = "P" + participantNumber + "_scalp.Poly5"
    
    SCALP_EEG = rawDataPath + scalpFilename
    
    subjFolder = "sub-" + participantNumber

    TRIGGER_CLK = 16
    THR_ERROR = -0.05
    TRANS_ERROR = 0.1

    #read scalp poly5
    scalp_eeg = poly52POPO(SCALP_EEG, 'scalp')
    scalp_eeg.decode_events(triggerClk=TRIGGER_CLK, thrError=THR_ERROR, transError=TRANS_ERROR)
    scalp_eegCodes = [ sub['code'] for sub in scalp_eeg.raw_events ]


#####################################################################################################################################################################
    #Good to check that the number of trigs is as expected:

    num_scalp_eeg_events = len(scalp_eeg.raw_events)

    #Calculate no. of expected trigs, compare to actual:  
    expectedTrigs = expectedTriggerCalculator(basePath, participantNumber)

    if expectedTrigs > num_scalp_eeg_events:
        diff = str(expectedTrigs - num_scalp_eeg_events)
        print("WARNING - " + diff + " SCALP EVENTS MISSING")#
    if expectedTrigs < num_scalp_eeg_events:
        diff = str(num_scalp_eeg_events - expectedTrigs)
        print("WARNING - " + diff + " EXCESS SCALP EVENTS DETECTED")


#######################################################################################################################################################################################################
#######################################################################################################################################################################################################
    #Save to files, in a BIDS-friendly format:
    
    outputDir = basePath + "bids_dataset\sub-" + participantNumber + "\eeg\\"
    outputDirExists = os.path.exists(outputDir)
    
    if not outputDirExists:
        os.makedirs(outputDir)
#######################################################################################################################################################################################################   
    
    scalp_eegLatencies = [ sub['sample_idx'] for sub in scalp_eeg.raw_events ]
    sfreq = 1000
    
    #Do this "task by task", i.e emotion decoding first etc:
    task1 = "emotion"
    filename = subjFolder + "_task-" + task1 + "_acq-scalp_events.tsv"
    scalpEvents_BIDS = (outputDir + filename)

    P1practiceEnded = False
    P1ended = False
    P2practiceEnded = False
    P2ended = False
    P3practiceEnded = False
    P3ended = False
    
    P1P3trialStartVals = np.arange(1, 73, 2) #Can reuse these later
    P1P3trialEndVals = np.arange(2, 74, 2)
    
    with open(scalpEvents_BIDS, 'w', newline='') as tsvfile:
        writer = csv.writer(tsvfile, delimiter='\t', lineterminator='\n')
        writer.writerow(["onset", "duration", "value", "significance", "trial"])
        i = 0
        j = 1 #For keeping track of main trials
        
        P1startLatency_scalp = scalp_eegLatencies[i]/sfreq - filterBufferPeriod
        duration = "0" #Throughout P1
        
        while P1ended == False:
            onset = scalp_eegLatencies[i]/sfreq - P1startLatency_scalp #So that the first trigger is at t = 0
            value = scalp_eegCodes[i]
                
            if P1practiceEnded == False:
                trial = "prac"
                if value in P1P3trialStartVals:
                    significance = "trial_start"
                else:
                    significance = "trial_end"
                    P1practiceEnded = True
                    
            elif value == 154:
                trial = "N/A"
                significance = "main_trials_start"
            elif value == 155:
                trial = "N/A"
                significance = "main_trials_end"
                
            else:
                trial = str(j)
                if value in P1P3trialStartVals:
                    significance = "trial_start"
                elif value in P1P3trialEndVals:
                    significance = "trial_end"
                    j += 1
                
            if value == 46: #These trials were about 42.7ms too long due to an error in expt setup.
            #For simplicity/consistency we trim the difference by moving end trigs forward.
                onset -= 0.043
                    
            writer.writerow([str(onset), duration, str(value), significance, trial])
            i += 1
            
            if significance == "main_trials_end":
                P1endLatency_scalp = onset + P1startLatency_scalp + filterBufferPeriod
                P1ended = True  
                         
        tsvfile.close
    
    
    #P2:
    task2 = "attnMultInstOBs"    
    filename = subjFolder + "_task-" + task2 + "_acq-scalp_events.tsv"
    scalpEvents_BIDS = (outputDir + filename)

    P2trialStartVals = np.arange(73, 144, 2) #Can reuse these later
    P2trialEndVals = np.arange(74, 145, 2)
    P2attendedOBvals = np.array([145, 149, 153])
    P2unattendedOBvals = np.array([146, 147, 148, 150, 151, 152])    
    
    with open(scalpEvents_BIDS, 'w', newline='') as tsvfile:
        writer = csv.writer(tsvfile, delimiter='\t', lineterminator='\n')
        writer.writerow(["onset", "duration", "value", "significance", "trial"])
        
        #Continue to use i from before.
        j = 1 #For keeping track of prac trials
        k = 1 #"     "       "   "  main   "
        
        P2startLatency_scalp = scalp_eegLatencies[i]/sfreq - filterBufferPeriod
        
        while P2ended == False:
            onset = scalp_eegLatencies[i]/sfreq - P2startLatency_scalp
            value = scalp_eegCodes[i]
            
            if value == 156:
                trial = "N/A"
                significance = "main_trials_start"
                P2practiceEnded = True
                
            elif P2practiceEnded == False:
                trial = "prac_" + str(j)
                if value in P2trialStartVals:
                    significance = "trial_start"
                elif value in P2attendedOBvals:
                    significance = "attended_OB"
                elif value in P2unattendedOBvals:
                    significance = "unattended_OB"
                elif value in P2trialEndVals:
                    significance = "trial_end"
                    j += 1
                    
            elif value == 157:
                trial = "N/A"
                significance = "main_trials_end"
                
            else:
                trial = str(k)
                if value in P2trialStartVals:
                    significance = "trial_start"
                elif value in P2attendedOBvals:
                    significance = "attended_OB"
                elif value in P2unattendedOBvals:
                    significance = "unattended_OB"
                elif value in P2trialEndVals:
                    significance = "trial_end"
                    k += 1
                
            if "OB" in significance: #Oddballs
                duration = "0.49197278911"
            else:
                duration = "0"
            writer.writerow([str(onset), duration, str(value), significance, trial])
            i += 1
            
            if significance == "main_trials_end":
                P2endLatency_scalp = onset + P2startLatency_scalp + filterBufferPeriod
                P2ended = True  
                
        tsvfile.close
        
    #P3:
    task3 = "attnOneInstNoOBs"    
    filename = subjFolder + "_task-" + task3 + "_acq-scalp_events.tsv"
    scalpEvents_BIDS = (outputDir + filename)
        
    with open(scalpEvents_BIDS, 'w', newline='') as tsvfile:
        writer = csv.writer(tsvfile, delimiter='\t', lineterminator='\n')
        writer.writerow(["onset", "duration", "value", "significance", "trial"])
        j = 1 #For keeping track of main trials
        
        P3startLatency_scalp = scalp_eegLatencies[i]/sfreq - filterBufferPeriod
        duration = "0" #Should already be set, but if e.g triggers above are missed, this acts as a failsafe.
        
        while P3ended == False:
            onset = scalp_eegLatencies[i]/sfreq - P3startLatency_scalp #So that the first trigger is at t = 0
            value = scalp_eegCodes[i]
                
            if P3practiceEnded == False:
                trial = "prac"
                if value in P1P3trialStartVals:
                    significance = "trial_start"
                else:
                    significance = "trial_end"
                    P3practiceEnded = True
                    
            elif value == 158:
                trial = "N/A"
                significance = "main_trials_start"
            elif value == 159:
                trial = "N/A"
                significance = "main_trials_end"
                
            else:
                trial = str(j)
                if value in P1P3trialStartVals:
                    significance = "trial_start"
                elif value in P1P3trialEndVals:
                    significance = "trial_end"
                    j += 1
                
            if value == 46: #These trials were about 42.7ms too long due to an error in expt setup.
            #For simplicity/consistency we trim the difference by moving end trigs forward.
                onset -= 0.043
                
            writer.writerow([str(onset), duration, str(value), significance, trial])
            i += 1
            
            if significance == "main_trials_end" or i == len(scalp_eegLatencies):
                P3endLatency_scalp = onset + P3startLatency_scalp + filterBufferPeriod
                P3ended = True  
                         
        tsvfile.close
        
    partStartLatencies_scalp =[P1startLatency_scalp, P2startLatency_scalp, P3startLatency_scalp]
    partEndLatencies_scalp = [P1endLatency_scalp, P2endLatency_scalp, P3endLatency_scalp]
    partStartEndLatencies_scalp = np.stack([partStartLatencies_scalp, partEndLatencies_scalp])
        
    return partStartEndLatencies_scalp

#####################################################################################################################################################################
#####################################################################################################################################################################

#Version for converting if no ceegrid data; this version also involves using triggers from .txt file, including manually-corrected ones:
def poly52trigs_no_ceegrid_addCorrections(basePath, participantNumber,filterBufferPeriod):
    rawDataPath = basePath + 'sourcedata\P' + participantNumber + '\\'
    
    subjFolder = "sub-" + participantNumber
    
    correctionsFile_scalp = rawDataPath + 'P' + participantNumber + '_scalpCorrTrigs.txt'
    
    scalp_eegCodes = ([x.split()[0] for x in open(correctionsFile_scalp).readlines()])
    scalp_eegLatencies = ([x.split()[1] for x in open(correctionsFile_scalp).readlines()])#Need to adjust this stuff..
    
    scalp_eegCodes.remove(scalp_eegCodes[0])
    scalp_eegLatencies.remove(scalp_eegLatencies[0])

    #Convert all to ints:
    scalp_eegCodes = [int(i) for i in scalp_eegCodes]
    scalp_eegLatencies = [int(i) for i in scalp_eegLatencies]

#####################################################################################################################################################################
    #Good to check that the number of trigs is as expected:

    num_scalp_eeg_events = len(scalp_eegCodes)

    #Calculate no. of expected trigs, compare to actual:  
    expectedTrigs = expectedTriggerCalculator(basePath, participantNumber)

    if expectedTrigs > num_scalp_eeg_events:
        diff = str(expectedTrigs - num_scalp_eeg_events)
        print("WARNING - " + diff + " SCALP EVENTS MISSING")#
    if expectedTrigs < num_scalp_eeg_events:
        diff = str(num_scalp_eeg_events - expectedTrigs)
        print("WARNING - " + diff + " EXCESS SCALP EVENTS DETECTED")

#######################################################################################################################################################################################################
    #Save to files, in a BIDS-friendly format:
    
    outputDir = basePath + "bids_dataset\sub-" + participantNumber + "\eeg\\"
    outputDirExists = os.path.exists(outputDir)
    
    if not outputDirExists:
        os.makedirs(outputDir)
#######################################################################################################################################################################################################   
    
    sfreq = 1000
    
    #Do this "task by task", i.e emotion decoding first etc:
    task1 = "emotion"
    filename = subjFolder + "_task-" + task1 + "_acq-scalp_events.tsv"
    scalpEvents_BIDS = (outputDir + filename)

    P1practiceEnded = False
    P1ended = False
    P2practiceEnded = False
    P2ended = False
    P3practiceEnded = False
    P3ended = False
    
    P1P3trialStartVals = np.arange(1, 73, 2) #Can reuse these later
    P1P3trialEndVals = np.arange(2, 74, 2)
    
    with open(scalpEvents_BIDS, 'w', newline='') as tsvfile:
        writer = csv.writer(tsvfile, delimiter='\t', lineterminator='\n')
        writer.writerow(["onset", "duration", "value", "significance", "trial"])
        i = 0
        j = 1 #For keeping track of main trials
        
        P1startLatency_scalp = scalp_eegLatencies[i]/sfreq - filterBufferPeriod
        duration = "0" #Throughout P1
        
        while P1ended == False:
            onset = scalp_eegLatencies[i]/sfreq - P1startLatency_scalp #So that the first trigger is at t = 0
            value = scalp_eegCodes[i]
                
            if P1practiceEnded == False:
                trial = "prac"
                if value in P1P3trialStartVals:
                    significance = "trial_start"
                else:
                    significance = "trial_end"
                    P1practiceEnded = True
                    
            elif value == 154:
                trial = "N/A"
                significance = "main_trials_start"
            elif value == 155:
                trial = "N/A"
                significance = "main_trials_end"
                
            else:
                trial = str(j)
                if value in P1P3trialStartVals:
                    significance = "trial_start"
                elif value in P1P3trialEndVals:
                    significance = "trial_end"
                    j += 1
                
            if value == 46: #These trials were about 42.7ms too long due to an error in expt setup.
            #For simplicity/consistency we trim the difference by moving end trigs forward.
                onset -= 0.043
                    
            writer.writerow([str(onset), duration, str(value), significance, trial])
            i += 1
            
            if significance == "main_trials_end":
                P1endLatency_scalp = onset + P1startLatency_scalp + filterBufferPeriod
                P1ended = True  
                         
        tsvfile.close
    
    
    #P2:
    task2 = "attnMultInstOBs"    
    filename = subjFolder + "_task-" + task2 + "_acq-scalp_events.tsv"
    scalpEvents_BIDS = (outputDir + filename)

    P2trialStartVals = np.arange(73, 144, 2) #Can reuse these later
    P2trialEndVals = np.arange(74, 145, 2)
    P2attendedOBvals = np.array([145, 149, 153])
    P2unattendedOBvals = np.array([146, 147, 148, 150, 151, 152])    
    
    with open(scalpEvents_BIDS, 'w', newline='') as tsvfile:
        writer = csv.writer(tsvfile, delimiter='\t', lineterminator='\n')
        writer.writerow(["onset", "duration", "value", "significance", "trial"])
        
        #Continue to use i from before.
        j = 1 #For keeping track of prac trials
        k = 1 #"     "       "   "  main   "
        
        P2startLatency_scalp = scalp_eegLatencies[i]/sfreq - filterBufferPeriod
        
        while P2ended == False:
            onset = scalp_eegLatencies[i]/sfreq - P2startLatency_scalp
            value = scalp_eegCodes[i]
            
            if value == 156:
                trial = "N/A"
                significance = "main_trials_start"
                P2practiceEnded = True
                
            elif P2practiceEnded == False:
                trial = "prac_" + str(j)
                if value in P2trialStartVals:
                    significance = "trial_start"
                elif value in P2attendedOBvals:
                    significance = "attended_OB"
                elif value in P2unattendedOBvals:
                    significance = "unattended_OB"
                elif value in P2trialEndVals:
                    significance = "trial_end"
                    j += 1
                    
            elif value == 157:
                trial = "N/A"
                significance = "main_trials_end"
                
            else:
                trial = str(k)
                if value in P2trialStartVals:
                    significance = "trial_start"
                elif value in P2attendedOBvals:
                    significance = "attended_OB"
                elif value in P2unattendedOBvals:
                    significance = "unattended_OB"
                elif value in P2trialEndVals:
                    significance = "trial_end"
                    k += 1
                
            if "OB" in significance: #Oddballs
                duration = "0.49197278911"
            else:
                duration = "0"
            writer.writerow([str(onset), duration, str(value), significance, trial])
            i += 1
            
            if significance == "main_trials_end":
                P2endLatency_scalp = onset + P2startLatency_scalp + filterBufferPeriod
                P2ended = True  
                
        tsvfile.close
        
    #P3:
    task3 = "attnOneInstNoOBs"    
    filename = subjFolder + "_task-" + task3 + "_acq-scalp_events.tsv"
    scalpEvents_BIDS = (outputDir + filename)
        
    with open(scalpEvents_BIDS, 'w', newline='') as tsvfile:
        writer = csv.writer(tsvfile, delimiter='\t', lineterminator='\n')
        writer.writerow(["onset", "duration", "value", "significance", "trial"])
        j = 1 #For keeping track of main trials
        
        P3startLatency_scalp = scalp_eegLatencies[i]/sfreq - filterBufferPeriod
        duration = "0" #Should already be set, but if e.g triggers above are missed, this acts as a failsafe.
        
        while P3ended == False:
            onset = scalp_eegLatencies[i]/sfreq - P3startLatency_scalp #So that the first trigger is at t = 0
            value = scalp_eegCodes[i]
                
            if P3practiceEnded == False:
                trial = "prac"
                if value in P1P3trialStartVals:
                    significance = "trial_start"
                else:
                    significance = "trial_end"
                    P3practiceEnded = True
                    
            elif value == 158:
                trial = "N/A"
                significance = "main_trials_start"
            elif value == 159:
                trial = "N/A"
                significance = "main_trials_end"
                
            else:
                trial = str(j)
                if value in P1P3trialStartVals:
                    significance = "trial_start"
                elif value in P1P3trialEndVals:
                    significance = "trial_end"
                    j += 1
                    
            if value == 46: #These trials were about 42.7ms too long due to an error in expt setup.
            #For simplicity/consistency we trim the difference by moving end trigs forward.
                onset -= 0.043
                
            writer.writerow([str(onset), duration, str(value), significance, trial])
            i += 1
            
            if significance == "main_trials_end" or i == len(scalp_eegLatencies):
                P3endLatency_scalp = onset + P3startLatency_scalp + filterBufferPeriod
                P3ended = True  
                         
        tsvfile.close
        
    partStartLatencies_scalp =[P1startLatency_scalp, P2startLatency_scalp, P3startLatency_scalp]
    partEndLatencies_scalp = [P1endLatency_scalp, P2endLatency_scalp, P3endLatency_scalp]
    partStartEndLatencies_scalp = np.stack([partStartLatencies_scalp, partEndLatencies_scalp])
        
    return partStartEndLatencies_scalp

#####################################################################################################################################################################
#####################################################################################################################################################################

#Version to convert for one participant with only partial ceegrid data; this version also involves using triggers from .txt file, including manually-corrected ones.
#Keeping in the scalp vs. ceegrid trig checks early on, as all of the ceegrid trigs recorded OK, and these are useful to have. Also, leaving the code generalisable
#as much as possible.
def poly52trigs_partial_ceegrid_addCorrections(basePath, participantNumber, filterBufferPeriod):  
    rawDataPath = basePath + 'sourcedata\P' + participantNumber + '\\'
    
    subjFolder = "sub-" + participantNumber
    
    correctionsFile_scalp = rawDataPath + 'P' + participantNumber + '_scalpCorrTrigs.txt'
    
    scalp_eegCodes = ([x.split()[0] for x in open(correctionsFile_scalp).readlines()])
    scalp_eegLatencies = ([x.split()[1] for x in open(correctionsFile_scalp).readlines()]) #Need to adjust this stuff..
    
    scalp_eegCodes.remove(scalp_eegCodes[0])
    scalp_eegLatencies.remove(scalp_eegLatencies[0])
    
    correctionsFile_ceegrid = rawDataPath + 'P' + participantNumber + '_ceegridCorrTrigs.txt'
    
    ceegridCodes = ([x.split()[0] for x in open(correctionsFile_ceegrid).readlines()])
    ceegridLatencies = ([x.split()[1] for x in open(correctionsFile_ceegrid).readlines()])
    
    ceegridCodes.remove(ceegridCodes[0])
    ceegridLatencies.remove(ceegridLatencies[0])

    #Convert all to ints:
    scalp_eegCodes = [int(i) for i in scalp_eegCodes]
    scalp_eegLatencies = [int(i) for i in scalp_eegLatencies]
    ceegridCodes = [int(i) for i in ceegridCodes]
    ceegridLatencies = [int(i) for i in ceegridLatencies]
#####################################################################################################################################################################
    #Good to run various checks: that there are the same number of events for the scalp/ceegrid files; that these do not contradict; and separately checking that events in
    #each are sensible. These are only rough and not exhaustive

    #Check same number of trigs recorded for scalp and ceegrid:
    num_scalp_eeg_events = len(scalp_eegCodes)
    num_ceegrid_events = len(ceegridCodes)
    difference = num_scalp_eeg_events - num_ceegrid_events
    if difference > 0:
        print("WARNING - MORE SCALP THAN CEEGRID EVENTS DETECTED")
        lesserEventCount = num_ceegrid_events
    elif difference < 0:
        print("WARNING - MORE CEEGRID EVENTS THAN SCALP EVENTS DETECTED")
        lesserEventCount = num_scalp_eeg_events
    else:
        print("Equal number of scalp and ceegrid events detected.")
        lesserEventCount = num_scalp_eeg_events #could use either 
        
    
    #Calculate no. of expected trigs, compare to recorded:   
    expectedTrigs = expectedTriggerCalculator(basePath, participantNumber)

    if expectedTrigs > num_scalp_eeg_events:
        diff = str(expectedTrigs - num_scalp_eeg_events)
        print("WARNING - " + diff + " SCALP EVENTS MISSING")#
    if expectedTrigs < num_scalp_eeg_events:
        diff = str(num_scalp_eeg_events - expectedTrigs)
        print("WARNING - " + diff + " EXCESS SCALP EVENTS DETECTED")
    if expectedTrigs > num_ceegrid_events:
        diff = str(expectedTrigs - num_ceegrid_events)
        print("WARNING - CEEGRID EVENTS MISSING")
    if expectedTrigs < num_ceegrid_events:
        diff = str(num_ceegrid_events - expectedTrigs)
        print("WARNING - " + diff + " EXCESS CEEGRID EVENTS DETECTED")
    if expectedTrigs == num_scalp_eeg_events and difference == 0:
        print("Good news: the number of trigs detected for both scalp and cEEGrid is what should be expected.")
    

    #Finally, check individual scalp and ceegrid trigs match up:
    x = 0
    for i in range(0, lesserEventCount):
        if scalp_eegCodes[i] != ceegridCodes[i]:
            print("WARNING - EVENT CODES DISCREPENCY")
            print("This is at the following sample in the scalp data: " + str(scalp_eegLatencies[i]))
            print("Alternatively, this is the following sample for the ceegrid data: " + str(ceegridLatencies[i]))
            
            
            #Single event checks. Note, if scalp/ceegrid EEG does have one or two more triggers, then will need to check the extra ones at the end
            #separately
         #  scalp_pattern = scalp_eeg.raw_events[i].get("pattern")
            scalp_code = scalp_eegCodes[i]
            
            if int(scalp_code) > 159:
                print("Scalp code value is too large.")
            
            ceegrid_code = ceegridCodes[i]
            
            if int(ceegrid_code) > 159:
                print("ceegrid code value is too large.")
                
            
            print("It is the " + str(i+1) + "th event in each data file. The scalp code is: " + str(scalp_code) + " and the ceegrid code is: " + str(ceegrid_code))
        if scalp_eegCodes[i] == ceegridCodes[i]:
            x += 1
            
    print(str(x) + " out of " + str(lesserEventCount) + " codes are the same between both data files. Note this assumes that the code numbers are the same, OR that if one file has more "
          + "events detected, these are at the end.")
    
#######################################################################################################################################################################################################
    #Save to files, in a BIDS-friendly format:
    
    outputDir = basePath + "bids_dataset\sub-" + participantNumber + "\eeg\\"
    outputDirExists = os.path.exists(outputDir)
    
    if not outputDirExists:
        os.makedirs(outputDir)
#######################################################################################################################################################################################################   
    #First, scalp:
    
    sfreq = 1000
    
    #Do this "task by task", i.e emotion decoding first etc:
    task1 = "emotion"
    filename = subjFolder + "_task-" + task1 + "_acq-scalp_events.tsv"
    scalpEvents_BIDS = (outputDir + filename)

    P1practiceEnded = False
    P1ended = False
    P2practiceEnded = False
    P2ended = False
    P3practiceEnded = False
    P3ended = False
    
    P1P3trialStartVals = np.arange(1, 73, 2) #Can reuse these later
    P1P3trialEndVals = np.arange(2, 74, 2)
    
    with open(scalpEvents_BIDS, 'w', newline='') as tsvfile:
        writer = csv.writer(tsvfile, delimiter='\t', lineterminator='\n')
        writer.writerow(["onset", "duration", "value", "significance", "trial"])
        i = 0
        j = 1 #For keeping track of main trials
        
        P1startLatency_scalp = scalp_eegLatencies[i]/sfreq - filterBufferPeriod
        duration = "0" #Throughout P1
        
        while P1ended == False:
            onset = scalp_eegLatencies[i]/sfreq - P1startLatency_scalp #So that the first trigger is at t = 0
            value = scalp_eegCodes[i]
                
            if P1practiceEnded == False:
                trial = "prac"
                if value in P1P3trialStartVals:
                    significance = "trial_start"
                else:
                    significance = "trial_end"
                    P1practiceEnded = True
                    
            elif value == 154:
                trial = "N/A"
                significance = "main_trials_start"
            elif value == 155:
                trial = "N/A"
                significance = "main_trials_end"
                
            else:
                trial = str(j)
                if value in P1P3trialStartVals:
                    significance = "trial_start"
                elif value in P1P3trialEndVals:
                    significance = "trial_end"
                    j += 1
                    
            if value == 46: #These trials were about 42.7ms too long due to an error in expt setup.
            #For simplicity/consistency we trim the difference by moving end trigs forward.
                onset -= 0.043
                
            writer.writerow([str(onset), duration, str(value), significance, trial])
            i += 1
            
            if significance == "main_trials_end":
                P1endLatency_scalp = onset + P1startLatency_scalp + filterBufferPeriod
                P1ended = True  
                         
        tsvfile.close
    
    
    #P2:
    task2 = "attnMultInstOBs"    
    filename = subjFolder + "_task-" + task2 + "_acq-scalp_events.tsv"
    scalpEvents_BIDS = (outputDir + filename)

    P2trialStartVals = np.arange(73, 144, 2) #Can reuse these later
    P2trialEndVals = np.arange(74, 145, 2)
    P2attendedOBvals = np.array([145, 149, 153])
    P2unattendedOBvals = np.array([146, 147, 148, 150, 151, 152])    
    
    with open(scalpEvents_BIDS, 'w', newline='') as tsvfile:
        writer = csv.writer(tsvfile, delimiter='\t', lineterminator='\n')
        writer.writerow(["onset", "duration", "value", "significance", "trial"])
        
        #Continue to use i from before.
        j = 1 #For keeping track of prac trials
        k = 1 #"     "       "   "  main   "
        
        P2startLatency_scalp = scalp_eegLatencies[i]/sfreq - filterBufferPeriod
        
        while P2ended == False:
            onset = scalp_eegLatencies[i]/sfreq - P2startLatency_scalp
            value = scalp_eegCodes[i]
            
            if value == 156:
                trial = "N/A"
                significance = "main_trials_start"
                P2practiceEnded = True
                
            elif P2practiceEnded == False:
                trial = "prac_" + str(j)
                if value in P2trialStartVals:
                    significance = "trial_start"
                elif value in P2attendedOBvals:
                    significance = "attended_OB"
                elif value in P2unattendedOBvals:
                    significance = "unattended_OB"
                elif value in P2trialEndVals:
                    significance = "trial_end"
                    j += 1
                    
            elif value == 157:
                trial = "N/A"
                significance = "main_trials_end"
                
            else:
                trial = str(k)
                if value in P2trialStartVals:
                    significance = "trial_start"
                elif value in P2attendedOBvals:
                    significance = "attended_OB"
                elif value in P2unattendedOBvals:
                    significance = "unattended_OB"
                elif value in P2trialEndVals:
                    significance = "trial_end"
                    k += 1
                
            if "OB" in significance: #Oddballs
                duration = "0.49197278911"
            else:
                duration = "0"
            writer.writerow([str(onset), duration, str(value), significance, trial])
            i += 1
            
            if significance == "main_trials_end":
                P2endLatency_scalp = onset + P2startLatency_scalp + filterBufferPeriod
                P2ended = True  
                
        tsvfile.close
        
    #P3:
    task3 = "attnOneInstNoOBs"    
    filename = subjFolder + "_task-" + task3 + "_acq-scalp_events.tsv"
    scalpEvents_BIDS = (outputDir + filename)
        
    with open(scalpEvents_BIDS, 'w', newline='') as tsvfile:
        writer = csv.writer(tsvfile, delimiter='\t', lineterminator='\n')
        writer.writerow(["onset", "duration", "value", "significance", "trial"])
        j = 1 #For keeping track of main trials
        
        P3startLatency_scalp = scalp_eegLatencies[i]/sfreq - filterBufferPeriod
        duration = "0" #Should already be set, but if e.g., triggers above are missed, this acts as a failsafe.
        
        while P3ended == False:
            onset = scalp_eegLatencies[i]/sfreq - P3startLatency_scalp #So that the first trigger is at t = 0
            value = scalp_eegCodes[i]
                
            if P3practiceEnded == False:
                trial = "prac"
                if value in P1P3trialStartVals:
                    significance = "trial_start"
                else:
                    significance = "trial_end"
                    P3practiceEnded = True
                    
            elif value == 158:
                trial = "N/A"
                significance = "main_trials_start"
            elif value == 159:
                trial = "N/A"
                significance = "main_trials_end"
                
            else:
                trial = str(j)
                if value in P1P3trialStartVals:
                    significance = "trial_start"
                elif value in P1P3trialEndVals:
                    significance = "trial_end"
                    j += 1
                    
            if value == 46: #These trials were about 42.7ms too long due to an error in expt setup.
            #For simplicity/consistency we trim the difference by moving end trigs forward.
                onset -= 0.043
                
            writer.writerow([str(onset), duration, str(value), significance, trial])
            i += 1
            
            if significance == "main_trials_end" or i == len(scalp_eegLatencies):
                P3endLatency_scalp = onset + P3startLatency_scalp + filterBufferPeriod
                P3ended = True  
                         
        tsvfile.close
        
    partStartLatencies_scalp =[P1startLatency_scalp, P2startLatency_scalp, P3startLatency_scalp]
    partEndLatencies_scalp = [P1endLatency_scalp, P2endLatency_scalp, P3endLatency_scalp]
    partStartEndLatencies_scalp = np.stack([partStartLatencies_scalp, partEndLatencies_scalp])
        
#######################################################################################################################################################################################################
    #ceegrid:
        
    sfreq = 1000
    
    #From careful inspection, already found which trials have no ground so will just input start/end latencies here manually:
    #For P2endLatency_ceegrid, choosing 1s AFTER the last OK trial ends.
    #For P3startLatency_ceegrid, choosing 1s BEFORE the first OK trial starts.
    #We also add/subtract filterBufferPeriod to those respectively (these periods don't include data without the ground).
    P2earlyStopLatency_ceegrid = 1544141/sfreq
    P3lateStartLatency_ceegrid = 2694658/sfreq
    P2endLatency_ceegrid = P2earlyStopLatency_ceegrid + filterBufferPeriod
    P3startLatency_ceegrid = P3lateStartLatency_ceegrid - filterBufferPeriod
    
    #Do this "task by task", i.e emotion decoding first etc:
    task1 = "emotion"
    filename = subjFolder + "_task-" + task1 + "_acq-ceegrid_events.tsv"
    ceegridEvents_BIDS = (outputDir + filename)

    P1practiceEnded = False
    P1ended = False
    P2practiceEnded = False
    P2ended = False
    P3practiceEnded = False
    P3ended = False
    
    P1P3trialStartVals = np.arange(1, 73, 2) #Can reuse these later
    P1P3trialEndVals = np.arange(2, 74, 2)
    
    with open(ceegridEvents_BIDS, 'w', newline='') as tsvfile:
        writer = csv.writer(tsvfile, delimiter='\t', lineterminator='\n')
        writer.writerow(["onset", "duration", "value", "significance", "trial"])
        i = 0
        j = 1 #For keeping track of main trials
        
        P1startLatency_ceegrid = ceegridLatencies[i]/sfreq - filterBufferPeriod
        
        while P1ended == False:
            onset = ceegridLatencies[i]/sfreq - P1startLatency_ceegrid #So that the first trigger is at t = 0
            value = ceegridCodes[i]
                
            if P1practiceEnded == False:
                trial = "prac"
                if value in P1P3trialStartVals:
                    significance = "trial_start"
                else:
                    significance = "trial_end"
                    P1practiceEnded = True
                    
            elif value == 154:
                trial = "N/A"
                significance = "main_trials_start"
            elif value == 155:
                trial = "N/A"
                significance = "main_trials_end"
                
            else:
                trial = str(j)
                if value in P1P3trialStartVals:
                    significance = "trial_start"
                elif value in P1P3trialEndVals:
                    significance = "trial_end"
                    j += 1
                
            if value == 46: #These trials were about 42.7ms too long due to an error in expt setup.
            #For simplicity/consistency we trim the difference by moving end trigs forward.
                onset -= 0.043
                
            writer.writerow([str(onset), duration, str(value), significance, trial])
            i += 1
            
            if significance == "main_trials_end":
                P1endLatency_ceegrid = onset + P1startLatency_ceegrid + filterBufferPeriod
                P1ended = True  

    #P2. We don't use P2 data but kept here as a 'placeholder'/to prevent confusion w/ P3.
    task2 = "attnMultInstOBs"    
    filename = subjFolder + "_task-" + task2 + "_acq-ceegrid_events.tsv"
    ceegridEvents_BIDS = (outputDir + filename)

    P2trialStartVals = np.arange(73, 144, 2) #Can reuse these later
    P2trialEndVals = np.arange(74, 145, 2)
    P2attendedOBvals = np.array([145, 149, 153])
    P2unattendedOBvals = np.array([146, 147, 148, 150, 151, 152])    
    
    with open(ceegridEvents_BIDS, 'w', newline='') as tsvfile:
        writer = csv.writer(tsvfile, delimiter='\t', lineterminator='\n')
        writer.writerow(["onset", "duration", "value", "significance", "trial"])
        
        #Continue to use i from before.
        j = 1 #For keeping track of prac trials
        k = 1 #"     "       "   "  main   "
        
        P2startLatency_ceegrid = ceegridLatencies[i]/sfreq - filterBufferPeriod
        
        while P2ended == False:
            onset = ceegridLatencies[i]/sfreq - P2startLatency_ceegrid
            value = ceegridCodes[i]
            
            if value == 156:
                trial = "N/A"
                significance = "main_trials_start"
                P2practiceEnded = True
                
            elif P2practiceEnded == False:
                trial = "prac_" + str(j)
                if value in P2trialStartVals:
                    significance = "trial_start"
                elif value in P2attendedOBvals:
                    significance = "attended_OB"
                elif value in P2unattendedOBvals:
                    significance = "unattended_OB"
                elif value in P2trialEndVals:
                    significance = "trial_end"
                    j += 1
                    
                
            elif onset + P2startLatency_ceegrid > P2endLatency_ceegrid:  #Once past the early stopping point, we should ignore 
            #the current trig, and go back to the early stopping point, as the ground comes loose after it.
                onset = P2earlyStopLatency_ceegrid - P2startLatency_ceegrid
                trial = "N/A"
                significance = "main_trials_end" #Give it this significance/value for simplicity.
                value = 157
                
            else:
                trial = str(k)
                if value in P2trialStartVals:
                    significance = "trial_start"
                elif value in P2attendedOBvals:
                    significance = "attended_OB"
                elif value in P2unattendedOBvals:
                    significance = "unattended_OB"
                elif value in P2trialEndVals:
                    significance = "trial_end"
                    k += 1
                    
            if "OB" in significance: #Oddballs
                duration = "0.49197278911"
            else:
                duration = "0"
                
            writer.writerow([str(onset), duration, str(value), significance, trial])
            i += 1
            
            if significance == "main_trials_end": #Set to stop here as the ground comes loose after.
                P2ended = True  
                
        tsvfile.close

    #P3:
    task3 = "attnOneInstNoOBs"    
    filename = subjFolder + "_task-" + task3 + "_acq-ceegrid_events.tsv"
    ceegridEvents_BIDS = (outputDir + filename)
        
    with open(ceegridEvents_BIDS, 'w', newline='') as tsvfile:
        writer = csv.writer(tsvfile, delimiter='\t', lineterminator='\n')
        writer.writerow(["onset", "duration", "value", "significance", "trial"])
        j = 3 #For keeping track of main trials. Start from 3rd trial since we miss the pract one/first two mains.
        P3lateStartOccurred = False
        
        while P3lateStartOccurred == False: #We keep moving up in latency indices, but don't leave this loop
        #until we've passed the late start latency.
        #Don't consider 'P3startLatency_ceegrid' here, comparing to overall latencies.
            onset = ceegridLatencies[i]/sfreq
            i += 1
            if onset > P3lateStartLatency_ceegrid:
                onset = float(filterBufferPeriod) #Equivalent to what's used in all other events files.
                value = 158
                trial = "N/A"
                significance = "main_trials_start"
                writer.writerow([str(onset), duration, str(value), significance, trial])
                P3lateStartOccurred = True
                
                i -= 1 #Otherwise we would miss the trig just after P3lateStartLatency_ceegrid
        
        duration = "0" #Should already be set, but if e.g., triggers above are missed, this acts as a failsafe.

        while P3ended == False:
            onset = ceegridLatencies[i]/sfreq - P3startLatency_ceegrid #So that the first trigger is at t = 0
            value = ceegridCodes[i]
            
            #Already passed pract trials and what would have been 'main_trials_start'
            if value == 159:
                trial = "N/A"
                significance = "main_trials_end"

            else:
                trial = str(j)
                if value in P1P3trialStartVals:
                    significance = "trial_start"
                elif value in P1P3trialEndVals:
                    significance = "trial_end"
                    j += 1
                
            if value == 46: #These trials were about 42.7ms too long due to an error in expt setup.
            #For simplicity/consistency we trim the difference by moving end trigs forward.
                onset -= 0.043
                
            writer.writerow([str(onset), duration, str(value), significance, trial])
            i += 1
            
            if significance == "main_trials_end" or i == len(ceegridLatencies):
                P3endLatency_ceegrid = onset + P3startLatency_ceegrid + filterBufferPeriod
                P3ended = True  
                
        tsvfile.close
    
    partStartLatencies_ceegrid = [P1startLatency_ceegrid, P2startLatency_ceegrid, P3startLatency_ceegrid]
    partEndLatencies_ceegrid = [P1endLatency_ceegrid, P2endLatency_ceegrid, P3endLatency_ceegrid]
    partStartEndLatencies_ceegrid = np.stack([partStartLatencies_ceegrid, partEndLatencies_ceegrid])
        
    return partStartEndLatencies_scalp, partStartEndLatencies_ceegrid

#######################################################################################################################################################################################################
#######################################################################################################################################################################################################

#Version for one participant where recording was stopped and restarted (meaning two scalp files, two ceegrid files):
def poly52trigs_splitRecs(basePath, participantNumber, rec1, rec2, filterBufferPeriod):
    rawDataPath = basePath + 'sourcedata\P' + participantNumber + '\\'
    scalpFilename_rec1 = "P" + participantNumber + '_' + rec1 + "_scalp.Poly5"
    scalpFilename_rec2 = "P" + participantNumber + '_' + rec2 + "_scalp.Poly5"
    
    ceegridFilename_rec1 = "P" + participantNumber + '_' + rec1 + "_ceegrid.Poly5"
    ceegridFilename_rec2 = "P" + participantNumber + '_' + rec2 + "_ceegrid.Poly5"
    
    SCALP_EEG_REC1 = rawDataPath + scalpFilename_rec1
    SCALP_EEG_REC2 = rawDataPath + scalpFilename_rec2
    
    CEEGRID_REC1 = rawDataPath + ceegridFilename_rec1
    CEEGRID_REC2 = rawDataPath + ceegridFilename_rec2
    
    subjFolder = "sub-" + participantNumber

    TRIGGER_CLK = 16
    THR_ERROR = -0.05
    TRANS_ERROR = 0.1

    #read scalp poly5
    scalp_eeg_rec1 = poly52POPO(SCALP_EEG_REC1, 'scalp_rec1')
    numSamps_scalpRec1 = scalp_eeg_rec1.num_samples #<- use this for rec2 offset. remember 1kHz SR
    scalp_eeg_rec1.decode_events(triggerClk=TRIGGER_CLK, thrError=THR_ERROR, transError=TRANS_ERROR)        
    
    scalp_eeg_rec2 = poly52POPO(SCALP_EEG_REC2, 'scalp_rec2')
    scalp_eeg_rec2.decode_events(triggerClk=TRIGGER_CLK, thrError=THR_ERROR, transError=TRANS_ERROR)
        
    for event in scalp_eeg_rec2.raw_events: #Add offset to all values in rec2
        event["sample_idx"] += numSamps_scalpRec1
        
    scalp_eegRawEvents = scalp_eeg_rec1.raw_events + scalp_eeg_rec2.raw_events
    
    scalp_eegCodes = [ sub['code'] for sub in scalp_eegRawEvents ]

    #read ceegrid poly5
    ceegrid_rec1 = poly52POPO(CEEGRID_REC1, 'ceegrid_rec1')
    numSamps_ceegridRec1 = ceegrid_rec1.num_samples #<- use this for rec2 offset. remember 1kHz SR
    ceegrid_rec1.decode_events(triggerClk=TRIGGER_CLK, thrError=THR_ERROR, transError=TRANS_ERROR)
    
    ceegrid_rec2 = poly52POPO(CEEGRID_REC2, 'ceegrid_rec2')
    ceegrid_rec2.decode_events(triggerClk=TRIGGER_CLK, thrError=THR_ERROR, transError=TRANS_ERROR)

    """Add in a Part 3 end trig: From careful inspection, the onset is 32,952 samples after that of the trigger before, and that was checked previously."""
    ceegrid_rec2.raw_events.append({'sample_idx': 3157949, 'pattern': '10011111', 'code': 159})

    for event in ceegrid_rec2.raw_events: #Add offset to all values in rec2
        event["sample_idx"] += numSamps_ceegridRec1
        
    ceegridRawEvents = ceegrid_rec1.raw_events + ceegrid_rec2.raw_events
    
    ceegridCodes = [ sub['code'] for sub in ceegridRawEvents ]

#####################################################################################################################################################################
    #Good to run various checks: that there are the same number of events for the scalp/ceegrid files; that these do not contradict; and separately checking that events in
    #each are sensible. These are only rough and not exhaustive

    #Check same number of trigs recorded for scalp and ceegrid:
    num_scalp_eeg_events = len(scalp_eegRawEvents)
    num_ceegrid_events = len(ceegridRawEvents)
    difference = num_scalp_eeg_events - num_ceegrid_events
    if difference > 0:
        print("WARNING - MORE SCALP THAN CEEGRID EVENTS DETECTED")
        lesserEventCount = num_ceegrid_events
    elif difference < 0:
        print("WARNING - MORE CEEGRID EVENTS THAN SCALP EVENTS DETECTED")
        lesserEventCount = num_scalp_eeg_events
    else:
        print("Equal number of scalp and ceegrid events detected.")
        lesserEventCount = num_scalp_eeg_events #could use either 
        
    #Calculate no. of expected trigs, compare to recorded:
    expectedTrigs = expectedTriggerCalculator(basePath, participantNumber)    
    if expectedTrigs > num_scalp_eeg_events:
        diff = str(expectedTrigs - num_scalp_eeg_events)
        print("WARNING - " + diff + " SCALP EVENTS MISSING")#
    if expectedTrigs < num_scalp_eeg_events:
        diff = str(num_scalp_eeg_events - expectedTrigs)
        print("WARNING - " + diff + " EXCESS SCALP EVENTS DETECTED")
    if expectedTrigs > num_ceegrid_events:
        diff = str(expectedTrigs - num_ceegrid_events)
        print("WARNING - CEEGRID EVENTS MISSING")
    if expectedTrigs < num_ceegrid_events:
        diff = str(num_ceegrid_events - expectedTrigs)
        print("WARNING - " + diff + " EXCESS CEEGRID EVENTS DETECTED")
    if expectedTrigs == num_scalp_eeg_events and difference == 0:
        print("Good news: the number of trigs detected for both scalp and cEEGrid is what should be expected.")
    
    
    #Finally, check individual scalp and ceegrid trigs match up:
    x = 0
    for i in range(0, lesserEventCount):
        if scalp_eegCodes[i] != ceegridCodes[i]:
            print("WARNING - EVENT CODES DISCREPENCY")
            print("This is at the following sample in the scalp data: " + str(scalp_eegRawEvents[i].get("sample_idx")))
            print("Alternatively, this is the following sample for the ceegrid data: " + str(ceegridRawEvents[i].get("sample_idx")))
            
            
            #Single event checks. Note, if scalp/ceegrid EEG does have one or two more triggers, then will need to check the extra
            #ones at the end separately
            scalp_pattern = scalp_eegRawEvents[i].get("pattern")
            scalp_code = scalp_eegRawEvents[i].get("code")
            
            if len(scalp_pattern) > 8 and int(scalp_code) > 159:
                print("Scalp pattern too long. Scalp code value is also too large.")
            elif len(scalp_pattern) > 8 and int(scalp_code) < 160:
                print("Scalp pattern too long. Scalp code value is NOT too large.")
            elif len(scalp_pattern) < 9 and int(scalp_code) > 159:
                print("Scalp pattern NOT too long. However, scalp code value is too large.")
            
            ceegrid_pattern = ceegridRawEvents[i].get("pattern")
            ceegrid_code = ceegridRawEvents[i].get("code")
            
            if len(ceegrid_pattern) > 8 and int(ceegrid_code) > 159:
                print("ceegrid pattern too long. ceegrid code value is also too large.")
            if len(ceegrid_pattern) > 8 and int(ceegrid_code) < 160:
                print("ceegrid pattern too long. ceegrid code value is NOT too large.")
            if len(ceegrid_pattern) < 9 and int(ceegrid_code) > 159:
                print("ceegrid pattern NOT too long. However, ceegrid code value is too large.")
                
            
            print("It is the " + str(i+1) + "th event in each data file. The scalp code is: " + str(scalp_code) + " and the ceegrid code is: " + str(ceegrid_code))
        if scalp_eegCodes[i] == ceegridCodes[i]:
            x += 1
            
    print(str(x) + " out of " + str(lesserEventCount) + " codes are the same between both data files. Note this assumes that the code numbers are the same, OR that if one file has more "
          + "events detected, these are at the end.")
    
    
#######################################################################################################################################################################################################
#######################################################################################################################################################################################################
    #Save to files, in a BIDS-friendly format:
    
    outputDir = basePath + "bids_dataset\sub-" + participantNumber + "\eeg\\"
    outputDirExists = os.path.exists(outputDir)
    
    if not outputDirExists:
        os.makedirs(outputDir)
#######################################################################################################################################################################################################   
    #First, scalp:
    
    scalp_eegLatencies = [ sub['sample_idx'] for sub in scalp_eegRawEvents ]
    sfreq = 1000
    
    #Do this "task by task", i.e emotion decoding first etc:
    task1 = "emotion"
    filename = subjFolder + "_task-" + task1 + "_acq-scalp_events.tsv"
    scalpEvents_BIDS = (outputDir + filename)

    P1practiceEnded = False
    P1ended = False
    P2practiceEnded = False
    P2ended = False
    P3practiceEnded = False
    P3ended = False
    
    P1P3trialStartVals = np.arange(1, 73, 2) #Can reuse these later
    P1P3trialEndVals = np.arange(2, 74, 2)
    
    with open(scalpEvents_BIDS, 'w', newline='') as tsvfile:
        writer = csv.writer(tsvfile, delimiter='\t', lineterminator='\n')
        writer.writerow(["onset", "duration", "value", "significance", "trial"])
        i = 0
        j = 1 #For keeping track of main trials
        
        P1startLatency_scalp = scalp_eegLatencies[i]/sfreq - filterBufferPeriod
        duration = "0" #Throughout P1
        
        while P1ended == False:
            onset = scalp_eegLatencies[i]/sfreq - P1startLatency_scalp #So that the first trigger is at t = 0
            value = scalp_eegCodes[i]
                
            if P1practiceEnded == False:
                trial = "prac"
                if value in P1P3trialStartVals:
                    significance = "trial_start"
                else:
                    significance = "trial_end"
                    P1practiceEnded = True
                    
            elif value == 154:
                trial = "N/A"
                significance = "main_trials_start"
            elif value == 155:
                trial = "N/A"
                significance = "main_trials_end"
                
            else:
                trial = str(j)
                if value in P1P3trialStartVals:
                    significance = "trial_start"
                elif value in P1P3trialEndVals:
                    significance = "trial_end"
                    j += 1

            if value == 46: #These trials were about 42.7ms too long due to an error in expt setup.
            #For simplicity/consistency we trim the difference by moving end trigs forward.
                onset -= 0.043
                
            writer.writerow([str(onset), duration, str(value), significance, trial])
            i += 1
            
            if significance == "main_trials_end":
                P1endLatency_scalp = onset + P1startLatency_scalp + filterBufferPeriod
                P1ended = True  
                         
        tsvfile.close
    
    
    #P2:
    task2 = "attnMultInstOBs"    
    filename = subjFolder + "_task-" + task2 + "_acq-scalp_events.tsv"
    scalpEvents_BIDS = (outputDir + filename)

    P2trialStartVals = np.arange(73, 144, 2) #Can reuse these later
    P2trialEndVals = np.arange(74, 145, 2)
    P2attendedOBvals = np.array([145, 149, 153])
    P2unattendedOBvals = np.array([146, 147, 148, 150, 151, 152])    
    
    with open(scalpEvents_BIDS, 'w', newline='') as tsvfile:
        writer = csv.writer(tsvfile, delimiter='\t', lineterminator='\n')
        writer.writerow(["onset", "duration", "value", "significance", "trial"])
        
        #Continue to use i from before.
        j = 1 #For keeping track of prac trials
        k = 1 #"     "       "   "  main   "
        
        P2startLatency_scalp = scalp_eegLatencies[i]/sfreq - filterBufferPeriod
        
        while P2ended == False:
            onset = scalp_eegLatencies[i]/sfreq - P2startLatency_scalp
            value = scalp_eegCodes[i]
            
            if value == 156:
                trial = "N/A"
                significance = "main_trials_start"
                P2practiceEnded = True
                
            elif P2practiceEnded == False:
                trial = "prac_" + str(j)
                if value in P2trialStartVals:
                    significance = "trial_start"
                elif value in P2attendedOBvals:
                    significance = "attended_OB"
                elif value in P2unattendedOBvals:
                    significance = "unattended_OB"
                elif value in P2trialEndVals:
                    significance = "trial_end"
                    j += 1
                    
            elif value == 157:
                trial = "N/A"
                significance = "main_trials_end"
                
            else:
                trial = str(k)
                if value in P2trialStartVals:
                    significance = "trial_start"
                elif value in P2attendedOBvals:
                    significance = "attended_OB"
                elif value in P2unattendedOBvals:
                    significance = "unattended_OB"
                elif value in P2trialEndVals:
                    significance = "trial_end"
                    k += 1
                
            if "OB" in significance: #Oddballs
                duration = "0.49197278911"
            else:
                duration = "0"
            writer.writerow([str(onset), duration, str(value), significance, trial])
            i += 1
            
            if significance == "main_trials_end":
                P2endLatency_scalp = onset + P2startLatency_scalp + filterBufferPeriod
                P2ended = True  
                
        tsvfile.close
        
    #P3:
    task3 = "attnOneInstNoOBs"    
    filename = subjFolder + "_task-" + task3 + "_acq-scalp_events.tsv"
    scalpEvents_BIDS = (outputDir + filename)
        
    with open(scalpEvents_BIDS, 'w', newline='') as tsvfile:
        writer = csv.writer(tsvfile, delimiter='\t', lineterminator='\n')
        writer.writerow(["onset", "duration", "value", "significance", "trial"])
        j = 1 #For keeping track of main trials
        
        P3startLatency_scalp = scalp_eegLatencies[i]/sfreq - filterBufferPeriod
        duration = "0" #Should already be set, but if e.g triggers above are missed, this acts as a failsafe.
        
        while P3ended == False:
            onset = scalp_eegLatencies[i]/sfreq - P3startLatency_scalp #So that the first trigger is at t = 0
            value = scalp_eegCodes[i]
                
            if P3practiceEnded == False:
                trial = "prac"
                if value in P1P3trialStartVals:
                    significance = "trial_start"
                else:
                    significance = "trial_end"
                    P3practiceEnded = True
                    
            elif value == 158:
                trial = "N/A"
                significance = "main_trials_start"
            elif value == 159:
                trial = "N/A"
                significance = "main_trials_end"
                
            else:
                trial = str(j)
                if value in P1P3trialStartVals:
                    significance = "trial_start"
                elif value in P1P3trialEndVals:
                    significance = "trial_end"
                    j += 1

            if value == 46: #These trials were about 42.7ms too long due to an error in expt setup.
            #For simplicity/consistency we trim the difference by moving end trigs forward.
                onset -= 0.043
                
            writer.writerow([str(onset), duration, str(value), significance, trial])
            i += 1
            
            if significance == "main_trials_end" or i == len(scalp_eegLatencies):
                P3endLatency_scalp = onset + P3startLatency_scalp + filterBufferPeriod
                P3ended = True  
                         
        tsvfile.close
        
    partStartLatencies_scalp = [P1startLatency_scalp, P2startLatency_scalp, P3startLatency_scalp]
    partEndLatencies_scalp = [P1endLatency_scalp, P2endLatency_scalp, P3endLatency_scalp]
    partStartEndLatencies_scalp = np.stack([partStartLatencies_scalp, partEndLatencies_scalp])
        
#######################################################################################################################################################################################################
    #ceegrid:
        
    ceegridLatencies = [ sub['sample_idx'] for sub in ceegridRawEvents ]
    sfreq = 1000
    
    #Do this "task by task", i.e emotion decoding first etc:
    task1 = "emotion"
    filename = subjFolder + "_task-" + task1 + "_acq-ceegrid_events.tsv"
    ceegridEvents_BIDS = (outputDir + filename)

    P1practiceEnded = False
    P1ended = False
    P2practiceEnded = False
    P2ended = False
    P3practiceEnded = False
    P3ended = False
    
    P1P3trialStartVals = np.arange(1, 73, 2) #Can reuse these later
    P1P3trialEndVals = np.arange(2, 74, 2)
    
    with open(ceegridEvents_BIDS, 'w', newline='') as tsvfile:
        writer = csv.writer(tsvfile, delimiter='\t', lineterminator='\n')
        writer.writerow(["onset", "duration", "value", "significance", "trial"])
        i = 0
        j = 1 #For keeping track of main trials
        
        P1startLatency_ceegrid = ceegridLatencies[i]/sfreq - filterBufferPeriod
        
        while P1ended == False:
            onset = ceegridLatencies[i]/sfreq - P1startLatency_ceegrid #So that the first trigger is at t = 0
            value = ceegridCodes[i]
                
            if P1practiceEnded == False:
                trial = "prac"
                if value in P1P3trialStartVals:
                    significance = "trial_start"
                else:
                    significance = "trial_end"
                    P1practiceEnded = True
                    
            elif value == 154:
                trial = "N/A"
                significance = "main_trials_start"
            elif value == 155:
                trial = "N/A"
                significance = "main_trials_end"
                
            else:
                trial = str(j)
                if value in P1P3trialStartVals:
                    significance = "trial_start"
                elif value in P1P3trialEndVals:
                    significance = "trial_end"
                    j += 1

            if value == 46: #These trials were about 42.7ms too long due to an error in expt setup.
            #For simplicity/consistency we trim the difference by moving end trigs forward.
                onset -= 0.043
                
            writer.writerow([str(onset), duration, str(value), significance, trial])
            i += 1
            
            if significance == "main_trials_end":
                P1endLatency_ceegrid = onset + P1startLatency_ceegrid + filterBufferPeriod
                P1ended = True  
                         
        tsvfile.close
    
    
    #P2:
    task2 = "attnMultInstOBs"    
    filename = subjFolder + "_task-" + task2 + "_acq-ceegrid_events.tsv"
    ceegridEvents_BIDS = (outputDir + filename)

    P2trialStartVals = np.arange(73, 144, 2) #Can reuse these later
    P2trialEndVals = np.arange(74, 145, 2)
    P2attendedOBvals = np.array([145, 149, 153])
    P2unattendedOBvals = np.array([146, 147, 148, 150, 151, 152])    
    
    with open(ceegridEvents_BIDS, 'w', newline='') as tsvfile:
        writer = csv.writer(tsvfile, delimiter='\t', lineterminator='\n')
        writer.writerow(["onset", "duration", "value", "significance", "trial"])
        
        #Continue to use i from before.
        j = 1 #For keeping track of prac trials
        k = 1 #"     "       "   "  main   "
        
        P2startLatency_ceegrid = ceegridLatencies[i]/sfreq - filterBufferPeriod
        
        while P2ended == False:
            onset = ceegridLatencies[i]/sfreq - P2startLatency_ceegrid
            value = ceegridCodes[i]
            
            if value == 156:
                trial = "N/A"
                significance = "main_trials_start"
                P2practiceEnded = True
                
            elif P2practiceEnded == False:
                trial = "prac_" + str(j)
                if value in P2trialStartVals:
                    significance = "trial_start"
                elif value in P2attendedOBvals:
                    significance = "attended_OB"
                elif value in P2unattendedOBvals:
                    significance = "unattended_OB"
                elif value in P2trialEndVals:
                    significance = "trial_end"
                    j += 1
                    
                
            elif value == 157:
                trial = "N/A"
                significance = "main_trials_end"
                
            else:
                trial = str(k)
                if value in P2trialStartVals:
                    significance = "trial_start"
                elif value in P2attendedOBvals:
                    significance = "attended_OB"
                elif value in P2unattendedOBvals:
                    significance = "unattended_OB"
                elif value in P2trialEndVals:
                    significance = "trial_end"
                    k += 1
                    
            if "OB" in significance: #Oddballs
                duration = "0.49197278911"
            else:
                duration = "0"
                
            writer.writerow([str(onset), duration, str(value), significance, trial])
            i += 1
            
            if significance == "main_trials_end":
                P2endLatency_ceegrid = onset + P2startLatency_ceegrid + filterBufferPeriod
                P2ended = True  
                
        tsvfile.close
        
    #P3:
    task3 = "attnOneInstNoOBs"    
    filename = subjFolder + "_task-" + task3 + "_acq-ceegrid_events.tsv"
    ceegridEvents_BIDS = (outputDir + filename)
        
    with open(ceegridEvents_BIDS, 'w', newline='') as tsvfile:
        writer = csv.writer(tsvfile, delimiter='\t', lineterminator='\n')
        writer.writerow(["onset", "duration", "value", "significance", "trial"])
        j = 1 #For keeping track of main trials
        
        P3startLatency_ceegrid = ceegridLatencies[i]/sfreq - filterBufferPeriod
        duration = "0" #Should already be set, but if e.g triggers above are missed, this acts as a failsafe.
        
        while P3ended == False:
            onset = ceegridLatencies[i]/sfreq - P3startLatency_ceegrid #So that the first trigger is at t = 0
            value = ceegridCodes[i]
                
            if P3practiceEnded == False:
                trial = "prac"
                if value in P1P3trialStartVals:
                    significance = "trial_start"
                else:
                    significance = "trial_end"
                    P3practiceEnded = True
                    
            elif value == 158:
                trial = "N/A"
                significance = "main_trials_start"
            elif value == 159:
                trial = "N/A"
                significance = "main_trials_end"
                
            else:
                trial = str(j)
                if value in P1P3trialStartVals:
                    significance = "trial_start"
                elif value in P1P3trialEndVals:
                    significance = "trial_end"
                    j += 1

            if value == 46: #These trials were about 42.7ms too long due to an error in expt setup.
            #For simplicity/consistency we trim the difference by moving end trigs forward.
                onset -= 0.043
                
            writer.writerow([str(onset), duration, str(value), significance, trial])
            i += 1
            
            if significance == "main_trials_end" or i == len(ceegridLatencies):
                P3endLatency_ceegrid = onset + P3startLatency_ceegrid + filterBufferPeriod
                P3ended = True  
                         
        tsvfile.close
        
    partStartLatencies_ceegrid = [P1startLatency_ceegrid, P2startLatency_ceegrid, P3startLatency_ceegrid]
    partEndLatencies_ceegrid = [P1endLatency_ceegrid, P2endLatency_ceegrid, P3endLatency_ceegrid]
    partStartEndLatencies_ceegrid = np.stack([partStartLatencies_ceegrid, partEndLatencies_ceegrid])
        
    return partStartEndLatencies_scalp, partStartEndLatencies_ceegrid

#######################################################################################################################################################################################################
#######################################################################################################################################################################################################

#Version for converting extra data- doesn't convert other data from the same participant:
def poly52trigs_extraData(basePath, participantNumber, filterBufferPeriod):
    rawDataPath = basePath + 'sourcedata\P' + participantNumber + '\\'
    
    subjFolder = "sub-" + participantNumber
    
    correctionsFile_scalp = rawDataPath + 'P' + participantNumber + '_scalpCorrTrigs_extraData.txt'
    
    scalp_eegCodes = ([x.split()[0] for x in open(correctionsFile_scalp).readlines()])
    scalp_eegLatencies = ([x.split()[1] for x in open(correctionsFile_scalp).readlines()])#Need to adjust this stuff..
    
    scalp_eegCodes.remove(scalp_eegCodes[0])
    scalp_eegLatencies.remove(scalp_eegLatencies[0])
    
    correctionsFile_ceegrid = rawDataPath + 'P' + participantNumber + '_ceegridCorrTrigs_extraData.txt'
    
    ceegridCodes = ([x.split()[0] for x in open(correctionsFile_ceegrid).readlines()])
    ceegridLatencies = ([x.split()[1] for x in open(correctionsFile_ceegrid).readlines()])
    
    ceegridCodes.remove(ceegridCodes[0])
    ceegridLatencies.remove(ceegridLatencies[0])

    #Convert all to ints:
    scalp_eegCodes = [int(i) for i in scalp_eegCodes]
    scalp_eegLatencies = [int(i) for i in scalp_eegLatencies]
    ceegridCodes = [int(i) for i in ceegridCodes]
    ceegridLatencies = [int(i) for i in ceegridLatencies]

#####################################################################################################################################################################
    #Good to run various checks: that there are the same number of events for the scalp/ceegrid files; that these do not contradict; and separately checking that events in
    #each are sensible. These are only rough and not exhaustive

    #Check same number of trigs recorded for scalp and ceegrid:
    num_scalp_eeg_events = len(scalp_eegCodes)
    num_ceegrid_events = len(ceegridCodes)
    difference = num_scalp_eeg_events - num_ceegrid_events
    if difference > 0:
        print("WARNING - MORE SCALP THAN CEEGRID EVENTS DETECTED")
        lesserEventCount = num_ceegrid_events
    elif difference < 0:
        print("WARNING - MORE CEEGRID EVENTS THAN SCALP EVENTS DETECTED")
        lesserEventCount = num_scalp_eeg_events
    else:
        print("Equal number of scalp and ceegrid events detected.")
        lesserEventCount = num_scalp_eeg_events #could use either 
        
    
    #Calculate no. of expected trigs, compare to recorded:   
    expectedTrigs = expectedTriggerCalculator(basePath, participantNumber)
    if expectedTrigs > num_scalp_eeg_events:
        diff = str(expectedTrigs - num_scalp_eeg_events)
        print("WARNING - " + diff + " SCALP EVENTS MISSING")#
    if expectedTrigs < num_scalp_eeg_events:
        diff = str(num_scalp_eeg_events - expectedTrigs)
        print("WARNING - " + diff + " EXCESS SCALP EVENTS DETECTED")
    if expectedTrigs > num_ceegrid_events:
        diff = str(expectedTrigs - num_ceegrid_events)
        print("WARNING - " + diff + " CEEGRID EVENTS MISSING")
    if expectedTrigs < num_ceegrid_events:
        diff = str(num_ceegrid_events - expectedTrigs)
        print("WARNING - " + diff + " EXCESS CEEGRID EVENTS DETECTED")
    if expectedTrigs == num_scalp_eeg_events and difference == 0:
        print("Good news: the number of trigs detected for both scalp and cEEGrid is what should be expected.")
    

    #Finally, check individual scalp and ceegrid trigs match up:
    x = 0
    for i in range(0, lesserEventCount):
        if scalp_eegCodes[i] != ceegridCodes[i]:
            print("WARNING - EVENT CODES DISCREPENCY")
            print("This is at the following sample in the scalp data: " + str(scalp_eegLatencies[i]))
            print("Alternatively, this is the following sample for the ceegrid data: " + str(ceegridLatencies[i]))
            
            
            #Single event checks. Note, if scalp/ceegrid EEG does have one or two more triggers, then will need to check the extra ones at the end
            #separately
         #  scalp_pattern = scalp_eeg.raw_events[i].get("pattern")
            scalp_code = scalp_eegCodes[i]
            
            if int(scalp_code) > 159:
                print("Scalp code value is too large.")
            
            ceegrid_code = ceegridCodes[i]
            
            if int(ceegrid_code) > 159:
                print("ceegrid code value is too large.")
                
            
            print("It is the " + str(i+1) + "th event in each data file. The scalp code is: " + str(scalp_code) + " and the ceegrid code is: " + str(ceegrid_code))
        if scalp_eegCodes[i] == ceegridCodes[i]:
            x += 1
            
    print(str(x) + " out of " + str(lesserEventCount) + " codes are the same between both data files. Note this assumes that the code numbers are the same, OR that if one file has more "
          + "events detected, these are at the end.")
    

#######################################################################################################################################################################################################
#######################################################################################################################################################################################################
    #Save to files
    
    outputDir = basePath + "bids_dataset\misc\\"
    outputDirExists = os.path.exists(outputDir)
    
    if not outputDirExists:
        os.makedirs(outputDir)
#######################################################################################################################################################################################################       
    sfreq = 1000
    i = 0
    partStartLatency_scalp = scalp_eegLatencies[i]/sfreq #Note- here we are only assuming up to one 'part' of the experiment recorded per participant (e.g part 2 scalp+ceegrid for P09)
    
    if participantNumber == "09": #Extra data for Part 2, scalp then ceegrid:
        P2practiceEnded = False
        P2ended = False

        task = "attnMultInstOBsExtra"    
        
        filename = subjFolder + "_task-" + task + "_acq-scalp_events.tsv"
        scalpEvents_BIDS = (outputDir + "sub-09\\eeg\\" + filename)
        os.makedirs(os.path.dirname(scalpEvents_BIDS), exist_ok=True)
        
        P2trialStartVals = np.arange(73, 144, 2)
        P2trialEndVals = np.arange(74, 145, 2)
        P2attendedOBvals = np.array([145, 149, 153])
        P2unattendedOBvals = np.array([146, 147, 148, 150, 151, 152])    
        
        for item in reversed(scalp_eegCodes):
            if item in P2trialEndVals:
                final_trig = item
                break
    
        with open(scalpEvents_BIDS, 'w', newline='') as tsvfile:
            writer = csv.writer(tsvfile, delimiter='\t', lineterminator='\n')
            writer.writerow(["onset", "duration", "value", "significance", "trial"])
            
            #Continue to use i from before.
            j = 1 #For keeping track of prac trials
            k = 1 #"     "       "   "  main   "
            
            
            while P2ended == False:
                onset = scalp_eegLatencies[i]/sfreq - partStartLatency_scalp
                value = scalp_eegCodes[i]
                
                if value == 156:
                    trial = "N/A"
                    significance = "main_trials_start"
                    P2practiceEnded = True
                    
                elif P2practiceEnded == False:
                    trial = "prac_" + str(j)
                    if value in P2trialStartVals:
                        significance = "trial_start"
                    elif value in P2attendedOBvals:
                        significance = "attended_OB"
                    elif value in P2unattendedOBvals:
                        significance = "unattended_OB"
                    elif value in P2trialEndVals:
                        significance = "trial_end"
                        j += 1
                        
                elif value == 157:
                    trial = "N/A"
                    significance = "main_trials_end"
                    
                else:
                    trial = str(k)
                    if value in P2trialStartVals:
                        significance = "trial_start"
                    elif value in P2attendedOBvals:
                        significance = "attended_OB"
                    elif value in P2unattendedOBvals:
                        significance = "unattended_OB"
                    elif value in P2trialEndVals:
                        significance = "trial_end"
                        k += 1
                    
                if "OB" in significance: #Oddballs
                    duration = "0.49197278911"
                else:
                    duration = "0"
                writer.writerow([str(onset), duration, str(value), significance, trial])
                i += 1
                
                if significance == "main_trials_end" or value == final_trig:
                    partEndLatency_scalp = onset + partStartLatency_scalp
                    P2ended = True  
                    
            tsvfile.close
        
#ceegrid:
        P2practiceEnded = False
        P2ended = False
        i = 0
        filename = subjFolder + "_task-" + task + "_acq-ceegrid_events.tsv"
        ceegridEvents_BIDS = (outputDir + "sub-09\\eeg\\" + filename)
        os.makedirs(os.path.dirname(ceegridEvents_BIDS), exist_ok=True)
        
        for item in reversed(ceegridCodes):
            if item in P2trialEndVals:
                final_trig = item
                break
        
        with open(ceegridEvents_BIDS, 'w', newline='') as tsvfile:
            writer = csv.writer(tsvfile, delimiter='\t', lineterminator='\n')
            writer.writerow(["onset", "duration", "value", "significance", "trial"])
            
            #Continue to use i from before.
            j = 1 #For keeping track of prac trials
            k = 1 #"     "       "   "  main   "
            
            partStartLatency_ceegrid = ceegridLatencies[i]/sfreq
            
            while P2ended == False:
                onset = ceegridLatencies[i]/sfreq - partStartLatency_ceegrid
                value = ceegridCodes[i]
                
                if value == 156:
                    trial = "N/A"
                    significance = "main_trials_start"
                    P2practiceEnded = True
                    
                elif P2practiceEnded == False:
                    trial = "prac_" + str(j)
                    if value in P2trialStartVals:
                        significance = "trial_start"
                    elif value in P2attendedOBvals:
                        significance = "attended_OB"
                    elif value in P2unattendedOBvals:
                        significance = "unattended_OB"
                    elif value in P2trialEndVals:
                        significance = "trial_end"
                        j += 1
                        
                    
                elif value == 157:
                    trial = "N/A"
                    significance = "main_trials_end"
                    
                else:
                    trial = str(k)
                    if value in P2trialStartVals:
                        significance = "trial_start"
                    elif value in P2attendedOBvals:
                        significance = "attended_OB"
                    elif value in P2unattendedOBvals:
                        significance = "unattended_OB"
                    elif value in P2trialEndVals:
                        significance = "trial_end"
                        k += 1
                        
                if "OB" in significance: #Oddballs
                    duration = "0.49197278911"
                else:
                    duration = "0"
                    
                writer.writerow([str(onset), duration, str(value), significance, trial])
                i += 1
                
                if significance == "main_trials_end" or value == final_trig:
                    partEndLatency_ceegrid = onset + partStartLatency_ceegrid
                    P2ended = True  
                    
            tsvfile.close
        
#######################################################################################################################################################################################################
    elif participantNumber == "28":        
        i = 0
        P3practiceEnded = False
        P3ended = False
        P1P3trialStartVals = np.arange(1, 73, 2)
        P1P3trialEndVals = np.arange(2, 74, 2)
        
        for item in reversed(scalp_eegCodes):
            if item in P1P3trialEndVals:
                final_trig = item
                break
            
        task = "attnOneInstNoOBsExtra"    
        filename = subjFolder + "_task-" + task + "_acq-scalp_events.tsv"
        scalpEvents_BIDS = (outputDir + "sub-28\\eeg\\" + filename)
        os.makedirs(os.path.dirname(scalpEvents_BIDS), exist_ok=True)
            
        with open(scalpEvents_BIDS, 'w', newline='') as tsvfile:
            writer = csv.writer(tsvfile, delimiter='\t', lineterminator='\n')
            writer.writerow(["onset", "duration", "value", "significance", "trial"])
            j = 1 #For keeping track of main trials
            
            partStartLatency_scalp = scalp_eegLatencies[i]/sfreq
            duration = "0" #Should already be set, but if e.g triggers above are missed, this acts as a failsafe.
            
            while P3ended == False:
                onset = scalp_eegLatencies[i]/sfreq - partStartLatency_scalp #So that the first trigger is at t = 0
                value = scalp_eegCodes[i]
                    
                if P3practiceEnded == False:
                    trial = "prac"
                    if value in P1P3trialStartVals:
                        significance = "trial_start"
                    else:
                        significance = "trial_end"
                        P3practiceEnded = True
                        
                elif value == 158:
                    trial = "N/A"
                    significance = "main_trials_start"
                elif value == 159:
                    trial = "N/A"
                    significance = "main_trials_end"
                    
                else:
                    trial = str(j)
                    if value in P1P3trialStartVals:
                        significance = "trial_start"
                    elif value in P1P3trialEndVals:
                        significance = "trial_end"
                        j += 1
                    
                if value == 46: #These trials were about 42.7ms too long due to an error in expt setup.
                #For simplicity/consistency we trim the difference by moving end trigs forward.
                    onset -= 0.043
                
                writer.writerow([str(onset), duration, str(value), significance, trial])
                i += 1
                
                if significance == "main_trials_end" or value == final_trig:
                    partEndLatency_scalp = onset + partStartLatency_scalp
                    P3ended = True  
                             
            tsvfile.close
#ceegrid:       
        P3practiceEnded = False
        P3ended = False
        i = 0
        
        P1P3trialStartVals = np.arange(1, 73, 2) #Can reuse these later
        P1P3trialEndVals = np.arange(2, 74, 2)
            
        #P3:
        filename = subjFolder + "_task-" + task + "_acq-ceegrid_events.tsv"
        ceegridEvents_BIDS = (outputDir + "sub-28\eeg\\" + filename)
        os.makedirs(os.path.dirname(ceegridEvents_BIDS), exist_ok=True)
            
        with open(ceegridEvents_BIDS, 'w', newline='') as tsvfile:
            writer = csv.writer(tsvfile, delimiter='\t', lineterminator='\n')
            writer.writerow(["onset", "duration", "value", "significance", "trial"])
            j = 1 #For keeping track of main trials
            
            partStartLatency_ceegrid = ceegridLatencies[i]/sfreq
            duration = "0" #Should already be set, but if e.g triggers above are missed, this acts as a failsafe.
            
            while P3ended == False:
                onset = ceegridLatencies[i]/sfreq - partStartLatency_ceegrid #So that the first trigger is at t = 0
                value = ceegridCodes[i]
                    
                if P3practiceEnded == False:
                    trial = "prac"
                    if value in P1P3trialStartVals:
                        significance = "trial_start"
                    else:
                        significance = "trial_end"
                        P3practiceEnded = True
                        
                elif value == 158:
                    trial = "N/A"
                    significance = "main_trials_start"
                elif value == 159:
                    trial = "N/A"
                    significance = "main_trials_end"
                    
                else:
                    trial = str(j)
                    if value in P1P3trialStartVals:
                        significance = "trial_start"
                    elif value in P1P3trialEndVals:
                        significance = "trial_end"
                        j += 1
                    
                if value == 46: #These trials were about 42.7ms too long due to an error in expt setup.
                #For simplicity/consistency we trim the difference by moving end trigs forward.
                    onset -= 0.043
                        
                writer.writerow([str(onset), duration, str(value), significance, trial])
                i += 1
                
                if significance == "main_trials_end" or value == final_trig:
                    partEndLatency_ceegrid = onset + partStartLatency_ceegrid
                    P3ended = True  
                             
            tsvfile.close

    partStartEndLatencies_scalp = np.stack([partStartLatency_scalp-filterBufferPeriod, partEndLatency_scalp+filterBufferPeriod])
    partStartEndLatencies_ceegrid = np.stack([partStartLatency_ceegrid-filterBufferPeriod, partEndLatency_ceegrid+filterBufferPeriod])
        
    return partStartEndLatencies_scalp, partStartEndLatencies_ceegrid