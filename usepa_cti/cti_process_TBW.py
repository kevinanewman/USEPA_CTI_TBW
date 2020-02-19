# -*- coding: utf-8 -*-
"""
cti_process_TBW.py
==================

Process time-based windows for NOx emissions

.. note::

    This is development code written by EPA staff and
    is intended only for evaluation purposes—it does not
    represent how we may or may not use the resulting
    output in the development or promulgation of future rules

@author: US EPA

"""

import os
import copy
from datetime import datetime
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.integrate import trapz

import cti_file_io as file_io
import cti_common as cti
# from importlib import reload
# to reload:
# cti = reload(cti)
from cti_plot import *
import cti_window_processor as wp
import cti_unit_conversions as convert

# ------------------------------------- #

co2_increment_pct = 2.5
co2_pct_range = np.arange(0, 100 + co2_increment_pct, co2_increment_pct)

pctile_increment_pct = 5
pctile_range = np.arange(0, 105, pctile_increment_pct).tolist()


# ------------------------------------- #

def tbw_processor(data_filename, output_folder, __options):
    """
    Process file for NOx emissions using time-based windows

    :param data_filename: Name of file to process
    :param output_folder:  Name of output file folder
    :param __options: Data structure of command line / runtime options settings
    :return: Generates plots in ::output_folder

    """

    verbose = __options.verbose

    # load data profile and set FTP grams CO2/hp-hr scale factor
    if __options.data_profile.engine_power_rating_hp == 'filename_7_3':
        options = copy.deepcopy(
            __options)  # need to make deep copy since we modify options.ftp_co2_gphphr and options.data_profile.engine_power_rating_hp/kW
        data_profile = options.data_profile
        data_profile = data_profile.get_power_rating(data_filename)
        if options.ftp_co2_gphphr == '':
            if 'HHD' in data_filename:
                options.ftp_co2_gphphr = 555
            else:
                options.ftp_co2_gphphr = 576
        else:
            options.ftp_co2_gphphr = eval(options.ftp_co2_gphphr)
    else:  # engine dyno test data...
        options = __options
        data_profile = options.data_profile
        options.ftp_co2_gphphr = 555

    # set engine power rating
    engine_power_rating_hp = data_profile.engine_power_rating_hp

    # load emissions data into dataframe
    if options.hdiut:
        # process time vector, create engine speed, torque and power in calcs_dataframe
        df, calcs_dataframe = cti.prep_calcs_dataframe(data_filename, data_profile, verbose)

        # calculate vehicle speed (mph and m/s)
        df, calcs_dataframe = cti.prep_vehicle_speed(df, calcs_dataframe, data_profile)
    else:
        df = pd.read_csv(data_filename, header=0, dtype=object)

    # make sure dataframe contains numeric data where possible
    df = cti.dataframe_to_numeric(df)

    # fix possible data source inconsistency
    if ('NOX_Mass_Sec' in df.columns) and ('NOX_Mass_Sec_Final' not in df.columns):
        print('\n%%%% FIXING NOX_Mass_Sec_Final %%%%')
        df['NOX_Mass_Sec_Final'] = df['NOX_Mass_Sec']

    # set maximum grams CO2/hour emissions rate scale factor
    max_co2_rate_gphr = options.ftp_co2_gphphr * engine_power_rating_hp

    print('\nprocessing %s %d HP' % (data_filename, engine_power_rating_hp))

    # perform signal scaling as defined in data source profile and ensure required data columns
    if data_filename.__contains__('vehMPH') or options.hdiut:
        # create scaled, common-name destination signals from source signals
        for destination_signal, source_signal, source_signal_scale in zip(data_profile.destination_signal_list,
                                                                          data_profile.source_signal_list,
                                                                          data_profile.source_signal_scale):
            if destination_signal is not '' and source_signal is not '':
                df[destination_signal] = cti.scale_signal(df, source_signal, source_signal_scale)

        if options.hdiut:
            df['Power hp'] = calcs_dataframe['engine_power_hp']
            df['Time secs'] = calcs_dataframe['time_secs']
            df['Vehicle Speed'] = calcs_dataframe['vehicle_speed_mph']
        else:
            df.rename(index=str, columns={'Power': 'Power kW', data_profile.time_signal: 'Time secs'}, inplace=True)
            df['Power hp'] = df['Power kW'] * convert.kW2hp

    else:  # using concatenated_cycles dataframe...
        # signals are already scaled, just rename a couple that we need:
        df.rename(index=str, columns={'engine_power_hp': 'Power hp', 'time_secs': 'Time secs',
                                      'Vehicle Speed MPH': 'Vehicle Speed'}, inplace=True)

    # ensure desired column exists
    if not 'Aftertreatment Out Temp C' in df.columns:
        df['Aftertreatment Out Temp C'] = 0

    # calculate cycle engine work hp-hr
    work_hps = trapz(np.maximum(0, df['Power hp']), df['Time secs'])
    work_hphr = work_hps / 3600

    # load idle speed cutoff MPH
    idle_cutoff_mph = float(options.idle_speed_thresh_mph)

    # integrate NOx emissions and calculate total NOx g/hp-hr for the cycle
    nox_g = trapz(df['Tailpipe NOX g/s'], df['Time secs'])
    nox_gphpr = nox_g / work_hphr

    print('\nWork hp-hr = %f' % work_hphr)
    print('NOx grams = %f' % nox_g)
    print('NOx grams/hp-hr = %f\n' % nox_gphpr)

    # error checking on cycle work
    if np.isnan(work_hphr):
        print("\n*** WORK IS NAN, EXITING ***\n")
        return

    if work_hphr < 0:
        print("\n*** WORK IS NEGATIVE, EXITING ***\n")
        return

    # time-based window size is length in seconds
    window_size = options.window_length_secs

    # create detailed output folder name and create folder if necessary
    foldername = file_io.get_filename(data_filename.replace('QAdone', 'QA')) + '_%d_%d%s' % \
                 (options.window_length_secs, options.window_step_secs, descriptor_str)
    figure_path = output_folder + os.sep + foldername + os.sep
    file_io.validate_folder(figure_path)

    if cti_verbose:
        print('figure_path = ' + figure_path)

    # calculate time-based window data
    df['unity'] = 1  # integral of 1*dt is time, trick to make work-based window code create time-based windows
    if verbose:
        print('Getting Windows...')
    import time
    start = time.time()
    wp_window_df = wp.find_windows(df, 'Time secs', 'unity', window_size,
                                   ['Power hp', 'Tailpipe NOX g/s', 'Tailpipe CO2 g/s'],
                                   data_chans=['Vehicle Speed MPH', 'Aftertreatment Out Temp C'],
                                   window_step=options.window_step_secs)

    # cull windows below minimum duration, if any:
    wp_window_df = wp_window_df.loc[wp_window_df['duration'] >= options.window_min_secs]

    end = time.time()
    if verbose:
        print(end - start)
        print('done')

    # calculate window work hp-hr and average power
    wp_window_df['Power hp-hr'] = wp_window_df['Power hp-sec'] / 3600
    wp_window_df['Avg Power hp'] = wp_window_df['Power hp-sec'] / wp_window_df['duration']

    # calculate window NOx g/hp-hr
    if options.co2_normalization:
        wp_window_df['NOX g/hp-hr'] = wp_window_df['Tailpipe NOX g'] / wp_window_df[
            'Tailpipe CO2 g'] * options.ftp_co2_gphphr
    else:
        wp_window_df['NOX g/hp-hr'] = wp_window_df['Tailpipe NOX g'] / wp_window_df['Power hp-hr']

    # calculate CO2 emissions rates
    wp_window_df['Tailpipe CO2 g/hr'] = wp_window_df['Tailpipe CO2 g'] / wp_window_df['duration'] * 3600
    wp_window_df['Tailpipe CO2 g/hp-hr'] = wp_window_df['Tailpipe CO2 g/hr'] / wp_window_df['Avg Power hp']
    wp_window_df['Tailpipe CO2 rate norm'] = wp_window_df['Tailpipe CO2 g/hr'] / max_co2_rate_gphr

    # sort windows by NOx g/hp-hr
    wp_window_df.sort_values('NOX g/hp-hr', inplace=True)
    wp_window_df.reset_index(drop=False, inplace=True)
    wp_window_df.rename(columns={'index': 'window_num'}, inplace=True)

    # get base file name without for plot titles
    plot_data_filename = file_io.get_filename(data_filename)

    # plot Vehicle Speed and NOx rate versus time
    fig, ax1, ax2 = fplotyyhg(df['Time secs'], df['Vehicle Speed'], '', df['Tailpipe NOX g/s'], 'r-')
    label_xyt(ax1, 'Time (secs)', 'Vehicle Speed (mph)',
              '%s\nVehicle Speed and NOX g/s v Time %.1f hp-hr total work' % (plot_data_filename, work_hphr))
    ax2.tick_params(axis='y', colors='red')
    ax2.set_ylabel('Tailpipe NOx g/s', color='red')
    fig.subplots_adjust(right=0.85)
    plt.savefig(figure_path + '1_NOX_gps_n_vspeed_v_t', orientation='landscape')

    # plot HP and NOx rate versus time
    fig, ax1, ax2 = fplotyyhg(df['Time secs'], df['Power hp'], '', df['Tailpipe NOX g/s'], 'r-')
    label_xyt(ax1, 'Time (secs)', 'Power (hp)',
              '%s\nPower and NOX g/s v Time %.1f hp-hr total work' % (plot_data_filename, work_hphr))
    ax2.tick_params(axis='y', colors='red')
    ax2.set_ylabel('Tailpipe NOx g/s', color='red')
    fig.subplots_adjust(right=0.85)
    plt.savefig(figure_path + '2_NOX_gps_n_HP_v_t', orientation='landscape')

    # plot HP and Exhaust temp versus time
    fig, ax1, ax2 = fplotyyhg(df['Time secs'], df['Power hp'], '', df['Exhaust Temp C'], 'r-')
    label_xyt(ax1, 'Time (secs)', 'Power (hp)',
              '%s\nPower and Exhaust Temp v Time %.1f hp-hr total work' % (plot_data_filename, work_hphr))
    ax2.tick_params(axis='y', colors='red')
    ax2.set_ylabel('Exhaust Temp (C)', color='red')
    fig.subplots_adjust(right=0.85)
    plt.savefig(figure_path + '3_Exh_tmp_n_HP_v_t', orientation='landscape')

    # plot window number and percentile versus NOx g/hp-hr for each window
    nox = wp_window_df['NOX g/hp-hr']
    fig, ax1, ax2 = fplotyyhg(nox.values, nox.index / nox.index.max() * 100, '', nox.index, '')
    label_xyt(ax1, 'Window NOx (g/hp-hr)', 'Percentile', '%s\nNOx (g/hp-hr) per Window' % plot_data_filename)
    label_xy(ax2, 'Window NOx (g/hp-hr)', 'Ranked Window Number')
    vlineat(ax1, nox_gphpr, 'r-')
    lineat(ax1, 95, 'b-')
    lineat(ax1, 90, 'c-')
    fig.subplots_adjust(right=0.875)
    ax1.legend(['Percentile/Ranked Window Number', 'Cycle NOx g/hp-hr', '95th pctile', '90th pctile'], fontsize=9)
    plt.savefig(figure_path + '4_NOX_gphphr_p_ranked_wdw', orientation='landscape')

    # plot work (hp-hr) versus window number
    fig, ax1 = fplothg(wp_window_df['window_num'], wp_window_df['Power hp-hr'], '.')
    label_xyt(ax1, 'Sequential Window Number', 'Window Size (hp-hr)',
              '%s\nWindow Size (hp-hr) versus Sequential Window Number' % plot_data_filename)
    # lineat(ax1, window_size / 3600, 'r')
    plt.savefig(figure_path + '5_wdw_size_hphr_v_wdw_num', orientation='landscape')

    # plot work (co2_g) versus window number
    fig, ax1 = fplothg(wp_window_df['window_num'], wp_window_df['Tailpipe CO2 g'], '.')
    label_xyt(ax1, 'Sequential Window Number', 'Window Size (CO2 g)',
              '%s\nWindow Size (CO2 g) versus Sequential Window Number' % plot_data_filename)
    lineat(ax1, window_size, 'r')
    plt.savefig(figure_path + '5a_wdw_size_co2g_v_wdw_num', orientation='landscape')

    # plot window timespans
    foo = wp_window_df[['start_time', 'end_time']].sort_values('start_time')
    fig, ax1 = fplothg(foo.start_time, foo.start_time, '.-')
    ax1.plot(foo.end_time, foo.start_time, 'r.-')
    label_xyt(ax1, 'Time (secs)', 'Sequential Window Number', '%s\nWindow Spans versus Time' % plot_data_filename)
    ax1.legend(['Window Start', 'Window End'], fontsize=9)
    plt.savefig(figure_path + '6_window_spans_v_time', orientation='landscape')

    # plot window lengths
    fig, ax1 = fplothg(wp_window_df['window_num'], wp_window_df['duration'], '.')
    label_xyt(ax1, 'Sequential Window Number', 'Window Length (secs)',
              '%s\nWindow Length versus Sequential Window Number' % plot_data_filename)
    plt.savefig(figure_path + '7_wdw_leng_v_wdw', orientation='landscape')

    # plot nox g/hp-hr versus window average power
    fig, ax1 = fplothg(wp_window_df['Avg Power hp'] / engine_power_rating_hp * 100, wp_window_df['NOX g/hp-hr'], '.')
    label_xyt(ax1, 'Window Avg Power (% rated hp)', 'Window NOx (g/hp-hr)',
              '%s\nWindow NOx (g/hp-hr) versus Window Avg Power (%% rated hp)' % plot_data_filename)
    ax1.set_xlim([0, 100])
    plt.savefig(figure_path + '8_nox_v_wdw_avg_pct_pwr', orientation='landscape')

    # calculate 'true idle' bin (window average vehicle speed below idle cutoff mph)
    if options.true_idle_bin:
        true_idle_pts = wp_window_df.loc[wp_window_df['Vehicle Speed MPH AVG'] < idle_cutoff_mph]
        true_idle_pts.reset_index(drop=True, inplace=True)
        # cull true idle points to process the rest as normal down below
        wp_window_df = wp_window_df.loc[wp_window_df['Vehicle Speed MPH AVG'] >= idle_cutoff_mph]
        true_idle_nox_gphr = true_idle_pts['Tailpipe NOX g'].sum() / true_idle_pts['duration'].sum() * 3600
        true_idle_aftertreatment_mean_tempC = true_idle_pts['Aftertreatment Out Temp C AVG'].mean()
        true_idle_aftertreatment_SD_tempC = true_idle_pts['Aftertreatment Out Temp C AVG'].std()
        fig = plt.figure()
        ax1 = plt.gca()
        ax1.plot('true idle\n%.3f' % true_idle_nox_gphr, true_idle_nox_gphr, '.')
        ax1.set_ylabel('True Idle Bin NOx (g/hr)')
        ax1.set_title('%s\nBin True Idle NOx Rate Plot\n%s' % (plot_data_filename, foldername), fontsize=9)
        plt.grid()
        plt.savefig(figure_path + '12_NOxTruIdl_binplot', orientation='landscape')
    else:
        true_idle_nox_gphr = np.NaN
        true_idle_nox_gphphr = np.NaN
        true_idle_pts = []
        true_idle_aftertreatment_mean_tempC = np.NaN
        true_idle_aftertreatment_SD_tempC = np.NaN

    # bin windows based on user supplied normalized CO2 rate cutpoints
    bins = {}
    previous_bin_frac = 0
    for cutpoint_frac in options.hp_cutpoints_frac:
        bin_name = ('%.1f->%.1f' % (previous_bin_frac * 100, cutpoint_frac * 100))
        bins[bin_name] = wp_window_df.loc[(wp_window_df['Tailpipe CO2 rate norm'] > previous_bin_frac) & (
                    wp_window_df['Tailpipe CO2 rate norm'] <= cutpoint_frac)]
        bins[bin_name].reset_index(drop=True, inplace=True)
        previous_bin_frac = cutpoint_frac

    bin_name = ('>%.1f' % (previous_bin_frac * 100))
    bins[bin_name] = (wp_window_df.loc[(wp_window_df['Tailpipe CO2 rate norm'] > previous_bin_frac)])
    bins[bin_name].reset_index(drop=True, inplace=True)

    # calculate results for emissions bins
    bin_results = {}

    if options.co2_normalization:
        if options.true_idle_bin:
            true_idle_nox_gphphr = true_idle_pts['Tailpipe NOX g'].sum() / true_idle_pts[
                'Tailpipe CO2 g'].sum() * options.ftp_co2_gphphr
        for bin_name, bin_data in bins.items():
            bin_results[bin_name + ' NOX g/hp-hr'] = bin_data['Tailpipe NOX g'].sum() / bin_data[
                'Tailpipe CO2 g'].sum() * options.ftp_co2_gphphr
    else:
        if options.true_idle_bin:
            true_idle_nox_gphphr = true_idle_pts['Tailpipe NOX g'].sum() / true_idle_pts['Power hp-hr'].sum()
        for bin_name, bin_data in bins.items():
            bin_results[bin_name + ' NOX g/hp-hr'] = bin_data['Tailpipe NOX g'].sum() / bin_data['Power hp-hr'].sum()

    for bin_name, bin_data in bins.items():
        bin_results[bin_name + ' Aftertreatment Out Temp C AVG'] = bin_data['Aftertreatment Out Temp C AVG'].mean()
        bin_results[bin_name + ' Aftertreatment Out Temp C SD'] = bin_data['Aftertreatment Out Temp C AVG'].std()
        bin_results[bin_name + ' Window Count'] = len(bin_data)

    # plot NOx g/hp-hr by bin
    fig = plt.figure()
    ax1 = plt.gca()
    plotted = False
    if options.true_idle_bin:
        ax1.plot('True Idle\n%.3f' % true_idle_nox_gphphr, true_idle_nox_gphphr, '.')
        plotted = True
    for bin_name, bin_result in bin_results.items():
        if 'NOX g/hp-hr' in bin_name:
            ax1.plot('%s\n%.3f' % (bin_name, bin_result), bin_result, '.')
            plotted = True
    ax1.set_ylabel('Bin NOx (g/hp-hr)')
    ax1.set_title('%s\nBin Brake Specific NOx Plot\n%s' % (plot_data_filename, foldername), fontsize=9)
    plt.grid()
    if plotted:
        plt.savefig(figure_path + '13_NOxCO2_binplot', orientation='landscape')

    # plot bin window count
    fig = plt.figure()
    ax1 = plt.gca()
    if options.true_idle_bin:
        ax1.bar('true idle\n%d' % len(true_idle_pts['Tailpipe NOX g']), len(true_idle_pts['Tailpipe NOX g']))
    for bin_name, bin_data in bins.items():
        ax1.bar('%s\n%d' % (bin_name, len(bin_data)), len(bin_data))
    ax1.set_ylabel('Window Count')
    ax1.set_title('%s\nBin Window Count Plot\n%s' % (plot_data_filename, foldername), fontsize=9)
    plt.grid()
    plt.savefig(figure_path + '14_wdw_cnt_binplot', orientation='landscape')

    # plot window window average percent power histogram
    fig = plt.figure()
    ax1 = plt.gca()
    plt.hist(wp_window_df['Avg Power hp'] / engine_power_rating_hp * 100, 100)
    ax1.set_ylabel('Window Count')
    ax1.set_xlabel('Window Avg Pct Power')
    ax1.set_title('%s\nWindow Avg Pct Power Histogram' % plot_data_filename, fontsize=9)
    for cutpoint_frac in options.hp_cutpoints_frac:
        vlineat(ax1, cutpoint_frac * 100, 'r--')
    plt.grid()
    plt.savefig(figure_path + '15_wdw_pwr_hist', orientation='landscape')

    # plot 'true idle' ranked window percentile chart
    if options.true_idle_bin:
        nox = true_idle_pts['NOX g/hp-hr']
        if len(nox) > 0:
            bin_name = 'True Idle'
            nox_pctile = nox.index / nox.index.max() * 100
            fig, ax1, ax2 = fplotyyhg(nox.values, nox_pctile, '', nox.index, '')
            label_xyt(ax1, '%s Window NOx (g/hp-hr)' % bin_name, 'Percentile',
                      '%s\nNOx (g/hp-hr) per Window' % plot_data_filename)
            label_xy(ax2, '%s Window NOx (g/hp-hr)' % bin_name, 'Ranked Window Number')
            lineat(ax1, 95, 'b-')
            lineat(ax1, 70, 'c-')
            nox_gphphr_95 = np.interp(95, nox_pctile, nox.values)
            nox_gphphr_70 = np.interp(70, nox_pctile, nox.values)
            vlineat(ax1, nox_gphphr_95, 'b--')
            vlineat(ax1, nox_gphphr_70, 'c--')
            fig.subplots_adjust(right=0.875)
            ax1.legend(['Percentile/Ranked Window Number', '95th pctile', '70th pctile',
                        '95th pctile NOx %.3f' % nox_gphphr_95,
                        '70th pctile NOx %.3f' % nox_gphphr_70], fontsize=9)
            for pctile in pctile_range:
                bin_results[bin_name + ' %dth pctile NOX g/hp-hr' % pctile] = np.interp(pctile, nox_pctile, nox.values)
            plt.savefig(figure_path + '16_Idle_NOX_gphphr_p_ranked_bin_wdw', orientation='landscape')
        else:
            bin_results[bin_name + ' 70th pctile NOX g/hp-hr'] = np.NaN
            bin_results[bin_name + ' 95th pctile NOX g/hp-hr'] = np.NaN

    # plot ranked window percentile chart for non-'true idle' bins
    fig_num = 17
    for bin_name, bin_data in bins.items():
        nox = bins[bin_name]['NOX g/hp-hr']
        if len(nox) > 0:
            nox_pctile = nox.index / nox.index.max() * 100
            fig, ax1, ax2 = fplotyyhg(nox.values, nox_pctile, '', nox.index, '')
            label_xyt(ax1, '%s Window NOx (g/hp-hr)' % bin_name, 'Percentile',
                      '%s\nNOx (g/hp-hr) per Window' % plot_data_filename)
            label_xy(ax2, '%s Window NOx (g/hp-hr)' % bin_name, 'Ranked Window Number')
            lineat(ax1, 95, 'b-')
            lineat(ax1, 70, 'c-')
            nox_gphphr_95 = np.interp(95, nox_pctile, nox.values)
            nox_gphphr_70 = np.interp(70, nox_pctile, nox.values)
            vlineat(ax1, nox_gphphr_95, 'b--')
            vlineat(ax1, nox_gphphr_70, 'c--')
            fig.subplots_adjust(right=0.875)
            ax1.legend(['Percentile/Ranked Window Number', '95th pctile', '70th pctile',
                        '95th pctile NOx %.3f' % nox_gphphr_95,
                        '70th pctile NOx %.3f' % nox_gphphr_70], fontsize=9)
            for pctile in pctile_range:
                bin_results[bin_name + ' %dth pctile NOX g/hp-hr' % pctile] = np.interp(pctile, nox_pctile, nox.values)

            plt.savefig(figure_path + '%d_NOX_gphphr_p_ranked_bin_wdw' % fig_num, orientation='landscape')
            fig_num = fig_num + 1
        else:
            bin_results[bin_name + ' 70th pctile NOX g/hp-hr'] = np.NaN
            bin_results[bin_name + ' 95th pctile NOX g/hp-hr'] = np.NaN

    # close plots
    plt.close('all')

    # generate results dictionary for this data file
    results_dict = dict()
    results_dict['file'] = plot_data_filename
    results_dict['True Idle NOX Rate g/hr'] = true_idle_nox_gphr
    results_dict['True Idle NOX g/hp-hr'] = true_idle_nox_gphphr
    results_dict['True Idle Window Count'] = len(true_idle_pts)

    for bin_name, bin_result in bin_results.items():
        results_dict[bin_name] = bin_result

    # return dataframe containing dictionary results
    res = pd.DataFrame.from_dict([results_dict])
    res.sort_index(axis='columns', inplace=True)

    return res


# entry point for script when called from command line
if __name__ == '__main__':

    # define command line arguments specific to time-based window processing
    additional_args = [
        "parser.add_argument('--window_length_secs', type=str, help='time-based window length (seconds) [default: 300]', default='300')",
        "parser.add_argument('--window_step_secs', type=str, help='time-based window step (seconds) [default: 300]', default='300')",
        "parser.add_argument('--window_min_secs', type=str, help='time-based window minimum size (seconds) [default: 30]', default='30')",
        "parser.add_argument('--hdiut', action='store_true', help='Data comes from EPA Heavy-Duty In-Use Testing')",
        "parser.add_argument('--idle_speed_thresh_mph', type=str, help='Speed threshhold for idle bin below this speed [default: 1]', default='1')",
        "parser.add_argument('--ftp_co2_gphphr', type=str, help='FTP CO2 g/hp-hr for this engine', default='')",
        "parser.add_argument('--co2_normalization', action='store_true', help='NOx g/hp-hr = NOx_g/CO2_g * CO2_g/FTP_hp-hr')",
        "parser.add_argument('--true_idle_bin', action='store_true', help='Add extra bin for true idle (vehicle speed < idle_speed_thresh_mph mph for entire window)')",
        "parser.add_argument('--hp_cutpoints_pct', type=str, help='Horsepower cutpoints for bin definitions [default: 25]', default='25')",
        "parser.add_argument('--reuse_output_folder', action='store_true', help='Reuse output folder, do not delete prior results')",
    ]

    additional_options = ["options.window_length_secs = args.window_length_secs",
                          "options.window_step_secs = args.window_step_secs",
                          "options.window_min_secs = args.window_min_secs",
                          "options.hdiut = args.hdiut",
                          "options.idle_speed_thresh_mph = args.idle_speed_thresh_mph",
                          "options.ftp_co2_gphphr = args.ftp_co2_gphphr",
                          "options.co2_normalization = args.co2_normalization",
                          "options.true_idle_bin = args.true_idle_bin",
                          "options.hp_cutpoints_pct = args.hp_cutpoints_pct",
                          "options.reuse_output_folder = args.reuse_output_folder",
                          ]

    # process script-specific and common (see cti_common.py) command line options
    options = cti.handle_command_line_options(
        app_description='Time-Based Window Processor, generates window plots for cutpoint analysis',
        additional_args=additional_args,
        additional_options=additional_options)

    options.window_length_secs = float(options.window_length_secs)
    options.window_step_secs = float(options.window_step_secs)
    options.window_min_secs = float(options.window_min_secs)

    # generate descriptor string based on user supplied settings
    descriptor_str = ''

    if options.true_idle_bin:
        descriptor_str = descriptor_str + '_TI'

    descriptor_str = descriptor_str + '_c(' + options.hp_cutpoints_pct + ')'

    if options.co2_normalization:
        descriptor_str = descriptor_str + '_co2n'

    descriptor_str = descriptor_str + '_idl' + options.idle_speed_thresh_mph

    # generate numeric array of bin normalized hp cutpoints
    options.hp_cutpoints_frac = eval('np.array([' + options.hp_cutpoints_pct + '])') / 100

    # generate output folder name based on user supplied settings
    tbw_folder_name = file_io.get_filename(__file__).replace('process_', '') + '_%d_%d%s' % (
    options.window_length_secs, options.window_step_secs, descriptor_str)

    if cti_verbose:
        print('tbw_folder_name = ' + tbw_folder_name )

    # generate fresh timestamp and delete previous output folder unless reusing
    datetime_str = ''
    if not options.reuse_output_folder:
        datetime_str = datetime_str + datetime.now().strftime('%Y%m%d_%H%M%S')
        file_io.delete_folder(options.output_path + os.sep + tbw_folder_name)  # delete folder so there's no old data

    # create results dictionary and dataframes to store bin emissions rates at various percentiles
    # for output summary file
    results_dict = dict()
    output_pctile_range = [100] + pctile_range

    for pctile in output_pctile_range:
        results_dict[pctile] = pd.DataFrame()
        results_dict[pctile]['co2_pct'] = co2_pct_range

    # create results summary dataframe (one row per file)
    results_df = pd.DataFrame()

    # calculate time-base window results for user-selected files
    for data_filename in options.file_list:
        file_results = tbw_processor(data_filename, options.output_path + os.sep + tbw_folder_name, options)
        results_df = results_df.append(file_results, ignore_index=True, sort=False)

    # gather results for box and whisker plots of emissions arates across all selected input files
    print('\nCollating Final Results...\n')

    # plot 'true idle' NOx emissions rates (g/hr)
    fig = plt.figure()
    if options.true_idle_bin:
        if len(results_df['True Idle NOX Rate g/hr'].dropna()) > 0:
            boxplot_dict = plt.boxplot(
                results_df['True Idle NOX Rate g/hr'].dropna(),
                whis=1e6, labels=['True Idle\n%0.3f Avg\n%0.3f Med' % (
                results_df['True Idle NOX Rate g/hr'].mean(), results_df['True Idle NOX Rate g/hr'].median())],
                showmeans=True)
            ax1 = plt.gca()
            ax1.set_ylabel('True Idle NOx Rate(g/hr)')
            ax1.set_title('True Idle NOx Rate Boxplot %s_%d_%d_%d%s' % (
            options.data_profile.regulatory_class, options.window_length_secs, options.window_step_secs,
            options.window_min_secs, descriptor_str), fontsize=9)
            ax1.legend(handles=[boxplot_dict['medians'][0], boxplot_dict['means'][0]], labels=['median', 'mean'])
            plt.grid()
            plt.savefig(options.output_path + os.sep + tbw_folder_name + '/NOx_TruIdle_plt %s_%d_%d_%d%s_%s' % (
            options.data_profile.regulatory_class, options.window_length_secs, options.window_step_secs,
            options.window_min_secs, descriptor_str, datetime_str), orientation='landscape')

    # plot brake-specific NOx emissions rates (g/hp-hr) for non-'true idle' bins
    gphphr_results = {}
    gphphr_labels = []
    # calculate mean and median emissions rates for plot labels for each bin
    for c in results_df.columns:
        if ('gphphr' in c) or ('g/hp-hr' in c) and ('pctile' not in c):
            print('Processing Column %s' % c)
            if len(results_df[c].dropna()) > 0:
                gphphr_results[c] = results_df[c].dropna()
                gphphr_labels.append('%s\n%0.3f Avg\n%0.3f Med' % (c, results_df[c].mean(), results_df[c].median()))

    fig = plt.figure()
    boxplot_dict = plt.boxplot(gphphr_results.values(), whis=1e6, labels=gphphr_labels, showmeans=True)
    ax1 = plt.gca()
    ax1.set_ylabel('Bin NOx (g/hp-hr)')
    ax1.set_title('Bin Brake Specific NOx Boxplot %s_%d_%d%s' % (
    options.data_profile.regulatory_class, options.window_length_secs, options.window_step_secs, descriptor_str),
                  fontsize=9)
    ax1.legend(handles=[boxplot_dict['medians'][0], boxplot_dict['means'][0]], labels=['median', 'mean'])
    plt.grid()
    plt.savefig(options.output_path + os.sep + tbw_folder_name + '/NOx_bin_plt %s_%d_%d%s_%s' % (
    options.data_profile.regulatory_class, options.window_length_secs, options.window_step_secs, descriptor_str,
    datetime_str), orientation='landscape')

    # generate CSV summary file from results dataframe
    csv_summary_filename = options.output_path + os.sep + tbw_folder_name + os.sep + tbw_folder_name + '_results_summary.csv'
    results_df.set_index('file', inplace=True)
    if file_io.file_exists(csv_summary_filename) and options.reuse_output_folder:
        prior_results = pd.read_csv(csv_summary_filename)
        new_results = prior_results.append(results_df)
        new_results.to_csv(csv_summary_filename)
    else:
        results_df.to_csv(csv_summary_filename)
