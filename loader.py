from datetime import date, timedelta
import logging
import requests
import json
import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
import re
from selenium import webdriver


# loading price_independent bids
def generate_series_url(series_list: list[str], interval: str, start_date: date, end_date: date):
    """
    generates webquery to load specified series
    :param series_list:
    :param interval:
    :param start_date:
    :param end_date:
    :param token:
    :return:
    """
    series_list_str = ','.join(series_list)
    series_url = ''.join(
        [f"""https://syspower5.skm.no/api/webquery/execute?fileformat=csv&series={series_list_str}&start="""
         f"""{start_date.strftime('%d.%m.%Y')}&end={end_date.strftime('%d.%m.%Y')}&interval={interval}&token="""
         f"""7EMf0VCcZxcIdBy&emptydata=no&currency=&dateFormat=nbno&numberFormat=nothousandsdot&headers=yes"""])
    return series_url


def syspower_auth(auth_url: str, sp_login: str, sp_pw: str):
    """
    Login to syspower using provided credentials
    :param url:
    :param sp_login:
    :param sp_pw:
    :return:
    """
    logging.info(f"Cloud login (user={sp_login})")
    try:
        logging.info(f'Trying to log in to {auth_url}...')
        response = requests.post(auth_url,
                                 json={"email": sp_login, "password": sp_pw, "forceLogin": True},
                                 verify=False)
        data = json.loads(response.text)
        assert data.get('tokenType') is not None
    except requests.exceptions.RequestException as e:
        logging.error(response)
        logging.error(f'Sending updated dictionary to Exergy failed!')
        raise SystemExit(e)
    except requests.exceptions.ConnectionError as e:
        logging.error(f'System failed to connect to {auth_url}!')
        raise SystemExit(e)

    token = data['issuedToken']
    logging.info(f'Obtained token {token}')
    return token


def load_weather_data(dt: date):
    """
    Load weather data from Syspower (EC12 Adj, EC12 and EC12 Ens series)
    :param dt: target date
    :param token: issued auth-token
    :return:
    """
    series_list = ['SMHITEMPNP_F', 'SMHITEMPNP_L', 'TEMPNP_N', 'SMHIPENNP_F', 'SMHIPENNP_L', 'SKMPENNP_N', \
                   'EC00TEMPNP_L', 'EC00PENNP_L', 'EC12TEMPNP_F', 'PENNPACCMEAN_L', 'EC12PENNP_F', 'NCGFS00PENNP_F']
                  # 'PENNPACCMEAN', 'PENNPACCMAX', 'PENNPACCMIN']

    interval = 'day'
    series_url = generate_series_url(series_list, interval, dt - timedelta(days=1), dt + timedelta(days=9))
    df = pd.read_csv(series_url, sep=';')

    last_frcst_cols = [c for c in df.columns if '_L' in c]
    rest_frcst_cols = [c for c in df.columns if '_L' not in c]
    if (df[rest_frcst_cols].isnull().values.any()) | (df[last_frcst_cols].iloc[:df.shape[0] - 1].isnull().values.any()):
        na_records = {}
        test_df = df.to_dict(orient='records')
        for row in test_df:
            for k, v in row.items():
                if k == '#Day':
                    continue
                if np.isnan(v):
                    na_records[row['#Day']] = k
        missed_data_msg = '\n'.join([f'{k}: {v}' for k, v in na_records.items()])
        raise Exception(f'Some data is not loaded: \n'
                        f'{missed_data_msg}')

    # construct values dict
    values = {}
    values['ec12_adj_precip'] = np.round(np.sum(df['SMHIPENNP_F'].iloc[1: df.shape[0]]) / 1000, 1)
    values['ec12_adj_precip_delta_prev'] = np.round(values['ec12_adj_precip'] - \
                                                    np.sum(df['SMHIPENNP_L'].iloc[0: df.shape[0] - 1]) / 1000, 1)
    values['ec12_adj_precip_delta_norm'] = np.round(values['ec12_adj_precip'] - \
                                                    np.sum(df['SKMPENNP_N'].iloc[1: df.shape[0]]) / 1000, 1)
    values['ec12_adj_temp'] = np.round(np.mean(df['SMHITEMPNP_F'].iloc[1: df.shape[0]]), 1)
    values['ec12_adj_temp_delta_prev'] = np.round(values['ec12_adj_temp'] - \
                                                  np.mean(df['SMHITEMPNP_L'].iloc[0: df.shape[0] - 1]), 1)
    values['ec12_adj_temp_delta_norm'] = np.round(values['ec12_adj_temp'] - \
                                                  np.mean(df['TEMPNP_N'].iloc[1: df.shape[0]]), 1)
    values['ec12_precip'] = np.round(np.sum(df['EC12PENNP_F'].iloc[1: df.shape[0]]) / 1000, 1)
    values['ec12_precip_delta_prev'] = np.round(values['ec12_precip'] - \
                                                np.sum(df['EC00PENNP_L'].iloc[0: df.shape[0] - 1]) / 1000, 1)
    values['ec12_precip_delta_norm'] = np.round(values['ec12_precip'] - \
                                                np.sum(df['SKMPENNP_N'].iloc[1: df.shape[0]]) / 1000, 1)

    return df


def load_thermals_data(dt: date):
    """
    Load thermals data from Montel
    :param dt: target date
    :return:
    """

    result = {}

    headers = {
        'authority': 'www.montelnews.com',
        'cache-control': 'max-age=0',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.106 Safari/537.36',
        'sec-fetch-dest': 'document',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-user': '?1',
        'accept-language': 'en-US,en;q=0.9',
    }
    session = requests.session()
    response = session.get("https://app.montelnews.com/en/default.aspx", headers=headers)
    if response.status_code == 200:
        print("Success")
    else:
        print("Bad result")

    URL = "https://app.montelnews.com/en/default.aspx"

    driver = webdriver.Chrome()
    driver.get("https://app.montelnews.com/en/default.aspx")
    user_name_input = driver.find_element(by='id', value='LoginForm1_LoginView1_Login1_UserName')
    user_name_input.send_keys('skmq2012_1')
    password_input = driver.find_element(by='id', value='LoginForm1_LoginView1_Login1_Password')
    password_input.send_keys('mpred1')
    sign_in_btn = driver.find_element(by='id', value='LoginForm1_LoginView1_Login1_LoginButton')
    sign_in_btn.click()
    driver.get('https://app.montelnews.com/Exchanges/ICE/coal.aspx?249')


    return result
