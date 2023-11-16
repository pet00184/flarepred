import pandas as pd
import numpy as np

# __all__ = ["flare_trigger_condition", "flare_end_condition", "FLARE_ALERT_MAP"]

def xrsa_condition(goes_data):
    ''' Condition to move algorithm from "searching" to "trigger" mode. This function can be easily changed
    for maximum flexibility, and is kept separate from the RealTimeTrigger algorithm to easily make
    such changes. '''
    a = goes_data['xrsa']
    flux_val = 3.5e-7#2.3e-6
    return a.iloc[-1] > flux_val #a.iloc[-1] - a.iloc[-1] > flux_deriv_val
    
def xrsb_condition(goes_data):
    b = goes_data['xrsb']
    flux_val = 1e-6
    return b.iloc[-1] > flux_val
    
def temp_condition(goes_data):
    temp = goes_data['Temp']
    temp_val = .01
    return temp.iloc[-1] > temp_val
    
def xrsa_3mindiff_condition(goes_data):
    xrsa3min = goes_data['3minxrsadiff']
    xrsa3min_val = 5e-8
    return xrsa3min.iloc[-1] > xrsa3min_val
    
def em_condition(goes_data):
    em = goes_data['emission measure']
    em_val = 2e48
    return em.iloc[-1] > em_val
    
def special_flare_trigger(goes_data):
    # flares are always happening...
    return True

def magic_flare_trigger(goes_data):
    # flares are always happening...
    return True
    
def flare_end_condition(goes_data):
    ''' Condition that signifies a flare has ended.'''
    a = goes_data['xrsa']
    b = goes_data['xrsb']
    flux_val = 2.3e-6
    flux_deriv_val = 1e-9
    return b.iloc[-1] < flux_val #(b.iloc[-1] < flux_val) and (a.iloc[-1] - a.iloc[-2] < flux_deriv_val)

# may need to standardise the inputs to the functions to simpler use

FLARE_ALERT_MAP = {'XRSA>3.5e-7 W/m<sup>2</sup>':xrsa_condition, 
                   'XRSB>1e-6 W/m<sup>2</sup>':xrsb_condition,
                   'Temp>0.01':temp_condition,
                   'Emission Measure>2e48 cm<sup>-3</sup>':em_condition,
                   '3-minute XRSA Increase>5e-8 W/m<sup>2</sup>':xrsa_3mindiff_condition} #