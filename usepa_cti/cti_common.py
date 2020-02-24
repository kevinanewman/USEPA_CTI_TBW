# -*- coding: utf-8 -*-
"""
cti_common.py
=============

Support and shared routines for window data analysis

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

import copy
import pandas as pd
import numpy as np
import cti_unit_conversions as convert
import cti_data_source_profile as omdsp
import cti_file_io as file_io
import os
import glob
from cti_plot import *

import tkinter as tk
from tkinter import filedialog

tk.Tk().withdraw()  # hide empty tk windows


def prep_calcs_dataframe(data_filename, data_source_profile, verbose=False, start_time=''):
    """

    Pull in data file header, process time vector and process engine speeds and powers

    :param data_filename: Name of file to process
    :param data_source_profile: an object of class DataSourceProfile
    :param verbose: if True then optional outputs are printed to the console
    :param start_time: Optional start time for processing data based on time signal
    :return: (source_dataframe, calcs_dataframe) tuple
    """

    if data_source_profile.engine_power_rating_hp == 'filename_7_3':
        # have to make a copy or else original data_source_profile will be permanently modified and subsequent files
        # may not pull in HP from filename since data_profile.get_power_rating()
        # overrides data_profile.engine_power_rating_hp
        data_profile = copy.deepcopy(data_source_profile)
        data_profile = data_profile.get_power_rating(data_filename)
        if verbose:
            print('\nFilename power Rating = %f HP %f kW' % (data_profile.engine_power_rating_hp,
                                                             data_profile.engine_power_rating_kW))
    else:
        data_profile = data_source_profile

    pd.set_option('chained_assignment', 'raise')

    print('\nprocessing ' + data_filename + '...')

    if data_profile.header_row >= 1:
        header_row = data_profile.header_row - 1  # excel is 1-indexed, pandas is 0-indexed so subtract 1
    else:
        header_row = None

    if data_filename.__contains__('.csv'):
        source_dataframe = pd.read_csv(data_filename, header=header_row, dtype=object)
    else:  # assume data_filename.__contains__('.xls'): for now...
        print('*** You Should Really Be Using .csv Files, They Load Much Quicker! ***')
        source_dataframe = pd.read_excel(data_filename, header=header_row, dtype=object)

    # drop rows between header and data, if there is a header
    if data_profile.header_row is not None and (data_profile.first_data_row - data_profile.header_row > 1):
        for i in range(data_profile.first_data_row - data_profile.header_row - 2,
                       data_profile.first_data_row - data_profile.header_row - 1):
            print('Dropping index %d' % i)
            source_dataframe.drop(index=i, inplace=True)

    # drop blank rows!
    source_dataframe.dropna(axis='index', how='all', inplace=True)

    # reset index so it starts at zero, which it might not after dropping rows:
    source_dataframe.reset_index(drop=True, inplace=True)

    # replace empty cells (NaNs) with zeroes
    source_dataframe.fillna(0, inplace=True)

    # replace column names that contain '%' so PyCharm preview will function properly
    source_dataframe.columns = source_dataframe.columns.str.replace('%', 'pct')

    # create calculated values dataframe
    calcs_dataframe = pd.DataFrame()

    # make sure time, engine speed and enigne torque columns are numeric...
    source_dataframe[data_profile.time_signal] = pd.to_numeric(source_dataframe[data_profile.time_signal])
    source_dataframe[data_profile.engine_speed_signal] = pd.to_numeric(
        source_dataframe[data_profile.engine_speed_signal])
    source_dataframe[data_profile.engine_torque_signal] = pd.to_numeric(
        source_dataframe[data_profile.engine_torque_signal])

    if data_profile.time_base == 'base60':
        # parse crazy base 60 time signal that looks like HHMMSS
        time_hrs_x1000 = np.floor(source_dataframe[data_profile.time_signal] / 10000) * 10000
        time_mins_x100 = np.floor((source_dataframe[data_profile.time_signal] - time_hrs_x1000) / 100) * 100
        time_secs = source_dataframe[data_profile.time_signal] - time_hrs_x1000 - time_mins_x100
        time = time_hrs_x1000 / 10000 * 3600 + time_mins_x100 / 100 * 60 + time_secs
        time = time - time[0]  # start at time zero

        time_wrap = 0
        for t in range(len(time) - 1):
            if time[t + 1] < time[t]:
                # calculate time wrap due to overflow at midnight = time gap plus nominal dt
                time_wrap = time[t] - time[t + 1] + np.nanmedian(np.diff(time))
            time[t + 1] = time[t + 1] + time_wrap

        calcs_dataframe['time_secs'] = time
    else:  # base1
        time_offset = source_dataframe.loc[1, data_profile.time_signal]
        if verbose:
            print('Time Offset = %d' % time_offset)
        source_dataframe[data_profile.time_signal] = source_dataframe[data_profile.time_signal] - time_offset
        calcs_dataframe['time_secs'] = source_dataframe[data_profile.time_signal]

    # eliminate time jumps
    calcs_dataframe['time_secs'] = np.minimum(1 / data_source_profile.data_rate_Hz,
                                              np.diff(calcs_dataframe['time_secs'], prepend=0)).cumsum()

    # copy cleaned up time signal back to source dataframe
    source_dataframe[data_profile.time_signal] = calcs_dataframe['time_secs']

    # handle non-zero start time
    if start_time is not '':
        if isinstance(start_time, str):
            start_time = eval(start_time)
        # set start time = zero seconds
        calcs_dataframe['time_secs'] = calcs_dataframe['time_secs'] - start_time
        source_dataframe[data_profile.time_signal] = source_dataframe[data_profile.time_signal] - start_time
        # drop data before time zero
        calcs_dataframe = calcs_dataframe[calcs_dataframe['time_secs'] >= 0].copy()
        source_dataframe = source_dataframe[source_dataframe[data_profile.time_signal] >= 0].copy()
        calcs_dataframe.reset_index(drop=True, inplace=True)
        source_dataframe.reset_index(drop=True, inplace=True)

    # calculate data rate
    calcs_dataframe['dt_secs'] = calcs_dataframe['time_secs'].diff().fillna(0)

    # calculate engine speed, torque and poewr signals

    if data_profile.engine_speed_units == 'RPM':
        calcs_dataframe['engine_speed_rpm'] = source_dataframe[data_profile.engine_speed_signal]
    else:  # radians/sec to RPM
        calcs_dataframe['engine_speed_rpm'] = source_dataframe[data_profile.engine_speed_signal] * convert.radps2rpm

    if data_profile.engine_torque_units == 'ft-lbs':
        calcs_dataframe['engine_torque_ftlbs'] = source_dataframe[data_profile.engine_torque_signal]
        calcs_dataframe['engine_torque_Nm'] = source_dataframe[data_profile.engine_torque_signal] * convert.ftlbs2Nm
    else:  # Newton-meters
        calcs_dataframe['engine_torque_Nm'] = source_dataframe[data_profile.engine_torque_signal]
        calcs_dataframe['engine_torque_ftlbs'] = source_dataframe[data_profile.engine_torque_signal] * convert.Nm2ftlbs

    calcs_dataframe['engine_power_hp'] = calcs_dataframe['engine_speed_rpm'] * calcs_dataframe[
        'engine_torque_ftlbs'] * convert.rpmftlbs2hp
    calcs_dataframe['engine_power_kW'] = calcs_dataframe['engine_speed_rpm'] * convert.rpm2radps * calcs_dataframe[
        'engine_torque_Nm'] * convert.W2kW
    calcs_dataframe['engine_power_norm'] = calcs_dataframe['engine_power_kW'] / data_profile.engine_power_rating_kW

    return source_dataframe, calcs_dataframe


def prep_vehicle_speed(source_dataframe, calcs_dataframe, data_profile):
    """
    Attempt to convert vehicle speed column from source dataframe to numeric values, then populate MPH and m/s speeds
    in the calcs dataframe

    :param source_dataframe: Pandas dataframe containing source data vehicle speed
    :param calcs_dataframe: Calculated values dataframe with vehicle speed in mph and m/s
    :param data_profile: an object of class DataSourceProfile
    :return: (source_dataframe, calcs_dataframe) tuple
    """

    # make sure vehicle speed is numeric
    source_dataframe[data_profile.vehicle_speed_signal] = pd.to_numeric(
        source_dataframe[data_profile.vehicle_speed_signal])

    if data_profile.vehicle_speed_units == 'MPH':
        calcs_dataframe['vehicle_speed_mph'] = source_dataframe[data_profile.vehicle_speed_signal]
    elif data_profile.vehicle_speed_units == 'km/h':
        calcs_dataframe['vehicle_speed_mph'] = source_dataframe[data_profile.vehicle_speed_signal] * convert.kmh2mph
    else:  # m/s
        calcs_dataframe['vehicle_speed_mph'] = source_dataframe[data_profile.vehicle_speed_signal] * convert.mps2mph

    calcs_dataframe['vehicle_speed_m/s'] = calcs_dataframe['vehicle_speed_mph'] * convert.mph2mps

    return source_dataframe, calcs_dataframe


def scale_signal(source_dataframe, source_signal, source_signal_scale):
    """
    Scale signal (i.e. column) from source dataframe using source signal scale factor

    :param source_dataframe: Pandas dataframe containing signal to scale
    :param source_signal: Name (column heading) of signal to scale
    :param source_signal_scale: Numeric scale factor or 'degF->degC' or 'degC->degF'
    :return: scaled signal
    """

    if source_signal not in source_dataframe.columns:
        scaled_signal = np.NaN
        print('WARNING::: source signal %s not present in source data, using NaN :::WARNING' % source_signal)
    else:
        if source_signal_scale == 'degF->degC':
            scaled_signal = convert.degF2degC(source_dataframe[source_signal])
        elif source_signal_scale == 'degC->degF':
            scaled_signal = convert.degC2degF(source_dataframe[source_signal])
        else:
            scaled_signal = source_dataframe[source_signal] * source_signal_scale

    return scaled_signal


class runtime_options(object):
    """
    Container class for runtime options
    """

    def __init__(self):
        self.source_path = ''
        self.output_path = ''
        self.profile_filename = ''
        self.verbose = False
        self.file_include_list = []
        self.file_exclude_list = []
        self.file_list = []
        self.data_profile = None
        self.file_include_filter = []
        self.idle_speed_mph = 1
        self.cruise_speed_mph = 0
        self.idle_rpm_threshold = 0
        self.straight_average = False
        self.time_align_emissions = False
        self.append_summary = False


def handle_command_line_options(app_description='Generic CTI App', additional_args=[], additional_options=[]):
    """
    Handle command line options shared across CTI processor scripts

    :param app_description: 'Generic CTI App'
    :param additional_args: None
    :param additional_options: Command-line options
    :return: ``runtime_options`` object
    """
    import argparse

    parser = argparse.ArgumentParser(description=app_description)
    parser.add_argument('--source_path', type=str, help='Path to folder containing files to process [default: .]]',
                        default='.')
    parser.add_argument('--output_path', type=str, help='Path to folder for output results [default: .\output]',
                        default='output')
    parser.add_argument('--profile', type=str,
                        help='Path and filename to a cti_data_source_profile spreadsheet or "prompt" to launch file browser [default: cti_data_source_profile.xlsx]',
                        default='cti_data_source_profile.xlsx')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose messages and file outputs')
    parser.add_argument('--include', type=str, help='File filter, files to include/accept [default: *.csv]',
                        default='*.csv')
    parser.add_argument('--exclude', type=str, help='File filter, files to exclude/reject [default: *calcs.csv]',
                        default='*calcs.csv')

    for addargs in additional_args:
        eval(addargs)

    args = parser.parse_args()

    options = runtime_options()
    options.source_path = args.source_path
    options.output_path = args.output_path
    options.profile_filename = args.profile
    options.verbose = args.verbose
    options.file_include_filter = args.include.split(',')
    options.file_exclude_filter = args.exclude.split(',')

    for addoptions in additional_options:
        exec(addoptions)

    file_io.validate_file(options.source_path)
    if options.output_path is not None:
        file_io.validate_folder(options.output_path)

    print('options.profile_filename = ' + options.profile_filename)
    if options.profile_filename == 'prompt':
        options.profile_filename = filedialog.askopenfilename(title='Select CTI Data Source Profile',
                                                              initialdir=options.source_path,
                                                              filetypes=[('cti data source profile',
                                                                          'cti_data_source_profile.xlsx', '*.xlsx')])

    if options.profile_filename is not '':
        if (os.sep in options.profile_filename) or (os.altsep in options.profile_filename):
            # assume absolute path
            file_io.validate_file(options.profile_filename)
        else:
            # assume profile in source folder
            file_io.validate_file(options.source_path + os.sep + options.profile_filename)
            options.profile_filename = options.source_path + os.sep + options.profile_filename
        # load data profile
        options.data_profile = omdsp.DataSourceProfile(options.profile_filename)

    # build file list based on one or more file filters
    options.file_list = []
    for file_filter in options.file_include_filter:
        if file_filter is not np.nan:
            options.file_include_list += glob.glob(options.source_path + os.sep + file_filter)

    for file_filter in options.file_exclude_filter:
        if file_filter is not np.nan:
            options.file_exclude_list += glob.glob(options.source_path + os.sep + file_filter)

    options.file_list = set.difference(set(options.file_include_list), set(options.file_exclude_list))

    # show file list
    if len(options.file_list) > 0:
        print('Found %d Files:' % len(options.file_list))
        for file_name in options.file_list:
            print('     ' + file_name)
    else:
        print(options.file_include_filter)
        raise Exception('No Files Selected, Check File Filter and Path')
    print()

    return options


def dataframe_to_numeric(df, verbose=False):
    """
    Convert all possible columns of a pandas dataframe to numeric values

    :param df: Pandas dataframe to convert
    :param verbose: If True then column names are printed to the console during processing
    :return: dataframe **df** with data converted to numeric values
    """
    for column in df.columns:
        if verbose:
            print("Processing %s" % column)
        try:
            df[column] = pd.to_numeric(df[column])
        except:
            print('dataframe_to_numeric Error Processing Signal %s' % column)
        finally:
            pass
    return df
