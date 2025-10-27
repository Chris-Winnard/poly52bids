%Because of how matlab.engine() works with functions, it was considered easiest to set this up as one very complex function. The alternative 
%options were: to have a class with several functions, which requires extra code setting up MATLAB paths in Python files (only a couple
%of lines, but repeated for each function call); or to have more functions with a separate .m file for each. The one complex function approach
%was considered the lesser of three evils.


function poly52set(basePath, participantNumber, recordingProperty, rec1, rec2)

%recordingProperty values:
%"baseline"
% "noCeegrid"
% "cER10switched", for later sessions where a ceegrid electrode had broken and was switched with a spare in the setup
% "invertedCeegrid", for sessions where the ceegrid arrays had been accidentally swapped and inverted.
% "splitRecs": for one participant where recording was stopped and restarted (meaning two scalp files, two ceegrid files).

%rec1 and rec2 are specifically for splitRecs (since splitRecs corresponds to a single participant we could use the splitRecs workflow and set
%rec1, rec2 for that participant, just included these for completeness/generalisability).
         
    %Arguments are input as chars, need to convert to strings:
    basePath = convertCharsToStrings(basePath);
    participantNumber = convertCharsToStrings(participantNumber);
    recordingProperty = convertCharsToStrings(recordingProperty);

    if recordingProperty ~= "splitRecs"    
        rawDataPath = basePath + '/sourcedata/P' + participantNumber + '/';
    
        fileName = 'P' + participantNumber + '_scalp';
        fileNamePath_full = rawDataPath + fileName + '.Poly5';
        fileNamePath_full = convertStringsToChars(fileNamePath_full);
    
        ChannelLabels = {'Fp1', 'Fpz', 'Fp2', 'F7', 'F3', 'Fz', 'F4', 'F8', 'FC5', 'FC1', 'FC2', 'FC6', 'M1', 'T7',...
        'C3', 'Cz', 'C4', 'T8', 'M2', 'CP5', 'CP1', 'CP2', 'CP6', 'P7', 'P3', 'Pz', 'P4', 'P8', 'POz', 'O1', 'Oz', 'O2'};
        
        EEG_scalp = pop_loadpoly5_2('filepath','','filename',fileNamePath_full,'ref_ch',[1:32],'NaNdiscSamples',true,'ChannelsDiscThd',1,'EnableSaturationDisc',true,'EnableSameValueDisc',false,'ChannelLabels',ChannelLabels);
        %Need to set to average reference. This is without irrelevant chans (and discarded chans not included), and also more accurate than the average referencing done within the Mobita.
    
        EEG_scalp=pop_select(EEG_scalp,'channel',1:32);
        
        %save as EEGLAB struct (useful for Python work):
        setFilePath = char(basePath + 'EEG Set Files (Unprocessed)\');
        outputFileName= char('P' + participantNumber + '_scalp.set');
        pop_saveset(EEG_scalp, outputFileName, setFilePath);
    
    
        %cEEGrid- something very similar to the scalp analysis, but accounting for different properties for different
        %participants:
        if recordingProperty == "noCeegrid" %For some participants there is no ceegrid, so skip
            return
        else
            fileName = 'P' + participantNumber + '_ceegrid';
            fileNamePath_full = rawDataPath + fileName + '.Poly5';
            fileNamePath_full = convertStringsToChars(fileNamePath_full);
    
            if recordingProperty == "baseline"
                %ceegrid - Fpz is reference:
                ChannelLabels = {'cEL1', 'cEL2', 'cEL3', 'cEL4', 'cEL5', 'cEL6', 'cEL7', 'cEL8','cEL9','cEL10','Fpz', '', '', '', '', '', ...
                                 'cER1', 'cER2', 'cER3', 'cER4', 'cER5', 'cER6', 'cER7', 'cER8', 'cER9', 'cER10', '','','','','',''};
            
            
                EEG_ceegrid = pop_loadpoly5_2('filepath','','filename',fileNamePath_full,'ref_ch',[1:11, 17:26],'NaNdiscSamples',true,'ChannelsDiscThd',1,'EnableSaturationDisc',true,'EnableSameValueDisc',false,'ChannelLabels',ChannelLabels);             
                EEG_ceegrid = pop_select(EEG_ceegrid,'channel',[1:11, 17:26]); %Remove empty channels
    
            elseif recordingProperty == "cER10switched"
                    ChannelLabels = {'cEL1', 'cEL2', 'cEL3', 'cEL4', 'cEL5', 'cEL6', 'cEL7', 'cEL8','cEL9','cEL10','Fpz', '', '', '', '', '', ...
                                     'cER1', 'cER2', 'cER3', 'cER4', 'cER5', 'cER6', 'cER7', 'cER8', 'cER9', '', '','','','','','cER10'};
    
    
                    EEG_ceegrid = pop_loadpoly5_2('filepath','','filename',fileNamePath_full,'ref_ch',[1:11, 17:25, 32],'NaNdiscSamples',true,'ChannelsDiscThd',1,'EnableSaturationDisc',true,'EnableSameValueDisc',false,'ChannelLabels',ChannelLabels);
                    EEG_ceegrid = pop_select(EEG_ceegrid,'channel',[1:11, 17:25, 32]); %Remove empty channels
    
            elseif recordingProperty == "invertedCeegrid"
                    % Use correct (standard) channel labels, ignoring the inversion for now
                    ChannelLabels = {'cEL1', 'cEL2', 'cEL3', 'cEL4', 'cEL5', 'cEL6', 'cEL7', 'cEL8','cEL9','cEL10','Fpz', '', '', '', '', '', ...
                                     'cER1', 'cER2', 'cER3', 'cER4', 'cER5', 'cER6', 'cER7', 'cER8', 'cER9', 'cER10', '', '', '', '', '', ''};
                
                    % Load data
                    EEG_ceegrid = pop_loadpoly5_2('filepath','','filename',fileNamePath_full, ...
                        'ref_ch',[1:11, 17:26], 'NaNdiscSamples', true, 'ChannelsDiscThd', 1, ...
                        'EnableSaturationDisc', true, 'EnableSameValueDisc', false, ...
                        'ChannelLabels', ChannelLabels);
                
                    left_idx  = 1:10;         % cEL1 – cEL10
                    right_idx = 17:26;        % cER1 – cER10
                    
                    % Reverse ears, while also reversing indices. Overall, flipping top-bottom and left-right
                    EEG_ceegrid.data([left_idx right_idx], :, :) = ...
                    EEG_ceegrid.data([fliplr(right_idx) fliplr(left_idx)], :, :);
                
                    % === Select only active cEEGrid channels ===
                    EEG_ceegrid = pop_select(EEG_ceegrid, 'channel', [1:11, 17:26]); %Remove empty channels
            
               
            %save as EEGLAB struct (useful for Python work):
            outputFileName= char('P' + participantNumber + '_ceegrid.set');
            pop_saveset(EEG_ceegrid, outputFileName, setFilePath);


    else %if recordingProperty == splitRecs
        rec1 = convertCharsToStrings(rec1);
        rec2 = convertCharsToStrings(rec2);
    
        rawDataPath = basePath + '/sourcedata/P' + participantNumber + '/';
        
        %Scalp:
    
        %First recording:
        fileName_rec1 = 'P' + participantNumber + '_' + rec1 +  '_scalp';
        fileNamePath_full = rawDataPath + fileName_rec1 + '.Poly5';
        fileNamePath_full = convertStringsToChars(fileNamePath_full);
    
        ChannelLabels = {'Fp1', 'Fpz', 'Fp2', 'F7', 'F3', 'Fz', 'F4', 'F8', 'FC5', 'FC1', 'FC2', 'FC6', 'M1', 'T7',...
        'C3', 'Cz', 'C4', 'T8', 'M2', 'CP5', 'CP1', 'CP2', 'CP6', 'P7', 'P3', 'Pz', 'P4', 'P8', 'POz', 'O1', 'Oz', 'O2'}; 

        EEG_scalp_rec1 = pop_loadpoly5_2('filepath','','filename',fileNamePath_full,'ref_ch',[1:32],'NaNdiscSamples',true,'ChannelsDiscThd',1,'EnableSaturationDisc',true,'EnableSameValueDisc',false,'ChannelLabels',ChannelLabels);
        %Need to set to average reference. This is without irrelevant chans (and discarded chans not included), and also more accurate than the average referencing done within the Mobita.
        
        EEG_scalp_rec1 = pop_select(EEG_scalp_rec1,'channel',1:32);
    
        %Second recording:
        fileName_rec2 = 'P' + participantNumber + '_' + rec2 +  '_scalp';
        fileNamePath_full = rawDataPath + fileName_rec2 + '.Poly5';
        fileNamePath_full = convertStringsToChars(fileNamePath_full);
    
        EEG_scalp_rec2 = pop_loadpoly5_2('filepath','','filename',fileNamePath_full,'ref_ch',[1:32],'NaNdiscSamples',true,'ChannelsDiscThd',1,'EnableSaturationDisc',true,'EnableSameValueDisc',false,'ChannelLabels',ChannelLabels);
        EEG_scalp_rec2 = pop_select(EEG_scalp_rec2,'channel',1:32);
    
        %Merge the two together, and then save:
        EEG_merged_scalp = pop_mergeset(EEG_scalp_rec1, EEG_scalp_rec2);
    
        setFilePath = char(basePath + 'EEG Set Files (Unprocessed)\');
        outputFileName = char('P' + participantNumber + '_scalp.set');
        pop_saveset(EEG_merged_scalp, outputFileName, setFilePath);
           
        %Now something very similar for the ceegrid data:
        fileName_rec1 = 'P' + participantNumber + '_' + rec1 +  '_ceegrid';
        fileNamePath_full = rawDataPath + fileName_rec1 + '.Poly5';
        fileNamePath_full = convertStringsToChars(fileNamePath_full);
    
        %Fpz is reference:
        ChannelLabels = {'cEL1', 'cEL2', 'cEL3', 'cEL4', 'cEL5', 'cEL6', 'cEL7', 'cEL8','cEL9','cEL10','Fpz', '', '', '', '', '', ...
                         'cER1', 'cER2', 'cER3', 'cER4', 'cER5', 'cER6', 'cER7', 'cER8', 'cER9', 'cER10', '','','','','',''};
        
        EEG_ceegrid_rec1 = pop_loadpoly5_2('filepath','','filename',fileNamePath_full,'ref_ch',[1:11, 17:26],'NaNdiscSamples',true,'ChannelsDiscThd',1,'EnableSaturationDisc',true,'EnableSameValueDisc',false,'ChannelLabels',ChannelLabels);
        EEG_ceegrid_rec1 = pop_select(EEG_ceegrid_rec1,'channel',[1:11, 17:26]);
        
        %Second recording:
        fileName_rec2 = 'P' + participantNumber + '_' + rec2 +  '_ceegrid';
        fileNamePath_full = rawDataPath + fileName_rec2 + '.Poly5';
        fileNamePath_full = convertStringsToChars(fileNamePath_full);
    
        EEG_ceegrid_rec2 = pop_loadpoly5_2('filepath','','filename',fileNamePath_full,'ref_ch',[1:11, 17:26],'NaNdiscSamples',true,'ChannelsDiscThd',1,'EnableSaturationDisc',true,'EnableSameValueDisc',false,'ChannelLabels',ChannelLabels);
        EEG_ceegrid_rec2 = pop_select(EEG_ceegrid_rec2,'channel',[1:11, 17:26]);
    
        %Merge the two together, and then save:
        EEG_merged_ceegrid = pop_mergeset(EEG_ceegrid_rec1, EEG_ceegrid_rec2);
    
        setFilePath = char(basePath + 'EEG Set Files (Unprocessed)\');
        outputFileName= char('P' + participantNumber + '_ceegrid.set');
        pop_saveset(EEG_merged_ceegrid, outputFileName, setFilePath);
        end
    end
end