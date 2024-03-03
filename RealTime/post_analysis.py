import pandas as pd
import numpy as np
import matplotlib
from matplotlib import pyplot as plt
from matplotlib.colors import ListedColormap
import os
import flare_conditions as fc

PACKAGE_DIR = os.path.dirname(os.path.realpath(__file__))

class PostRunAnalysis:
    
    extra_plot_time = 10 #additional minutes to plot before and after flare
    
    def __init__(self, foldername):
        
        self.foldername = foldername 
        self.goes_data = pd.read_csv(f"{PACKAGE_DIR}/SessionSummaries/{foldername}/GOES.csv")
        self.summary_times = pd.read_csv(f"{PACKAGE_DIR}/SessionSummaries/{foldername}/timetag_summary.csv", index_col=[0])
        self.launch_analysis_summary = pd.DataFrame(columns = ['XRSA Flare Flux', 'XRSB Flare Flux', 'Time Tags', 'Flare Flux', 'Flare Class', 'Above C5?', 'Max Observed Flux FOXSI', 'Average Observed Flux FOXSI', 'Max Observed Flux HiC', 'Average Observed Flux HiC'])
        self.hold_analysis_summary = pd.DataFrame(columns = ['XRSA Flare Flux', 'XRSB Flare Flux', 'Time Tags', 'Flare Flux', 'Flare Class', 'Above C5?'])
        self.triggers_only_analysis_summary = pd.DataFrame(columns = ['XRSA Flare Flux', 'XRSB Flare Flux', 'Time Tags', 'Flare Flux', 'Flare Class', 'Above C5?'])
        
        #making necessary folder(s):
        os.makedirs(f"{PACKAGE_DIR}/SessionSummaries/{self.foldername}/Launches", exist_ok=True)
        os.makedirs(f"{PACKAGE_DIR}/SessionSummaries/{self.foldername}/Holds", exist_ok=True)
        os.makedirs(f"{PACKAGE_DIR}/SessionSummaries/{self.foldername}/TriggersOnly", exist_ok=True)
        
    def sort_summary(self):
        ''' Sorting out the triggers between triggers that weren't acted upon, triggers that resulted in a hold, and 
        triggers resulting in a launch.
        '''
        self.launches = self.summary_times[self.summary_times['Launch'].notna()].reset_index(drop=True)     
        self.holds = self.summary_times[self.summary_times['Hold'].notna()].reset_index(drop=True)
        self.triggers_only = self.summary_times[(self.summary_times['Countdown Initiated'].isna()) & (self.summary_times['Hold'].isna()) & (self.summary_times['Launch'].isna())].reset_index(drop=True)
        
        self.total_triggers = self.summary_times.shape[0]
        self.total_launches = self.launches.shape[0]
        self.total_triggers_only = self.triggers_only.shape[0]
        self.total_holds = self.holds.shape[0]
        
    def calculate_flare_class(self, i, summary_type):
        max_flux = np.max(summary_type.loc[i, 'XRSB Flare Flux'])
        summary_type.loc[i, 'Flare Flux'] = max_flux
        #checking for C5 or above:
        if max_flux > 5e-6:
            summary_type.loc[i, 'Above C5?'] = True
        else: 
            summary_type.loc[i, 'Above C5?'] = False
        #checking the flare class
        if 1e-7 >= max_flux > 1e-8:
            summary_type.loc[i, 'Flare Class'] = 'A'
        elif 1e-6 >= max_flux > 1e-7:
            summary_type.loc[i, 'Flare Class'] = 'B'
        elif 1e-5 >= max_flux > 1e-6:
            summary_type.loc[i, 'Flare Class'] = 'C'
        elif 1e-4 >= max_flux > 1e-5:
            summary_type.loc[i, 'Flare Class'] = 'M'
        elif 1e-3 >= max_flux >1e-4:
            summary_type.loc[i, 'Flare Class'] = 'X'
        elif max_flux > 1e-3:
            summary_type.loc[i, 'Flare Class'] = 'X10'
        
############################ LAUNCH ANALYSIS ####################################################################
        
    def save_launch_flux(self, i):
        trigger_value = np.where(self.goes_data['time_tag'] == self.launches['Realtime Trigger'].iloc[i])[0][0]
        if self.launches['Flare End'].iloc[i].isna():
            flare_end_value = np.where(self.goes_data['time_tag'] == self.launches['HiC Obs End'].iloc[i] + timedelta(minutes=30))[0][0]
        else:
            flare_end_value = np.where(self.goes_data['time_tag'] == self.launches['Flare End'].iloc[i])[0][0]
        ept = self.extra_plot_time
        
        xrsa_data = np.array(self.goes_data['xrsa'][trigger_value-ept:flare_end_value+ept])
        self.launch_analysis_summary.loc[i, 'XRSA Flare Flux'] = xrsa_data
        xrsb_data = np.array(self.goes_data['xrsb'][trigger_value-ept:flare_end_value+ept])
        self.launch_analysis_summary.loc[i, 'XRSB Flare Flux'] = xrsb_data
        time_tags = np.array(self.goes_data['time_tag'][trigger_value-ept:flare_end_value+ept])
        self.launch_analysis_summary.loc[i, 'Time Tags'] = time_tags
            
    def calculate_FOXSI_stats(self, i):
        ''' Calculates the maximum and average flux observed by FOXSI.'''
        foxsi_start_time = np.where(self.launch_analysis_summary.loc[i, 'Time Tags'] == self.launches.loc[i, 'FOXSI Obs Start'])[0][0]
        foxsi_end_time = np.where(self.launch_analysis_summary.loc[i, 'Time Tags'] == self.launches.loc[i, 'FOXSI Obs End'])[0][0]
        max_foxsi = np.max(self.launch_analysis_summary.loc[i, 'XRSB Flare Flux'][foxsi_start_time:foxsi_end_time])
        ave_foxsi = np.sum(self.launch_analysis_summary.loc[i, 'XRSB Flare Flux'][foxsi_start_time:foxsi_end_time])/6
        self.launch_analysis_summary.loc[i, 'Max Observed Flux FOXSI'] = max_foxsi
        self.launch_analysis_summary.loc[i, 'Average Observed Flux FOXSI'] = ave_foxsi
        
    def calculate_HiC_stats(self, i):
        ''' Calculates the maximum and average flux observed by HiC.'''
        hic_start_time = np.where(self.launch_analysis_summary.loc[i, 'Time Tags'] == self.launches.loc[i, 'HiC Obs Start'])[0][0]
        hic_end_time = np.where(self.launch_analysis_summary.loc[i, 'Time Tags'] == self.launches.loc[i, 'HiC Obs End'])[0][0]
        max_hic = np.max(self.launch_analysis_summary.loc[i, 'XRSB Flare Flux'][hic_start_time:hic_end_time])
        ave_hic = np.sum(self.launch_analysis_summary.loc[i, 'XRSB Flare Flux'][hic_start_time:hic_end_time])/6
        self.launch_analysis_summary.loc[i, 'Max Observed Flux HiC'] = max_hic
        self.launch_analysis_summary.loc[i, 'Average Observed Flux HiC'] = ave_hic
        
    def do_launch_analysis(self):
        ''' Calculates observation summaries and plots for all launches.'''
        if not self.launches.shape[0] == 0:
            for i in range(self.launches.shape[0]):
                self.save_launch_flux(i)
                self.calculate_flare_class(i, self.launch_analysis_summary)
                self.calculate_FOXSI_stats(i)
                self.calculate_HiC_stats(i)
                self.plot_launches(i)
            
    def plot_launches(self, i):
        plt.rcParams['axes.titlesize'] = 16
        plt.rcParams['axes.labelsize'] = 14
        plt.rcParams['xtick.labelsize'] = 14
        plt.rcParams['ytick.labelsize'] = 14
        plt.rcParams['grid.linestyle'] = ':'
        
        fig = plt.figure(figsize=(12,8))
        ax = fig.gca()
        ax.cla()
        plt.grid(True,which='major',axis='both',linestyle=':')
        #plotting data
        xrsb = self.launch_analysis_summary.loc[i, 'XRSB Flare Flux']
        xrsa = self.launch_analysis_summary.loc[i, 'XRSA Flare Flux']
        timestamps = [pd.Timestamp(time) for time in self.launch_analysis_summary.loc[i, 'Time Tags']]
        ax.plot(timestamps, xrsb, c='r')
        ax.plot(timestamps, xrsa, c='b')
        #plotting launch and observation times: 
        trigger = pd.Timestamp(self.launches.loc[i, 'Realtime Trigger'])
        data_trigger = pd.Timestamp(self.launches.loc[i, 'Trigger'])
        foxsi_launch = pd.Timestamp(self.launches.loc[i, 'Launch'])
        hic_launch = pd.Timestamp(self.launches.loc[i, 'FOXSI Obs Start'])
        foxsi_obs_window = [pd.Timestamp(self.launches.loc[i, 'FOXSI Obs Start']), pd.Timestamp(self.launches.loc[i, 'FOXSI Obs End'])]
        hic_obs_window = [pd.Timestamp(self.launches.loc[i, 'HiC Obs Start']), pd.Timestamp(self.launches.loc[i, 'HiC Obs End'])]
        ax.vlines(data_trigger, 0, 1e-3, color='gray', lw=2, ls='--', label='Data Trigger')
        ax.vlines(trigger, 0, 1e-3, color='k', lw=2, ls='-', label='Realtime Trigger')
        ax.vlines(countdown_initiated, 0, 1e-3, color='green', lw=2, ls='--', label='Countdown Initiated')
        ax.vlines(foxsi_launch, 0, 1e-3, color='orange', lw=2, ls='-', label='FOXSI Launch')
        ax.vlines(hic_launch, 0, 1e-3, color='purple', lw=2, ls='-', label='HiC Launch')
        ax.axvspan(foxsi_obs_window[0], foxsi_obs_window[1], alpha=0.3, color='orange', label='FOXSI Observation')
        ax.axvspan(hic_obs_window[0], hic_obs_window[1], alpha=0.3, color='purple', label='HiC Observation')
        #format y axis:
        ax.set_yscale('log')
        ax.set_ylim(1e-8, 1e-3)
        ax.set_ylabel(f'GOES Flux [W m$^{{-2}}$]',)
        #add flare classification:
        ax2 = ax.twinx()
        ax2.set_yscale("log")
        ax2.set_ylim(1e-8, 1e-3)
        ax2.set_yticks((1e-8, 1e-7, 1e-6, 1e-5, 1e-4, 1e-3))
        ax2.set_yticklabels(('A', 'B', 'C', 'M', 'X', 'X10'),)
        #trying to get dates working:
        formatter = matplotlib.dates.DateFormatter('%H:%M')
        ax.xaxis.set_major_formatter(formatter)
        ax.set_xlabel(timestamps[0].strftime('%Y-%m-%d'))
        #save plot
        ax.set_title(f"GOES XRS \n Max Observed Flux: {max(self.launch_analysis_summary.loc[i, 'Max Observed Flux FOXSI'], self.launch_analysis_summary.loc[i, 'Max Observed Flux HiC']):.1e}")
        ax.legend(loc='upper right')
        plt.tight_layout()
        plt.savefig(f"{PACKAGE_DIR}/SessionSummaries/{self.foldername}/Launches/Launch{i}_{timestamps[0].strftime('%Y-%m-%d')}.png")

#################### HOLD ANALYSIS #######################################################################      
    def save_hold_flux(self, i):
        trigger_value = np.where(self.goes_data['time_tag'] == self.holds['Realtime Trigger'].iloc[i])[0][0]
        if self.holds['Flare End'].iloc[i].isna():
            flare_end_value = np.where(self.goes_data['time_tag'] == self.holds['HiC Obs End'].iloc[i] + timedelta(minutes=30))[0][0]
        else:
            flare_end_value = np.where(self.goes_data['time_tag'] == self.holds['Flare End'].iloc[i])[0][0]
        ept = self.extra_plot_time
    
        xrsa_data = np.array(self.goes_data['xrsa'][trigger_value-ept:flare_end_value+ept])
        self.hold_analysis_summary.loc[i, 'XRSA Flare Flux'] = xrsa_data
        xrsb_data = np.array(self.goes_data['xrsb'][trigger_value-ept:flare_end_value+ept])
        self.hold_analysis_summary.loc[i, 'XRSB Flare Flux'] = xrsb_data
        time_tags = np.array(self.goes_data['time_tag'][trigger_value-ept:flare_end_value+ept])
        self.hold_analysis_summary.loc[i, 'Time Tags'] = time_tags
        
    def do_hold_analysis(self):
        ''' Calculates observation summaries and plots for all launches.'''
        if not self.holds.shape[0] == 0:
            for i in range(self.holds.shape[0]):
                self.save_hold_flux(i)
                self.calculate_flare_class(i, self.hold_analysis_summary)
                self.plot_holds(i)  
                
    def plot_holds(self, i):
        plt.rcParams['axes.titlesize'] = 16
        plt.rcParams['axes.labelsize'] = 14
        plt.rcParams['xtick.labelsize'] = 14
        plt.rcParams['ytick.labelsize'] = 14
        plt.rcParams['grid.linestyle'] = ':'
        
        fig = plt.figure(figsize=(12,8))
        ax = fig.gca()
        ax.cla()
        plt.grid(True,which='major',axis='both',linestyle=':')
        #plotting data
        xrsb = self.hold_analysis_summary.loc[i, 'XRSB Flare Flux']
        xrsa = self.hold_analysis_summary.loc[i, 'XRSA Flare Flux']
        timestamps = [pd.Timestamp(time) for time in self.hold_analysis_summary.loc[i, 'Time Tags']]
        ax.plot(timestamps, xrsb, c='r')
        ax.plot(timestamps, xrsa, c='b')
        #plotting launch and observation times: 
        trigger = pd.Timestamp(self.holds.loc[i, 'Realtime Trigger'])
        data_trigger = pd.Timestamp(self.holds.loc[i, 'Trigger'])
        countdown_start = pd.Timestamp(self.holds.loc[i, 'Countdown Initiated'])
        hold_time = pd.Timestamp(self.holds.loc[i, 'Hold'])
        ax.vlines(data_trigger, 0, 1e-3, color='gray', lw=2, ls='--', label='Data Trigger')
        ax.vlines(trigger, 0, 1e-3, color='k', lw=2, ls='-', label='Realtime Trigger')
        ax.vlines(countdown_start, 0, 1e-3, color='red', lw=2, ls='--', label='Countdown Initiated')
        ax.vlines(hold_time, 0, 1e-3, color='red', lw=2, ls='-', label='Launch Held')
        #format y axis:
        ax.set_yscale('log')
        ax.set_ylim(1e-8, 1e-3)
        ax.set_ylabel(f'GOES Flux [W m$^{{-2}}$]',)
        #add flare classification:
        ax2 = ax.twinx()
        ax2.set_yscale("log")
        ax2.set_ylim(1e-8, 1e-3)
        ax2.set_yticks((1e-8, 1e-7, 1e-6, 1e-5, 1e-4, 1e-3))
        ax2.set_yticklabels(('A', 'B', 'C', 'M', 'X', 'X10'),)
        #trying to get dates working:
        formatter = matplotlib.dates.DateFormatter('%H:%M')
        ax.xaxis.set_major_formatter(formatter)
        ax.set_xlabel(timestamps[0].strftime('%Y-%m-%d'))
        #save plot
        ax.set_title(f"GOES XRS \n Flare Class: {self.hold_summary_analysis['Flare Class'].iloc[i]}")
        ax.legend(loc='upper right')
        plt.tight_layout()
        plt.savefig(f"{PACKAGE_DIR}/SessionSummaries/{self.foldername}/Holds/Hold{i}_{timestamps[0].strftime('%Y-%m-%d')}.png")
        
##################### TRIGGERS ONLY ##################################################################

    def save_triggers_only_flux(self, i):
        trigger_value = np.where(self.goes_data['time_tag'] == self.triggers_only['Realtime Trigger'].iloc[i])[0][0]
        if self.triggers_only['Flare End'].iloc[i].isna():
            flare_end_value = np.where(self.goes_data['time_tag'] == self.triggers_only['HiC Obs End'].iloc[i] + timedelta(minutes=30))[0][0]
        else:
            flare_end_value = np.where(self.goes_data['time_tag'] == self.triggers_only['Flare End'].iloc[i])[0][0]
        ept = self.extra_plot_time
    
        xrsa_data = np.array(self.goes_data['xrsa'][trigger_value-ept:flare_end_value+ept])
        self.triggers_only_analysis_summary.loc[i, 'XRSA Flare Flux'] = xrsa_data
        xrsb_data = np.array(self.goes_data['xrsb'][trigger_value-ept:flare_end_value+ept])
        self.triggers_only_analysis_summary.loc[i, 'XRSB Flare Flux'] = xrsb_data
        time_tags = np.array(self.goes_data['time_tag'][trigger_value-ept:flare_end_value+ept])
        self.triggers_onlyanalysis_summary.loc[i, 'Time Tags'] = time_tags
        
    def do_triggers_only_analysis(self):
        ''' Calculates observation summaries and plots for all launches.'''
        if not self.triggers_only.shape[0] == 0:
            for i in range(self.triggers_only.shape[0]):
                self.save_triggers_only_flux(i)
                self.calculate_flare_class(i, self.triggers_only_analysis_summary)
                self.plot_triggers_only(i)
        
    def plot_triggers_only(self, i):
        plt.rcParams['axes.titlesize'] = 16
        plt.rcParams['axes.labelsize'] = 14
        plt.rcParams['xtick.labelsize'] = 14
        plt.rcParams['ytick.labelsize'] = 14
        plt.rcParams['grid.linestyle'] = ':'
        
        fig = plt.figure(figsize=(12,8))
        ax = fig.gca()
        ax.cla()
        plt.grid(True,which='major',axis='both',linestyle=':')
        #plotting data
        xrsb = self.triggers_only_analysis_summary.loc[i, 'XRSB Flare Flux']
        xrsa = self.triggers_only_analysis_summary.loc[i, 'XRSA Flare Flux']
        timestamps = [pd.Timestamp(time) for time in self.triggers_only_analysis_summary.loc[i, 'Time Tags']]
        ax.plot(timestamps, xrsb, c='r')
        ax.plot(timestamps, xrsa, c='b')
        #plotting launch and observation times: 
        trigger = pd.Timestamp(self.triggers_only.loc[i, 'Realtime Trigger'])
        data_trigger = pd.Timestamp(self.triggers_only.loc[i, 'Trigger'])
        ax.vlines(data_trigger, 0, 1e-3, color='gray', lw=2, ls='--', label='Data Trigger')
        ax.vlines(trigger, 0, 1e-3, color='k', lw=2, ls='-', label='Realtime Trigger')
        #format y axis:
        ax.set_yscale('log')
        ax.set_ylim(1e-8, 1e-3)
        ax.set_ylabel(f'GOES Flux [W m$^{{-2}}$]',)
        #add flare classification:
        ax2 = ax.twinx()
        ax2.set_yscale("log")
        ax2.set_ylim(1e-8, 1e-3)
        ax2.set_yticks((1e-8, 1e-7, 1e-6, 1e-5, 1e-4, 1e-3))
        ax2.set_yticklabels(('A', 'B', 'C', 'M', 'X', 'X10'),)
        #trying to get dates working:
        formatter = matplotlib.dates.DateFormatter('%H:%M')
        ax.xaxis.set_major_formatter(formatter)
        ax.set_xlabel(timestamps[0].strftime('%Y-%m-%d'))
        #save plot
        ax.set_title(f"GOES XRS \n Flare Class: {self.triggers_only_summary_analysis['Flare Class'].iloc[i]}")
        ax.legend(loc='upper right')
        plt.tight_layout()
        plt.savefig(f"{PACKAGE_DIR}/SessionSummaries/{self.foldername}/TriggersOnly/TriggerOnly{i}_{timestamps[0].strftime('%Y-%m-%d')}.png")
        
################### TEXT SUMMARY #################################################################    
        
    def write_text_summary(self):
        date = pd.Timestamp(self.goes_data['time_tag'].iloc[0]).strftime('%Y-%m-%d')
        if not self.summary_times.shape[0]==0:
            with open(f"{PACKAGE_DIR}/SessionSummaries/{self.foldername}/TextSummary_{date}.txt", 'w') as f:
                f.write('Real-time Flare Run Summary: \n')
                f.write(f"Run Time: {self.goes_data['time_tag'].iloc[30]} - {self.goes_data['time_tag'].iloc[-1]} ({pd.Timedelta(pd.Timestamp(self.goes_data['time_tag'].iloc[-1]) - pd.Timestamp(self.goes_data['time_tag'].iloc[0]))}) \n")
                f.write(f"Trigger Conditions: \n")
                for keys in fc.FLARE_ALERT_MAP.keys():
                    f.write("\t")
                    f.write(keys.replace('<sup>', '^').replace('</sup>', ''))
                    f.write("\n")
                f.write("\n")
                f.write(f"Total Triggers: {self.total_triggers} \n")
                f.write(f"Launches: {self.total_launches}  ({(self.total_launches/self.total_triggers)*100:.2f}%) \n")
                f.write(f"Holds: {self.total_holds} ({(self.total_holds/self.total_triggers)*100:.2f}%) \n")
                f.write(f"No Countdown Started for Trigger: {self.total_triggers_only} ({(self.total_triggers_only/self.total_triggers)*100:.2f}%) \n \n")
                f.write(f"Observation Summary of Launches: \n")
                for i in range(self.launches.shape[0]):
                    f.write(f"Launch {i}: \n")
                    f.write(f"Trigger Realtime: {self.launches.loc[i, 'Realtime Trigger']} \n")
                    f.write(f"Countdown Initiated Time: {self.launches.loc[i, 'Countdown Initiated']} \n")
                    f.write(f"Launch Time: {self.launches.loc[i, 'Launch']} \n")
                    f.write(f"Flare Class: {self.launch_analysis_summary.loc[i, 'Flare Class']}-Class \n")
                    f.write(f"Maximum Flux: {self.launch_analysis_summary.loc[i, 'Flare Flux']:.2e} \n")
                    f.write(f"Maximum Flux Observed (FOXSI): {self.launch_analysis_summary.loc[i, 'Max Observed Flux FOXSI']:.2e} \n")
                    f.write(f"Maximum Flux Observed (HiC): {self.launch_analysis_summary.loc[i, 'Max Observed Flux HiC']:.2e} \n \n")
                f.write(f"Summary of Holds: \n")
                for i in range(self.holds.shape[0]):
                    f.write(f"Hold {i}: \n")
                    f.write(f"Trigger Realtime: {self.holds.loc[i, 'Realtime Trigger']} \n")
                    f.write(f"Countdown Initiated Time: {self.holds.loc[i, 'Countdown Initiated']} \n")
                    f.write(f"Hold Time: {self.holds.loc[i, 'Hold']} \n")
                    f.write(f"Flare Class: {self.hold_analysis_summary.loc[i, 'Flare Class']}-Class \n")
                    f.write(f"Maximum Flux: {self.hold_analysis_summary.loc[i, 'Flare Flux']:.2e} \n \n")
                f.write("Summary of Triggers Only (No Countdown): \n")
                for i in range(self.triggers_only.shape[0]):
                    f.write(f"Trigger Only {i}: \n")
                    f.write(f"Trigger Realtime: {self.triggers_only.loc[i, 'Realtime Trigger']} \n")
                    f.write(f"Flare Class: {self.triggers_only_analysis_summary.loc[i, 'Flare Class']}-Class \n")
                    f.write(f"Maximum Flux: {self.triggers_only_analysis_summary.loc[i, 'Flare Flux']:.2e} \n \n")
        else: 
            with open(f"{PACKAGE_DIR}/SessionSummaries/{self.foldername}/TextSummary_{date}.txt", 'w') as f:
                f.write('Real-time Flare Run Summary: \n')
                f.write(f"Run Time: {self.goes_data['time_tag'].iloc[30]} - {self.goes_data['time_tag'].iloc[-1]} ({pd.Timedelta(pd.Timestamp(self.goes_data['time_tag'].iloc[-1]) - pd.Timestamp(self.goes_data['time_tag'].iloc[30]))}) \n")
                f.write(f"Trigger Conditions: \n")
                for keys in fc.FLARE_ALERT_MAP.keys():
                    f.write("\t")
                    f.write(keys.replace('<sup>', '^').replace('</sup>', ''))
                    f.write('\n')
                f.write("\n")
                f.write("No triggers during this run.")
        
                   
        
# def main():
#     pra = PostRunAnalysis('ObservationSummary/GOES_XRSA.csv', 'ObservationSummary/GOES_XRSB.csv', 'ObservationSummary/historical_summary.csv')
#     pra.sort_summary()
#     pra.do_flare_analysis()
#     pra.write_text_summary()
#
# if __name__ == '__main__':
#     main()