# USEPA_CTI_TBW
US EPA Clean Truck Initiative Time Based Window Code

Example Command Line Usage
-------------

Default options, using data from sample_data folder:

    python cti_process_TBW.py --source_path sample_data --hdiut

Overlapping 300-second windows with power bins based on rate power CO2 normalization with a 25% window average power bin cutoff and a < 1 MPH true idle bin

    python cti_process_TBW.py --source_path sample_data --hdiut --window_step_secs 1 --window_length_secs 300 --co2_normalization --idle_speed_thresh_mph 1 --true_idle_bin --hp_cutpoints_pct 25           
 
Overlapping 180-second windows with power bins based on rate power CO2 normalization with 8% and 25% window average power bin cutoffs

    python cti_process_TBW.py --source_path sample_data --hdiut --window_step_secs 1 --window_length_secs 180 --co2_normalization --hp_cutpoints_pct 8,25           

For non-overlapping windows, set the window_step_secs equal to the window_length_secs

    usage: cti_process_TBW.py [-h] [--source_path SOURCE_PATH]
                          [--output_path OUTPUT_PATH] [--profile PROFILE]
                          [--verbose] [--include INCLUDE] [--exclude EXCLUDE]
                          [--window_length_secs WINDOW_LENGTH_SECS]
                          [--window_step_secs WINDOW_STEP_SECS]
                          [--window_min_secs WINDOW_MIN_SECS] [--hdiut]
                          [--idle_speed_thresh_mph IDLE_SPEED_THRESH_MPH]
                          [--ftp_co2_gphphr FTP_CO2_GPHPHR]
                          [--co2_normalization] [--true_idle_bin]
                          [--hp_cutpoints_pct HP_CUTPOINTS_PCT]
                          [--reuse_output_folder]

    Time-Based Window Processor, generates window plots for cutpoint analysis
    
    optional arguments:
      -h, --help            show this help message and exit
      
      --source_path SOURCE_PATH
                            Path to folder containing files to process [default: .]]
                            
      --output_path OUTPUT_PATH
                            Path to folder for output results [default: .\output]
                            
      --profile PROFILE     Path and filename to a cti_data_source_profile
                            spreadsheet or "prompt" to launch file browser
                            [default: cti_data_source_profile.xlsx]
                            
      --verbose             Enable verbose messages and file outputs
      
      --include INCLUDE     File filter, files to include/accept [default: *.csv]
      
      --exclude EXCLUDE     File filter, files to exclude/reject [default: *calcs.csv]
      
      --window_length_secs WINDOW_LENGTH_SECS
                            time-based window length (seconds) [default: 300]
                            
      --window_step_secs WINDOW_STEP_SECS
                            time-based window step (seconds) [default: 300]
                            
      --window_min_secs WINDOW_MIN_SECS
                            time-based window minimum size (seconds) [default: 30]
                            
      --hdiut               Data comes from EPA Heavy-Duty In-Use Testing
      
      --idle_speed_thresh_mph IDLE_SPEED_THRESH_MPH
                            Speed threshhold for idle bin below this speed
                            [default: 1]
                            
      --ftp_co2_gphphr FTP_CO2_GPHPHR
                            FTP CO2 g/hp-hr for this engine
                            
      --co2_normalization   NOx g/hp-hr = NOx_g/CO2_g * CO2_g/FTP_hp-hr
      
      --true_idle_bin       Add extra bin for true idle (vehicle speed < idle_speed_thresh_mph for
                            entire window)
                            
      --hp_cutpoints_pct HP_CUTPOINTS_PCT
                            Horsepower cutpoints for bin definitions [default: 25]
                            
      --reuse_output_folder
                            Reuse output folder, do not delete prior results
                            