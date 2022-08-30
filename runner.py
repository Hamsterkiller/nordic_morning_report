from datetime import date
import pandas as pd
from loader import load_weather_data, load_thermals_data
import logging
import numpy as np
import math
import os


def generate_report_comment(values: dict, dt: date):
    """
    Produce comment text
    :param values: dict with numeric values of key indices
    :return:
    """

    # WEATHER
    ec12adj_precip = values['ec12_adj_precip']
    ec12adj_precip_delta_norm = values['ec12_adj_precip'] - values['precip_norm']
    if round(ec12adj_precip_delta_norm, 1) < 0:
        ec12adj_precip_norm_dir = 'below'
    else:
        ec12adj_precip_norm_dir = 'above'

    ec12adj_precip_delta_prev = values['ec12_adj_precip'] - values['ec12_precip_prev']
    if round(ec12adj_precip_delta_prev, 1) < 0:
        ec12adj_precip_prev_dir = 'drier'
    else:
        ec12adj_precip_prev_dir = 'wetter'

    ec12adj_temp = values['ec12_adj_temp']
    ec12adj_temp_delta_norma = values['ec12_adj_temp'] - values['temp_norm']
    if round(ec12adj_precip_delta_prev, 1) < 0:
        ec12adj_temp_norma_dir = 'colder'
    else:
        ec12adj_temp_norma_dir = 'warmer'

    ec12adj_temp_delta_prev = values['ec12_adj_temp'] - values['ec12_temp_prev']
    if round(ec12adj_temp_delta_prev, 1) < 0:
        ec12adj_temp_prev_dir = 'colder'
    else:
        ec12adj_temp_prev_dir = 'warmer'

    ec12unadj_precip = values['ec12_unadj_precip']
    ec12unadj_precip_delta_norm = values['ec12_unadj_precip'] - values['precip_norm']
    if round(ec12unadj_precip_delta_norm, 1) < 0:
        ec12unadj_precip_norm_dir = 'below'
    else:
        ec12unadj_precip_norm_dir = 'above'

    ec12unadj_precip_delta_prev = values['ec12_unadj_precip'] - values['ec00_precip_prev']
    if round(ec12unadj_precip_delta_prev, 1) < 0:
        ec12unadj_precip_prev_dir = 'drier'
    else:
        ec12unadj_precip_prev_dir = 'wetter'

    ec12ens_precip = values['ec12_ens_precip']
    ec12ens_precip_delta_norm = values['ec12_ens_precip'] - values['precip_norm']
    if round(ec12ens_precip_delta_norm, 1) < 0:
        ec12ens_precip_norm_dir = 'below'
    else:
        ec12ens_precip_norm_dir = 'above'

    ec12ens_precip_delta_prev = values['ec12_ens_precip'] - values['ec12_precip_prev']
    if round(ec12adj_precip_delta_prev, 1) < 0:
        ec12ens_precip_prev_dir = 'drier'
    else:
        ec12ens_precip_prev_dir = 'wetter'

    ec12ens_temp = values['ec12_ens_temp']
    ec12ens_temp_delta_prev = values['ec12_ens_temp'] - values['ec12_temp_prev']
    if round(ec12ens_temp_delta_prev, 1) < 0:
        ec12ens_temp_prev_dir = 'colder'
    else:
        ec12ens_temp_prev_dir = 'warmer'

    front_quarter = math.fmod((np.ceil(dt.month / 3) + 1), 4)
    front_quarter_year = int(math.fmod((dt.today().year + (front_quarter < int((np.ceil(dt.month / 3))))), 2000))

    # THERMALS
    coal_closing_price = values['coal_closing_price']
    coal_np_closing_price = values['coal_np_closing_price']
    coal_delta = coal_closing_price - coal_np_closing_price
    if coal_delta < 0:
        coal_delta_dir = 'down'
    else:
        coal_delta_dir = 'up'

    gas_closing_price = values['gas_closing_price']
    gas_np_closing_price = values['gas_np_closing_price']
    gas_delta = gas_closing_price - gas_np_closing_price
    if gas_delta < 0:
        gas_delta_dir = 'down'
    else:
        gas_delta_dir = 'up'

    carbon_closing_price = values['carbon_closing_price']
    carbon_np_closing_price = values['carbon_np_closing_price']
    carbon_delta = carbon_closing_price - carbon_np_closing_price
    if carbon_delta < 0:
        carbon_delta_dir = 'down'
    else:
        carbon_delta_dir = 'up'

    current_oil_price = values['current_oil_price']
    oil_delta = values['oil_delta']
    if oil_delta < 0:
        oil_delta_dir = 'down'
    else:
        oil_delta_dir = 'up'

    report_comment = f"""
    EC12 adjusted is forecasting {ec12adj_precip} TWh, {abs(ec12adj_precip_delta_norm)} TWh {ec12adj_precip_norm_dir} normal \
    and {abs(ec12adj_precip_delta_prev)} TWh {ec12adj_precip_prev_dir} than EC12 SMHI yesterday. \
    Temperature index is at {ec12adj_temp} degrees, {abs(ec12adj_temp_delta_norma)}°C {ec12adj_temp_norma_dir} than \
    normal and {ec12adj_temp_delta_prev}°C {ec12adj_temp_prev_dir} than yesterday. \
    Unadjusted EC12 is forecasting {ec12unadj_precip} TWh, {abs(ec12unadj_precip_delta_norm)} TWh \
    {ec12unadj_precip_norm_dir} normal and {abs(ec12unadj_precip_delta_prev)} TWh {ec12unadj_precip_prev_dir} \
    than EC00 yesterday. EC12 ensemble mean for the next 10 days predicts ... TWh, ... \
    TWh wetter/drier than normal and ... TWh wetter/drier than EC00 ens yesterday. \
    In ensemble, the temperature index is at ... degrees, ... codler/warmer than earlier ensemble.
    
    Coal Q{front_quarter}-{front_quarter_year} closed at {coal_closing_price} USD/t, {coal_delta_dir} by {abs(coal_delta)} \
    USD/t after NP close. Gas TTF Q{front_quarter}-{front_quarter_year} contract closed at {gas_closing_price} EUR/MWh, \
    {gas_delta_dir} by {gas_delta} EUR/MWh after NP close. Carbon DEC-22 closed at {carbon_closing_price} EUR/t \
    {carbon_delta_dir} by {carbon_delta} EUR/t after NP close. Oil Brent \
    front month is traded at {current_oil_price} USD/bbl, {oil_delta_dir} by {oil_delta} USD/bbl this morning. \
    We expect market to open up on a back of drier weather forecasts and mostly higher thermals.
    """

    return report_comment


def generateMorningReport(dt: date, out_folder: str, sp_login: str, sp_pw: str):
    """
    Generate morning report comment text
    :param dt: date of analysis
    :param out_folder: folder to which output text file will be saved
    :return:
    """

    logging.basicConfig(level=logging.DEBUG)

    # generate output file path
    out_file = out_folder + 'morning_report_' + f"""{dt.isoformat().replace('-', '_')}""" + '.txt'

    # load weather data
    # weather_data = load_weather_data(dt)

    # load thermals data
    thermals_data = load_thermals_data(dt)

    return out_file
