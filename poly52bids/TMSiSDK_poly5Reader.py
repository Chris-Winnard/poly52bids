'''
Copyright 2021 Twente Medical Systems international B.V., Oldenzaal The Netherlands

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

-#######  #     #   #####   #  ######      #     #
-   #     ##   ##  #        #  #     #     #     #
-   #     # # # #  #        #  #     #     #     #
-   #     #  #  #   #####   #  ######       #   #
-   #     #     #        #  #  #     #      #   #
-   #     #     #        #  #  #     #       # #
-   #     #     #  #####    #  ######   #     #     #

TMSiSDK: Poly5 File Reader

@version: 2021-06-07

Modified by Nhan Nguyen, Center for EarEEG. 2021-10-10
Later modified by Chris Winnard, AIM CDT. 2025-10-27

'''
import numpy as np
import struct
import datetime
import tkinter as tk
from tkinter import filedialog

class Poly5Reader: 
    def __init__(self, filename=None):
        if filename==None:
            root = tk.Tk()

            filename = filedialog.askopenfilename()
            root.withdraw()
            
        self.filename = filename
        print('Reading file ', filename)
        self._readFile(filename)
        
    def _readFile(self, filename):
        try:
            f = open(filename, "rb")
            try:    
                self._readHeader(f)
                self.channels=self._readSignalDescription(f)
                
                sample_buffer=np.zeros(self.num_channels*self.num_samples)
                for i in range(self.num_data_blocks):
                    print('\rProgress: % 0.1f %%' %(100*i/self.num_data_blocks), end="\r")
                    i_start=i*self.num_data_blocks+1;
                    i_end=min((i+1)*self.num_data_blocks, self.num_samples)
                    data_block=self._readSignalBlock(f, i_end - i_start + 1)
                    i1=i*self.num_samples_per_block*self.num_channels
                    i2=(i+1)*self.num_samples_per_block*self.num_channels
                    np.put(sample_buffer, range(i1, i2),data_block)
                   
                samples=np.transpose(np.reshape(sample_buffer, [self.num_samples_per_block*(i+1), self.num_channels]))
                self.samples=samples
                print('Done reading data.')
                f.close()
            except:
                print('Reading data failed.')
        except:
            print('Could not open file. ')
        
            
    def _readHeader(self, f):
        header_data=struct.unpack("=31sH81phhBHi4xHHHHHHHiHHH64x", f.read(217))
        self.magic_number=str(header_data[0])
        self.version_number=header_data[1]
        self.name = str(header_data[2])
        self.sample_rate=header_data[3]
        self.storage_rate=header_data[4]
        self.num_channels=header_data[6]//2
        self.num_samples=header_data[7]
        self.start_time=datetime.datetime(header_data[8], header_data[9], header_data[10], header_data[12], header_data[13], header_data[14])
        self.num_data_blocks=header_data[15]
        self.num_samples_per_block=header_data[16]
        self.size_data_block=header_data[17]
        self.compression_flag=header_data[18]
        if self.magic_number !="b'POLY SAMPLE FILEversion 2.03\\r\\n\\x1a'":
            print('This is not a Poly5 file.')
        elif  self.version_number != 203:
            print('Version number of file is invalid.')
        else:
            print('\t Number of samples:  %s ' %self.num_samples)
            print('\t Number of channels:  %s ' % self.num_channels)
            print('\t Sample rate: %s Hz' %self.sample_rate)
            
            
    def _readSignalDescription(self, f): 
        chan_list = []
        for ch in range(self.num_channels):
            ch = Channel()
            channel_description=struct.unpack("=41p4x11pffffHH60x", f.read(136))
            ch.name = channel_description[0][5:].decode('ascii')
            ch.unit_name = channel_description[1].decode('utf-8')
            ch.unit_low = channel_description[2]
            ch.unit_high = channel_description[3]
            ch.adc_low = channel_description[4]
            ch.adc_high = channel_description[5]
            ch.index = channel_description[6]
            ch.cache_offset = channel_description[7]
            chan_list.append(ch)
            f.read(136)
        return chan_list
        
            
    
    def _readSignalBlock(self, f, n):
        f.read(86)
        buffer_size=self.num_channels*self.num_samples_per_block
        sampleData=f.read(buffer_size*4)
        DataBlock=struct.unpack((str(buffer_size) + 'f'), sampleData)
        SignalBlock=np.asarray(DataBlock)
        return SignalBlock
        

class Channel:
    """ 'Channel' represents a device channel. It has the next properties:

        name : 'string' The name of the channel.

        unit_name : 'string' The name of the unit (e.g. 'μVolt)  of the sample-data of the channel.
                                                   
        unit_low
        
        unit_high
        
        adc_low
        
        adc_high
        
        index
        
        cache_offset
    """

    def __init__(self, name=None, unit_name=None, unit_low=None, unit_high=None, adc_low=None, adc_high=None, index=None, cache_offset=None):
        self.name = name
        self.unit_name = unit_name
        self.unit_low = unit_low
        self.unit_high = unit_high
        self.adc_low = adc_low
        self.adc_high = adc_high
        self.index = index
        self.cache_offset = cache_offset        
        
if __name__ == "__main__":

    data=Poly5Reader()
