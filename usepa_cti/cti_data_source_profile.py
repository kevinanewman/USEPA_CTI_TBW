# -*- coding: utf-8 -*-
"""

cti_data_source_profile.py
==========================

Class to define and interpret a data source profile (engine specs, signal source, destination and scaling) spreadsheet

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

import pandas as pd
import numpy as np
import cti_unit_conversions as convert
import cti_file_io as file_io

class DataSourceProfile(object):
    """
    Class to define and interpret a data source profile (engine specs, signal source, destination and scaling) spreadsheet
    """
    def __init__(self, profile_filename):
        """
        Create ``DataSourceProfile`` object from data source proflie file

        :param profile_filename: filename of .xlsx data source profile to read
        """
        self.dataframe = pd.DataFrame()
        # self.file_filter = ''
        self.header_row = 1
        self.first_data_row = 2
        self.regulatory_class = ''
        self.engine_name = file_io.get_parent_foldername(profile_filename)
        self.engine_power_rating_hp = 0
        self.engine_power_rating_units = ''
        self.engine_power_rating_kW = 0
        self.data_rate_Hz = 0
        self.time_signal = ''
        self.time_base = ''
        self.engine_speed_signal = ''
        self.engine_speed_units = ''
        self.engine_idle_speed_rpm = 0
        self.engine_torque_signal = ''
        self.engine_torque_units = ''
        self.vehicle_speed_signal = ''
        self.vehicle_speed_units = ''
        self.vehicle_grade_signal = ''
        self.vehicle_grade_units = ''
        self.destination_signal_list = list()
        self.source_signal_list = list()
        self.source_signal_scale = list()
        self.load_data_source_profile(profile_filename)

    def read_parameter(self, index_str, allrows=False):
        """
        Read parameter (row) from data source profile dataframe

        :param index_str: index (row name) into ``self.dataframe``
        :param allrows: if True then all rows at the given index are read at once
        :return: single cell value or value of the desired row
        """
        if allrows:
            return  self.dataframe[index_str]
        else:
            return self.dataframe[index_str][1]

    def validate_predefined_input(self, input_str, valid_inputs):
        """
        Check to see if a predefined parameter is one of the the predefined (allowed) choices

        .. warning:: Exception raised on validation failure

        :param input_str: string to validate
        :param valid_inputs: python ``dict`` or ``set`` of acceptable string values
        :return: validated input string or raise exception if not valid
        """
        if valid_inputs.__contains__(input_str):
            if type(valid_inputs) is dict:
                return valid_inputs[input_str]
            elif type(valid_inputs) is set:
                return input_str
            else:
                raise Exception(
                    'validate_predefined_input(...,valid_inputs) error: valid_inputs must be a set or dictionary')
        else:
            raise Exception('Invalid input "%s", expecting %s' % (input_str, str(valid_inputs)))

    def load_data_source_profile(self, profile_filename):
        """
        Attempt to read a CTI data source profile spreadsheet and populate the ``DataSourceProfile`` properties

        :param profile_filename: path and filename of the data source profile to read

        """
        self.dataframe = pd.read_excel(profile_filename, header=1)
        # drop units row
        self.dataframe.drop(index=0, inplace=True)

        # self.file_filter                = self.read_parameter('File Filter', allrows=True)
        self.header_row                 = self.read_parameter('Header Row')
        if not self.header_row >= 0:
            raise Exception('Header row must be >= 0')

        self.first_data_row             = self.read_parameter('First Data Row')
        if not self.first_data_row >= 1:
            raise Exception('First data row must be >= 1')

        self.regulatory_class           = self.validate_predefined_input(self.read_parameter('Regulatory Class'), {'LHD', 'MHD', 'HHD', 'BUS'})
        self.engine_power_rating_hp     = self.read_parameter('Engine Power Rating')
        self.engine_power_rating_units  = self.read_parameter('Engine Power Rating Units')
        self.engine_idle_speed_rpm      = self.read_parameter('Engine Idle Speed')
        self.time_signal                = self.read_parameter('Time Signal')
        self.data_rate_Hz               = self.read_parameter('Data Rate')

        self.time_base                  = self.validate_predefined_input(self.read_parameter('Time Base'), {'base1', 'base60'})
        self.engine_speed_signal        = self.read_parameter('Engine Speed')
        self.engine_speed_units         = self.validate_predefined_input(self.read_parameter('Engine Speed Units'),{'RPM', 'rad/s'})
        self.engine_torque_signal       = self.read_parameter('Engine Torque')
        self.engine_torque_units        = self.validate_predefined_input(self.read_parameter('Engine Torque Units'), {'ft-lbs', 'Nm'})
        self.vehicle_speed_signal       = self.read_parameter('Vehicle Speed')
        self.vehicle_speed_units        = self.validate_predefined_input(self.read_parameter('Vehicle Speed Units'), {'MPH', 'm/s', 'km/h'})
        self.vehicle_grade_signal       = self.read_parameter('Vehicle Grade')
        self.vehicle_grade_units        = self.validate_predefined_input(self.read_parameter('Vehicle Grade Units'), {'%', 'angle', np.NAN})
        self.destination_signal_list    = self.read_parameter('Signal Destination', allrows=True)
        self.destination_signal_list.replace(np.nan, '', inplace=True)
        self.source_signal_list         = self.read_parameter('Signal Source', allrows=True)
        self.source_signal_list.replace(np.nan, '', inplace=True)
        self.source_signal_scale        = self.read_parameter('Signal Scale', allrows=True)

        if self.engine_power_rating_hp != 'filename_7_3':
            if self.engine_power_rating_units == 'KW':
                self.engine_power_rating_kW = self.engine_power_rating_hp
            else:
                self.engine_power_rating_kW = self.engine_power_rating_hp * convert.hp2kW

    def get_power_rating(self, filename):
        """
        Parse engine power rating from HDIUT data filename

        :param filename: name of file to parse
        :return: self
        """
        filename = file_io.get_filename(filename)

        if self.engine_power_rating_hp == 'filename_7_3':
            if self.engine_power_rating_units == 'KW':
                self.engine_power_rating_kW = float(filename[7:10])
                self.engine_power_rating_hp = self.engine_power_rating_kW * convert.kW2hp
            else:
                self.engine_power_rating_hp = float(filename[7:10])
                self.engine_power_rating_kW = self.engine_power_rating_hp * convert.hp2kW

        return self


if __name__ == '__main__':
    import tkinter as tk
    from tkinter import filedialog

    tk.Tk().withdraw()  # hide empty tk windows

    profile_filename = filedialog.askopenfilename(title='Select Opmode Data Source Profile',
                                                              initialdir='.',
                                                              filetypes=[('opmode data source profile',
                                                                          'opmode_data_source_profile.xlsx')])
    data_profile = DataSourceProfile(profile_filename)

    print(data_profile.source_signal_scale)