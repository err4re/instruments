import numpy as np
import sys

def update_progress(progress,more_status=""):
    barLength = 40 # Modify this to change the length of the progress bar
    status = ""
    if isinstance(progress, int):
        progress = float(progress)
    if not isinstance(progress, float):
        progress = 0
        status = "error: progress var must be float\r\n"
    if progress < 0:
        progress = 0
        status = "Halt.\r\n"
    if progress >= 1:
        progress = 1
        status = "Done.\r\n"
    block = int(round(barLength*progress))
    all_status = more_status + " " + status
    text = "\rProgress: [{0}] {1:.2f}% {2}".format( "#"*block + "-"*(barLength-block), progress*100, all_status)
    sys.stdout.write(text)
    sys.stdout.flush()

def linfunc(x, a, b):
    return a*x+b

def fit_linear(xdata, ydata, a0, b0):
    import scipy.optimize as opt
    return opt.curve_fit(linfunc, xdata, ydata, p0=[a0,b0])

def dBm_to_Vrms(PdBm):
    R = 50
    return np.sqrt(R*10**(PdBm/10)/1000)

def Vrms_to_dBm(Vrms):
    R = 50
    return 10*np.log10(Vrms**2/R*1000)

def dBm_to_W(PdBm):
    R = 50
    return dBm_to_Vrms(PdBm)**2/R

def W_to_dBm(P):
    R = 50
    return Vrms_to_dBm(np.sqrt(P*R))