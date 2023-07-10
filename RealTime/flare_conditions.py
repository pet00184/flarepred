import pandas as pd

def flare_trigger_condition(xrsa_data, xrsb_data):
    ''' Condition to move algorithm from "searching" to "trigger" mode. This function can be easily changed
    for maximum flexibility, and is kept separate from the RealTimeTrigger algorithm to easily make
    such changes. '''
    a = xrsa_data['flux']
    b = xrsb_data['flux']
    flux_val = 2e-6
    flux_deriv_val = 1e-9
    return b.iloc[-1] > flux_val and (b.iloc[-1] - b.iloc[-2]) > 0 #a.iloc[-1] - a.iloc[-1] > flux_deriv_val
    
def flare_end_condition(xrsa_data, xrsb_data):
    ''' Condition that signifies a flare has ended.'''
    a = xrsa_data['flux']
    b = xrsb_data['flux']
    flux_val = 2.3e-6
    flux_deriv_val = 1e-9
    return b.iloc[-1] < flux_val #(b.iloc[-1] < flux_val) and (a.iloc[-1] - a.iloc[-2] < flux_deriv_val)
