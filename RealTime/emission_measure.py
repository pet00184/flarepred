import numpy as np
from astropy.io import fits
import pandas as pd
import urllib.request as req
import scipy.interpolate as interp
import os

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


def compute_goes_emission_measure(goes_data: pd.DataFrame) -> np.ndarray:
    '''
    Assumes modern (number 16+) GOES satellites.
    Modifications required for older satellites.
    See https://docs.sunpy.org/projects/sunkit-instruments/en/stable/_modules/sunkit_instruments/goes_xrs/goes_chianti_tem.html#calculate_temperature_em

    Returns: array of emission measure estimated from GOES short/long in units of cm**-3
    '''
    sat_nums = np.atleast_1d(goes_data['satellite'])
    if any(sn < 16 for sn in sat_nums):
        raise ValueError('Only support GOES 16+')

    if not os.path.exists(RESPONSE_FILE_NAME):
        download_latest_goes_response()

    long = np.atleast_1d(goes_data['xrsb'])
    short = np.atleast_1d(goes_data['xrsa'])

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
    return np.array(ret) * 1e49
