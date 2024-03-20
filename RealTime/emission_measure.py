import numpy as np
from astropy.io import fits
import pandas as pd
import urllib.request as req
import scipy.interpolate as interp
import os
import math

RESPONSE_FILE_NAME = 'goes-response-latest.fits'

def download_latest_goes_response() -> None:
    ''' Get the latest GOES response function and save it to a .fits file '''
    URL = 'https://sohoftp.nascom.nasa.gov/solarsoft/gen/idl/synoptic/goes/goes_chianti_response_latest.fits'
    req.urlretrieve(URL, RESPONSE_FILE_NAME)


def load_response_data(satellite_number: int | np.ndarray[int]) -> dict[int, dict[str, np.ndarray]]:
    # response data calculated for coronal abundances
    # for multiple GOES satellites
    ret = dict()
    response_data = fits.getdata(RESPONSE_FILE_NAME);
    snums = np.atleast_1d(satellite_number)
    for sn in snums:
        # only need data for each satellite number once
        if sn in ret: continue
        ret[sn] = {
            'temperature': response_data['temp_mk'][sn],
            'converter': 10.0 ** (49.0 - response_data['alog10em'][sn]),
            'ratio': response_data['FSHORT_COR'][sn] / response_data['FLONG_COR'][sn],
            'long': response_data['FLONG_COR'][sn]
        }
    return ret


def compute_goes_emission_measure(xrsa_data, xrsb_data, goes_sat) -> np.ndarray:
    '''
    Assumes modern (number 16+) GOES satellites. 
    Updated to provide XRSA and XRSB arrays, so that flux differences may be used.
    Modifications required for older satellites.
    See https://docs.sunpy.org/projects/sunkit-instruments/en/stable/_modules/sunkit_instruments/goes_xrs/goes_chianti_tem.html#calculate_temperature_em

    Returns: array of emission measure aestimated from GOES short/long in units of cm**-3, and temp in units MK
    '''
    sat_nums = np.atleast_1d(goes_sat)
    if any(sn < 16 for sn in sat_nums):
        raise ValueError('Only support GOES 16+')

    if not os.path.exists(RESPONSE_FILE_NAME):
        download_latest_goes_response()
        
    long = np.atleast_1d(xrsb_data)
    short = np.atleast_1d(xrsa_data)
    
    # #checking to make sure the xrsa and xrsb aren't negative- this avoids FAI happening during the gradual phase of a flare.
    # if np.any(short < 0) or np.any(long < 0):
    #     nanz = np.nan * short
    #     return nanz, nanz
        
    ratio = short / long
    bad = (short < 1e-10) | (long < 3e-8)
    ratio[bad] = 0.003

    denominators = dict()
    response_dat = load_response_data(sat_nums)
    for sn in sat_nums:
        d = response_dat[sn]
        temp_spline = interp.splrep(d['ratio'], d['temperature'], s=0)
        temps = interp.splev(ratio, temp_spline, der=0)
        converter_spline = interp.splrep(
            d['temperature'],
            d['long'] * d['converter'], s=0
        )
        denominators[sn] = interp.splev(temps, converter_spline, der=0)


    ret = np.zeros_like(long)
    for i, sn in enumerate(sat_nums):
        ret[i] = (long / denominators[sn])[i]
        
    #put nan where either xrsa or xrsb difference is negative: 
    nan_indx = np.where((long < 0) | (short < 0))[0]
    print(nan_indx)
    ret[nan_indx] = np.nan
    temps[nan_indx] = np.nan
    print(ret)
    return ret * 1e49, temps
