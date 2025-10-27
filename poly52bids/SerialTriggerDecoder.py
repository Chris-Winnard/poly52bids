import matplotlib as plt
import os
import numpy as np

class SerialTriggerDecoder:
    """
    Serial Trigger decoder for EEG recordings

    ...
    Attributes
    ----------


    Methods
    -------
    """
    
    MAX_TRIG_DISTANCE = 1.5 #second
    
    def __init__(self, trigger, fsEEG, clkSerial, thrError, transError, max_trig_distance=MAX_TRIG_DISTANCE):
        self.__fsEEG = fsEEG
        self.__clkSerial = clkSerial
        self.__trigger = trigger
        self.__transError = transError
        self.__thrError = thrError 
        self.__nHalfPeriod = round(self.__fsEEG/self.__clkSerial/2)
        self.__nHalfPeriod_low = self.__nHalfPeriod*(1+self.__thrError)
        self.__nHalfPeriod_high = self.__nHalfPeriod*(1-self.__thrError)
        self.__max_distance = max_trig_distance
    
    @property
    def fsEEG(self):
        return self.__fsEEG
    @fsEEG.setter
    def fsEEG(self, value):
        self.__fsEEG = value 

    @property
    def clkSerial(self):
        return self.__clkSerial
    @clkSerial.setter
    def clkSerial(self, value):
        self.__clkSerial = value 

    @property
    def transError(self):
        return self.__transError
    @transError.setter
    def transError(self, value):
        self.__transError = value

    @property
    def thrError(self):
        return self.__thrError
    @transError.setter
    def thrError(self, value):
        self.__thrError = value

    def decode(self, **kwargs):
        errorsLowerBound = 0
        
        for key,value in kwargs.items():
            if key=='trigger':
                self.__trigger = value
        events = []
        #Count samples of changed value (2 levels)
        counts = np.zeros((2,1), np.int32)
        nsamples = len(self.__trigger)
        for i in range(1, nsamples):
            if(self.__trigger[i] != self.__trigger[i-1]):
                new_change = np.zeros((2,1), np.int16)
                counts = np.concatenate((counts,new_change), axis=1)
            counts[self.__trigger[i], counts.shape[1]-1]+=1
        bit_pattern = ''
        numOfChange = counts.shape[1]
        #detect false jumping and clear (length < 5)
        i=1
        while i<numOfChange-1:
            if  counts[0,i]>0 and counts[0,i]<5 and counts[1,i-1]<2*self.__nHalfPeriod_high and counts[1,i+1]<2*self.__nHalfPeriod_high:
                counts[1,i-1] += (counts[0,i] + counts[1,i+1])
                counts = np.delete(counts, [i,i+1], axis=1)
                i -= 1
                numOfChange-=2
            if  counts[1,i]>0 and counts[1,i]<5 and counts[0,i-1]<2*self.__nHalfPeriod_high and counts[0,i+1]<2*self.__nHalfPeriod_high:
                counts[0,i-1] += (counts[1,i] + counts[0,i+1])
                counts = np.delete(counts, [i,i+1], axis=1)
                i -= 1
                numOfChange-=2
            i+=1
        #decode
        event_started = False
        i = 1
        lastbit = 0
        event_idx = 0
        min_no_trig_duration = 2*max(self.__nHalfPeriod_high, self.__nHalfPeriod_low)*(1+self.__transError) 
        while i<numOfChange-1:
            if (not event_started) and counts[0,i-1] > min_no_trig_duration and counts[1,i] >= self.__nHalfPeriod_high*0.1 and counts[1,i] <= self.__nHalfPeriod_high*(1+self.__transError) and counts[0,i+1] >= self.__nHalfPeriod_low*(1-self.__transError): #event started
                event_started = True
                lastbit = 0
                event_idx = np.sum(counts[:,:i])
            elif event_started and counts[0,i] > min_no_trig_duration: #event finished
                event_started = False
                if len(bit_pattern) > 0:
                    event = {
                        'sample_idx':event_idx,
                        'pattern':bit_pattern,
                        'code':int(bit_pattern, 2)
                    }
                    if len(bit_pattern) > 8 and int(bit_pattern, 2) > 159:
                        print("        WARNING: PATTERN TOO LONG. CODE VALUE IS ALSO TOO LARGE. This is at sample " + str(event_idx) + ".         ")
                        errorsLowerBound += 1
                        
                    if len(bit_pattern) > 8 and int(bit_pattern, 2) < 160:  
                        errorsLowerBound += 1
                        print("        WARNING: PATTERN TOO LONG. CODE VALUE IS NOT TOO LARGE. This is at sample " + str(event_idx) + ".         ")
                        
                    if len(bit_pattern) < 9 and int(bit_pattern, 2) > 159:  
                        print("        WARNING: CODE VALUE IS NOT TOO LARGE. PATTERN IS NOT TOO LONG. This is at sample " + str(event_idx) + ".         ")
                        errorsLowerBound += 1
                        
                    events.append(event)
                    bit_pattern = ''
           
            elif event_started and counts[1,i] >= (self.__nHalfPeriod_high*(1-self.__transError) + self.__nHalfPeriod*lastbit) and counts[1,i] <= (self.__nHalfPeriod_high*(1+self.__transError) + self.__nHalfPeriod*lastbit) and counts[0,i+1] >= self.__nHalfPeriod_low*(1-self.__transError): #Machester 0
                bit_pattern += '0'
                lastbit = 0
            elif event_started and counts[0,i] >= (self.__nHalfPeriod_low*(1-self.__transError) + self.__nHalfPeriod*(1-lastbit)) and counts[0,i] <= (self.__nHalfPeriod_low*(1+self.__transError) + self.__nHalfPeriod*(1-lastbit)) and counts[1,i+1] >= self.__nHalfPeriod_high*(1-self.__transError): #Machestor 1
                bit_pattern += '1'
                lastbit = 1
            if len(bit_pattern) > 0 and ((counts[1,i+1]>=self.__nHalfPeriod_high*(1-self.__transError) and counts[1,i+1]<=self.__nHalfPeriod_high*(1+self.__transError)) or (counts[0,i+1]>=self.__nHalfPeriod_low*(1-self.__transError) and counts[0,i+1]<=self.__nHalfPeriod_low*(1+self.__transError))):
                i+=2
            else:
                i+=1
            
        print("Errors - this is a LOWER BOUND estimate based on code sizes and pattern lengths: " + str(errorsLowerBound))
            
        return events
    
    #for bug fix of Yousef2 recording
    def decode_2(self, **kwargs):
        errorsLowerBound = 0
        
        for key,value in kwargs.items():
            if key=='trigger':
                self.__trigger = value
        events = []
        #Count samples of changed value (2 levels)
        counts = np.zeros((2,1), np.int32)
        nsamples = len(self.__trigger)
        for i in range(1, nsamples):
            if(self.__trigger[i] != self.__trigger[i-1]):
                new_change = np.zeros((2,1), np.int16)
                counts = np.concatenate((counts,new_change), axis=1)
            counts[self.__trigger[i], counts.shape[1]-1]+=1
        plt.plot(self.__trigger)
        bit_pattern = ''
        numOfChange = counts.shape[1]
        event_started = False
        i = 1
        lastbit = 0
        event_idx = 0
        min_no_trig_duration = 2*max(self.__nHalfPeriod_high, self.__nHalfPeriod_low)*(1+self.__transError) 
        while i<numOfChange-1:
            if (not event_started) and counts[0,i-1] > min_no_trig_duration and counts[1,i] >= self.__nHalfPeriod_high*0.1 and counts[1,i] <= 2*self.__nHalfPeriod_high*(1+self.__transError): #and counts[0,i+1] >= self.__nHalfPeriod_low*(1-self.__transError): #event started
                event_started = True
                lastbit = 0
                event_idx = np.sum(counts[:,:i])
            elif event_started and counts[0,i] > min_no_trig_duration: #event finished
                event_started = False
                if len(bit_pattern) > 0:
                    event = {
                        'sample_idx':event_idx,
                        'pattern':bit_pattern,
                        'code':int(bit_pattern, 2)
                    }
                    if len(bit_pattern) > 8 and int(bit_pattern, 2) > 159:
                        print("        WARNING: PATTERN TOO LONG. CODE VALUE IS ALSO TOO LARGE. This is at sample " + str(event_idx) + ".         ")
                        errorsLowerBound += 1
                        
                    if len(bit_pattern) > 8 and int(bit_pattern, 2) < 160:  
                        errorsLowerBound += 1
                        print("        WARNING: PATTERN TOO LONG. CODE VALUE IS NOT TOO LARGE. This is at sample " + str(event_idx) + ".         ")
                        
                    if len(bit_pattern) < 9 and int(bit_pattern, 2) > 159:  
                        print("        WARNING: CODE VALUE IS NOT TOO LARGE. PATTERN IS NOT TOO LONG This is at sample " + str(event_idx) + ".         ")
                        errorsLowerBound += 1
                        
                    if(len(events)>0):
                        if event['code']==9:
                            event['code']=0
                        if (event['sample_idx'] - events[-1]['sample_idx'] > 4000):
                            event['code'] = 8
                        if event['code'] == 8 and (events[-1]['code']!=9) and (events[-1]['code']!=14):
                                events[-1]['code'] = 9
                    events.append(event)
                    bit_pattern = ''
                    
           
            elif event_started and counts[1,i] >= (self.__nHalfPeriod_high*(1-self.__transError) + self.__nHalfPeriod*lastbit) and counts[1,i] <= (self.__nHalfPeriod_high*(1+self.__transError) + self.__nHalfPeriod*lastbit) and counts[0,i+1] >= self.__nHalfPeriod_low*(1-self.__transError): #Machester 0
                bit_pattern += '0'
                lastbit = 0
            elif event_started and counts[0,i] >= (self.__nHalfPeriod_low*(1-self.__transError) + self.__nHalfPeriod*(1-lastbit)) and counts[0,i] <= (self.__nHalfPeriod_low*(1+self.__transError) + self.__nHalfPeriod*(1-lastbit)) and counts[1,i+1] >= self.__nHalfPeriod_high*(1-self.__transError): #Machestor 1
                bit_pattern += '1'
                lastbit = 1
            if len(bit_pattern) > 0 and ((counts[1,i+1]>=self.__nHalfPeriod_high*(1-self.__transError) and counts[1,i+1]<=self.__nHalfPeriod_high*(1+self.__transError)) or (counts[0,i+1]>=self.__nHalfPeriod_low*(1-self.__transError) and counts[0,i+1]<=self.__nHalfPeriod_low*(1+self.__transError))):
                i+=2
            else:
                i+=1

        events[-1]['code'] = 9
        
        print("Errors - this is a LOWER BOUND estimate based on code sizes and pattern lengths: " + str(errorsLowerBound))
        
        return events

    def decodeWithRef(self, trigRefPath):
        thrErrorbk = self.__thrError
        transErrorbk = self.__transError

        refTrigFile = open(trigRefPath, 'r')
        trueEvents = np.array(refTrigFile.readlines(), dtype=np.int16)
        outEvents = []
        maxAcc = 0
        for m in [0, -1, 1, -2, 2]:
            for n in range(10):
                self.thrError = thrErrorbk + 0.05*m
                self.transError = transErrorbk + 0.05*n
                decodedEvents = []
                events = self.decode()
                for i in range(len(events)):
                    j = max(0,i-1)
                    fromPrevious = events[i]['sample_idx']-events[j]['sample_idx']
                    event = events[i]['code']
                    if(fromPrevious > self.__max_distance*self.__fsEEG*(1+self.__transError)):
                        decodedEvents.append(-1)
                    decodedEvents.append(event)
                decodedEvents = np.array(decodedEvents, dtype=np.int16)
                length = min(len(trueEvents), len(decodedEvents))
                acc = np.sum(trueEvents[0:length] == decodedEvents[0:length])/length
                if acc > maxAcc:
                    maxAcc = acc
                    outEvents = events

                if maxAcc == 1:
                    self.thrError = thrErrorbk
                    self.transError = transErrorbk
                    return (outEvents, maxAcc)

        self.thrError = thrErrorbk
        self.transError = transErrorbk
        return (outEvents, maxAcc)

       
    def print(self):
        print('Half clock samples high: {}'.format(self.__nHalfPeriod_high))
        print('Half clock samples low: {}'.format(self.__nHalfPeriod_low))
        print('EEG sample rate: {}'.format(self.__fsEEG))
        print('Clock rate: {}'.format(self.__clkSerial))
        print('Thresholding error: {}'.format(self.__thrError))
        print('Transfer error: {}'.format(self.__transError))


    def generateTrialTrigger():
        print("Re-generating trigger ...")
