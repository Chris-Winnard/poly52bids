import mne
from mne_bids import BIDSPath, write_raw_bids, update_sidecar_json
import pybv
import ceegrid_coords
import os
import datetime
from datetime import timezone
import numpy as np
import pandas as pd

"""Versions of setAndTrigs2bids (in order):
-Baseline.
-No ceegrid data.
-Only some ceegrid data.
-Extra data. Only for converting the extra data, not other data from the chosen participant."""

#Baseline version:
def setAndTrigs2bids(basePath, participantNumber, partStartEndLatencies_scalp, partStartEndLatencies_ceegrid, additionalData):
    setDataPath = basePath + 'EEG Set Files (Unprocessed)\\'
    
    bidsRoot = basePath + 'bids_dataset'
    
    """IMPORTANT: Remember to change recording date/time, participant sex and birthday. If birthday is unknown,
    can just assume it was the day before the recording (only care about age in years)."""

    subjFolder = "sub-"+ participantNumber
    
    sfreq = 1000
    
    #Recording date/time, and subject info:
    sex = additionalData["sex"]
    birthday = additionalData["Birthdate placeholder"]
    hand = additionalData["hand"]
    date = additionalData["Recdate UTC form"]
    date = date.astimezone(timezone.utc)
    
    subj_info_dict = {"id": int(participantNumber),
                      "his_id": subjFolder,
                      "sex" : sex, "hand" : hand,
                      "birthday" : birthday}


    #Date needs to be in form <class 'datetime.datetime'>

    #Include high/low cutoffs? Units?
    
############################################################################################################################################
    #scalp:
    eeg_type = "scalp"
    
    #Import data:
    participantID = 'P' + participantNumber
    fileName_set = participantID + '_' + eeg_type + '.set'
    fileFullPath = os.path.join(setDataPath, fileName_set)
    
    eeg_raw = mne.io.read_raw_eeglab(fileFullPath)
    
    startLats_scalp = partStartEndLatencies_scalp[0,:]
    
    #Get the duration of the EEG recording in seconds
    eeg_duration_scalp = eeg_raw.times[-1]  #Gets the time of the last sample
    n_channels = eeg_raw.info['nchan']  #Number of EEG channels
    
    #Adjust endLats but keep buffer in mind for padding later
    endLats_scalp = partStartEndLatencies_scalp[1,:]
    
    #Add in info:
    standard_1020 = mne.channels.make_standard_montage("standard_1020", head_size=0.095)
    eeg_raw.set_montage(standard_1020)
    
    eeg_raw.info['subject_info'] = subj_info_dict
    eeg_raw.info['line_freq'] = 50
    eeg_raw.set_meas_date(date)
    
    #Set NaNs to 0:
    eeg_raw_array = eeg_raw.get_data() #Convert mne data to numpy darray
    eeg_raw_array[np.isnan(eeg_raw_array)] = 0
    eeg_raw = mne.io.RawArray(eeg_raw_array, eeg_raw.info) #Convert output to mne RawArray again
    
    segments = []
    for start, stop in zip(startLats_scalp, endLats_scalp):
        if stop > eeg_duration_scalp:
            #Calculate how many samples of zero-padding are needed
            extra_samples = int((stop - eeg_duration_scalp) * sfreq)
            
            #Get the segment up to the end of the recording
            segment_data = eeg_raw.copy().crop(tmin=start, tmax=eeg_duration_scalp).get_data()
            
            #Create a zero array for padding, matching the number of channels and extra samples
            padding = np.zeros((n_channels, extra_samples))
            
            #Concatenate the actual data with the zero padding
            segment_padded = np.concatenate((segment_data, padding), axis=1)
            
            #Create an MNE RawArray from the padded segment
            segment_padded_raw = mne.io.RawArray(segment_padded, eeg_raw.info)
            segments.append(segment_padded_raw)
        else:
            #No padding needed, crop normally
            segments.append(eeg_raw.copy().crop(tmin=start, tmax=stop))
    
    #Note: measurement date and time will (should?) automatically be adjusted
    
    for i, segment in enumerate(segments):
        task = ['emotion', 'attnMultInstOBs', 'attnOneInstNoOBs'][i]
        
        if task == 'emotion':
            taskDes = "A task based around listening to 30s music pieces and feeding back emotions for emotion decoding purposes. Utilises the (continuous) VAD emotion model."
            instructions = "Listen to a brief music piece, and afterwards record your emotions using sliders. Repeat for all trials."
        elif task == 'attnMultInstOBs':
            taskDes = "An oddball test where the participant must focus on one of three spatially separated instruments, and have to count oddballs in a designated instrument whilst ignoring those in the other two instruments."
            instructions = "Listen to three instruments from different directions, attending to a designated instrument (30s of music, 5s pause, music repeats). There will be 1-3 pitch oddballs in all three streams in the final 30s, count the attended instrument's oddballs. Repeat for all trials."
        else:
            taskDes = "An attention-based task, where a participant is told to attend to some music or just let their mind wander (equal probability), before a 30s piece plays. Each trial followed by a mini 'interview' on the participant's thoughts, primarily to help them focus."
            instructions = ("""Some music will play, and you will be told to either 'Attend' to the music, or to 'Not attend', in which case you can just let your mind wander, or think about something else, e.g what you will have for dinner later, a place, anything apart from the music. After the
             music has finished, the experimenter will either ask you what you thought of the music (if you were told to 'Attend'), or ask what you were thinking about instead of the music (if you were told to 'Not attend').""")

        additional_metadata = {"EEGGround" : "Rear neck", #Note: RecordingDuration handled automatically.
                                "SoftwareFilters": "n/a",
                                "EEGReference": "Average",
                                "SamplingFrequency": sfreq,
                                "CapManufacturer": "TMSi",
                                "CapManufacturersModelName": "TMSI MobA-Headcap 10-20M",
                                "EEGChannelCount": 32,
                                "ECGChannelCount": 0,
                                "EOGChannelCount": 0,
                                "MISCChannelCount": 0,
                                "TriggerChannelCount": 1,
                                "Manufacturer": "BIOPAC",
                                "ManufacturersModelName": "Mobita",
                                "RecordingType" : "continuous",
                                "EEGPlacementScheme" : "10-20",
                                "HardwareFilters": "n/a",
                                "TaskName" : task,
                                "TaskDescription": taskDes,
                                "Instructions": instructions}
        
        bids_path = BIDSPath(subject=participantNumber, datatype='eeg', root=bidsRoot,
                             task=task, acquisition=eeg_type)
    
        write_raw_bids(segment, bids_path=bids_path,overwrite=True,allow_preload=True,format="EDF")
        # Create new BIDSPath pointing to the sidecar JSON
        json_path = bids_path.copy().update(suffix='eeg', extension='.json')
        
        # Now update the JSON
        update_sidecar_json(json_path, additional_metadata, verbose=False)
        
###########################################################################################################################################################################################
    #cEEGrid:
    eeg_type = "ceegrid"

    #Import data:
    fileName_set = participantID + '_' + eeg_type + '.set'
    fileFullPath = os.path.join(setDataPath, fileName_set)
        
    eeg_raw = mne.io.read_raw_eeglab(fileFullPath)
    
    startLats_ceegrid = partStartEndLatencies_ceegrid[0,:]
    
    #Get the duration of the EEG recording in seconds
    eeg_duration_ceegrid = eeg_raw.times[-1]  #Gets the time of the last sample
    n_channels = eeg_raw.info['nchan']  #Number of EEG channels
    
    #Adjust endLats but keep buffer in mind for padding later
    endLats_ceegrid = partStartEndLatencies_ceegrid[1,:]
    
    #Add in info:
    ceegrid_montage = ceegrid_coords.montage(1000)
    eeg_raw.set_montage(ceegrid_montage.get_montage())
    
    eeg_raw.info['subject_info'] = subj_info_dict
    eeg_raw.info['line_freq'] = 50
    eeg_raw.set_meas_date(date)
    
    #Set NaNs to 0:
    eeg_raw_array = eeg_raw.get_data() #Convert mne data to numpy darray
    eeg_raw_array[np.isnan(eeg_raw_array)] = 0
    eeg_raw = mne.io.RawArray(eeg_raw_array, eeg_raw.info) #Convert output to mne RawArray again
    
    segments = []
    for start, stop in zip(startLats_ceegrid, endLats_ceegrid):
        if stop > eeg_duration_ceegrid:
            #Calculate how many samples of zero-padding are needed
            extra_samples = int((stop - eeg_duration_ceegrid) * sfreq)
            
            #Get the segment up to the end of the recording
            segment_data = eeg_raw.copy().crop(tmin=start, tmax=eeg_duration_ceegrid).get_data()
            
            #Create a zero array for padding, matching the number of channels and extra samples
            padding = np.zeros((n_channels, extra_samples))
            
            #Concatenate the actual data with the zero padding
            segment_padded = np.concatenate((segment_data, padding), axis=1)
            
            #Create an MNE RawArray from the padded segment
            segment_padded_raw = mne.io.RawArray(segment_padded, eeg_raw.info)
            segments.append(segment_padded_raw)
        else:
            #No padding needed, crop normally
            segments.append(eeg_raw.copy().crop(tmin=start, tmax=stop))
    
    #Note: measurement date and time will (should?) automatically be adjusted
    
    for i, segment in enumerate(segments):
        task = ['emotion', 'attnMultInstOBs', 'attnOneInstNoOBs'][i]
        
        if task == 'emotion':
            taskDes = "A task based around listening to 30s music pieces and feeding back emotions for emotion decoding purposes. Utilises the (continuous) VAD emotion model."
            instructions = "Listen to a brief music piece, and afterwards record your emotions using sliders. Repeat for all trials."
        elif task == 'attnMultInstOBs':
            taskDes = "An oddball test where the participant must focus on one of three spatially separated instruments, and have to count oddballs in a designated instrument whilst ignoring those in the other two instruments."
            instructions = "Listen to three instruments from different directions, attending to a designated instrument (30s of music, 5s pause, music repeats). There will be 1-3 pitch oddballs in all three streams in the final 30s, count the attended instrument's oddballs. Repeat for all trials."
        else:
            taskDes = "An attention-based task, where a participant is told to attend to some music or just let their mind wander (equal probability), before a 30s piece plays. Each trial followed by a mini 'interview' on the participant's thoughts, primarily to help them focus."
            instructions = ("""Some music will play, and you will be told to either 'Attend' to the music, or to 'Not attend', in which case you can just let your mind wander, or think about something else, e.g what you will have for dinner later, a place, anything apart from the music. After the
                            music has finished, the experimenter will either ask you what you thought of the music (if you were told to 'Attend'), or ask what you were thinking about instead of the music (if you were told to 'Not attend').""")
             
        additional_metadata = {"EEGGround" : "chin", #Note: RecordingDuration handled automatically.
                                "SoftwareFilters": "n/a",
                                "EEGReference": "Average",
                                "SamplingFrequency": sfreq,
                                "CapManufacturer": "TMSi",
                                "CapManufacturersModelName": "TMSI MobA-Headcap 10-20M",
                                "EEGChannelCount": 21,
                                "ECGChannelCount": 0,
                                "EOGChannelCount": 0,
                                "MISCChannelCount": 0,
                                "TriggerChannelCount": 1,
                                "Manufacturer": "BIOPAC",
                                "ManufacturersModelName": "Mobita",
                                "RecordingType" : "continuous",
                                "EEGPlacementScheme" : "ceegrid",
                                "HardwareFilters": "n/a",
                                "TaskName" : task,
                                "TaskDescription": taskDes,
                                "Instructions": instructions}
        
        bids_path = BIDSPath(subject=participantNumber, datatype='eeg', root=bidsRoot,
                             task=task, acquisition=eeg_type)
        
        write_raw_bids(segment, bids_path=bids_path,overwrite=True,allow_preload=True,format="EDF")
        # Create new BIDSPath pointing to the sidecar JSON
        json_path = bids_path.copy().update(suffix='eeg', extension='.json')
        
        # Now update the JSON
        update_sidecar_json(json_path, additional_metadata, verbose=False)
###########################################################################################################################################
    #Whilst we're at it:
        
    dataPath = basePath + '/sourcedata/P' + participantNumber + '/'
    
    questionnairePath = dataPath + 'Questionnaire Data.csv'
    
    task = "questionnaire"
    #Read and save questionnaire data
    questionnaire_data = pd.read_csv(questionnairePath)
    questionnaire_bids_path = BIDSPath(subject=participantNumber, task=task, suffix='beh', extension='.tsv', root=bidsRoot, datatype='beh')
    questionnaire_bids_path.mkdir()
    questionnaire_data.to_csv(questionnaire_bids_path.fpath, sep='\t', index=False)

    #Save participant response files
    response_files = ['Part 1 Data.csv', 'Part 2 Data.csv', 'Part 3 Data.csv']
    response_tasks = ['emotion', 'attnMultInstOBs', 'attnOneInstNoOBs']
    
    for response_file, task in zip(response_files, response_tasks):
        responsePath = os.path.join(dataPath, response_file)
        response_data = pd.read_csv(responsePath)
        response_bids_path = BIDSPath(subject=participantNumber, task=task, suffix='beh', extension='.tsv', root=bidsRoot, datatype='beh')
        response_bids_path.mkdir()
        response_data.to_csv(response_bids_path.fpath, sep='\t', index=False)


#Version for converting if no ceegrid data:
def setAndTrigs2bids_no_ceegrid(basePath, participantNumber, partStartEndLatencies_scalp, additionalData):
    setDataPath = basePath + 'EEG Set Files (Unprocessed)\\'
    
    bidsRoot = basePath + 'bids_dataset'
    
    """IMPORTANT: Remember to change recording date/time, participant sex and birthday. If birthday is unknown,
    can just assume it was the day before the recording (only care about age in years)."""

    subjFolder = "sub-"+ participantNumber
    
    sfreq = 1000
    
    #Recording date/time, and subject info:
    sex = additionalData["sex"]
    birthday = additionalData["Birthdate placeholder"]
    hand = additionalData["hand"]
    date = additionalData["Recdate UTC form"]
    date = date.astimezone(timezone.utc)
    
    subj_info_dict = {"id": int(participantNumber),
                      "his_id": subjFolder,
                      "sex" : sex, "hand" : hand,
                      "birthday" : birthday}
    
############################################################################################################################################
    #scalp:
    eeg_type = "scalp"
    
    #Import data:
    participantID = 'P' + participantNumber
    fileName_set = participantID + '_' + eeg_type + '.set'
    fileFullPath = os.path.join(setDataPath, fileName_set)
    
    eeg_raw = mne.io.read_raw_eeglab(fileFullPath)
    
    startLats_scalp = partStartEndLatencies_scalp[0,:]
    
    #Get the duration of the EEG recording in seconds
    eeg_duration_scalp = eeg_raw.times[-1]  #Gets the time of the last sample
    n_channels = eeg_raw.info['nchan']  #Number of EEG channels
    
    #Adjust endLats but keep buffer in mind for padding later
    endLats_scalp = partStartEndLatencies_scalp[1,:]
    
    #Add in info:
    standard_1020 = mne.channels.make_standard_montage("standard_1020", head_size=0.095)
    eeg_raw.set_montage(standard_1020)
    
    eeg_raw.info['subject_info'] = subj_info_dict
    eeg_raw.info['line_freq'] = 50
    eeg_raw.set_meas_date(date)
    
    #Set NaNs to 0:
    eeg_raw_array = eeg_raw.get_data() #Convert mne data to numpy darray
    eeg_raw_array[np.isnan(eeg_raw_array)] = 0
    eeg_raw = mne.io.RawArray(eeg_raw_array, eeg_raw.info) #Convert output to mne RawArray again
    
    segments = []
    for start, stop in zip(startLats_scalp, endLats_scalp):
        if stop > eeg_duration_scalp:
            #Calculate how many samples of zero-padding are needed
            extra_samples = int((stop - eeg_duration_scalp) * sfreq)
            
            #Get the segment up to the end of the recording
            segment_data = eeg_raw.copy().crop(tmin=start, tmax=eeg_duration_scalp).get_data()
            
            #Create a zero array for padding, matching the number of channels and extra samples
            padding = np.zeros((n_channels, extra_samples))
            
            #Concatenate the actual data with the zero padding
            segment_padded = np.concatenate((segment_data, padding), axis=1)
            
            #Create an MNE RawArray from the padded segment
            segment_padded_raw = mne.io.RawArray(segment_padded, eeg_raw.info)
            segments.append(segment_padded_raw)
        else:
            #No padding needed, crop normally
            segments.append(eeg_raw.copy().crop(tmin=start, tmax=stop))
    
    #Note: measurement date and time will (should?) automatically be adjusted
    
    for i, segment in enumerate(segments):
        task = ['emotion', 'attnMultInstOBs', 'attnOneInstNoOBs'][i]
        
        if task == 'emotion':
            taskDes = "A task based around listening to 30s music pieces and feeding back emotions for emotion decoding purposes. Utilises the (continuous) VAD emotion model."
            instructions = "Listen to a brief music piece, and afterwards record your emotions using sliders. Repeat for all trials."
        elif task == 'attnMultInstOBs':
            taskDes = "An oddball test where the participant must focus on one of three spatially separated instruments, and have to count oddballs in a designated instrument whilst ignoring those in the other two instruments."
            instructions = "Listen to three instruments from different directions, attending to a designated instrument (30s of music, 5s pause, music repeats). There will be 1-3 pitch oddballs in all three streams in the final 30s, count the attended instrument's oddballs. Repeat for all trials."
        else:
            taskDes = "An attention-based task, where a participant is told to attend to some music or just let their mind wander (equal probability), before a 30s piece plays. Each trial followed by a mini 'interview' on the participant's thoughts, primarily to help them focus."
            instructions = ("""Some music will play, and you will be told to either 'Attend' to the music, or to 'Not attend', in which case you can just let your mind wander, or think about something else, e.g what you will have for dinner later, a place, anything apart from the music. After the
             music has finished, the experimenter will either ask you what you thought of the music (if you were told to 'Attend'), or ask what you were thinking about instead of the music (if you were told to 'Not attend').""")
             
        additional_metadata = {"EEGGround" : "Rear neck", #Note: RecordingDuration handled automatically.
                                "SoftwareFilters": "n/a",
                                "EEGReference": "Average",
                                "SamplingFrequency": sfreq,
                                "CapManufacturer": "TMSi",
                                "CapManufacturersModelName": "TMSI MobA-Headcap 10-20M",
                                "EEGChannelCount": 32,
                                "ECGChannelCount": 0,
                                "EOGChannelCount": 0,
                                "MISCChannelCount": 0,
                                "TriggerChannelCount": 1,
                                "Manufacturer": "BIOPAC",
                                "ManufacturersModelName": "Mobita",
                                "RecordingType" : "continuous",
                                "EEGPlacementScheme" : "10-20",
                                "HardwareFilters": "n/a",
                                "TaskName" : task,
                                "TaskDescription": taskDes,
                                "Instructions": instructions}
        
        bids_path = BIDSPath(subject=participantNumber, datatype='eeg', root=bidsRoot,
                             task=task, acquisition=eeg_type)
            
        write_raw_bids(segment, bids_path=bids_path,overwrite=True,allow_preload=True,format="EDF")
        # Create new BIDSPath pointing to the sidecar JSON
        json_path = bids_path.copy().update(suffix='eeg', extension='.json')
        
        # Now update the JSON
        update_sidecar_json(json_path, additional_metadata, verbose=False)

###########################################################################################################################################
    #Whilst we're at it:
        
    dataPath = basePath + '/sourcedata/P' + participantNumber + '/'
    
    questionnairePath = dataPath + 'Questionnaire Data.csv'
    
    task = "questionnaire"
    #Read and save questionnaire data
    questionnaire_data = pd.read_csv(questionnairePath)
    questionnaire_bids_path = BIDSPath(subject=participantNumber, task=task, suffix='beh', extension='.tsv', root=bidsRoot, datatype='beh')
    questionnaire_bids_path.mkdir()
    questionnaire_data.to_csv(questionnaire_bids_path.fpath, sep='\t', index=False)

    #Save participant response files
    response_files = ['Part 1 Data.csv', 'Part 2 Data.csv', 'Part 3 Data.csv']
    response_tasks = ['emotion', 'attnMultInstOBs', 'attnOneInstNoOBs']
    
    for response_file, task in zip(response_files, response_tasks):
        responsePath = os.path.join(dataPath, response_file)
        response_data = pd.read_csv(responsePath)
        response_bids_path = BIDSPath(subject=participantNumber, task=task, suffix='beh', extension='.tsv', root=bidsRoot, datatype='beh')
        response_bids_path.mkdir()
        response_data.to_csv(response_bids_path.fpath, sep='\t', index=False)


#Version for converting if only some ceegrid data:
def setAndTrigs2bids_partial_ceegrid(basePath, participantNumber, partStartEndLatencies_scalp, partStartEndLatencies_ceegrid, additionalData):
    setDataPath = basePath + 'EEG Set Files (Unprocessed)\\'
    
    bidsRoot = basePath + 'bids_dataset'
    
    """IMPORTANT: Remember to change recording date/time, participant sex and birthday. If birthday is unknown,
    can just assume it was the day before the recording (only care about age in years)."""

    subjFolder = "sub-"+ participantNumber
    
    sfreq = 1000
    
    #Recording date/time, and subject info:
    sex = additionalData["sex"]
    birthday = additionalData["Birthdate placeholder"]
    hand = additionalData["hand"]
    date = additionalData["Recdate UTC form"]
    date = date.astimezone(timezone.utc)
    
    subj_info_dict = {"id": int(participantNumber),
                      "his_id": subjFolder,
                      "sex" : sex, "hand" : hand,
                      "birthday" : birthday}
    
############################################################################################################################################
    #scalp:
    eeg_type = "scalp"
    
    #Import data:
    participantID = 'P' + participantNumber
    fileName_set = participantID + '_' + eeg_type + '.set'
    fileFullPath = os.path.join(setDataPath, fileName_set)
    
    eeg_raw = mne.io.read_raw_eeglab(fileFullPath)
    
    startLats_scalp = partStartEndLatencies_scalp[0,:]
    
    #Get the duration of the EEG recording in seconds
    eeg_duration_scalp = eeg_raw.times[-1]  #Gets the time of the last sample
    n_channels = eeg_raw.info['nchan']  #Number of EEG channels
    
    #Adjust endLats but keep buffer in mind for padding later
    endLats_scalp = partStartEndLatencies_scalp[1,:]
    
    #Add in info:
    standard_1020 = mne.channels.make_standard_montage("standard_1020", head_size=0.095)
    eeg_raw.set_montage(standard_1020)
    
    eeg_raw.info['subject_info'] = subj_info_dict
    eeg_raw.info['line_freq'] = 50
    eeg_raw.set_meas_date(date)
    
    #Set NaNs to 0:
    eeg_raw_array = eeg_raw.get_data() #Convert mne data to numpy darray
    eeg_raw_array[np.isnan(eeg_raw_array)] = 0
    eeg_raw = mne.io.RawArray(eeg_raw_array, eeg_raw.info) #Convert output to mne RawArray again
    
    segments = []
    for start, stop in zip(startLats_scalp, endLats_scalp):
        if stop > eeg_duration_scalp:
            #Calculate how many samples of zero-padding are needed
            extra_samples = int((stop - eeg_duration_scalp) * sfreq)
            
            #Get the segment up to the end of the recording
            segment_data = eeg_raw.copy().crop(tmin=start, tmax=eeg_duration_scalp).get_data()
            
            #Create a zero array for padding, matching the number of channels and extra samples
            padding = np.zeros((n_channels, extra_samples))
            
            #Concatenate the actual data with the zero padding
            segment_padded = np.concatenate((segment_data, padding), axis=1)
            
            #Create an MNE RawArray from the padded segment
            segment_padded_raw = mne.io.RawArray(segment_padded, eeg_raw.info)
            segments.append(segment_padded_raw)
        else:
            #No padding needed, crop normally
            segments.append(eeg_raw.copy().crop(tmin=start, tmax=stop))
    
    #Note: measurement date and time will (should?) automatically be adjusted

    for i, segment in enumerate(segments):
        task = ['emotion', 'attnMultInstOBs', 'attnOneInstNoOBs'][i]
        
        if task == 'emotion':
            taskDes = "A task based around listening to 30s music pieces and feeding back emotions for emotion decoding purposes. Utilises the (continuous) VAD emotion model."
            instructions = "Listen to a brief music piece, and afterwards record your emotions using sliders. Repeat for all trials."
        elif task == 'attnMultInstOBs':
            taskDes = "An oddball test where the participant must focus on one of three spatially separated instruments, and have to count oddballs in a designated instrument whilst ignoring those in the other two instruments."
            instructions = "Listen to three instruments from different directions, attending to a designated instrument (30s of music, 5s pause, music repeats). There will be 1-3 pitch oddballs in all three streams in the final 30s, count the attended instrument's oddballs. Repeat for all trials."
        else:
            taskDes = "An attention-based task, where a participant is told to attend to some music or just let their mind wander (equal probability), before a 30s piece plays. Each trial followed by a mini 'interview' on the participant's thoughts, primarily to help them focus."
            instructions = ("""Some music will play, and you will be told to either 'Attend' to the music, or to 'Not attend', in which case you can just let your mind wander, or think about something else, e.g what you will have for dinner later, a place, anything apart from the music. After the
             music has finished, the experimenter will either ask you what you thought of the music (if you were told to 'Attend'), or ask what you were thinking about instead of the music (if you were told to 'Not attend').""")

        additional_metadata = {"EEGGround" : "Rear neck", #Note: RecordingDuration handled automatically.
                                "SoftwareFilters": "n/a",
                                "EEGReference": "Average",
                                "SamplingFrequency": sfreq,
                                "CapManufacturer": "TMSi",
                                "CapManufacturersModelName": "TMSI MobA-Headcap 10-20M",
                                "EEGChannelCount": 32,
                                "ECGChannelCount": 0,
                                "EOGChannelCount": 0,
                                "MISCChannelCount": 0,
                                "TriggerChannelCount": 1,
                                "Manufacturer": "BIOPAC",
                                "ManufacturersModelName": "Mobita",
                                "RecordingType" : "continuous",
                                "EEGPlacementScheme" : "10-20",
                                "HardwareFilters": "n/a",
                                "TaskName" : task,
                                "TaskDescription": taskDes,
                                "Instructions": instructions}
        
        bids_path = BIDSPath(subject=participantNumber, datatype='eeg', root=bidsRoot,
                             task=task, acquisition=eeg_type)
        
        write_raw_bids(segment, bids_path=bids_path,overwrite=True,allow_preload=True,format="EDF")
        # Create new BIDSPath pointing to the sidecar JSON
        json_path = bids_path.copy().update(suffix='eeg', extension='.json')
        
        # Now update the JSON
        update_sidecar_json(json_path, additional_metadata, verbose=False)

###########################################################################################################################################################################################
    #cEEGrid:
    eeg_type = "ceegrid"

    #Import data:
    fileName_set = participantID + '_' + eeg_type + '.set'
    fileFullPath = os.path.join(setDataPath, fileName_set)
        
    eeg_raw = mne.io.read_raw_eeglab(fileFullPath)
    
    startLats_ceegrid = partStartEndLatencies_ceegrid[0,:]
    
    #Get the duration of the EEG recording in seconds
    eeg_duration_ceegrid = eeg_raw.times[-1]  #Gets the time of the last sample
    n_channels = eeg_raw.info['nchan']  #Number of EEG channels
    
    #Adjust endLats but keep buffer in mind for padding later
    endLats_ceegrid = partStartEndLatencies_ceegrid[1,:]
    
    #Add in info:
    ceegrid_montage = ceegrid_coords.montage(1000)
    eeg_raw.set_montage(ceegrid_montage.get_montage())
    
    eeg_raw.info['subject_info'] = subj_info_dict
    eeg_raw.info['line_freq'] = 50
    eeg_raw.set_meas_date(date)
    
    #Set NaNs to 0:
    eeg_raw_array = eeg_raw.get_data() #Convert mne data to numpy darray
    eeg_raw_array[np.isnan(eeg_raw_array)] = 0
    eeg_raw = mne.io.RawArray(eeg_raw_array, eeg_raw.info) #Convert output to mne RawArray again
    
    segments = []
    for start, stop in zip(startLats_ceegrid, endLats_ceegrid):
        if stop > eeg_duration_ceegrid:
            #Calculate how many samples of zero-padding are needed
            extra_samples = int((stop - eeg_duration_ceegrid) * sfreq)
            
            #Get the segment up to the end of the recording
            segment_data = eeg_raw.copy().crop(tmin=start, tmax=eeg_duration_ceegrid).get_data()
            
            #Create a zero array for padding, matching the number of channels and extra samples
            padding = np.zeros((n_channels, extra_samples))
            
            #Concatenate the actual data with the zero padding
            segment_padded = np.concatenate((segment_data, padding), axis=1)
            
            #Create an MNE RawArray from the padded segment
            segment_padded_raw = mne.io.RawArray(segment_padded, eeg_raw.info)
            segments.append(segment_padded_raw)
        else:
            #No padding needed, crop normally
            segments.append(eeg_raw.copy().crop(tmin=start, tmax=stop))
    
    #Note: measurement date and time will (should?) automatically be adjusted
    
    for i, segment in enumerate(segments):
        task = ['emotion', 'attnMultInstOBs', 'attnOneInstNoOBs'][i]
        
        if task == 'emotion':
            taskDes = "A task based around listening to 30s music pieces and feeding back emotions for emotion decoding purposes. Utilises the (continuous) VAD emotion model."
            instructions = "Listen to a brief music piece, and afterwards record your emotions using sliders. Repeat for all trials."
        elif task == 'attnMultInstOBs':
            taskDes = "An oddball test where the participant must focus on one of three spatially separated instruments, and have to count oddballs in a designated instrument whilst ignoring those in the other two instruments."
            instructions = "Listen to three instruments from different directions, attending to a designated instrument (30s of music, 5s pause, music repeats). There will be 1-3 pitch oddballs in all three streams in the final 30s, count the attended instrument's oddballs. Repeat for all trials."
        else:
            taskDes = "An attention-based task, where a participant is told to attend to some music or just let their mind wander (equal probability), before a 30s piece plays. Each trial followed by a mini 'interview' on the participant's thoughts, primarily to help them focus."
            instructions = ("""Some music will play, and you will be told to either 'Attend' to the music, or to 'Not attend', in which case you can just let your mind wander, or think about something else, e.g what you will have for dinner later, a place, anything apart from the music. After the
             music has finished, the experimenter will either ask you what you thought of the music (if you were told to 'Attend'), or ask what you were thinking about instead of the music (if you were told to 'Not attend').""")

        additional_metadata = {"EEGGround" : "Rear neck", #Note: RecordingDuration handled automatically.
                                "SoftwareFilters": "n/a",
                                "EEGReference": "Average",
                                "SamplingFrequency": sfreq,
                                "CapManufacturer": "TMSi",
                                "CapManufacturersModelName": "TMSI MobA-Headcap 10-20M",
                                "EEGChannelCount": 32,
                                "ECGChannelCount": 0,
                                "EOGChannelCount": 0,
                                "MISCChannelCount": 0,
                                "TriggerChannelCount": 1,
                                "Manufacturer": "BIOPAC",
                                "ManufacturersModelName": "Mobita",
                                "RecordingType" : "continuous",
                                "EEGPlacementScheme" : "10-20",
                                "HardwareFilters": "n/a",
                                "TaskName" : task,
                                "TaskDescription": taskDes,
                                "Instructions": instructions}
    
        bids_path = BIDSPath(subject=participantNumber, datatype='eeg', root=bidsRoot,
                             task=task, acquisition=eeg_type)
            
        write_raw_bids(segment, bids_path=bids_path,overwrite=True,allow_preload=True,format="EDF")
        # Create new BIDSPath pointing to the sidecar JSON
        json_path = bids_path.copy().update(suffix='eeg', extension='.json')
        
        # Now update the JSON
        update_sidecar_json(json_path, additional_metadata, verbose=False)
        
###########################################################################################################################################
    #Whilst we're at it:
        
    dataPath = basePath + '/sourcedata/P' + participantNumber + '/'
    
    questionnairePath = dataPath + 'Questionnaire Data.csv'
    
    task = "questionnaire"
    #Read and save questionnaire data
    questionnaire_data = pd.read_csv(questionnairePath)
    questionnaire_bids_path = BIDSPath(subject=participantNumber, task=task, suffix='beh', extension='.tsv', root=bidsRoot, datatype='beh')
    questionnaire_bids_path.mkdir()
    questionnaire_data.to_csv(questionnaire_bids_path.fpath, sep='\t', index=False)

    #Save participant response files
    response_files = ['Part 1 Data.csv', 'Part 2 Data.csv', 'Part 3 Data.csv']
    response_tasks = ['emotion', 'attnMultInstOBs', 'attnOneInstNoOBs']
    
    for response_file, task in zip(response_files, response_tasks):
        responsePath = os.path.join(dataPath, response_file)
        response_data = pd.read_csv(responsePath)
        response_bids_path = BIDSPath(subject=participantNumber, task=task, suffix='beh', extension='.tsv', root=bidsRoot, datatype='beh')
        response_bids_path.mkdir()
        response_data.to_csv(response_bids_path.fpath, sep='\t', index=False)


#Version to convert extra data- doesn't convert other data from the same participant:
def setAndTrigs2bids_extraData(basePath, participantNumber, partStartEndLatencies_scalp, partStartEndLatencies_ceegrid, additionalData):
    setDataPath = basePath + 'EEG Set Files (Unprocessed)\\'
    
    bidsRoot = basePath + 'bids_dataset'
    
    subjFolder = "sub-"+ participantNumber
    
    sfreq = 1000
    
    #Recording date/time, and subject info:
    sex = additionalData["sex"]
    birthday = additionalData["Birthdate placeholder"]
    hand = additionalData["hand"]
    date = additionalData["Recdate UTC form"]
    date = date.astimezone(timezone.utc)
    
    subj_info_dict = {"id": int(participantNumber),
                      "his_id": subjFolder,
                      "sex" : sex, "hand" : hand,
                      "birthday" : birthday}

############################################################################################################################################
    if participantNumber == "09":
        task = 'attnMultInstOBsExtra'
    if participantNumber == "28":
        task = 'attnOneInstNoOBsExtra'
        
    subjFolder = 'sub-' + participantNumber
        
    eeg_type = "scalp"
    
    #Import data:
    participantID = 'P' + participantNumber
    fileName_set = participantID + '_' + eeg_type + '.set'
    fileFullPath = os.path.join(setDataPath, fileName_set)
    
    eeg_raw = mne.io.read_raw_eeglab(fileFullPath)

    startLat_scalp = partStartEndLatencies_scalp[0]

    #Get the duration of the EEG recording in seconds
    eeg_duration_scalp = eeg_raw.times[-1]  #Gets the time of the last sample
    n_channels = eeg_raw.info['nchan']  #Number of EEG channels

    #Adjust endLats but keep buffer in mind for padding later
    endLat_scalp = partStartEndLatencies_scalp[1]

    #Add in info:
    standard_1020 = mne.channels.make_standard_montage("standard_1020", head_size=0.095)
    eeg_raw.set_montage(standard_1020)

    eeg_raw.info['subject_info'] = subj_info_dict
    eeg_raw.info['line_freq'] = 50
    eeg_raw.set_meas_date(date)

    #Set NaNs to 0:
    eeg_raw_array = eeg_raw.get_data() #Convert mne data to numpy darray
    eeg_raw_array[np.isnan(eeg_raw_array)] = 0
    eeg_raw = mne.io.RawArray(eeg_raw_array, eeg_raw.info) #Convert output to mne RawArray again
    
    if endLat_scalp > eeg_duration_scalp:
        #Calculate how many samples of zero-padding are needed
        extra_samples = int((endLat_scalp - eeg_duration_scalp) * sfreq)
        
        #Get the segment up to the end of the recording
        segment_data = eeg_raw.copy().crop(tmin=startLat_scalp, tmax=eeg_duration_scalp).get_data()
        
        #Create a zero array for padding, matching the number of channels and extra samples
        padding = np.zeros((n_channels, extra_samples))
        
        #Concatenate the actual data with the zero padding
        segment_padded = np.concatenate((segment_data, padding), axis=1)
        
        #Create an MNE RawArray from the padded segment
        segment = mne.io.RawArray(segment_padded, eeg_raw.info)
    else:
        #No padding needed, crop normally
        segment = eeg_raw.copy().crop(tmin=startLat_scalp, tmax=endLat_scalp)
    
    #Note: measurement date and time will (should?) automatically be adjusted

    if task == 'attnMultInstOBsExtra':
        taskDes = "An oddball test where the participant must focus on one of three spatially separated instruments, and have to count oddballs in a designated instrument whilst ignoring those in the other two instruments."
        instructions = "Listen to three instruments from different directions, attending to a designated instrument (30s of music, 5s pause, music repeats). There will be 1-3 pitch oddballs in all three streams in the final 30s, count the attended instrument's oddballs. Repeat for all trials."
    else:
        taskDes = "An attention-based task, where a participant is told to attend to some music or just let their mind wander (equal probability), before a 30s piece plays. Each trial followed by a mini 'interview' on the participant's thoughts, primarily to help them focus."
        instructions = ("""Some music will play, and you will be told to either 'Attend' to the music, or to 'Not attend', in which case you can just let your mind wander, or think about something else, e.g what you will have for dinner later, a place, anything apart from the music. After the
         music has finished, the experimenter will either ask you what you thought of the music (if you were told to 'Attend'), or ask what you were thinking about instead of the music (if you were told to 'Not attend').""")
         
    additional_metadata = {"EEGGround" : "Rear neck", #Note: RecordingDuration handled automatically.
                            "SoftwareFilters": "n/a",
                            "EEGReference": "Average",
                            "SamplingFrequency": sfreq,
                            "CapManufacturer": "TMSi",
                            "CapManufacturersModelName": "TMSI MobA-Headcap 10-20M",
                            "EEGChannelCount": 32,
                            "ECGChannelCount": 0,
                            "EOGChannelCount": 0,
                            "MISCChannelCount": 0,
                            "TriggerChannelCount": 1,
                            "Manufacturer": "BIOPAC",
                            "ManufacturersModelName": "Mobita",
                            "RecordingType" : "continuous",
                            "EEGPlacementScheme" : "10-20",
                            "HardwareFilters": "n/a",
                            "TaskName" : task,
                            "TaskDescription": taskDes,
                            "Instructions": instructions}
 
    #Use 'misc' folder instead of participant-specific folder
    misc_folder = os.path.join(bidsRoot, 'misc')
    if not os.path.exists(misc_folder):
        os.makedirs(misc_folder)
            
    #Create BIDSPath for saving to 'misc' folder
    bids_path = BIDSPath(datatype='eeg', root=misc_folder, task=task, acquisition=eeg_type,subject=participantNumber)
            
    #Example for one EEG type, repeat similarly for other parts of your code
    write_raw_bids(segment, bids_path=bids_path, overwrite=True, allow_preload=True, format="EDF")
    
    # Create new BIDSPath pointing to the sidecar JSON
    json_path = bids_path.copy().update(suffix='eeg', extension='.json')
    
    # Now update the JSON
    update_sidecar_json(json_path, additional_metadata, verbose=False)

###########################################################################################################################################################################################
    #cEEGrid:
    eeg_type = "ceegrid"

    #Import data:
    fileName_set = participantID + '_' + eeg_type + '.set'
    fileFullPath = os.path.join(setDataPath, fileName_set)
        
    eeg_raw = mne.io.read_raw_eeglab(fileFullPath)
    
    startLat_ceegrid = partStartEndLatencies_ceegrid[0]
    
    #Get the duration of the EEG recording in seconds
    eeg_duration_ceegrid = eeg_raw.times[-1]  #Gets the time of the last sample
    n_channels = eeg_raw.info['nchan']  #Number of EEG channels
    
    #Adjust endLats but keep buffer in mind for padding later
    endLat_ceegrid = partStartEndLatencies_ceegrid[1]
    
    #Add in info:
    ceegrid_montage = ceegrid_coords.montage(1000)
    eeg_raw.set_montage(ceegrid_montage.get_montage())
    
    eeg_raw.info['subject_info'] = subj_info_dict
    eeg_raw.info['line_freq'] = 50
    eeg_raw.set_meas_date(date)
    
    #Set NaNs to 0:
    eeg_raw_array = eeg_raw.get_data() #Convert mne data to numpy darray
    eeg_raw_array[np.isnan(eeg_raw_array)] = 0
    eeg_raw = mne.io.RawArray(eeg_raw_array, eeg_raw.info) #Convert output to mne RawArray again

    if endLat_ceegrid > eeg_duration_ceegrid:
        #Calculate how many samples of zero-padding are needed
        extra_samples = int((endLat_ceegrid - eeg_duration_ceegrid) * sfreq)
        
        #Get the segment up to the end of the recording
        segment_data = eeg_raw.copy().crop(tmin=startLat_ceegrid, tmax=eeg_duration_ceegrid).get_data()
        
        #Create a zero array for padding, matching the number of channels and extra samples
        padding = np.zeros((n_channels, extra_samples))
        
        #Concatenate the actual data with the zero padding
        segment_padded = np.concatenate((segment_data, padding), axis=1)
        
        #Create an MNE RawArray from the padded segment
        segment = mne.io.RawArray(segment_padded, eeg_raw.info)
    else:
        #No padding needed, crop normally
        segment = eeg_raw.copy().crop(tmin=startLat_ceegrid, tmax=endLat_ceegrid)
    
    #Note: measurement date and time will (should?) automatically be adjusted

    if task == 'attnMultInstOBsExtra':
        taskDes = "An oddball test where the participant must focus on one of three spatially separated instruments, and have to count oddballs in a designated instrument whilst ignoring those in the other two instruments."
        instructions = "Listen to three instruments from different directions, attending to a designated instrument (30s of music, 5s pause, music repeats). There will be 1-3 pitch oddballs in all three streams in the final 30s, count the attended instrument's oddballs. Repeat for all trials."
    else:
        taskDes = "An attention-based task, where a participant is told to attend to some music or just let their mind wander (equal probability), before a 30s piece plays. Each trial followed by a mini 'interview' on the participant's thoughts, primarily to help them focus."
        instructions = ("""Some music will play, and you will be told to either 'Attend' to the music, or to 'Not attend', in which case you can just let your mind wander, or think about something else, e.g what you will have for dinner later, a place, anything apart from the music. After the
         music has finished, the experimenter will either ask you what you thought of the music (if you were told to 'Attend'), or ask what you were thinking about instead of the music (if you were told to 'Not attend').""")
             
    additional_metadata = {"EEGGround" : "chin", #Note: RecordingDuration handled automatically.
                            "SoftwareFilters": "n/a",
                            "EEGReference": "Average",
                            "SamplingFrequency": sfreq,
                           "CapManufacturer": "TMSi",
                           "CapManufacturersModelName": "TMSI MobA-Headcap 10-20M",
                            "EEGChannelCount": 21,
                            "ECGChannelCount": 0,
                            "EOGChannelCount": 0,
                            "MISCChannelCount": 0,
                            "TriggerChannelCount": 1,
                            "Manufacturer": "BIOPAC",
                            "ManufacturersModelName": "Mobita",
                            "RecordingType" : "continuous",
                            "EEGPlacementScheme" : "ceegrid",
                            "HardwareFilters": "n/a",
                            "TaskName" : task,
                            "TaskDescription": taskDes,
                            "Instructions": instructions}
    
    #Use 'misc' folder instead of participant-specific folder
    misc_folder = os.path.join(bidsRoot, 'misc')
    if not os.path.exists(misc_folder):
        os.makedirs(misc_folder)
    
    #Create BIDSPath for saving to 'misc' folder
    bids_path = BIDSPath(datatype='eeg', root=misc_folder, task=task, acquisition=eeg_type,subject=participantNumber)
    
    #Example for one EEG type, repeat similarly for other parts of your code
    write_raw_bids(segment, bids_path=bids_path, overwrite=True, allow_preload=True, format="EDF")
    
    # Create new BIDSPath pointing to the sidecar JSON
    json_path = bids_path.copy().update(suffix='eeg', extension='.json')
    
    # Now update the JSON
    update_sidecar_json(json_path, additional_metadata, verbose=False)