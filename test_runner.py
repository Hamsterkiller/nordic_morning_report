from datetime import date, timedelta
from runner import generateMorningReport


if __name__ == '__main__':

    sp_login = 'ilya.zemskov@skmenergy.com'
    sp_pw = 'Ilyaz1987'
    dt = date.today() - timedelta(days=1)

    generateMorningReport(dt, 'D:\\tmp\\', sp_login, sp_pw);

    pass