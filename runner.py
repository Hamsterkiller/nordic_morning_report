from datetime import date
import pandas as pd
from loader import load_weather_data, load_thermals_data
import logging
import numpy as np
import math
import logging
import pickle
import os


def config_logging(out_folder: str):
    """
    Configurate logging
    :param out_folder: output folder to write logs to
    :return:
    """
    filepath = out_folder + '/morning_report_logs.log'
    logging.basicConfig(filename=out_folder + '/morning_report_logs.log', level=logging.INFO)


def generate_report_comment(values: dict, dt: date):
    """
    Produce comment text
    :param values: dict with numeric values of key indices
    :return:
    """

    # WEATHER
    ec12_adj_precip = values['ec12_adj_precip']
    ec12_adj_precip_delta_norm = values['ec12_adj_precip_delta_norm']
    if round(ec12_adj_precip_delta_norm, 1) < 0:
        ec12_adj_precip_norm_dir = 'below'
    else:
        ec12_adj_precip_norm_dir = 'above'

    ec12_adj_precip_delta_prev = values['ec12_adj_precip_delta_prev']
    if round(ec12_adj_precip_delta_prev, 1) < 0:
        ec12_adj_precip_prev_dir = 'drier'
    else:
        ec12_adj_precip_prev_dir = 'wetter'

    ec12_adj_temp = values['ec12_adj_temp']
    ec12_adj_temp_delta_norm = values['ec12_adj_temp_delta_norm']
    if round(ec12_adj_temp_delta_norm, 1) < 0:
        ec12_adj_temp_norma_dir = 'colder'
    else:
        ec12_adj_temp_norma_dir = 'warmer'

    ec12_adj_temp_delta_prev = values['ec12_adj_temp_delta_prev']
    if round(ec12_adj_temp_delta_prev, 1) < 0:
        ec12_adj_temp_prev_dir = 'colder'
    else:
        ec12_adj_temp_prev_dir = 'warmer'

    ec12_precip = values['ec12_precip']
    ec12_precip_delta_norm = values['ec12_precip_delta_norm']
    if round(ec12_precip_delta_norm, 1) < 0:
        ec12_precip_norm_dir = 'below'
    else:
        ec12_precip_norm_dir = 'above'

    ec12_precip_delta_prev = values['ec12_precip_delta_prev']
    if round(ec12_precip_delta_prev, 1) < 0:
        ec12_precip_prev_dir = 'drier'
    else:
        ec12_precip_prev_dir = 'wetter'

    ec12ens_precip = values['ec12ens_precip']
    ec12ens_precip_delta_norm = values['ec12ens_precip_delta_norm']
    if round(ec12ens_precip_delta_norm, 1) < 0:
        ec12ens_precip_norm_dir = 'below'
    else:
        ec12ens_precip_norm_dir = 'above'

    ec12ens_precip_delta_prev = values['ec12ens_precip_delta_prev']
    if round(ec12ens_precip_delta_prev, 1) < 0:
        ec12ens_precip_prev_dir = 'drier'
    else:
        ec12ens_precip_prev_dir = 'wetter'

    ec12ens_temp = values['ec12ens_temp']
    ec12ens_temp_delta_prev = values['ec12ens_precip_delta']
    if round(ec12ens_temp_delta_prev, 1) < 0:
        ec12ens_temp_prev_dir = 'colder'
    else:
        ec12ens_temp_prev_dir = 'warmer'

    front_quarter = int(math.fmod((np.ceil(dt.month / 3) + 1), 4) + 1)
    front_quarter_year = int(math.fmod((dt.today().year + (front_quarter < int((np.ceil(dt.month / 3))))), 2000))

    # THERMALS
    coal_closing_price = values['coal_close']
    coal_np_closing_price = values['coal_np_close']
    coal_delta = round(coal_closing_price - coal_np_closing_price, 1)
    if coal_closing_price > 0:
        if coal_delta < 0:
            coal_delta_dir = 'down'
        else:
            coal_delta_dir = 'up'
    else:
        coal_delta_dir = "(no trading session)"

    gas_closing_price = values['gas_close']
    gas_np_closing_price = values['gas_np_close']
    gas_delta = round(gas_closing_price - gas_np_closing_price, 1)

    if gas_closing_price > 0:
        if gas_delta < 0:
            gas_delta_dir = 'down'
        else:
            gas_delta_dir = 'up'
    else:
        gas_delta_dir = "(no trading session)"

    carbon_closing_price = values['co2_close']
    carbon_np_closing_price = values['co2_np_close']
    carbon_delta = round(carbon_closing_price - carbon_np_closing_price, 1)

    if carbon_closing_price > 0:
        if carbon_delta < 0:
            carbon_delta_dir = 'down'
        else:
            carbon_delta_dir = 'up'
    else:
        carbon_delta = "(no trading session)"

    current_oil_price = values['oil_last_price']
    oil_delta = values['oil_last_delta']
    if oil_delta < 0:
        oil_delta_dir = 'down'
    else:
        oil_delta_dir = 'up'

    # define overall directions
    overall_weather_dir_arr = [ec12_adj_precip_prev_dir, ec12_precip_prev_dir, ec12ens_precip_prev_dir]
    overall_thermals_dir_arr = [coal_delta_dir, gas_delta_dir, carbon_delta_dir, oil_delta_dir]
    overall_weather_wetter_cnt = sum([1 if el == 'wetter' else 0 for el in overall_weather_dir_arr])
    overall_weather_dir = 'drier'
    if overall_weather_wetter_cnt >= 2:
        overall_weather_dir == 'wetter'
    overall_thermals_up_cnt = sum([1 if el == 'up' else 0 for el in overall_thermals_dir_arr])
    if overall_thermals_up_cnt > 2:
        overall_thermals_dir = 'mostly higher'
    elif overall_thermals_up_cnt == 2:
        overall_thermals_dir = 'mixed'
    else:
        overall_thermals_dir = 'mostly lower'

    if (overall_weather_dir == 'wetter') & (overall_thermals_dir == 'mostly higher'):
        overall_dir = 'down'
    elif (overall_weather_dir == 'drier') & (overall_thermals_dir == 'mostly lower'):
        overall_dir = 'up'
    else:
        overall_dir = 'sideways'

    if dt.weekday() > 0:
        friday = ''
    else:
        friday = " on Friday"

    report_comment = ''.join([f"EC12 adjusted is forecasting {ec12_adj_precip} TWh, {abs(ec12_adj_precip_delta_norm)} TWh {ec12_adj_precip_norm_dir} normal " ,
    f"and {abs(ec12_adj_precip_delta_prev)} TWh {ec12_adj_precip_prev_dir} than EC12 SMHI yesterday. ",
    f"Temperature index is at {ec12_adj_temp} degrees, {abs(ec12_adj_temp_delta_norm)}°C {ec12_adj_temp_norma_dir} than ",
    f"normal and {abs(ec12_adj_temp_delta_prev)}°C {ec12_adj_temp_prev_dir} than yesterday. ",
    f"Unadjusted EC12 is forecasting {ec12_precip} TWh, {abs(ec12_precip_delta_norm)} TWh ",
    f"{ec12_precip_norm_dir} normal and {abs(ec12_precip_delta_prev)} TWh {ec12_precip_prev_dir} ",
    f"than EC00 yesterday. EC12 ensemble mean for the next 10 days predicts {ec12ens_precip} TWh, {abs(ec12ens_precip_delta_norm)} ",
    f"TWh {ec12ens_precip_norm_dir} normal and {abs(ec12ens_precip_delta_prev)} TWh {ec12ens_precip_prev_dir} than EC00 ens yesterday. ",
    f"In ensemble, the temperature index is at {ec12ens_temp} degrees, {abs(ec12ens_temp_delta_prev)} {ec12ens_temp_prev_dir} than earlier ensemble.\n",
    f"Coal Q{front_quarter}-{front_quarter_year} closed at {coal_closing_price} USD/t{friday}, {coal_delta_dir} by {abs(coal_delta)} ",
    f"USD/t after NP close. Gas TTF Q{front_quarter}-{front_quarter_year} contract closed at {gas_closing_price} EUR/MWh, ",
    f"{gas_delta_dir} by {abs(gas_delta)} EUR/MWh after NP close. Carbon DEC-22 closed at {carbon_closing_price} EUR/t{friday} ",
    f"{carbon_delta_dir} by {abs(carbon_delta)} EUR/t after NP close. Oil Brent ",
    f"front month is traded at {current_oil_price} USD/bbl, {oil_delta_dir} by {abs(oil_delta)} USD/bbl this morning. ",
    f"We expect market to open {overall_dir} on a back of {overall_weather_dir} weather forecasts and {overall_thermals_dir} thermals."])

    return report_comment


def generateMorningReport(dt: date, out_folder: str, syspower_login: str, syspower_pw: str):
    """
    Generate morning report comment text
    :param syspower_pw: syspower login
    :param syspower_login: syspower password
    :param dt: date of analysis
    :param out_folder: folder to which output text file will be saved
    :return:
    """

    config_logging(out_folder)

    # generate output file path
    out_file = out_folder + '/' + 'morning_report_' + f"""{dt.isoformat().replace('-', '_')}""" + '.txt'

    # load weather data
    weather_data = load_weather_data(dt, syspower_login, syspower_pw)

    # load thermals data
    thermals_data = load_thermals_data(dt, out_folder)

    # merge two dicts into one
    report_values = {}
    for k, v in weather_data.items():
        report_values[k] = v
    for k, v in thermals_data.items():
        report_values[k] = v
    #
    # with open('result_report_values', 'wb') as handle:
    #     pickle.dump(report_values, handle, protocol=pickle.HIGHEST_PROTOCOL)

    # with open('result_report_values', 'rb') as handle:
    #     report_values = pickle.load(handle)

    report_comment = generate_report_comment(report_values, dt)

    # save report_comment to txt file
    with open(out_file, 'w') as f:
        f.write(report_comment)

    return out_file
