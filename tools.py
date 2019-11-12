import numpy as np
import sys

def load_npz(file):
    with np.load(file) as data:
        sdata   = data['arr_0']
        freq    = data['arr_2']
        current = data['arr_3']
    M = sdata.shape[0]
    N = sdata.shape[1]
    P = sdata.shape[2]
    return [freq, sdata, current, M, N, P]

def load_npz_probe_vs_field(file):
    with np.load(file) as data:
        f       = data['arr_0']
        z       = data['arr_1']
        maglog  = data['arr_2']
        current = data['arr_3']
        IF_BW   = data['arr_4']
        powr    = ''#data['arr_5']
    # P = f.shape
    # M = current.shape
    return [f, z, maglog, current, IF_BW, powr]

def load_npz_spectro(file):
    with np.load(file) as data:
        M = data['M']
        N = data['N']
        P = data['P']
        Q = data['Q']
        if_bw = data['if_bw']
        probe_power = data['probe_power']
        pump_power = data['pump_power']
        freq = data['freq']
        freq2 = data['freq2']
        sdata = data['sdata']
        current = data['current']
        fc = data['fc']
        df = data['df']
        # exp_start_time = data['exp_start_time']
        # exp_stop_time = data['exp_stop_time']
        exp_duration_calc = data['exp_duration_calc']
        exp_duration = data['exp_duration']
    return [M, N, P, Q, if_bw, probe_power, pump_power, freq, freq2, sdata, current, fc, df, exp_duration_calc, exp_duration.all()]


def load_npz_shapiro(file):
    with np.load(file) as data:
        calibration=data["calibration"]
        nbiterations=data["nbiterations"]
        failed=data["failed"]
        freq=data["freq"]
        istop=data["istop"]
        noise=data["noise"]
        reflevel=data["reflevel"]
        sensitivity=data["sensitivity"]
        timeconstant=data["timeconstant"]
        clock=data["clock"]
    return [calibration,nbiterations,failed,freq,istop,noise,reflevel,sensitivity,timeconstant,clock]
 

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

#, p0=[a0,b0]

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


def plot(x, y, **kwargs):
    # default values
    if "marker" not in kwargs.keys(): kwargs["marker"] = '.'
    if "linewidth" in kwargs.keys(): kwargs["linewidth"] = 0.5
    if "markersize" not in kwargs.keys(): kwargs["markersize"] = 1.5
    if "alpha" not in kwargs.keys(): kwargs["alpha"] = 0.5

    # separate arguments for different function calls
    key_for_subplot = "figsize"
    key_for_xlabel = "xlabel"
    key_for_ylabel = "ylabel"
    key_for_title = "title"
    keys_for_legend = ["loc"]
    keys_for_plot = [k for k in kwargs if k not in [key_for_subplot] + [key_for_xlabel] + [key_for_ylabel] + [key_for_title] + keys_for_legend ]

    # work
    f, a = plt.subplots(1, 1, **{k:kwargs[k] for k in kwargs if k in ["figsize"]})
    a.plot(x, y, **{k:kwargs[k] for k in kwargs if k in keys_for_plot})
    a.set_xlabel(kwargs[key_for_xlabel])
    a.set_ylabel(kwargs[key_for_ylabel])
    a.set_title(kwargs[key_for_title])
    plt.legend(**{k:kwargs[k] for k in kwargs if k in keys_for_legend})

    return f, a