# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
# flake8: noqa: F401

# --- Do not remove these libs ---
import numpy as np  # noqa
import pandas as pd  # noqa
from pandas import DataFrame
from functools import reduce

from freqtrade.strategy import (BooleanParameter, CategoricalParameter, DecimalParameter,
                                IStrategy, IntParameter)

# --------------------------------
# Add your lib to import here
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib


class DoubleBollingerStrategy(IStrategy):
    
    buy_sma20_drop_ratio = DecimalParameter(0.6, 0.8, decimals=1, default=0.8, space="buy")
    sell_sma5_higher_ratio = DecimalParameter(0.9, 1.3, decimals=1, default=1.3, space="sell")
    
    # Strategy interface version - allow new iterations of the strategy interface.
    # Check the documentation or the Sample strategy to get the latest version.
    INTERFACE_VERSION = 2

    # Minimal ROI designed for the strategy.
    # This attribute will be overridden if the config file contains "minimal_roi".
    minimal_roi = {
        "0": 0.579,
        "3653": 0.373,
        "19881": 0.161,
        "41906": 0
    }

    # Stoploss:
    stoploss = -0.048

    # Trailing stop:
    trailing_stop = True
    trailing_stop_positive = 0.294
    trailing_stop_positive_offset = 0.385
    trailing_only_offset_is_reached = True
   
    # Optimal timeframe for the strategy.
    timeframe = '1d'

    # Run "populate_indicators()" only for new candle.
    process_only_new_candles = False

    # These values can be overridden in the "ask_strategy" section in the config.
    use_sell_signal = True
    sell_profit_only = False
    ignore_roi_if_buy_signal = False

    # Number of candles the strategy requires before producing valid signals
    startup_candle_count: int = 30

    # Optional order type mapping.
    order_types = {
        'buy': 'limit',
        'sell': 'limit',
        'stoploss': 'market',
        'stoploss_on_exchange': False
    }

    # Optional order time in force.
    order_time_in_force = {
        'buy': 'gtc',
        'sell': 'gtc'
    }
    
    plot_config = {
        # Main plot indicators (Moving averages, ...)
        'main_plot': {
            'tema': {},
            'sar': {'color': 'white'},
        },
        'subplots': {
            # Subplots - each dict defines one additional plot
            "MACD": {
                'macd': {'color': 'blue'},
                'macdsignal': {'color': 'orange'},
            },
            "RSI": {
                'rsi': {'color': 'red'},
            }
        }
    }
    def informative_pairs(self):
        """
        Define additional, informative pair/interval combinations to be cached from the exchange.
        These pair/interval combinations are non-tradeable, unless they are part
        of the whitelist as well.
        For more information, please consult the documentation
        :return: List of tuples in the format (pair, interval)
            Sample: return [("ETH/USDT", "5m"),
                            ("BTC/USDT", "15m"),
                            ]
        """
        return []

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Adds several different TA indicators to the given DataFrame

        Performance Note: For the best performance be frugal on the number of indicators
        you are using. Let uncomment only the indicator you are using in your strategies
        or your hyperopt configuration, otherwise you will waste your memory and CPU usage.
        :param dataframe: Dataframe with data from the exchange
        :param metadata: Additional information, like the currently traded pair
        :return: a Dataframe with all mandatory indicators for the strategies
        """
        
        # Momentum Indicators
        # ------------------------------------
         # MACD
        macd = ta.MACD(dataframe)
        dataframe['macd'] = macd['macd']        
        dataframe['macdhist'] = macd['macdhist']
        
        bollinger = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=20, stds=2)
        dataframe['bb_lowerband20'] = bollinger['lower']
        
        bollinger = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=5, stds=2)
        dataframe['bb_lowerband5'] = bollinger['lower']   
        
        dataframe['sma5'] = ta.SMA(dataframe, timeperiod=5)
        

        return dataframe

    def populate_buy_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
     
        conditions = []
        # GUARDS AND TRENDS
        conditions.append(dataframe['close'] < dataframe['bb_lowerband20'])
        conditions.append(dataframe['close'] > dataframe['bb_lowerband5'])
        conditions.append(dataframe['bb_lowerband20'] > dataframe['bb_lowerband5'])
        # conditions.append(dataframe['slowk'] < 25)
        # conditions.append(dataframe['slowk'] > dataframe['slowd'])
        conditions.append(dataframe['macdhist'].shift(1) < 0)
        conditions.append(dataframe['macdhist'] > dataframe['macdhist'].shift(1))
        conditions.append(dataframe['volume'] > 0)

        if conditions:
            dataframe.loc[
                reduce(lambda x, y: x & y, conditions),
                'buy'] = 1

        return dataframe   
      

    def populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Based on TA indicators, populates the sell signal for the given dataframe
        :param dataframe: DataFrame populated with indicators
        :param metadata: Additional information, like the currently traded pair
        :return: DataFrame with buy column
        """
        conditions = []
        # GUARDS AND TRENDS
        conditions.append(dataframe['close'] > dataframe['sma5'])
        conditions.append(dataframe['volume'] > 0)

        if conditions:
            dataframe.loc[
                reduce(lambda x, y: x & y, conditions),
                'buy'] = 1

        return dataframe
    
        # dataframe.loc[
        #     (
        #         (dataframe['close'] > dataframe['sma5']*1.1) &
        #         (dataframe['volume'] > 0)  # Make sure Volume is not 0
        #     ),
        #     'sell'] = 1
        # return dataframe
    