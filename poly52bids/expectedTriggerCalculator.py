#Code to read through oddball start times list and check they are not too close.
import os
import re
import pandas as pd

def expectedTriggerCalculator(basePath, participantNumber):
    #Use participantNumber to get practice stimuli played:
    
    rawDataPath = basePath + "/sourcedata/P" + participantNumber + "/"
    
    practiceTrialStimuliAll = ["Set01-Oddball Test Mix-Keyb Attended.wav", "Set01-Oddball Test Mix-Harm Attended.wav", "Set01-Oddball Test Mix-Vibr Attended.wav", "Set04-Oddball Test Mix-Keyb Attended.wav", "Set04-Oddball Test Mix-Harm Attended.wav", "Set04-Oddball Test Mix-Vibr Attended.wav"]
    practiceTrialStimuliPlayed = []
    
    p2CSVFile = rawDataPath + "Part 2 Data.csv"
        
    df = pd.read_csv(p2CSVFile)
    df = df[['stimuli_0']]
    
    #Drop rows with empty or NaN values in 'stimuli_0' column
    df = df.dropna(subset=['stimuli_0']).reset_index(drop=True)

    for i in df['stimuli_0']:
        
        if "Set01" in i or "Set04" in i:
            practiceTrialStimuliPlayed.append(i[-40:])
            
    practiceTrialStimuliNotPlayed = list(set(practiceTrialStimuliAll) - set(practiceTrialStimuliPlayed))

    ##########################################################################################################################   
    #Let's read and convert the start time data
    startTimesFile = rawDataPath + "Oddball Start Times.txt"
    startTimesData = open(startTimesFile, 'r')
    lines = startTimesData.readlines()
    startTimesData.close()
    
    def p2TrigCounter(rawDataPath):
        totalP2Trigs = 2 #start and end of main trials
        #################################################################################################################################################
    
        def numOBs(filename):
            
            attendedInst = filename[-17:-13]
            
            thisMixVibr = filename[0:6] + "Vibr Oddball Test-" + filename[-17:] #E.g, Set01-Oddball Test Mix-Harm Attended.wav -> Set01-Vibr Oddball Test-Harm Attended.wav
            thisMixHarm = filename[0:6] + "Harm Oddball Test-" + filename[-17:] #E.g, Set01-Oddball Test Mix-Harm Attended.wav -> Set01-Harm Oddball Test-Harm Attended.wav
            thisMixKeyb = filename[0:6] + "Keyb Oddball Test-" + filename[-17:] 
            
            linesReadFrom = 0        
            for line in lines:
                if thisMixVibr in line:
                    vibrOddballStartTimes = re.findall("\d+\.\d+", line)
                    for i in range(0,len(vibrOddballStartTimes)):
                        vibrOddballStartTimes[i] = vibrOddballStartTimes[i] + ' vib' 
                    linesReadFrom += 1
                elif thisMixHarm in line:
                    harmOddballStartTimes = re.findall("\d+\.\d+", line)
                    for i in range(0,len(harmOddballStartTimes)):
                        harmOddballStartTimes[i] = harmOddballStartTimes[i] + ' har'
                    linesReadFrom += 1
                elif thisMixKeyb in line:
                    keybOddballStartTimes = re.findall("\d+\.\d+", line)
                    for i in range(0,len(keybOddballStartTimes)):
                        keybOddballStartTimes[i] = keybOddballStartTimes[i] + ' key'
                    linesReadFrom += 1
                
                if linesReadFrom == 3:
                    break
            
            allOBTimes = vibrOddballStartTimes + harmOddballStartTimes + keybOddballStartTimes
            
            numOBTimes = len(allOBTimes)
            
            vibrOddballStartTimes.sort()
            harmOddballStartTimes.sort()
            keybOddballStartTimes.sort()
            
            allOBTimes.sort()
            
            return numOBTimes
            
        ########################################################################################################################################################
        
        numTrigsTot= 2 #Part start and end ones are a given
        for file in os.scandir(rawDataPath):
         if "Oddball Test Mix" in file.name and file.name not in practiceTrialStimuliNotPlayed: #Slightly more convenient to discount stimuli NOT played in practice trials
             numOBsStim = numOBs(file.name)
             numTrigsTot += numOBsStim+2 #plus start and end ones
             
        return numTrigsTot
    
    #################################################################################################################################################
    
    totalP2Trigs = p2TrigCounter(rawDataPath) #Start and end ones
   #print(totalP2Trigs)
    expectedP1Trigs = 34
    expectedP3Trigs = 34
    
    totalTrigsEntireExpt = expectedP1Trigs + totalP2Trigs + expectedP3Trigs
  # print(totalTrigsEntireExpt)
    return totalTrigsEntireExpt

#print(expectedTriggerCalculator(r"C:\Users\cjwin\OneDrive - Queen Mary, University of London\Documents\DAAMEE\Data Prepro+An 10-23 On\\", "10"))