from TMSiSDK_poly5Reader import *
from SerialTriggerDecoder import *

class EEGData:
    def __init__(self):
        self.name = None
        self.start_time = None
        self.sample_rate = None
        self.num_samples = 0
        self.samples = None        
        self.num_channels = 0
        self.channels = []
        self.raw_events = None

    def addChannel(self, name, unit_name, channel_type='EEG'):
        ch = Channel(name, unit_name, channel_type)
        self.channels.append(ch)
        
    def decode_events(self, triggerClk=8, thrError=-0.3, transError=0.1):
        self.trigger = (self.samples[35, :]==0).astype(int)
        decoder = SerialTriggerDecoder(self.trigger, self.sample_rate, triggerClk, thrError, transError)
        self.raw_events = decoder.decode()
        print('number of events: ', len(self.raw_events))
            
class Channel:
    """ 'Channel' represents a device channel. It has the next properties:

        name : 'string' The name of the channel.

        unit_name : 'string' The name of the unit (e.g. 'μVolt) of the sample-data of the channel.
                                                   
        ch_type
        
    """
    
    def __init__(self, name=None, unit_name=None, ch_type='EEG'):
        self.name = name
        self.unit_name = unit_name
        self.ch_type = ch_type

def poly52POPO(poly5_path, name=None): #Converts into a Plain Old Python Object
    eeg = EEGData()
    try:
        data = Poly5Reader(poly5_path)
    except:
        print('Error in reading poly5 file.')
        return None
    if name!=None:
        eeg.name = name
    else:
        eeg.name = data.name
    eeg.start_time = data.start_time
    eeg.sample_rate = data.sample_rate
    eeg.num_samples = data.num_samples
    eeg.samples = data.samples
    eeg.num_channels = data.num_channels
    for ch in data.channels:
        eeg.addChannel(ch.name, ch.unit_name)
    
    return eeg