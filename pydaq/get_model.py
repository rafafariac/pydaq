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

    def get_model_arduino_gui(self):

        sg.theme("Dark")

        first_column = [
            [sg.Text("Choose your arduino: ")],
            [sg.Text("Sample period (s)")],
            [sg.Text("Session duration (s)")],
            [sg.Text("Input signal")],
            [sg.Text("Plot data?")],
            [sg.Text("Save data?")],
            [sg.Text("Path")],
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
                    values=("PRBS", "1", "2"),
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
        ]

        third_column = []

        bottom_line = [[sg.Button("GET MODEL")]]

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
            [sg.Text("Input Informations")],
            [sg.Text("Bits:")],
            [sg.InputText("", size=(6, 1))],
            [sg.Text("Seed:")],
            [sg.InputText("", size=(6, 1))],
            [sg.Text("TB_var:")],
            [sg.InputText("", size=(6, 1))],
        ]
        window.extend_layout(window["-third_column-"], prbs_infos)
        window["-third_column-"].update(visible=False)
        while True:

            event, values = window.read()

            if values["-Sig_type-"] != "PRBS":
                window["-third_column-"].update(visible=False)

            if event == sg.WIN_CLOSED:
                break
            if event == "-Sig_type-":
                if values["-Sig_type-"] == "PRBS":
                    window["-third_column-"].update(visible=True)
        window.close()

        return
