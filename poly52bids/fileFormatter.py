import os
import pandas as pd
import json
import pathlib
from collections import OrderedDict

"""Three functions:
-One to format jsons.
-One to format all beh files.
-One to run the former two."""

def jsonFileFormatter(bidsPath):
    # Institution details to insert
    institution_info = {"InstitutionName": "Aarhus University",
                        "InstitutionAddress": "Nordre Ringgade 1, 8000 Aarhus C",
                        "InstitutionalDepartmentName": "Department of Electrical and Computer Engineering"}
    
    # Desired key order
    desired_order = ["TaskName",
                     "TaskDescription",
                     "Instructions",
                     "InstitutionName",
                     "InstitutionAddress",
                     "InstitutionalDepartmentName",
                     "SamplingFrequency",
                     "Manufacturer",
                     "ManufacturersModelName",
                     "CapManufacturer",
                     "CapManufacturersModelName",
                     "EEGChannelCount",
                     "EOGChannelCount",
                     "ECGChannelCount",
                     "EMGChannelCount",
                     "MiscChannelCount",
                     "TriggerChannelCount",
                     "PowerLineFrequency",
                     "EEGPlacementScheme",
                     "EEGReference",
                     "EEGGround",
                     "SoftwareFilters",
                     "HardwareFilters",
                     "RecordingDuration",
                     "RecordingType"]
    
    try:
        # Find all *_eeg.json files
        eeg_json_files = bidsPath.rglob("*_eeg.json")    
        
        for json_path in eeg_json_files:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        
            # Clean redundant keys (e.g., remove incorrect casing like 'MISCChannelCount')
            data.pop("MISCChannelCount", None)
        
            # Insert or update institution info
            data.update(institution_info)
        
            # Reorder according to desired key order
            ordered_data = OrderedDict()
            for key in desired_order:
                if key in data:
                    ordered_data[key] = data.pop(key)
            
            # Add any remaining keys at the end
            for key in sorted(data.keys()):
                ordered_data[key] = data[key]
        
            # Overwrite the original file
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(ordered_data, f, indent=4)
        
        print("\"json\" files have been formatted.")
    except Exception as e:
        print("Failed to format \"json\" files:", str(e))
        print("A common issue is permission errors. If using OneDrive or similar, we recommend pausing syncing.")

    
def behFileFormatter(bidsPath):
    try:
        # Find all *_beh.tsv files
        eeg_beh_files = bidsPath.rglob("*_beh.tsv")    
        
        for beh_path in eeg_beh_files:
            #Load the tsv file into a pandas dataframe
            df = pd.read_csv(beh_path, sep='\t')
            
            df.rename(columns={'stimuli_0': 'stimuli'}, inplace=True)
             
            if 'stimuli' in df.columns:
            #Remove everything up to and including 'Group' from each entry
                df['stimuli'] = df['stimuli'].str.replace(r'.*Group', 'Group', regex=True)
                
            #Find columns starting with 'block' and drop them
            columns_to_drop = [col for col in df.columns if col.startswith('block') or col.startswith('psychopyVersion') 
                               or col.startswith('date') or col.startswith('task') or col.startswith('expName') or
                               col.startswith('Participant ID') or col.startswith('trigger') or col.startswith('Unnamed')]
            
            if 'emotion' in str(beh_path): #Need to convert from path to str.
                columns_to_drop.extend([col for col in df.columns if col.startswith('music_attended')])
                
            df.drop(columns=columns_to_drop, inplace=True)
            
            #Save the modified dataframe back to a .tsv file
            df.to_csv(beh_path, sep='\t', index=False)
            
        print("\"beh\" files have been formatted.")
    except Exception as e:
        print("Failed to format \"beh\" files:", str(e))
        print("A common issue is permission errors. If using OneDrive or similar, we recommend pausing syncing.")
        
def fileFormatter(bidsPath):
    bidsPath = pathlib.Path(bidsPath) #Slightly more convenient for looping through directories.
    behFileFormatter(bidsPath)
    jsonFileFormatter(bidsPath)