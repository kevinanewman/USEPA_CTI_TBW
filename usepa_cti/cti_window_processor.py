# -*- coding: utf-8 -*-
"""

cti_window_processor.py
=======================

.. note::

    This is development code written by EPA staff and
    is intended only for evaluation purposes—it does not
    represent how we may or may not use the resulting
    output in the development or promulgation of future rules

@author: US EPA

"""

from __init__ import *

if cti_verbose:
    print('Loading %s...' % __name__)

import numpy as np
from numpy import cumsum, minimum, diff, searchsorted
from scipy.integrate import cumtrapz
import pandas as pd


def find_windows(data, time_chan, window_chan, window_size, integrate_chans, data_chans = [], scaling_dict=dict(), window_step=1, max_dt=1, verbose=False):
    """
    Calculate windows of size (integrated quantity) window_size from the data dataframe using the window_chan column

    :param data: pandas dataframe of time-based emissions data
    :param time_chan: name (i.e. column heading) of time channel
    :param window_chan: name of channel to integrate (non-negative values only) to define window span
    :param window_size: desired window size (::window_chan integrated quantity)
    :param integrate_chans: other channel names to integrate over the window duration, string or list of strings
    :param scaling_dict: dictionary of multipliers for scaling signals (i.e. unit conversion)
    :param window_step: time interval between the start of consecutive windows, in seconds
    :param max_dt: maximum time step allowed (larger time steps are truncated to max_dt) - allows removal of time gaps
    :param verbose: if True then window contents are printed to the console
    :return: a pandas dataframe containing results by window
    """

    # allow integrate_chans to be string or list of string:
    if isinstance(integrate_chans, str):
        # make string a list:
        integrate_chans = [integrate_chans]

    # handle signal scaling if required:
    for key in scaling_dict.keys():
        data[key] = data[key] * scaling_dict[key]

    # remove time gaps greater than max_dt seconds (e.g. time gaps due to ignition-off events)
    real_time = data[time_chan]
    squeeze_time = cumsum(minimum(max_dt, diff(real_time, prepend=0)))

    # integrate only positive values for window creation
    integrated_window = cumtrapz(np.maximum(0, data[window_chan]), squeeze_time, initial=0)
    data['integrated_window'] = integrated_window

    # create dictionary of output signal names
    chan_out = dict()
    # add data channels to output signal list
    for signal_name in data_chans:
        chan_out[signal_name] = signal_name

    # calculate the integrals over time of desired channels and create new output columns
    # add integrated data channels to output signal list
    integrated_data = dict()
    for signal_name in integrate_chans:
        # data signal integrates positive and negative values
        integrated_data[signal_name] = cumtrapz(data[signal_name], squeeze_time, initial=0)
        if signal_name.__contains__('/s'):
            # 'value/s' column becomes 'value'
            chan_out[signal_name] = signal_name.replace('/s', '')
        else:
            # 'value' column becomes 'value-sec'
            chan_out[signal_name] = signal_name + '-sec'

    # initialize window-search variables
    window_start_idx = 0
    window_end_idx = 0
    window_start_time = -np.Inf

    # initialize result lists, values of window_data dict become columns in output dataframe, keys become column names
    window_data = dict()
    window_data['start_time'] = []
    window_data['end_time'] = []
    window_data['duration'] = []
    window_data['window_size'] = []

    for signal_name in integrate_chans:
        window_data[chan_out[signal_name]] = []

    for signal_name in data_chans:
        window_data[chan_out[signal_name] + ' MIN'] = []
        window_data[chan_out[signal_name] + ' MAX'] = []
        window_data[chan_out[signal_name] + ' AVG'] = []
        window_data[chan_out[signal_name] + ' SD'] = []

    # perform window search
    while window_start_idx <= window_end_idx < len(real_time) - 1:

        # find start index of window
        window_start_idx = searchsorted(real_time, window_start_time + window_step, side='left')

        # increment index until window size is reached or end of data
        while window_end_idx < len(real_time)-1 and integrated_window[window_end_idx] < (integrated_window[window_start_idx] + window_size):
            window_end_idx = window_end_idx + 1

        if verbose:
            # print informative window properties
            print([window_start_idx, window_end_idx, integrated_window[window_end_idx] , integrated_window[window_start_idx], integrated_window[window_end_idx] - integrated_window[window_start_idx]])

        # if valid window found, add window properties to output lists and calculate window statistics
        if (integrated_window[window_end_idx] >= integrated_window[window_start_idx] + window_size) \
                or (window_end_idx == len(real_time)-1):
            window_start_time = real_time[window_start_idx]
            window_end_time   = real_time[window_end_idx]

            window_data['start_time'].append(window_start_time)
            window_data['end_time'].append(window_end_time)
            window_data['duration'].append(window_end_time - window_start_time)
            window_data['window_size'].append(integrated_window[window_end_idx] - integrated_window[window_start_idx])

            for signal_name in integrate_chans:
                window_data[chan_out[signal_name]].append(integrated_data[signal_name][window_end_idx] - integrated_data[signal_name][window_start_idx])

            for signal_name in data_chans:
                window_data[chan_out[signal_name] + ' MIN'].append(data[signal_name][window_start_idx:window_end_idx + 1].min())
                window_data[chan_out[signal_name] + ' MAX'].append(data[signal_name][window_start_idx:window_end_idx + 1].max())
                window_data[chan_out[signal_name] + ' AVG'].append(data[signal_name][window_start_idx:window_end_idx + 1].mean())
                window_data[chan_out[signal_name] + ' SD'].append(data[signal_name][window_start_idx:window_end_idx + 1].std())

    # put data in a dataframe:
    window_df = pd.DataFrame()
    for k in window_data.keys():
        window_df[k] = window_data[k]

    return window_df
