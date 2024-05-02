import PySimpleGUI as sg

sg.theme("Dark")

first_column = [
    [sg.Text("Choose your arduino: ")],
    [sg.Text("Sample period (s)")],
    [sg.Text("Session duration (s)")],
    [sg.Text("Input signal")],
    [sg.Text("Bits:")],
    [sg.Text("Seed:")],
    [sg.Text("Var_tb:")],
    [sg.Text("Plot data?")],
    [sg.Text("Save data?")],
    [sg.Text("Path")],
]

second_column = [
    [sg.InputText(size=(15, 1))],
    [sg.InputText(size=(15, 1))],
    [sg.InputText(size=(15, 1))],
    [sg.InputText(size=(15, 1))],
    [sg.InputText(size=(5, 1))],
    [sg.InputText(size=(5, 1))],
    [sg.InputText(size=(5, 1))],
    [sg.Checkbox("Yes"), sg.Checkbox("No")],
    [sg.Checkbox("Yes"), sg.Checkbox("No")],
    [sg.InputText(size=(15, 1))],
]

bottom_line = [[sg.Button("GET MODEL")]]

layout = [
    [
        sg.Column(first_column, vertical_alignment="top"),
        sg.VSeparator(),
        sg.Column(second_column, vertical_alignment="center"),
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
while True:

    event, values = window.read()

    if event == sg.WIN_CLOSED:
        break

window.close()
