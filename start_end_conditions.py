def initial_start_cond(goes_data, i):
    a = goes_data['xrsa']
    b = goes_data['xrsb']
    flux_val = 2e-6
    flux_deriv_val = 1e-9
    return a[i] - a[i-1] > flux_deriv_val

def initial_end_cond(goes_data, i):
    a = goes_data['xrsa']
    b = goes_data['xrsb']
    flux_val = 2e-6
    flux_deriv_val = 1e-9
    return (b[i] < flux_val) and (a[i] - a[i-1] < flux_deriv_val)

def magnitude_hold_condition(goes_data, start, last_hold):
    a = goes_data['xrsa']
    b = goes_data['xrsb']
    flux_val_xrsa = 3e-7
    flux_val_xrsb = 2.3e-6
    last_hold = 4
    test_index = min(start + last_hold, len(a) - 1)
    return (a[test_index] < flux_val_xrsa) and (b[test_index] < flux_val_xrsb)
	
