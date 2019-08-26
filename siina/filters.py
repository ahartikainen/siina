"""Filter specific utilities."""
from numpy import asarray
from scipy.signal import sosfiltfilt, butter as signal_butter


def butterworth(data, cutoff, fs, order=6, btype="lowpass", axis=0):
    """Butterworth sosfiltfilt (forward-backward filter).

    Parameters
    ----------
    data : numpy array
        Array shape N,D
    cutoff : float or tuple of float
        Cutoff frequency for the filter
        A float for a lowpass and a highpass filters
        A tuple (lower, upper) for a bandpass and bandstop filters
    fs : float
        Sampling frequency
    order : int
        Filter order
    btype : {'lowpass', ‘highpass’, ‘bandpass’, ‘bandstop’}, optional
        A type of a filter.
        Default is lowpass
    axis : int, optional
        Axis to which the filter is applied.
        Default is 0

    Returns
    -------
    y : ndarray
        The filtered output from the `sosfiltfilt`-function
    """
    if isinstance(cutoff, (list, tuple)):
        cutoff = asarray(cutoff)
    # nyquist frequency = 1/2 * sampling frequency
    nyq = 0.5 * fs
    # normal cutoff = cutoff frequency / nyquist frequency
    # = 2 * cutt off frequency / sampling frequency
    normal_cutoff = cutoff / nyq
    # Get sos parameters
    sos = signal_butter(N=order, Wn=normal_cutoff, btype=btype, analog=False, output="sos")
    # run filter
    return sosfiltfilt(sos, data, axis=axis)
