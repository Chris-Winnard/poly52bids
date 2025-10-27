import pandas as pd
from datetime import datetime

def additionalDataReader(basePath, participantNumber, handedness):
    "Read participant data such as age, rec date, etc."
    
    rawDataPath = basePath + "/sourcedata/P" + participantNumber + "/"
    questionnaireFile = rawDataPath + "Questionnaire Data.csv"
        
    df = pd.read_csv(questionnaireFile)
    df = df[['genderResp.response', 'genderRespOther.text', 'ageResp.text', 'date']]
    
    recDateTime = str(df.iloc[0]['date'])
    input_format = '%Y-%m-%d_%H:%M.%S%z'
    
    # Fix length (optional but helps to guarantee no issues by ensuring common length).
    #Will pad zeroes on, so 0.305 becomes 0.305000, since Python works with microsecs here.
    parts = recDateTime.split('.')
    if len(parts[-1]) < 6:
        parts[-1] = parts[-1].ljust(6, '0')
        recDateTime = '.'.join(parts)

    #Recordings were taken in Denmark, need to convert to Coordinated Universal Time.
    #For this particular dataset, all data was collected in Sep./early Oct. 2023 (Central European Summer Time, -2 hrs), or Jan./Feb. 2024 (-1hr),
    #so we can just use the year.
    if recDateTime[:4] == '2023':
        recDateTime = recDateTime[:13] + ':' + recDateTime[14:-7] + '-02:00'
    elif recDateTime[:4] == '2024':
        recDateTime = recDateTime[:13] + ':' + recDateTime[14:-7] + '-01:00'
    
    recDateTime_UTCform = datetime.strptime(recDateTime, input_format)

    sex = df.iloc[0]['genderResp.response'] #Note BIDS EEG considers bio. sex.
    if sex == "Male" or sex == "Transgender female":
        sexInt = 1
    elif sex == "Female" or sex == "Transgender male":
        sexInt = 2
    else:
        sexInt = 0 #"Other" (Note that mne-bids uses 'N/A'. The DAAMEE dataset only contains M/F/TM/TF anyway so not an issue.)
    
    if handedness == "right":
        handednessInt = 1
    elif handedness == "left":
        handednessInt = 2
    else:
        handednessInt = 3 #"Ambidextrous"
      
    age = df.iloc[0]['ageResp.text']
    
    #MNE's BIDS writer asks for birth date, and uses it to calculate age in yrs. We don't ask for birth date in the questionnaire, so set it to
    #exactly (age in yrs - 1 day or so) before the recording date (it gets recorded in years at the end anyway).
    yearPlaceholder = int(recDateTime[:4]) - age
    if int(recDateTime[8:10]) == 1: #If it's on the first of the month
        monthPlaceholder= int(recDateTime[5:7]) - 1
        dayPlaceholder = 28 #This will work e.g for rec on 01/03
    else:
        monthPlaceholder = int(recDateTime[5:7])
        dayPlaceholder = int(recDateTime[8:10])  - 1 #If recording takes place on the first, will need to change date formatting slightly..
    birthdatePlaceholder = [yearPlaceholder, monthPlaceholder, dayPlaceholder]
    additionalInfo = {"sex": sexInt, "Birthdate placeholder": birthdatePlaceholder, "hand" : handednessInt, "Recdate UTC form": recDateTime_UTCform}
    
    return additionalInfo