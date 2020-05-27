
import numpy as np
import pandas as pd
from scipy.stats import norm
from scipy import optimize


def black_scholes(spot, strike, selic, sigma, days, option_type='call', debug=False):
    r = np.log(1+selic/100)
    T = days / 252
    d1 = (np.log(spot / strike) + (r + sigma**2/2) * T) \
        / (sigma * np.sqrt(T)) 
    d2 = d1 - sigma * np.sqrt(T)
    PVK = strike * np.exp(-r * T)
    Nd1 = norm.cdf(d1)
    Nd2 = norm.cdf(d2)
    call_price = Nd1 * spot - Nd2 * PVK
    put_price = PVK - spot + call_price
    dNd1 = norm.pdf(d1)
    ret = pd.DataFrame()

    iscall = option_type == 'call'
    if debug:
        ret['d1'] = d1
        ret['d2'] = d2
        ret['Nd1'] = Nd1
        ret['Nd2'] = Nd2
        ret['PVK'] = PVK
        ret['sigT'] = sigma * np.sqrt(T)
    ret['price'] = np.where(iscall, call_price, put_price)
    ret['gamma'] = dNd1 / (spot * sigma * np.sqrt(T))
    ret['vega'] = spot * dNd1 * np.sqrt(T)
    ret['delta'] = np.where(iscall, Nd1, Nd1 - 1)
    ret['theta'] = np.where(
        iscall,
        -(spot * dNd1 * sigma) / (2*np.sqrt(T)) - r * PVK * Nd2,
        -(spot * dNd1 * sigma) / (2*np.sqrt(T)) - r * PVK * norm.cdf(-d2)
    )
    ret['rho'] = np.where(
        iscall,
        strike * T * np.exp(-r*T) * Nd2,
        - strike * T * np.exp(-r*T) * norm.cdf(-d2)
    )
    return ret


def implied_vol(option_price, spot, strike, selic, days, option_type='call'):
    x = optimize.fsolve(
        lambda x: (
            black_scholes(spot, strike, selic, x, days, option_type)['price'] -
            option_price
            ),
        0.02
    )
    return x[0]
