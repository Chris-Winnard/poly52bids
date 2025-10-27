% Created by: Simon Lind Kappel - simon@lkappel.dk - February 2018
%The code for decoding poly5 files was inspired by "tms_read.m", provided by TMSi
%
% pop_loadpoly5() - Read poly5 files from TMSi
%
% Usage:
%   >> EEG = pop_loadpoly5;                                                 % an interactive uigetfile window
%   >> EEG = pop_loadpoly5( 'filename','filename.poly5', filepath, 'c:/');   % no pop-up window
%   >> EEG = pop_loadpoly5( PropertyName, PropertyValue);
%
% Optional properties:
%   filename:               Filename of the *.poly5 file
%   filepath:               File path of the *-poly5 file
%   ref_ch:                 The reference channel or channels. '[]' = no referencing
%
%   >> Discarding <<
%   NaNdiscSamples:         true: Set discarded samples to NaN | false: The value of discarded samples are not changed, unless the channel is discarded.
%   NaNdiscChannels:        true: Set all samples of discarded channels to NaN | false: Discarded channels are removed from the EEG struct.
%   ChannelsDiscThd:        Channels will be discarded if more than 'ChannelsDiscThd' percent of the samples in a channel is marked for discarding
%                           To disable, set 'ChannelsDiscThd' = 1;
%
%   EnableSaturationDisc:   true: Discard channels or samples
%   SaturationValue:        The saturation value
%
%   EnableSameValueDisc:    true: Enable discarding based on the number of samples with the same value.
%   SameValueThd:           Discard all samples with the most common sample value, if more than 'SameValueThd' percent of the samples in a channel have the same value
%   
%   >> Channel labels <<
%   If all channel label are "EXGxx" the following properties will be used:
%   > ChannelLabels:        Cell array with channel names, which will be used instead of the names in the *.poly5 file. [type=cell array of strings]
%   > ChLabelsFromStimMng:  Load channel names from a *.mat file created using StimulusManager. [type=logic]
%
% Outputs:
%   EEG:                    EEGLAB data structure
%   signal:                 TMSi data struct
%
% Example: (set all saturated samples to NaN)
%   pop_loadpoly5('ref_ch',[],'NaNdiscSamples',true,'ChannelsDiscThd',1,'EnableSaturationDisc',true,'EnableSameValueDisc',false)


% version history:
% 5.2: added trigger extraction
function [EEG, command, signal] = pop_loadpoly5_2(varargin)

%% Settings
ref_ch = [];               
NaNdiscSamples = false;      
NaNdiscChannels = true; 
ChannelsDiscThd = 0.5;

EnableSaturationDisc = true;
SaturationValue = -52420076;    % TMSi Mobita saturation value

EnableSameValueDisc = false;
SameValueThd = 0.5;

ChLabelsFromStimMng = true;

% Trigger extraction settings
nEventSum = 10;             % Minimum samples below the threshold before a trigger i registered [unit=seconds]
EventDeadTime = 20*1e-3;    % Time before a new trigger can be registered. [unit=seconds]

%% Allocate memory
command = '';
EEG = [];
ChannelLabels_in = '';

%% Create input argument structure
if ~isempty(varargin)
    try
        Properties = struct(varargin{:});
    catch
        disp('Setevent: wrong syntax in function arguments');
        return;
    end
else
    Properties = struct();
end

%% History
if ~isempty(which('vararg2str'))
    command = sprintf('[EEG, command] = pop_loadpoly5(%s);', vararg2str(varargin));
end

%% Create new EEG struct
if ~isempty(which('eeg_emptyset'))
    EEG = eeg_emptyset;
else
    eeglab
    EEG = eeg_emptyset;
end


%% test the presence of variables
if isfield(Properties, 'filepath')
    EEG.filepath = Properties(1).filepath;
else
    EEG.filepath = pwd;
end

if ~isfield(Properties, 'filename')
    [EEG.filename, EEG.filepath, FilterIndex] = uigetfile({'*.poly5','*.poly5 (TMSi polybench)'},'Select a recording from a TMSi amplifier',EEG.filepath);
    if FilterIndex < 1, return, end
else
    EEG.filename = Properties(1).filename;
end

if (~strcmp(EEG.filename(end-5:end),'.Poly5'))
    EEG.filename = strcat(EEG.filename,'.Poly5');
end

Filename = fullfile(EEG.filepath,EEG.filename);

%% handle input arguments
tmpfields = [];
if ~isempty(Properties)
    tmpfields = fieldnames(Properties);
end

for curfield = tmpfields'
    FieldData = getfield(Properties, {1}, curfield{1});    
    
    switch lower(curfield{1})
        
        case 'filename' % do nothing now
            
        case 'filepath' % do nothing now
            
        case 'ref_ch'
            ref_ch = {Properties.(curfield{1})};            
         
        case lower('NaNdiscSamples')
            if FieldData ~= false && FieldData ~= true
                warning('The ''NaNdiscSamples'' property must be ''false'' or ''true''')
            else
                NaNdiscSamples = FieldData;
            end            
            
        case lower('NaNdiscChannels')
            if FieldData ~= false && FieldData ~= true
                warning('The ''NaNdiscChannels'' property must be ''false'' or ''true''')
            else
                NaNdiscChannels = FieldData;
            end
            
        case lower('ChannelsDiscThd')
            if isnumeric(FieldData) && length(FieldData) ~= 1
                warning('The ''ChannelsDiscThd'' property must be a mumeric value')
            else
                ChannelsDiscThd = FieldData;
            end 
            
        case lower('EnableSaturationDisc')
            if FieldData ~= false && FieldData ~= true
                warning('The ''EnableSaturationDisc'' property must be ''false'' or ''true''')
            else
                EnableSaturationDisc = FieldData;
            end
            
        case lower('SaturationValue')
            if isnumeric(FieldData) || length(FieldData) ~= 1
                warning('The ''SaturationValue'' property must be a mumeric value')
            else
                SaturationValue = FieldData;
            end  
            
        case lower('EnableSameValueDisc')
            if FieldData ~= false && FieldData ~= true
                warning('The ''EnableSameValueDisc'' property must be ''false'' or ''true''')
            else
                EnableSameValueDisc = FieldData;
            end
            
        case lower('SameValueThd')
            if isnumeric(FieldData) || length(FieldData) ~= 1
                warning('The ''SameValueThd'' property must be a mumeric value')
            else
                SameValueThd = FieldData;
            end             
        
        case {lower('SameValueDiscLim')} % Property for compatibiliy with earlier versions of the script
            EnableSameValueDisc = true;
            SameValueThd = Properties.(curfield{1});            
            
        case {lower('ChannelLabels')}
                ChannelLabels_in = {Properties.(curfield{1})};
                ChannelLabels_in = strtrim(ChannelLabels_in);
            
        otherwise, error(['pop_editset() error: unrecognized field ''' curfield{1} '''']);
    end
end

%% Read the Poly5 file and extract the EEG data and other options
try
fid=fopen(Filename);
if fid==-1
    error([Filename ' not found']);
end
catch e
    e
    error(['Loading error when handling ' Filename])
end

% Signal header
%determine signal file version
pos = 31;
fseek(fid,pos,-1);
version = fread(fid,1,'int16');
if version == 203
    frewind(fid);
    signal.header.FID                   = fread(fid,31,'uchar');
    signal.header.VersionNumber         = fread(fid, 1,'int16');
else % version 204
    frewind(fid);
    signal.header.FID                   = fread(fid,32,'uchar');
    signal.header.VersionNumber         = fread(fid, 1,'int16');
end
signal.header.MeasurementName       = fread(fid,81,'uchar');
signal.header.FS                    = fread(fid, 1,'int16');
signal.header.StorageRate           = fread(fid, 1,'int16');
signal.header.StorageType           = fread(fid, 1,'uchar');
signal.header.NumberOfSignals       = fread(fid, 1,'int16');
signal.header.NumberOfSamplePeriods = fread(fid, 1,'int32');
signal.header.EMPTYBYTES            = fread(fid, 4,'uchar');
signal.header.StartMeasurement      = fread(fid,14,'uchar');
signal.header.NumberSampleBlocks    = fread(fid, 1,'int32');
signal.header.SamplePeriodsPerBlock = fread(fid, 1,'uint16');
signal.header.SizeSignalDataBlock   = fread(fid, 1,'uint16');
signal.header.DeltaCompressionFlag  = fread(fid, 1,'int16');
signal.header.TrailingZeros         = fread(fid,64,'uchar');

%conversion to char of text values
signal.header.FID               = char(signal.header.FID);
signal.header.MeasurementName   = char(signal.header.MeasurementName(2:signal.header.MeasurementName(1)+1));
signal.fs = signal.header.FS;

%check for right fileversion
if signal.header.VersionNumber ~= 203
   error('Wrong file version! Imput file must be a Poly5/TMS version 2.03 file!');
   return;
end

% Signal description
for idx=1:signal.header.NumberOfSignals
    signal.description(idx).SignalName        = fread(fid,41,'uchar');
    signal.description(idx).Reserved          = fread(fid, 4,'uchar');
    signal.description(idx).UnitName          = fread(fid,11,'uchar');
    signal.description(idx).UnitLow           = fread(fid, 1,'float32');
    signal.description(idx).UnitHigh          = fread(fid, 1,'float32');
    signal.description(idx).ADCLow            = fread(fid, 1,'float32');
    signal.description(idx).ADCHigh           = fread(fid, 1,'float32');
    signal.description(idx).IndexSignalList   = fread(fid, 1,'int16');
    signal.description(idx).CacheOffset       = fread(fid, 1,'int16');
    signal.description(idx).Reserved2         = fread(fid,60,'uchar');
    
    % conversion of char values (to right format)
    signal.description(idx).SignalName = char(signal.description(idx).SignalName(2:signal.description(idx).SignalName(1)+1));
    signal.description(idx).UnitName   = char(signal.description(idx).UnitName(2:signal.description(idx).UnitName(1)+1));
end  %for

%read data blocks
NB = signal.header.NumberSampleBlocks;
SD = signal.header.SizeSignalDataBlock;
NS = signal.header.NumberOfSignals;
NS_32bit = NS/2;

%reserve memory
%signal.data = zeros(NS_32bit,SD*NB/(NS_32bit*4));

%h = waitbar(0,'Reading measurement data ...');

for idx=1:NB
    
    %jump to right position in file
    if signal.header.VersionNumber == 203
        pos = 217 + NS*136 + (idx-1) *(86+SD);
    else
        pos = 218 + NS*136 + (idx-1) *(86+SD);
    end
    fseek(fid,pos,-1);
    
    signal.block(idx).PI = fread(fid,1,'int32'); %period index
    fread(fid,4,'uchar'); %reserved for extension of previous field to 8 bytes
    signal.block(idx).BT = fread(fid,14/2,'int16'); %dostime
    fread(fid,64,'uchar'); %reserved
    data = single(fread(fid,SD/4,'float32'));
    
    % Convert data to 32bit values.
    % In case also 16bit values have to be measured, these values are
    % typecasted below:
    %data = fread(fid,SD/2,'int16'); %read data
    %data = int16(data);
    %data = typecast(data,'int32');
    %signal.block(idx).DATA = data;
    signal.data{idx} = reshape(data,NS_32bit,SD/(NS_32bit*4));
  %  waitbar(idx/NB,h)
end %for
%close(h); %close waitbar
fclose(fid);

%disp('Converting data to a usable format ...');
signal.data = cell2mat(signal.data);
signal.data = cast(signal.data, 'double');
%    signal.data = cell(NS_32bit,1);
signal.data = mat2cell(signal.data,ones(NS_32bit,1),size(signal.data,2));

for idx = 1:NS_32bit  % represent data in [uV]
    signal.data{idx} = (signal.data{idx} - signal.description(idx*2).ADCLow)./(signal.description(idx*2).ADCHigh - signal.description(idx*2).ADCLow)  .* (signal.description(idx*2).UnitHigh - signal.description(idx*2).UnitLow) + signal.description(idx*2).UnitLow ; %correction for uV
end
%signal.data = reshape(signal.data,NS_32bit,SD*NB);

% datum = signal.block(1,1).BT;
% signal.measurementdate = [num2str(datum(3),'%02.0f') '-' num2str(datum(2),'%02.0f') '-' num2str(datum(1),'%02.0f')];
% signal.measurementtime = [num2str(datum(5),'%02.0f') ':' num2str(datum(6),'%02.0f') ':' num2str(datum(7),'%02.0f')];
% 
% ts = size(signal.data{1},2)/signal.fs;
% th = floor(ts / 3600);
% tm = floor(ts/60 - th*60);
% tss = floor(ts - th*3600 - tm * 60);
% signal.measurementduration = [num2str(th,'%02.0f') ':' num2str(tm,'%02.0f') ':' num2str(tss,'%02.0f')];

signal.data = remove_not_measured_chan(signal.data);

%% Extract channellabels and units
ChannelLabels = {signal.description(1:2:length(signal.description)).SignalName};
ChannelLabels = cellfun(@(x) x(6:end)',ChannelLabels,'UniformOutput',false);
ChannelLabels = strtrim(ChannelLabels);

Unit = cell(1,length(ChannelLabels));
for iCh = 1:2:length(signal.description)
    Unit{(iCh+1)/2} = [signal.description(iCh).UnitName]';
end
mEEGch = cellfun(@(x) ~isempty(strfind(lower(x), 'uv')), Unit);

%% Extract Accelerometer data
iAccX = find(cellfun(@(strCh) strCh(1:min(1,end)) == 'X', ChannelLabels) == 1);
iAccY = find(cellfun(@(strCh) strCh(1:min(1,end)) == 'Y', ChannelLabels) == 1);
iAccZ = find(cellfun(@(strCh) strCh(1:min(1,end)) == 'Z', ChannelLabels) == 1);

% Extract Accelerometer data if the selected channels are not EEG channels
if all(~isempty([iAccX iAccY iAccZ])) && all(mEEGch([iAccX iAccY iAccZ]) == 0)
    EEG.etc.acc.data = cat(1,signal.data{[iAccX iAccY iAccZ]});
    EEG.etc.acc.labels = {'accX', 'accY', 'accZ'};
    EEG.etc.acc.description = 'Mobita Accelerometer data';
end

%% Extract Trigger Channel
iTrig = find(strcmp(ChannelLabels,'Dig'));

% Extract Accelerometer data if the selected channels are not EEG channels
if all(~isempty(iTrig)) && all(mEEGch(iTrig) == 0)
    EEG.etc.trigger.data = cat(1,signal.data{iTrig});
    EEG.etc.acc.labels = {'trigger'};
    EEG.etc.acc.description = 'Trigger channel';
end


%% Extract EEG data
%mEEGch = cellfun(@(x) ~isempty(strfind(lower(x), 'exg')), ChannelLabels);
ChannelLabels = ChannelLabels(mEEGch);

EEG.data = single(cat(1,signal.data{mEEGch}));
EEG.srate = signal.fs;
[EEG.nbchan, EEG.pnts] = size(EEG.data);

%% Discarding of samples and channels
mChAccept = true(1, EEG.nbchan);
mSamplesDisc = false(EEG.nbchan, EEG.pnts);

% Examine if SameValueDiscLim percent of the samples have the same value, if this is the case - discard the the channel.
if EnableSameValueDisc && SameValueThd < 1
    procSameValue = zeros(1, EEG.nbchan);
    maxSameValue = zeros(1, EEG.nbchan);
    for iCh = 1:EEG.nbchan
        valuesUnique = sort(unique(EEG.data(iCh,:)),'ascend');
        nValueBin = histcounts(EEG.data(iCh,:), [valuesUnique valuesUnique(end)+1]);
        [procSameValue(iCh), iMax] = max(nValueBin / EEG.pnts);
        maxSameValue(iCh) = valuesUnique(iMax);
        
        % Channel discarding
        if procSameValue(iCh) > ChannelsDiscThd
            mChAccept(iCh) = false;
        end
        
        % Sample discarding
        mSamplesDisc(iCh, EEG.data(iCh,:) == maxSameValue(iCh)) = true;
    end
end

% Locate saturated samples
if EnableSaturationDisc && isempty(SaturationValue) == false
    procSaturated = zeros(1, EEG.nbchan);
    for iCh = 1:EEG.nbchan
        
        % Channel discarding
        procSaturated(iCh) = sum(EEG.data(iCh,:) == SaturationValue) / EEG.pnts;
        if procSaturated(iCh) > ChannelsDiscThd
            mChAccept(iCh) = false;
        end        
        
        % Sample discarding
        mSamplesDisc(iCh, EEG.data(iCh,:) == SaturationValue) = true;
    end
end

% Discard samples
if NaNdiscSamples
    EEG.data(mSamplesDisc) = NaN;
end

iChAccept = find(mChAccept == 1);  

%% Extract the trigger data from the Poly5 file and create the event struct for EEGlab

iTrigCh = [];
for iCh = 1:length(signal.data)
    tmp = signal.data{iCh};
    if ~isempty(tmp) && length(tmp) == length(tmp(tmp == 8 | tmp == 0))
        iTrigCh = [iTrigCh iCh];
    end
end

if length(iTrigCh) == 1    
    nEventDeadTime = EventDeadTime * EEG.srate;
    
    TrigData = signal.data{iTrigCh};
    
    iEvent = 1;
    iLastEventEnd = -nEventDeadTime;
    TrigEndLocated = false;
    for iData = 2 : EEG.pnts-nEventSum
        if TrigData(iData-1) == 8 &&  TrigData(iData) == 0 && ...      % Detect rising edge
                sum( TrigData( (1:nEventSum)+iData ) == 0 ) == nEventSum && ...    % Ensure that the trig i stable and not just an artifact
                iLastEventEnd + nEventDeadTime < iData                                % Ensure that trigger jitter does not count as a trig
            
            EEG.event(iEvent).type = 'trigger';
            EEG.event(iEvent).position = 1;
            EEG.event(iEvent).latency = iData;
            EEG.event(iEvent).urevent = iEvent;
            TrigEndLocated = false;
            iLastEventEnd = iData;
            
            iEvent = iEvent + 1;            
        end
        
        % Find falling edge (restricted to not be closer to rising edge than 
        if TrigData(iData) == 8 && TrigEndLocated == false && iLastEventEnd+nEventDeadTime/4 < iData
            iLastEventEnd = iData;
            TrigEndLocated = true;
        end
    end
    
    %remove the last event if it is closer than 1 seconds from the end of the data
    if numel(EEG.event)>0 && (EEG.event(end).latency + EEG.srate > EEG.pnts)
        warning('Removing last event at time %0.1fs', EEG.event(end).latency/EEG.srate)
        EEG.event(end) = [];
    end
        
    display('Trigger channel located, including sample cnt. of rise time in the ''EEG.event'' struct');
elseif length(iTrigCh) > 1
    display('More then one trigger channel located - The trigger data will not be used!')
else
    display('No trigger data or channel located')
end

if ~any(ismember(lower(tmpfields),'ref_ch'))
    res = inputgui( 'geometry', 2, ...
        'geomvert', 1, 'uilist', { ...
        { 'style', 'text', 'string', 'Reference channel:' }, ...
        { 'style', 'edit', 'string', num2str(ref_ch)}});
    if ~isempty(res{1})
        ref_ch = res{1};
        if ~iscell(ref_ch)
            ref_ch = {ref_ch};
        end
    end
end

%% Go through the channel label and determine if all are 'EXGxx', if so try to use channel names from the given property.
if sum(cellfun(@(x) isempty(strfind(lower(x), 'exg')), ChannelLabels)) == 0    
    strStimMngFile = [EEG.filename(1:end-5) 'mat'];
    
    if isempty(ChannelLabels_in) == false && length(ChannelLabels_in) == length(ChannelLabels)
        ChannelLabels = ChannelLabels_in;
    elseif isempty(ChannelLabels_in) == false && sum(mChAccept) == length(ChannelLabels)    
        ChannelLabels(mChAccept) = ChannelLabels_in;
        
    % If "ChLabelsFromMat" is true, try to load channelnames a *.mat files created by stimulusmanager.        
    elseif ChLabelsFromStimMng && exist(fullfile(EEG.filepath, strStimMngFile), 'file')
        tmp = load(fullfile(EEG.filepath, strStimMngFile));
        try
            ChannelLabels = tmp.Settings.TMSi.ChLabels;
            display(sprintf('Channel labels were loaded from the stimulus manager file: ''%s''',strStimMngFile))
        catch
           warning('The file: ''%s'' did not contain a channel label in the struct field ''Settings.TMSi.ChLabels''.', strStimMngFile); 
        end
        clear tmp;
    end
end

% Create chanlocs struct
EEG.chanlocs = struct('labels', cellstr(ChannelLabels));

%% Rereference data
if ~isempty(ref_ch) && length(ref_ch) == 1
    % Find the ref channel in the ChannelNames cell array
    if iscell(ref_ch)
        strRefCh = ref_ch{1};
    else
        strRefCh = ref_ch;
    end
    
    if isempty(strRefCh)
        display('An empty reference string was given - the returned data has not been rereferenced.')
    else
        iRefCh = str2double(strRefCh);
        if isnan(iRefCh) % The input was a string
            iRefCh = find(cellfun(@(x) strcmpi(x,strRefCh), {EEG.chanlocs.labels}) == 1);
        elseif iRefCh < 1 || iRefCh > size(EEG.data,1) % The index is not within the boundaries of the channels
            iRefCh = [];
        end
        
        if ~isempty(iRefCh)
            if mChAccept(iRefCh) == 0
                warning(sprintf('The given reference channel (%s - Ch%i) were not accepted - returning data array only containing NaN values',EEG.chanlocs(iRefCh).labels,iRefCh))
                EEG.data(:) = NaN;
            else
                for n = 1:length(EEG.chanlocs)
                    EEG.chanlocs(n).ref = EEG.chanlocs(iRefCh).labels;
                end
                EEG.ref = EEG.chanlocs(iRefCh).labels;
                
                %Rereference the data
                EEG.data = EEG.data - repmat(EEG.data(iRefCh,:), size(EEG.data,1),1);
                display(sprintf('Data have been rereferenced to %s (Ch%i)',EEG.chanlocs(iRefCh).labels,iRefCh));
            end
        else
            error('The reference channel was not located in the channel names array - you must specify a valid reference channel!')
        end
    end
else
    warning('The ref_ch was not formatted correctly, data has not been referenced. The ref channel must be a channel number or name')
end

%% Asign fields to the EEG struct
EEG.nbchan          = size(EEG.data,1);
EEG.trials          = 1;
EEG.xmin            = 0;
EEG.xmax            = EEG.xmin + (EEG.pnts-1)/EEG.srate;
EEG.setname 		= EEG.filename(1:end-6);

if ~isempty(which('eeg_checkset'))
    EEG = eeg_checkset(EEG);
end

% Write load report
disp(' ');
disp('------------------------- File information -------------------------');
fprintf('\tFile name                : %s\n',EEG.filename);
fprintf('\tSample frequency         : %4.0f Hz\n',signal.header.FS);
fprintf('\tAccepted channels        : ');
for iCh = iChAccept
    fprintf('%s',ChannelLabels{iCh}, sum(isnan(EEG.data(iCh,:)))/EEG.pnts*100)
    
    % Write the percent of samples set to NaN (discarded)
    if NaNdiscSamples
        fprintf('(NaNsamp=%0.2f%%)',sum(isnan(EEG.data(iCh,:)))/EEG.pnts*100);
    end
    fprintf(', ');
end
fprintf('\n')
fprintf('\tDiscarded channels       : ');

iDiscard = find(mChAccept == 0);
for iCh = iDiscard
    fprintf('%s (',ChannelLabels{iCh})
    
    % Write the percent of samples set to NaN (discarded)
    if NaNdiscSamples
        fprintf('NaNsamp=%0.2f%%',sum(isnan(EEG.data(iCh,:)))/EEG.pnts*100);
    end    
    
    % Write the percent of saturated samples
    if EnableSaturationDisc
        fprintf(', sat=%0.2f%%', procSaturated(iCh)*100);
    end
    
    % Write the percent of samples with the same value
    if EnableSameValueDisc
        fprintf(', sameVal=%0.2f%%', procSameValue(iCh)*100);
    end
    fprintf(')');
end
fprintf('\n')
disp('--------------------------------------------------------------------');
%    fprintf('Measurement duration: %
disp(' ');

%% Remove discarded (not accepted) channels
if NaNdiscChannels
    EEG.data(~mChAccept,:) = NaN;
else
    EEG.data = EEG.data(mChAccept,:);
    EEG.chanlocs = EEG.chanlocs(mChAccept);
end

end
%% Remove not measured channels
function [sig] = remove_not_measured_chan(data)


sig = cell(size(data));
% convert to cell structure
for g = 1:size(data,1)
    tmpdata = data{g};
    gem = mean(tmpdata);
    afw = std(tmpdata);
    if gem == 0 && afw == 0
        sig{g} = []; % remove zeros (nothing is measured anyway);
    else
        sig{g} = double(tmpdata);
        %fprintf('%2.0f ', g );
    end %if
end %for
%fprintf('\n');
end %function