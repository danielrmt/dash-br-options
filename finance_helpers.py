
import numpy as np
import pandas as pd
from scipy.stats import norm
from scipy import optimize


def black_scholes(spot, strike, selic, sigma, days, option_type='call'):
    r = np.log(1+selic/100)
    T = days / 252
    d1 = 1 / (sigma * np.sqrt(T)) * \
        (np.log(spot / strike) + (selic + sigma**2/2) * T)
    d2 = d1 - sigma * np.sqrt(T)
    PVK = strike * np.exp(-r * T)
    Nd1 = norm.cdf(d1)
    Nd2 = norm.cdf(d2)
    call_price = Nd1 * spot - Nd2 * PVK
    put_price = PVK - spot + call_price
    dNd1 = norm.pdf(d1)
    ret = {'type': option_type}

    ret['gamma'] = dNd1 / (spot * sigma * np.sqrt(T))
    ret['vega'] = spot * dNd1 * np.sqrt(T)

    if option_type == 'call':
        ret['delta'] = Nd1
        ret['theta'] = -(spot * dNd1 * sigma) / (2*np.sqrt(T)) - \
            r * strike * np.exp(-r*T) * Nd2
        ret['rho'] = strike * T * np.exp(-r*T) * Nd2
        ret['price'] = call_price
    elif option_type == 'put':
        ret['delta'] = Nd1 - 1
        ret['theta'] = -(spot * dNd1 * sigma) / (2*np.sqrt(T)) - \
            r * strike * np.exp(-r*T) * norm.cdf(-d2)
        ret['rho'] = - strike * T * np.exp(-r*T) * norm.cdf(-d2)
        ret['price'] = put_price

    return ret


def df_black_scholes(spot, strike, selic, sigma, days, option_type):
    df = pd.DataFrame(index=strike.index,
        columns=['delta','gamma','vega','theta','rho'])
    for i in list(df.index):
        bs = black_scholes(spot, strike[i], selic, sigma[i], days,
            option_type[i])
        for j in list(df.columns):
            df.loc[i, j] = bs[j]
    df['theta'] = df['theta'] / 252
    return df



def implied_vol(option_price, spot, strike, selic, days, option_type='call'):
    x = optimize.fsolve(
        lambda x: (
            black_scholes(spot, strike, selic, x, days, option_type)['price'] -
            option_price
            ),
        0.02
    )
    return x[0]
