import os
import time
import warnings
import PySimpleGUI as sg
import matplotlib.pyplot as plt
import nidaqmx
from nidaqmx.constants import TerminalConfiguration
import numpy as np
import serial
import serial.tools.list_ports
from pydaq.utils.base import Base
from pydaq.utils.PRBS import Signal
from sysidentpy.parameter_estimation import Estimators

import pandas as pd
from sysidentpy.model_structure_selection import FROLS
from sysidentpy.basis_function._basis_function import Polynomial
from sysidentpy.metrics import root_relative_squared_error
from sysidentpy.utils.generate_data import get_siso_data
from sysidentpy.utils.display_results import results
from sysidentpy.utils.plotting import plot_residues_correlation, plot_results
from sysidentpy.residues.residues_correlation import (
    compute_residues_autocorrelation,
    compute_cross_correlation,
)


class Get_model(Base):

    def __init__(
        self,
        device="Dev1",
        channel="ai0",
        terminal="Diff",
        com="COM1",
        ts=0.5,
        session_duration=10.0,
        save=True,
        plot=True,
    ):

        super().__init__()
        self.device = device
        self.channel = channel
        self.ts = ts
        self.session_duration = session_duration
        self.save = save
        self.plot = plot
        self.signal = Signal(6, 100, 1)
        self.legend = ["Output", "Input"]

        self.out_read = []
        self.time_var = []

        # Error flags
        self.error_path = False

        # COM ports
        self.com_ports = [i.description for i in serial.tools.list_ports.comports()]
        self.com_port = com  # Default COM port

        # Plot title
        self.title = None

        # Plot legend
        self.legend = ["Input"]

        # Defining default path
        self.path = os.path.join(os.path.join(os.path.expanduser("~")), "Desktop")

        # Arduino ADC resolution (in bits)
        self.arduino_ai_bits = 10

        # Arduino analog input max and min
        self.ard_ai_max, self.ard_ai_min = 5, 0

        # Value per bit - Arduino
        self.ard_vpb = (self.ard_ai_max - self.ard_ai_min) / (2**self.arduino_ai_bits)

        # Number of necessary cycles
        self.cycles = None

    def get_model_arduino(self):
        sinal = self.signal.sinal_prbs
        self.data = []
        self.time_var = []

        self._check_path()

        self.cycles = len(sinal)

        self._open_serial()

        self.data_send = [b"1" if i == 1 else b"0" for i in sinal]
        sinal = np.array(sinal)

        if self.plot:  # If plot, start updatable plot
            self.title = f"PYDAQ - Geting Data. Arduino, Port: {self.com_port}"
            self._start_updatable_plot()

        time.sleep(2)

        for k in range(self.cycles):

            st = time.time()

            self.ser.reset_input_buffer()  # Reseting serial input buffer
            self.ser.write(self.data_send[k])

            temp = int(self.ser.read(13).split()[-2].decode("UTF-8")) * self.ard_vpb

            self.out_read.append(temp)

            self.time_var.append(k * self.ts)
            if self.plot:

                # Checking if there is still an open figure. If not, stop the for loop.
                try:
                    plt.get_figlabels().index("iter_plot")
                except BaseException:
                    break

                # Updating data values
                self._update_plot(
                    [self.time_var, self.time_var],
                    [sinal[0 : k + 1], self.out_read[0 : k + 1]],
                    2,
                )
            print(f"Iteration: {k} of {self.cycles-1}")

            et = time.time()

            try:
                time.sleep(self.ts + (st - et))
            except:
                warnings.warn(
                    "Time spent to append data and update interface was greater than ts. "
                    "You CANNOT trust time.dat"
                )

        self.ser.write(b"0")
        self.ser.close()

        return

    def get_model_arduino_gui(self):

        sg.theme("Dark")

        first_column = [
            [sg.Text("Data acquisition", font=("Helvetica", 12, "bold"))],
            [sg.Text("Choose your arduino: ")],
            [sg.Text("Sample period (s)")],
            [sg.Text("Session duration (s)")],
            [sg.Text("Input signal")],
            [sg.Text("Plot data?")],
            [sg.Text("Save data?")],
            [sg.Text("Path")],
            [sg.Text("   ")],
            [sg.Text("System Identification", font=("Helvetica", 12, "bold"))],
            [sg.Text("Output lag")],
            [sg.Text("Input lag")],
            [sg.Text("Number of information values")],
            [sg.Text("Estimator")],
            [sg.Text("Extended least squares algorithm")],
        ]

        second_column = [
            [
                sg.DD(
                    self.com_ports,
                    size=(40, 1),
                    enable_events=True,
                    default_value=self.com_ports[-1],
                    key="-COM-",
                )
            ],
            [sg.I(self.ts, enable_events=True, key="-TS-", size=(40, 1))],
            [sg.I(self.session_duration, enable_events=True, key="-SD-", size=(40, 1))],
            [
                sg.DD(
                    values=("PRBS", ""),
                    enable_events=True,
                    key="-Sig_type-",
                    size=(40, 1),
                )
            ],
            [
                sg.Radio("Yes", "plot_radio", default=True, key="-Plot-"),
                sg.Radio("No", "plot_radio", default=False),
            ],
            [
                sg.Radio("Yes", "save_radio", default=True, key="-Save-"),
                sg.Radio("No", "save_radio", default=False),
            ],
            [
                sg.In(
                    size=(32, 1),
                    enable_events=True,
                    key="-Path-",
                    default_text=os.path.join(
                        os.path.join(os.path.expanduser("~")), "Desktop"
                    ),
                ),
                sg.FolderBrowse(),
            ],
            [sg.Text("    ")],
            [sg.Text("   ")],
            [sg.Spin([i + 1 for i in range(1000)], size=(40, 1))],
            [sg.Spin([i + 1 for i in range(1000)], size=(40, 1))],
            [sg.Spin([i + 1 for i in range(1000)], size=(40, 1))],
            [
                sg.DD(
                    values=[i for i in Estimators.__dict__.keys() if i[:1] != "_"],
                    size=(40, 1),
                )
            ],
            [sg.DD(values=("True", "False"), size=(40, 1))],
        ]

        third_column = []

        bottom_line = [[sg.Button("GET MODEL", key="-Start-", auto_size_button=True)]]

        layout = [
            [
                sg.Column(first_column, vertical_alignment="top"),
                sg.VSeparator(),
                sg.Column(second_column, vertical_alignment="center"),
                sg.VSeparator(),
                sg.Column(third_column, vertical_alignment="top", key="-third_column-"),
            ],
            [sg.HSeparator()],
            [sg.Column(bottom_line, vertical_alignment="center")],
        ]

        window = sg.Window(
            "PYDAQ & SysidentPy - Model Acquisition (ARDUINO)",
            layout,
            resizable=False,
            finalize=True,
            element_justification="center",
            font="Helvetica",
        )

        prbs_infos = [
            [sg.Text("Input Informations", font=("Helvetica", 12, "bold"))],
            [sg.Text("Bits:")],
            [sg.InputText("", key="-prbs_n_bits-", size=(6, 1))],
            [sg.Text("Seed:")],
            [sg.InputText("", key="-prbs_seed-", size=(6, 1))],
            [sg.Text("TB_var:")],
            [sg.InputText("", key="-prbs_var_tb-", size=(6, 1))],
        ]
        window.extend_layout(window["-third_column-"], prbs_infos)
        window["-third_column-"].update(visible=False)
        while True:

            event, values = window.read()
            print(values["-Sig_type-"])
            if values["-Sig_type-"] != "PRBS":
                window["-third_column-"].update(visible=False)
            if event == sg.WIN_CLOSED:
                break
            if event == "-Sig_type-":
                if values["-Sig_type-"] == "PRBS":
                    window["-third_column-"].update(visible=True)
            if event == "-Start-":
                print("oi")
                try:

                    self.data, self.time_var = [], []

                    # Separating variables
                    self.ts = float(values["-TS-"])
                    self.session_duration = float(values["-SD-"])
                    self.com_port = serial.tools.list_ports.comports()[
                        self.com_ports.index(values["-COM-"])
                    ].name
                    self.save = values["-Save-"]
                    self.path = values["-Path-"]
                    self.plot = values["-Plot-"]
                    self.signal = Signal(
                        int(values["-prbs_n_bits-"]),
                        int(values["-prbs_seed-"]),
                        int(values["-prbs_var_tb-"]),
                    )

                    self.out_read = []

                except BaseException:
                    self._error_window()
                    self.error_path = True

                # Calling data aquisition method
                if not self.error_path:
                    self.get_model_arduino()

        window.close()

        return
