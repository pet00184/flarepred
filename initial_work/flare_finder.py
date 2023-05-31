# importing necessary packages:
import warnings
import datetime
import math

from matplotlib import pyplot as plt
import matplotlib
from matplotlib.colors import ListedColormap
import numpy as np
import astropy.time
import astropy.units as u
import astropy.table
from sunpy.time import parse_time
from sunpy import timeseries
from sunpy.net import Fido, attrs as a
from scipy.signal import savgol_filter
from scipy.interpolate import interp1d
import h5py
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
import os
import pandas as pd

class FlareTriggerFinder:   
    'docstring here :-)'
    
    FOXSI_LAUNCH = 5
    FOXSI_OBS_START = FOXSI_LAUNCH + 2
    FOXSI_OBS_END = FOXSI_OBS_START + 6
    
    HIC_LAUNCH = 7
    HIC_OBS_START = HIC_LAUNCH + 2
    HIC_OBS_END = HIC_OBS_START  + 6
    
    def __init__(self, goesxrs_files: str):
        self.goesxrs_files = goesxrs_files
        self.goes_data = None
        self.flare_bounds = list()
        self.summary_stats = {
            'foxsi': list(),
            'hi-c': list()
        }
        
    def load_data(self):
        self.goes_data = timeseries.TimeSeries(files, concatenate=True).to_table()
        #self.goes_data['date'] = astropy.time.Time(self.goes_data['date']) 
        #self.goes_data['time'] = (self.goes_data['date'] - self.goes_data['date'][0]).to('s')
        
    def find_starts_ends(self, start_cond, end_cond):
        flare_occuring = False
        for i in range(len(self.goes_data['xrsb'])):
            if flare_occuring and end_cond(self.goes_data, i): 
                self.flare_bounds[-1].append(i) 
                flare_occuring = False
            if not flare_occuring and start_cond(self.goes_data, i):
                self.flare_bounds.append([i])
                flare_occuring = True
        
    def implement_hold_conditions(self): 
        foxsi_hold_capability = self.FOXSI_LAUNCH - 1
        i = 0
        while i < len(self.flare_bounds): 
            start, end = self.flare_bounds[i]
            magnitude_hold = magnitude_hold_condition(self.goes_data, start, foxsi_hold_capability)
            duration_hold = end - start < foxsi_hold_capability
            if duration_hold or magnitude_hold:
                del self.flare_bounds[i]
                continue
            i += 1
            
    def calculate_summary_statistics(self):
        for flare in self.flare_bounds:
            instrument_bounds = {'foxsi': [flare[0] + self.FOXSI_OBS_START, flare[0] + self.FOXSI_OBS_END],
                                'hi-c': [flare[0] + self.HIC_OBS_START, flare[0] + self.HIC_OBS_END]}
            for instrument, bound in instrument_bounds.items():
                stats = dict()
                xrsa_flare = self.goes_data['xrsa'][bound[0]:bound[1]]
                xrsb_flare = self.goes_data['xrsb'][bound[0]:bound[1]]
                xrsb_total_flare = self.goes_data['xrsb'][flare[0]:flare[1]]
                stats['xrsa_max_flux'] = np.max(xrsa_flare)
                stats['xrsa_tot_flux'] = np.sum(xrsa_flare)
                stats['xrsa_ave_flux'] = np.sum(xrsa_flare)/len(xrsa_flare)
                stats['xrsb_max_flux'] = np.max(xrsb_flare)
                stats['xrsb_tot_flux'] = np.sum(xrsb_flare)
                stats['xrsb_ave_flux'] = np.sum(xrsb_flare)/len(xrsa_flare)
                stats['flare_peak_flux'] = np.max(xrsb_total_flare)
                if xrsb_flare[0] < 0.99*stats['xrsb_max_flux']:
                    stats['peak_query'] = 'yes'
                else: stats['peak_query'] = 'no'
                self.summary_stats[instrument].append(stats)

        for k, l in self.summary_stats.items():
            self.summary_stats[k] = pd.DataFrame.from_dict(l)

def plotting_flares(finder, dir_name):
    cmap_goes = ListedColormap(['blue', 'red'], N=2)
    plt.rcParams['axes.titlesize'] = 16
    plt.rcParams['axes.labelsize'] = 14
    plt.rcParams['xtick.labelsize'] = 14
    plt.rcParams['ytick.labelsize'] = 14
    plt.rcParams['grid.linestyle'] = ':'
     
    for i, flare in enumerate(finder.flare_bounds):        
        plot_start = max(0, flare[0]-5)
        trigger = flare[0] - plot_start
        plot_end = max(flare[1], plot_start + trigger + finder.HIC_OBS_END)
        flare_df = finder.goes_data[plot_start:plot_end+1].to_pandas()
        
        fig = plt.figure(figsize=(12,8))
        ax = fig.gca()
        ax.cla()
        flare_df.plot(x='date', y=['xrsa', 'xrsb'], ax=ax, lw=2, colormap=cmap_goes, legend=False)
        plt.grid(True,which='major',axis='both',linestyle=':')
        ax.vlines(flare_df['date'][trigger], 0, 1e-3, ls='-', color='black', lw=2, label='Trigger')
        ax.vlines(flare_df['date'][trigger + finder.FOXSI_LAUNCH], 0, 1e-3, ls='-', color='orange', lw=2, label='FOXSI Launch')
        ax.axvspan(flare_df['date'][trigger + finder.FOXSI_OBS_START], flare_df['date'][trigger + finder.FOXSI_OBS_END], alpha=0.3, 				color='orange', label='FOXSI Observation')
        ax.vlines(flare_df['date'][trigger + finder.HIC_LAUNCH], 0, 1e-3, ls='-', color='purple', lw=2, label='Hi-C Launch')
        ax.axvspan(flare_df['date'][trigger + finder.HIC_OBS_START], flare_df['date'][trigger + finder.HIC_OBS_END], alpha=0.2, 				color='purple', label='Hi-C Observation')
        # Format y-axis
        ax.set_yscale('log')
        ax.set_ylim(1e-8, 1e-3)
        ax.set_ylabel(f'GOES Flux [W m$^{{-2}}$]',)
        # Add flare classifcation axis
        ax2 = ax.twinx()
        ax2.set_yscale("log")
        ax2.set_ylim(1e-8, 1e-3)
        ax2.set_yticks((1e-8, 1e-7, 1e-6, 1e-5, 1e-4, 1e-3))
        ax2.set_yticklabels(('A', 'B', 'C', 'M', 'X', 'X10'),)
        # Format x-axis
        time = flare_df['date'][flare[0]- plot_start].strftime('%H:%M:%S')
        date = flare_df['date'][0].strftime('%Y:%m:%d')
        max_flux = np.max(flare_df['xrsb'])
        formatter = matplotlib.dates.DateFormatter('%H:%M')
        ax.xaxis.set_major_formatter(formatter)
        ax.set_xlabel(date)
        # Save
        plt.tight_layout()
        ax.legend(loc='upper right')
        ax.set_title(f'GOES XRS, Triggered {time} \n Peak Flux {max_flux:.1e} W m$^{{-2}}$')
        plt.savefig(f'{dir_name}/flare{i}', bbox_inches='tight')