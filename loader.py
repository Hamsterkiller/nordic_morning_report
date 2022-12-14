import os
from datetime import date, timedelta
import logging
import json
import pandas as pd
import numpy as np
import requests
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import platform
import time
from io import StringIO
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select


def every_downloads_chrome(driver: webdriver):
    """
    Wait until files downloaded
    :param driver:
    :return:
    """
    if not driver.current_url.startswith("chrome://downloads"):
        driver.get("chrome://downloads/")
    return driver.execute_script("""
        var items = document.querySelector('downloads-manager')
            .shadowRoot.getElementById('downloadsList').items;
        if (items.every(e => e.state === "COMPLETE"))
            return items.map(e => e.fileUrl || e.file_url);
        """)


def get_prev_day_data(dt: date, driver: webdriver, original_window: str, download_dir: str):
    """
    :param dt: target date
    :param driver: selenium driver
    :param original_window: id of the main Montel window
    :param download_dir: directory to download files to
    :return:
    """

    close_price = 0
    np_close_price = 0

    # find 'Previous' button
    prev_button = driver.find_element(by='id', value='btn-prev')

    # if current day is not monday - use previous day data, else - data of last friday
    if dt.weekday() > 0:
        prev_button.click()
        time.sleep(3)
    else:
        cnt = 3
        while cnt > 0:
            prev_button.click()
            time.sleep(3)
            cnt -= 1

    # set focus back on the window
    switch_to_new_window(driver, original_window)

    # find table element with data
    price_table = driver.find_element(by='id', value='divGridContainer')

    # if there're some montel data files left from the past - remove them
    montel_data_files = [el for el in os.listdir(download_dir) if 'export' in el.lower()]
    if montel_data_files:
        for f in montel_data_files:
            os.remove(download_dir + '/' + f)

    # find export link
    export_link = driver.find_element(By.PARTIAL_LINK_TEXT, value='excel')
    export_link.click()

    # wait until file is loaded or time out
    montel_data_files = [el for el in os.listdir(download_dir) if 'export' in el.lower()]
    timer = 5
    while (not montel_data_files) & (timer <= 20):
        print(f'Loading excel data file: timer={timer}')
        time.sleep(timer)
        montel_data_files = [el for el in os.listdir(download_dir) if 'export' in el.lower()]
        timer = timer * 2

    # wait until download process is completed
    # paths = WebDriverWait(driver, 120, 1).until(every_downloads_chrome)
    # logging.info(paths)

    # read downloaded file
    montel_data_files = [el for el in os.listdir(download_dir) if 'export' in el.lower()]
    if montel_data_files:
        file_name = [el for el in os.listdir(download_dir) if 'export' in el.lower()][0]
        file_path = download_dir + '/' + file_name
        data = pd.read_excel(file_path)
        # delete data file
        for f in montel_data_files:
            os.remove(download_dir + '/' + f)
    else:
        logging.error('Failed to download the montel data!')
        return np_close_price

    # read data from the downloaded file
    if not data.empty:
        data = data.iloc[3:data.shape[0], [1, 4]]
        data.columns = ['price', 'datetime']
        data['datetime'] = pd.to_datetime(data['datetime'], yearfirst=True)
        data.sort_values(['datetime'], inplace=True)
        data['price'] = pd.to_numeric(data['price'])
        # close_price = data['price'].tail(1).values[0]
        if dt.weekday() > 0:
            pred_dt = dt - timedelta(days=1)
        else:
            pred_dt = dt - timedelta(days=3)
        cutted_to_np_close_data = data[data.datetime < datetime(pred_dt.year, pred_dt.month, pred_dt.day, 16, 0, 0)]
        if not cutted_to_np_close_data.empty:
            np_close_price = cutted_to_np_close_data['price'].tail(1).values[0]
        else:
            np_close_price = data['price'].head(1).values[0]

    # close the window with data - no more need in it
    driver.close()

    # back to main window
    driver.switch_to.window(original_window)

    return np_close_price


def montel_log_out(driver: webdriver, original_window: str):
    """
    Log out from Montel
    :param driver: selenium webdriver
    :param original_window: original window id
    :return: void
    """
    driver.switch_to(original_window)
    logout_btn = driver.find_element(by='id', value='ctl00_Top_lnkLogOut')
    logout_btn.send_keys(Keys.RETURN)


def switch_to_new_window(driver: webdriver, original_window: str):
    """
    Check if there's only two windows opened and switch to second (not initial)
    :param driver: selenium webdriver object
    :param original_window: original window id
    :return: void
    """
    try:
        assert len(driver.window_handles) == 2
    except AssertionError:
        montel_log_out(driver, original_window)
        raise Exception('More than 2 windows are open!')
    # Loop through until we find a new window handle
    for window_handle in driver.window_handles:
        if window_handle != original_window:
            driver.switch_to.window(window_handle)
            break


def auth_to_montel(driver: webdriver, login: str, pw: str):
    """
    Authenticate on Montel
    :param driver: selenium webdriver
    :param login: Montel login
    :param pw: Montel password
    :return: void
    """
    driver.get("https://app.montelnews.com/en/default.aspx")
    user_name_input = driver.find_element(by='id', value='LoginForm1_LoginView1_Login1_UserName')
    user_name_input.send_keys(login)
    password_input = driver.find_element(by='id', value='LoginForm1_LoginView1_Login1_Password')
    password_input.send_keys(pw)
    password_input.send_keys(Keys.RETURN)
    time.sleep(5)


def auth_to_syspower(driver: webdriver, login: str, pw: str):
    """
    Authenticate to Syspower
    :param driver: selenium webdriver
    :param login: Syspower login
    :param pw: Syspower password
    :return: void
    """
    driver.get("https://syspower5.skm.no/login")
    user_name_input = driver.find_element(by='id', value='work-email')
    user_name_input.send_keys(login)
    password_input = driver.find_element(by='id', value='work-email-password')
    password_input.send_keys(pw)
    password_input.send_keys(Keys.RETURN)
    time.sleep(5)

    # check if approving window appeared and click 'Yes'
    if 'Yes' in driver.page_source:
        yes_button = driver.find_element(By.CSS_SELECTOR, value='.bp4-button.bp4-small.bp4-intent-warning')
        yes_button.click()
        time.sleep(5)


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


def load_weather_data(dt: date, syspower_login: str, syspower_pw: str):
    """
    Load weather data from Syspower (EC12 Adj, EC12 and EC12 Ens series)
    :param syspower_pw: syspower password
    :param syspower_login: syspower login
    :param dt: target date
    :return:
    """
    series_list = ['SMHITEMPNP_F', 'SMHITEMPNP_L', 'TEMPNP_N', 'SMHIPENNP_F', 'SMHIPENNP_L', 'SKMPENNP_N', \
                   'EC00TEMPNP_L', 'EC00PENNP_L', 'EC12TEMPNP_F', 'PENNPACCMEAN_L', 'EC12PENNP_F', 'NCGFS00PENNP_F']
    # 'PENNPACCMEAN', 'PENNPACCMAX', 'PENNPACCMIN']

    # login and password for syspower
    # syspower_login = 'ilya.zemskov@skmenergy.com'
    # syspower_pw = 'Ilyaz1987'

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
        logging.debug(f'Some data is not loaded: \n'
                      f'{missed_data_msg}')
    df.fillna(0, inplace=True)
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


    # load ensemble forecasts data from Syspower through Selenium
    try:
        if 'mac' in platform.platform():
            driver = webdriver.Chrome('./chromedriver')
        else:
            driver = webdriver.Chrome()
    except Exception:
        raise Exception(f'No Google Chrome browser driver was found!')

    # Setup wait for later
    wait = WebDriverWait(driver, 10)

    # set prefered window size
    # driver.set_window_size(height=1024, width=768)

    # authenticate to Syspower
    try:
        auth_to_syspower(driver, syspower_login, syspower_pw)
    except Exception:
        raise Exception('Syspower authentication failed!')

    # get weather panel page
    driver.get('https://syspower5.skm.no/desktop/364/1/15')
    time.sleep(5)

    # find date picker combobox
    date_p_selector = '#desktop-content > div > div._3NmFTnNW1Jd3IVJM-cPZDm > div:nth-child(2) > div:nth-child(1) > div.d-flex.flex-wrap.align-items-center > div > div > select'
    date_picker = driver.find_element(By.CSS_SELECTOR, value=date_p_selector)
    date_picker = Select(date_picker)
    date_picker.select_by_index('1')
    time.sleep(2)

    # get E12Ens data
    e12ens_button = driver.find_element(By.XPATH, "//button[contains(text(),'EC12 Ens')]")
    e12ens_button.click()

    # find needed values in the data tables
    value_tables = driver.find_elements(By.CSS_SELECTOR, value='._3JLoIh4MlgupAmYAArFi8Q')
    time.sleep(5)
    precip_values = value_tables[0]
    precip_values = precip_values.text.split('\n')
    precip_values = [el for el in precip_values if el != 'adv']
    precip_frcst = float(precip_values[7])
    precip_delta_norm = float(precip_values[10])
    precip_delta_prev = float(precip_values[13])

    # find same values for temperature forecast
    temp_values = value_tables[1]
    temp_values = temp_values.text.split('\n')
    temp_frcst = float(temp_values[7])
    temp_delta_prev = float(temp_values[13])

    # if it's monday, then choose friday in date picker else - current date
    if dt.weekday() == 0:
        date_picker.select_by_index('4')
        time.sleep(2)

        # get EC12Adj data for friday
        e12adj_button = driver.find_element(By.XPATH, "//button[contains(text(),'EC12 Adj')]")
        e12adj_button.click()
        time.sleep(2)
        value_tables_fr = driver.find_elements(By.CSS_SELECTOR, value='._3JLoIh4MlgupAmYAArFi8Q')
        precip_values_fr = value_tables_fr[0]
        precip_values_fr = precip_values_fr.text.split('\n')
        precip_values_fr = [el for el in precip_values_fr if el != 'adv']
        precip_fr_frcst_ec12adj = float(precip_values_fr[6])
        temp_values_fr = value_tables_fr[1]
        temp_values_fr = temp_values_fr.text.split('\n')
        temp_frcst_fr_ec12adj = float(temp_values_fr[6])

        # get EC12 data for friday
        e12_button = driver.find_element(By.XPATH, "//button[contains(text(),'EC12')]")
        e12_button.click()
        time.sleep(2)
        value_tables_fr = driver.find_elements(By.CSS_SELECTOR, value='._3JLoIh4MlgupAmYAArFi8Q')
        precip_values_fr = value_tables_fr[0]
        precip_values_fr = precip_values_fr.text.split('\n')
        precip_values_fr = [el for el in precip_values_fr if el != 'adv']
        precip_fr_frcst_ec12 = float(precip_values_fr[6])
        temp_values_fr = value_tables_fr[1]
        temp_values_fr = temp_values_fr.text.split('\n')
        temp_frcst_fr_ec12 = float(temp_values_fr[6])

        # get EC00Ens data for friday
        e00ens_button = driver.find_element(By.XPATH, "//button[contains(text(),'EC00 Ens')]")
        e00ens_button.click()
        time.sleep(2)
        value_tables_fr = driver.find_elements(By.CSS_SELECTOR, value='._3JLoIh4MlgupAmYAArFi8Q')
        precip_values_fr = value_tables_fr[0]
        precip_values_fr = precip_values_fr.text.split('\n')
        precip_values_fr = [el for el in precip_values_fr if el != 'adv']
        precip_fr_frcst_ec00ens = float(precip_values_fr[7])
        temp_values_fr = value_tables_fr[1]
        temp_values_fr = temp_values_fr.text.split('\n')
        temp_frcst_fr_ec00ens = float(temp_values_fr[7])

        # store values to the result
        values['precip_fr_frcst_ec12adj'] = precip_fr_frcst_ec12adj
        values['temp_frcst_fr_ec12adj'] = temp_frcst_fr_ec12adj
        values['precip_fr_frcst_ec12'] = precip_fr_frcst_ec12
        values['temp_frcst_fr_ec12'] = temp_frcst_fr_ec12
        values['precip_fr_frcst_ec00ens'] = precip_fr_frcst_ec00ens
        values['temp_frcst_fr_ec00ens'] = temp_frcst_fr_ec00ens

    # store values to the result
    values['ec12ens_precip'] = round(precip_frcst, 1)
    values['ec12ens_precip_delta_norm'] = round(precip_delta_norm, 1)
    values['ec12ens_precip_delta_prev'] = round(precip_delta_prev, 1)
    values['ec12ens_temp'] = round(temp_frcst, 1)
    values['ec12ens_precip_delta'] = round(temp_delta_prev, 1)

    # close the browser
    driver.close()
    driver.quit()

    return values


def load_thermals_data(dt: date, download_dir: str):
    """
    Load thermals data from Montel
    :param download_dir: directory to download files to
    :param dt: target date
    :return:
    """

    def get_next_quarter(dt: date):
        current_quarter = (dt.month - 1) // 3 + 1
        if current_quarter == 4:
            next_quarter = 1
        else:
            next_quarter = current_quarter + 1
        return next_quarter

    # load closing prices for coal, gas and CO2 from series in Syspower
    series_list = ['SKMIDXAPI2QFR1', 'SPCTTTFQFR1', 'NPEUACALFR1']
    interval = 'day'
    if dt.weekday() == 0:
        lag = 3
    else:
        lag = 1
    series_url = generate_series_url(series_list, interval, dt - timedelta(days=lag), dt)
    coal_gas_co2_df = pd.read_csv(series_url, sep=';')
    coal_close = coal_gas_co2_df.SKMIDXAPI2QFR1.values[0]
    gas_close = coal_gas_co2_df.SPCTTTFQFR1.values[0]
    co2_close = coal_gas_co2_df.NPEUACALFR1.values[0]

    front_quarter_str = f'Q{get_next_quarter(dt)}-{dt.year + (get_next_quarter(dt) == 1)}'
    # Ljuba said that next MidDec period is incremented somewhere in the last days of the current year
    # let it be 5 days
    lookforward_date = dt + timedelta(days=11)
    mid_dec_str = f'MidDec-{lookforward_date.year}'

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

    chromeOptions = webdriver.ChromeOptions()
    prefs = {"download.default_directory": download_dir,
             "download.prompt_for_download": False,
             "download.directory_upgrade": True,
             "safebrowsing.enabled": True}
    chromeOptions.add_experimental_option("prefs", prefs)

    try:
        if 'mac' in platform.platform():
            driver = webdriver.Chrome('./chromedriver', options=chromeOptions)
        else:
            driver = webdriver.Chrome(options=chromeOptions)
    except Exception:
        raise Exception(f'No Google Chrome browser driver was found!')

    # Setup wait for later
    wait = WebDriverWait(driver, 10)

    # set prefered window size
    driver.set_window_size(height=1024, width=768)

    # authenticate to Montel
    auth_to_montel(driver, 'skm2012_1', 'mpred1')

    # if account is busy - authenticate with other available account
    if 'support@montelgroup.com' in driver.page_source:
        auth_to_montel(driver, 'skm2012_2', 'mpred2')
        # if other is busy too - raise an error
        if 'support@montelgroup.com' in driver.page_source:
            raise Exception('All Montel accounts are busy!')

    # Store the ID of the original window
    original_window = driver.current_window_handle

    # get page with coal data
    driver.get('https://app.montelnews.com/Exchanges/ICE/coal.aspx?249')
    time.sleep(5)

    # Choose last trading session
    data_table = driver.find_element(By.CSS_SELECTOR, value='#ctl00_m_r6_C_t6_et_table')
    row_list = data_table.find_elements(By.TAG_NAME, value='tr')
    target_row = [el for el in row_list if front_quarter_str in el.text][0]
    target_row_cell_links = target_row.find_elements(By.TAG_NAME, value='a')
    fq_last = target_row_cell_links[len(target_row_cell_links) - 1]
    # fq_last = driver.find_element(by='id', value='ctl00_m_r6_C_t6_et_b5e8fd6b4f518dbfa10dedb5c6cd0040_LL')
    fq_last.send_keys(Keys.RETURN)

    # wait until second window is open
    wait.until(EC.number_of_windows_to_be(2))

    # set second window as active
    switch_to_new_window(driver, original_window)
    time.sleep(5)

    # check if there is data in the previous session
    coal_np_close = get_prev_day_data(dt, driver, original_window, download_dir)

    # get page with gas data
    driver.get('https://app.montelnews.com/Exchanges/ICE/DutchNatGas.aspx?137')
    time.sleep(5)

    # Choose last trading session
    data_table = driver.find_element(By.CSS_SELECTOR, value='#ctl00_m_r2_C_t2_et_table')
    row_list = data_table.find_elements(By.TAG_NAME, value='tr')
    target_row = [el for el in row_list if front_quarter_str in el.text][0]
    target_row_cell_links = target_row.find_elements(By.TAG_NAME, value='a')
    fq_last = target_row_cell_links[len(target_row_cell_links) - 1]
    # fq_last = driver.find_element(by='id', value='ctl00_m_r2_C_t2_et_2361a5c262b088be50e9ea1ff52f76e8_LL')
    fq_last.send_keys(Keys.RETURN)

    # wait until second window is open
    wait.until(EC.number_of_windows_to_be(2))

    # set second window as active
    switch_to_new_window(driver, original_window)
    time.sleep(5)

    # check if there is data in the previous session
    gas_np_close = get_prev_day_data(dt, driver, original_window, download_dir)

    # get page with carbon data
    driver.get('https://app.montelnews.com/Exchanges/ICE/Co2.aspx?86')
    time.sleep(5)

    # Choose last trading session
    data_table = driver.find_element(By.CSS_SELECTOR, value='#ctl00_m_rd2_C_t5_et_table')
    row_list = data_table.find_elements(By.TAG_NAME, value='tr')
    target_row = [el for el in row_list if mid_dec_str in el.text][0]
    target_row_cell_links = target_row.find_elements(By.TAG_NAME, value='a')
    fq_last = target_row_cell_links[len(target_row_cell_links) - 1]
    # fq_last = driver.find_element(by='id', value='ctl00_m_rd2_C_t5_et_40d5cd17e40f478082b8321264995f18_LL')
    fq_last.send_keys(Keys.RETURN)

    # wait until second window is open
    wait.until(EC.number_of_windows_to_be(2))

    # set second window as active
    switch_to_new_window(driver, original_window)
    time.sleep(5)

    # check if there is data in the previous session
    co2_np_close = get_prev_day_data(dt, driver, original_window, download_dir)

    # get oil brent data
    driver.get('https://app.montelnews.com/Exchanges/ICE/Brent.aspx?74')
    time.sleep(10)
    data_table = driver.find_element(By.CSS_SELECTOR, value='#ctl00_m_e0_C_t3_et_table')
    row_list = data_table.find_elements(By.TAG_NAME, value='tr')
    target_row = row_list[3].text.split(' ')
    # oil_last_price = driver.find_element(by='id', value='ctl00_m_e0_C_t3_et_0ba3fd3edc00a54941b7fd02ecb2d5aa_LL')
    # oil_last_price = float(oil_last_price.text)
    oil_last_price = float(target_row[8])
    # oil_last_delta = driver.find_element(by='id', value='ctl00_m_e0_C_t3_et_0ba3fd3edc00a54941b7fd02ecb2d5aa_Chg')
    # oil_last_delta = float(oil_last_delta.text)
    oil_last_delta = float(target_row[9])

    # close all the browser
    driver.close()
    driver.quit()

    result = {
        'coal_close': round(coal_close, 1),
        'coal_np_close': round(coal_np_close, 1),
        'gas_close': round(gas_close, 1),
        'gas_np_close': round(gas_np_close, 1),
        'co2_close': round(co2_close, 1),
        'co2_np_close': round(co2_np_close, 1),
        'oil_last_price': round(oil_last_price, 1),
        'oil_last_delta': round(oil_last_delta, 1)
    }

    return result


def load_forward_data(dt: date):
    """
    Loads data for german forward prices
    :param dt: target dateQ
    :param syspower_login:
    :param syspower_pw:
    :return:
    """

    series_list = ['EEXDEBQFR1', 'NPENOFUTBLQFR1']

    interval = 'day'
    if dt.weekday() < 2:
        lookup = 4
    else:
        lookup = 2
    series_url = generate_series_url(series_list, interval, dt - timedelta(days=lookup), dt)
    df = pd.read_csv(series_url, sep=';')
    german_close = round(df.EEXDEBQFR1.values[1], 2)
    delta_german_close = round(df.EEXDEBQFR1.values[1] - df.EEXDEBQFR1.values[0], 2)
    np_close = round(df.NPENOFUTBLQFR1.values[1], 2)
    delta_np_close = round(df.NPENOFUTBLQFR1.values[1] - df.NPENOFUTBLQFR1.values[0], 2)
    german_forward_data = {
        'german_close': german_close,
        'delta_german_close': delta_german_close,
        'np_close': np_close,
        'delta_np_close': delta_np_close
    }
    return german_forward_data
