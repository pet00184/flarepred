import pandas as pd
import numpy as np
import matplotlib
from matplotlib import pyplot as plt
from matplotlib.colors import ListedColormap
import os

PACKAGE_DIR = os.path.dirname(os.path.realpath(__file__))

class PostRunAnalysis:
    
    extra_plot_time = 10 #additional minutes to plot before and after flare
    
    def __init__(self, foldername):
        
        self.foldername = foldername 
        self.xrsa_data = pd.read_csv(f"{PACKAGE_DIR}/SessionSummaries/{foldername}/GOES_XRSA.csv")
        self.xrsb_data = pd.read_csv(f"{PACKAGE_DIR}/SessionSummaries/{foldername}/GOES_XRSB.csv")
        self.summary_times = pd.read_csv(f"{PACKAGE_DIR}/SessionSummaries/{foldername}/timetag_summary.csv", index_col=[0])
        self.launch_analysis_summary = pd.DataFrame(columns = ['XRSA Flare Flux', 'XRSB Flare Flux', 'Time Tags', 'Flare Flux', 'Flare Class', 'Above C5?', 'Max Observed Flux FOXSI', 'Average Observed Flux FOXSI', 'Max Observed Flux HiC', 'Average Observed Flux HiC'])
        
        #adding trigger to cancel times for separating held launches and cancelled triggers
        self.trigger_to_cancel = [pd.Timedelta(pd.Timestamp(self.summary_times['Flare End'].iloc[i]) - pd.Timestamp(self.summary_times['Trigger'].iloc[i])).seconds/60 for i in range(self.summary_times.shape[0])]
        self.summary_times['Trigger to Cancel'] = self.trigger_to_cancel
        
        #making necessary folder(s):
        if not os.path.exists(f"{PACKAGE_DIR}/SessionSummaries/{foldername}/Launches"):
            os.mkdir(f"{PACKAGE_DIR}/SessionSummaries/{self.foldername}/Launches")
        
    def sort_summary(self):
        self.launches = self.summary_times[self.summary_times['Launch'].notna()].reset_index(drop=True)
        self.cancelled_nohold = self.summary_times[(self.summary_times['Launch'].isna()) & (self.summary_times['Trigger to Cancel'] <= 4.0)]
        self.cancelled_hold = self.summary_times[(self.summary_times['Launch'].isna()) & (self.summary_times['Trigger to Cancel'] > 4.0)]
        
        self.total_triggers = self.summary_times.shape[0]
        self.total_launches = self.launches.shape[0]
        self.cancelled_triggers = self.cancelled_nohold.shape[0]
        self.held_launches = self.cancelled_hold.shape[0]
        
    def save_launch_flux(self, i):
        trigger_value = np.where(self.xrsa_data['time_tag'] == self.launches['Trigger'].iloc[i])[0][0]
        flare_end_value = np.where(self.xrsa_data['time_tag'] == self.launches['Flare End'].iloc[i])[0][0]
        ept = self.extra_plot_time
        
        xrsa_data = np.array(self.xrsa_data['flux'][trigger_value-ept:flare_end_value+ept])
        self.launch_analysis_summary.loc[i, 'XRSA Flare Flux'] = xrsa_data
        xrsb_data = np.array(self.xrsb_data['flux'][trigger_value-ept:flare_end_value+ept])
        self.launch_analysis_summary.loc[i, 'XRSB Flare Flux'] = xrsb_data
        time_tags = np.array(self.xrsa_data['time_tag'][trigger_value-ept:flare_end_value+ept])
        self.launch_analysis_summary.loc[i, 'Time Tags'] = time_tags
            
    def calculate_flare_class(self, i):
        max_flux = np.max(self.launch_analysis_summary.loc[i, 'XRSB Flare Flux'])
        self.launch_analysis_summary.loc[i, 'Flare Flux'] = max_flux
        #checking for C5 or above:
        if max_flux > 5e-6:
            self.launch_analysis_summary.loc[i, 'Above C5?'] = True
        else: 
            self.launch_analysis_summary.loc[i, 'Above C5?'] = False
        #checking the flare class
        if 1e-7 >= max_flux > 1e-8:
            self.launch_analysis_summary.loc[i, 'Flare Class'] = 'A'
        elif 1e-6 >= max_flux > 1e-7:
            self.launch_analysis_summary.loc[i, 'Flare Class'] = 'B'
        elif 1e-5 >= max_flux > 1e-6:
            self.launch_analysis_summary.loc[i, 'Flare Class'] = 'C'
        elif 1e-4 >= max_flux > 1e-5:
            self.launch_analysis_summary.loc[i, 'Flare Class'] = 'M'
        elif 1e-3 >= max_flux >1e-4:
            self.launch_analysis_summary.loc[i, 'Flare Class'] = 'X'
        elif max_flux > 1e-3:
            self.launch_analysis_summary.loc[i, 'Flare Class'] = 'X10'
            
    def calculate_FOXSI_stats(self, i):
        max_foxsi = np.max(self.launch_analysis_summary.loc[i, 'XRSB Flare Flux'][9:15])
        ave_foxsi = np.sum(self.launch_analysis_summary.loc[i, 'XRSB Flare Flux'][9:15])/6
        self.launch_analysis_summary.loc[i, 'Max Observed Flux FOXSI'] = max_foxsi
        self.launch_analysis_summary.loc[i, 'Average Observed Flux FOXSI'] = ave_foxsi
        
    def calculate_HiC_stats(self, i):
        max_hic = np.max(self.launch_analysis_summary.loc[i, 'XRSB Flare Flux'][11:17])
        ave_hic = np.sum(self.launch_analysis_summary.loc[i, 'XRSB Flare Flux'][11:17])/6
        self.launch_analysis_summary.loc[i, 'Max Observed Flux HiC'] = max_hic
        self.launch_analysis_summary.loc[i, 'Average Observed Flux HiC'] = ave_hic
        
    def do_launch_analysis(self):
        if not self.launches.shape[0] == 0:
            for i in range(self.launches.shape[0]):
                self.save_launch_flux(i)
                self.calculate_flare_class(i)
                self.calculate_FOXSI_stats(i)
                self.calculate_HiC_stats(i)
                self.plot_launches(i)
        else: print('No launches to plot in this run.')
            
    def plot_launches(self, i):
        cmap_goes = ListedColormap(['blue', 'red'], N=2)
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
        ax.plot(timestamps, xrsb, c='b')
        ax.plot(timestamps, xrsa, c='r')
        #plotting launch and observation times: 
        trigger = pd.Timestamp(self.launches.loc[i, 'Trigger'])
        foxsi_launch = pd.Timestamp(self.launches.loc[i, 'Launch'])
        hic_launch = pd.Timestamp(self.launches.loc[i, 'FOXSI Obs Start'])
        foxsi_obs_window = [pd.Timestamp(self.launches.loc[i, 'FOXSI Obs Start']), pd.Timestamp(self.launches.loc[i, 'FOXSI Obs End'])]
        hic_obs_window = [pd.Timestamp(self.launches.loc[i, 'HiC Obs Start']), pd.Timestamp(self.launches.loc[i, 'HiC Obs End'])]
        ax.vlines(trigger, 0, 1e-3, color='k', lw=2, ls='-', label='Trigger')
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
            
        
    def write_text_summary(self):
        if not self.summary_times.shape[0]==0:
            date = pd.Timestamp(self.xrsa_data['time_tag'].iloc[0]).strftime('%Y-%m-%d')
            with open(f"{PACKAGE_DIR}/SessionSummaries/{self.foldername}/TextSummary_{date}.txt", 'w') as f:
                f.write('Real-time Flare Run Summary: \n')
                f.write(f"Run Time: {self.xrsa_data['time_tag'].iloc[0]} - {self.xrsa_data['time_tag'].iloc[-1]} ({pd.Timedelta(pd.Timestamp(self.xrsa_data['time_tag'].iloc[-1]) - pd.Timestamp(self.xrsa_data['time_tag'].iloc[0]))}) \n \n")
                f.write(f"Total Triggers: {self.total_triggers} \n")
                f.write(f"Launches: {self.total_launches}  ({(self.total_launches/self.total_triggers)*100}%) \n")
                f.write(f"Triggers Cancelled before Launch Called: {self.cancelled_triggers} ({(self.cancelled_triggers/self.total_triggers)*100}%) \n")
                f.write(f"Triggers Cancelled after Launch Called (Hold Launch): {self.held_launches} ({(self.held_launches/self.total_triggers)*100}%) \n \n")
                f.write(f"Observation Summary of Launches: \n")
                for i in range(self.launches.shape[0]):
                    f.write(f"Launch {i}: {self.launch_analysis_summary.loc[i, 'Flare Class']}-Class \n")
                    f.write(f"Maximum Flux: {self.launch_analysis_summary.loc[i, 'Flare Flux']:.2e} \n")
                    f.write(f"Maximum Flux Observed (FOXSI): {self.launch_analysis_summary.loc[i, 'Max Observed Flux FOXSI']:.2e} \n")
                    f.write(f"Maximum Flux Observed (HiC): {self.launch_analysis_summary.loc[i, 'Max Observed Flux HiC']:.2e} \n \n")
        else: print('No triggers- no TextSummary saved.')
            
        
        
# def main():
#     pra = PostRunAnalysis('ObservationSummary/GOES_XRSA.csv', 'ObservationSummary/GOES_XRSB.csv', 'ObservationSummary/historical_summary.csv')
#     pra.sort_summary()
#     pra.do_flare_analysis()
#     pra.write_text_summary()
#
# if __name__ == '__main__':
#     main()