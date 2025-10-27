import numpy as np
import mne
import matplotlib.pyplot as plt

def montage(sfreq_in):

    #Coordinates for A1 and A2
    a1_coords = np.array([-0.0860761, -0.0249897, -0.067986])
    a2_coords = np.array([0.0857939, -0.0250093, -0.068031])
    
    singleEarElectrodes = 10 #Number of electrodes around each ear
    
    #Parameters for the elongated oval
    radius = 0.03  #in meters (adjust based on how close to the ears you want)
    inward_offset = 0.01  #1cm inward offset from A1/A2
    width = 0.015  #in meters (adjust based on the lateral extension)
    
    #Function to calculate electrode coordinates
    def calculate_coordinates(base_coords, clockwise=True):
        
        #First, find x, y, z coords without adding base coords:
            
        #x - need to remove the offset:
        if base_coords[0] > 0:
            x_points = inward_offset
        else:
            x_points = inward_offset
        
        #Start at cEL1/cER1:
        def generate_semicircle_points(width, height, num_points=5):
            #Generate angles for the points
            angles = np.linspace(0, np.pi, num_points)
    
            #Calculate x and y coordinates for the points
            y_points = width * np.cos(angles)
            z_points = height * np.sin(angles)
    
            return y_points, z_points
    
        #Set the width and height parameters
        width = 0.015
        height = 0.0105 #Assumes cEL1 is 0.9cm directly above cER10
        
        #Generate 5 points for the semicircle-ish shape
        y_points, z_points = generate_semicircle_points(width, height)
        
        #Add the 'offset':
        z_points = z_points + 0.0045
        
        #Need to consider the 10 other points:   
        z_points_reflected = -z_points
        y_points_reflected = -y_points
        z_points = np.append(z_points, z_points_reflected)
        y_points = np.append(y_points, y_points_reflected)
    
        #Next, need to combine x, y, z coords for a 2D matrix of points:
        x_points = np.repeat(x_points,10)
        points = np.vstack((x_points, y_points, z_points))
        points = np.transpose(points)
        
        
        
        #Add base coords, i.e A1/A2: 
        for i in range(0,10):
            points[i,:] = points[i,:] + base_coords
        
        #Finally, add channel names. First need to convert array data type, and insert empty column:
        points = points.astype('str')
        points = np.insert(points, 0, 0, axis=1)
        
        for i in range(0,10):
            points[i,0] = f'cE{"L" if clockwise else "R"}{i+1}'
        
        return points
    
    #Calculate coordinates for the left ear (cEL)
    electrode_coords_left = calculate_coordinates(a1_coords, clockwise=True)
    
    #Calculate coordinates for the right ear (cER)
    electrode_coords_right = calculate_coordinates(a2_coords, clockwise=False)
    
    
    #Extract Fpz coordinates from (built-in) standard_1020 montage:
    montage_1020 = mne.channels.make_standard_montage('standard_1020')
    fpz_coords = montage_1020.dig[4]['r']
    
    #Add Fpz coords to left electrode coords:
    electrode_coords = np.vstack([electrode_coords_left, ['Fpz'] + fpz_coords.tolist()])
    
    #Add right coords:
    electrode_coords = np.vstack([electrode_coords, electrode_coords_right])
    
    
    #Create an Info object
    info = mne.create_info(ch_names=electrode_coords[:,0].tolist(),
                           ch_types=['eeg'] * len(electrode_coords),
                           sfreq=sfreq_in)  #Set the appropriate sampling frequency
    
    #Dictionary of channel positions. Keys are channel names and values are 3D coordinates
    #- array of shape (3,) - in native digitizer space in m.
    keys = electrode_coords[:, 0]
    values = electrode_coords[:, 1:]
    
    #Convert to a dictionary
    channel_positions = {key: value for key, value in zip(keys, values)}
    
    #print(channel_positions)
    
    #Set the electrode locations
    info.set_montage(mne.channels.make_dig_montage(ch_pos=channel_positions))
    
    
    #Plot the montage in 3D
    #mne.viz.plot_sensors(info, kind='3d', title='cEEGrid Approx Electrode Locations')
    #fig, ax = plt.subplots()
    #mne.viz.plot_topomap(montage=montage_1020, show_names=True, axes=ax)
    #Try to export it?
    
    return info