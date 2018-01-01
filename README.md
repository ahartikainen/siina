# Siina

## Description

Pure Python library for Ground Penetrating Radar (GPR): IO, processing and visualization.  
Tested with Python 3.6.


## Installation

Èither clone the repo and install with `setup.py`

```git clone https://github.com/ahartikainen/siina  
cd siina
python setup.py install
```

or with a `pip`

`python -m pip install git+https://github.com/ahartikainen/siina`


## Underlying  datastructures

Header information is saved as a dictionary: `obj.header` 
Measurement data is saved as a list of ndarrays: `obj.data_list`
Main channel can be accessed with `.data` -method

## Example usage

```
import siina
import matplotlib.pyplot as plt

# create RadarFile object
meas = siina.RadarFile()

# read in the data
meas.read_file("./example_path/example_file.DZT")

# set the center frequency for GPR (in Hertz) if not done
if meas.header.get('frequency', None) is None:
    meas.header['frequency'] = 1e9 # 1 GHz

# print dimensions for the data
print("points in samples={}, samples={}, channels={}".format(meas.nrows, meas.ncols, meas.nchan)

# strip markers (important step with .DZT files)
meas.read_markers()

# center each sample 
meas.func_dc(start=500)

# apply lowpass filter with cutoff= 6 * frequency
#     if cutoff is float -> cutoff = cutoff
#     if cutoff is str -> cutoff = float(cutoff) * frequency
meas.func_filter(cutoff='6')

# plot mean function for the first channel
# all channels are found under obj.data_list

import matplotlib.pyplot as plt
plt.plot(meas.data.mean(1))

# plot radargram with plt.imshow
# be careful with the profile size (meas.ncols < 5000)
plt.imshow(meas.data, aspect='auto')

```
