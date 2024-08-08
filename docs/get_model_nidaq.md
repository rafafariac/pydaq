# Model Acquisition with NIDAQ Boards

**NOTE**: before working with PYDAQ, device driver should be installed and working correctly as a DAQ (Data Acquisition) device

## Adquiring the model using Graphical User Interface (GUI)

Using GUI to adquire the model is really straighforward and require only three LOC (lines of code):

```python
from pydaq.pydaq_global import PydaqGui

PydaqGui()
```
After this command, the following screen will show up, where the user should select the NIDAQ option and go to Get Model tab, to be able to define parameters and start to acquire data.

![](img/get_model_nidaq.PNG)

## Parameters

 - **Choose Device**: The user is able to select desired device.

 - **Choose Channel**: The user is able to select desired channel.

 - **Terminal Configuration**: The user can chance the terminal configuration (Differential, RSE and NRSE).

 - **Sample Period**: The user can change the time interval between sample readings.

 - **Start Saving Data**: Choose when the data will start being recorded to obtain the model.

 - **Session Duration**: The user can choose the session duration, which will change the number of iterations.

 - **Plot and Save data**: The user can choose whether to plot and save the data.

 - **Path**: Choose where the data will be saved.

 - **Input Signal**: The user can choose which input signal will be sent to the Arduino.

 - **Config signal**: Allows customization of the signal parameters.

 - **Advanced Settings**: Allows customization of the parameters for obtaining the model.

By pressing the **Get Model** button, the program will start and the model will be obtained.

<REFAZER O RODANDO POR LINEAS DE CODIGO>

## Run Get model from the command line
```python

# Importing PYDAQ
from pydaq.get_model import GetModel

# Defining parameters
com_port_arduino = 'COM3'
session_duration_in_s = 100
sample_period_in_s = 0.5
save_data = True
plot_data = True

# system identification parameters
degree = 2
start_save_time_in_s = 0
out_lag = 2
inp_lag = 2
num_info_val = 6
estimator = 'least_squares'
ext_lsq = True
perc_value_to_train_the_model = 15

# PRBS input parameters
prbs_bits = 6
prbs_seed = 100
var_tb = 1

# Class GetModel
g = GetModel(
    com= com_port_arduino,
    session_duration= session_duration_in_s,
    ts= sample_period_in_s,
    save= save_data,
    plot= plot_data,
    degree= 2,
    start_save_time= start_save_time_in_s,
    out_lag= out_lag,
    inp_lag= inp_lag,
    num_info_values= num_info_val,
    estimator= estimator,
    ext_lsq= ext_lsq,
    perc_value= perc_value_to_train_the_model,
    prbs_bits= prbs_bits,
    prbs_seed= prbs_seed,
    var_tb= var_tb
    )

# Method get_model_arduino
g.get_model_arduino()

```
**NOTE**: data will be saved on descktop, by default. To chance the path the user can define "g.path = Desired path".

If the user chooses to plot, this screen will appear:

![](img/adquired_data_arduino_getmodel.PNG)

At the end of the user-defined time, screens with the results will appear.


<Colocar gif mostrando o uso no final>