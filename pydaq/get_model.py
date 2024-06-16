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
from math import floor
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
        var_tb=1,
        session_duration=10.0,
        save=True,
        plot=True,
    ):

        super().__init__()
        self.device = device
        self.channel = channel
        self.session_duration = session_duration
        self.ts = ts
        self.var_tb = var_tb
        self.save = save
        self.plot = plot
        self.signal = Signal(6, 100, 1)
        self.legend = ["Input", "Output"]
        self.sinal = self.prbs_final()

        self.out_read = []
        self.time_var = []

        # Error flags
        self.error_path = False

        # COM ports
        self.com_ports = [i.description for i in serial.tools.list_ports.comports()]
        self.com_port = com  # Default COM port

        # Plot title
        self.title = None

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

        # PRBS values
        self.prbs_bits = 6
        self.prbs_seed = 100

    def prbs_final(self):
        TB = self.ts * self.var_tb

        self.cycles = int(np.floor(self.session_duration / TB)) + 1
        len_sinal_prbs = len(self.signal.sinal_prbs)

        # Verifica se Nt é menor que o comprimento de self.signal.sinal_prbs
        if self.cycles < len_sinal_prbs:
            return self.signal.sinal_prbs[: self.cycles]
        else:
            n_rep_int = self.cycles // len_sinal_prbs
            n_resto = self.cycles % len_sinal_prbs
            sinal = self.signal.sinal_prbs * n_rep_int
            sinal.extend(self.signal.sinal_prbs[:n_resto])
            print(len(sinal))

        return sinal

    def get_model_arduino(self):

        self.data = []
        self.time_var = []

        self._check_path()
        self.sinal = self.prbs_final()
        sinal = np.array(self.sinal)

        self._open_serial()

        self.data_send = [b"1" if i == 1 else b"0" for i in sinal]

        if self.plot:  # If plot, start updatable plot
            self.title = f"PYDAQ - Geting Data. Arduino, Port: {self.com_port}"
            self._start_updatable_plot()

        time.sleep(2)

        for k in range(self.cycles):

            st = time.time()
            self.ser.reset_input_buffer()  # Reseting serial input buffer
            self.ser.write(self.data_send[k])

            temp = int(self.ser.read(14).split()[-2].decode("UTF-8")) * self.ard_vpb

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
                    [sinal[0 : k + 1] * 5, self.out_read[0 : k + 1]],
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

        TB = self.ts * self.var_tb

        time_save = int(self.start_save_time / TB)

        data_x = sinal
        data_y = np.array(self.out_read)
        perc_index = floor(data_x.shape[0] - data_x.shape[0] * (self.perc_value / 100))

        x_train, x_valid = (
            data_x[time_save:perc_index].reshape(-1, 1),
            data_x[perc_index:].reshape(-1, 1),
        )
        y_train, y_valid = (
            data_y[time_save:perc_index].reshape(-1, 1),
            data_y[perc_index:].reshape(-1, 1),
        )

        basis_function = Polynomial(degree=self.degree)

        model = FROLS(
            order_selection=True,
            n_info_values=self.num_info_val,
            extended_least_squares=self.ext_lsq,
            ylag=[i + 1 for i in range(self.inp_lag)],
            xlag=[i + 1 for i in range(self.out_lag)],
            info_criteria="aic",
            estimator=self.estimator,
            basis_function=basis_function,
        )
        model.fit(X=x_train, y=y_train)
        yhat = model.predict(X=x_valid, y=y_valid)
        rrse = root_relative_squared_error(y_valid, yhat)
        print(rrse)
        r = pd.DataFrame(
            results(
                model.final_model,
                model.theta,
                model.err,
                model.n_terms,
                err_precision=8,
                dtype="sci",
            ),
            columns=["Regressors", "Parameters", "ERR"],
        )
        print(r)
        plt.style.available
        plot_results(
            y=y_valid,
            yhat=yhat,
            n=1000,
            title="test",
            xlabel="Samples",
            ylabel=r"y, $\hat{y}$",
            data_color="#1f77b4",
            model_color="#ff7f0e",
            marker="o",
            model_marker="*",
            linewidth=1.5,
            figsize=(10, 6),
            style="seaborn-v0_8-notebook",
            facecolor="white",
        )
        ee = compute_residues_autocorrelation(y_valid, yhat)
        plot_residues_correlation(
            data=ee, title="Residues", ylabel="$e^2$", style="seaborn-v0_8-notebook"
        )
        x1e = compute_cross_correlation(y_valid, yhat, x_valid)
        plot_residues_correlation(
            data=x1e, title="Residues", ylabel="$x_1e$", style="seaborn-v0_8-notebook"
        )
        self.display_results_in_window(r, rrse)
        return

    def display_results_in_window(self, results_df, rrse):
        layout = [
            [sg.Text("Model Results", font=("Helvetica", 16))],
            [sg.Multiline(results_df.to_string(), size=(80, 20))],
            [sg.Button("OK")],
        ]
        window = sg.Window("Results", layout, modal=True)
        while True:
            event, values = window.read()
            if event == "OK" or event == sg.WIN_CLOSED:
                break
        window.close()

    def get_model_arduino_gui(self):

        sg.theme("Dark")

        first_column = [
            [sg.Text("Data acquisition", font=("Helvetica", 12, "bold"))],
            [sg.Text("Choose your arduino: ")],
            [sg.Text("Sample period (s)")],
            [sg.Text("Session duration (s)")],
            [sg.Text("Start Saving Data (s)")],
            [sg.Text("Input signal")],
            [sg.Text("Plot data?")],
            [sg.Text("Save data?")],
            [sg.Text("Path")],
            [sg.Text("   ")],
            [sg.Text("System Identification", font=("Helvetica", 12, "bold"))],
            [sg.Text("Degree")],
            [sg.Text("Output lag")],
            [sg.Text("Input lag")],
            [sg.Text("Number of information values")],
            [sg.Text("Estimator")],
            [sg.Text("Extended least squares algorithm")],
            [sg.Text("Percentage of data for validacion")],
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
                sg.Spin(
                    [i + 1 for i in range(1000)],
                    size=(40, 1),
                    initial_value=4,
                    key="-Save_val_time-",
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
            [
                sg.Spin(
                    [i + 1 for i in range(1000)],
                    size=(40, 1),
                    initial_value=2,
                    key="-Pol_deg-",
                )
            ],
            [
                sg.Spin(
                    [i + 1 for i in range(1000)],
                    size=(40, 1),
                    initial_value=3,
                    key="-Out_lag-",
                )
            ],
            [
                sg.Spin(
                    [i + 1 for i in range(1000)],
                    size=(40, 1),
                    initial_value=3,
                    key="-Inp_lag-",
                )
            ],
            [
                sg.Spin(
                    [i + 1 for i in range(1000)],
                    size=(40, 1),
                    initial_value=6,
                    key="-N_info_val-",
                )
            ],
            [
                sg.Combo(
                    values=[i for i in Estimators.__dict__.keys() if i[:1] != "_"],
                    size=(40, 1),
                    default_value="least_squares",
                    key="-Estim_alg-",
                )
            ],
            [
                sg.Radio("True", "ext_lsq", default=True, key="-Ext_lsq-"),
                sg.Radio("False", "ext_lsq", default=False),
            ],
            [
                sg.Spin(
                    [i + 1 for i in range(1000)],
                    size=(40, 1),
                    initial_value=15,
                    key="-Perc_value-",
                )
            ],
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
            [sg.Input(self.prbs_bits, key="-prbs_n_bits-", size=(20, 1))],
            [sg.Text("Seed:")],
            [sg.Input(self.prbs_seed, key="-prbs_seed-", size=(20, 1))],
            [sg.Text("TB:")],
            [sg.Input(self.var_tb, key="-prbs_tb-", size=(20, 1))],
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
                    self.com_port = serial.tools.list_ports.comports()[
                        self.com_ports.index(values["-COM-"])
                    ].name
                    self.ts = float(values["-TS-"])
                    self.session_duration = float(values["-SD-"])
                    self.start_save_time = int(values["-Save_val_time-"])
                    self.save = values["-Save-"]
                    self.path = values["-Path-"]
                    self.plot = values["-Plot-"]
                    self.signal = Signal(
                        int(values["-prbs_n_bits-"]),
                        int(values["-prbs_seed-"]),
                        int(values["-prbs_tb-"]),
                    )

                    self.out_read = []
                    self.degree = values["-Pol_deg-"]
                    self.out_lag = values["-Out_lag-"]
                    self.inp_lag = values["-Inp_lag-"]
                    self.num_info_val = values["-N_info_val-"]
                    self.estimator = values["-Estim_alg-"]
                    self.ext_lsq = values["-Ext_lsq-"]
                    self.perc_value = values["-Perc_value-"]

                except BaseException:
                    self._error_window()
                    self.error_path = True

                # Calling data aquisition method
                if not self.error_path:
                    self.get_model_arduino()

        window.close()

        return
