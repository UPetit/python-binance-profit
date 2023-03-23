# Welcome to python-binance-profit GitHub repository!
## Notes
The script allows you to place a buy order and automatically place an [OCO order](https://www.investopedia.com/terms/o/oco.asp) to secure (and exit) your trade.
It's using the binance API python wrapper from @sammchardy [python-binance](https://github.com/sammchardy/python-binance).
If you want to create Binance account, here's [my referral link](https://www.binance.com/en/register?ref=UYUPUS6W): earn 10% commission on the fees from my trades.
## Disclaimer
Even if the scripts are easy to understand, errors exists that's why the [Issues](https://github.com/UPetit/python-binance-profit/issues) section is important to report any bug that you may find. I recommend to use the [latest release](https://github.com/UPetit/python-binance-profit/releases/latest) because it has been tested multiple times compared to the other branches.
## Requirements
- Python 3.8+, if you don't have it yet, you can install it:
  - Following [official instructions](https://docs.python.org/3/using/index.html)
  - With [Anaconda](https://www.anaconda.com/))

- Create an API key after logging in to your Binance account https://www.binance.com/en/my/settings/api-management:
  - Check both `Enable Reading` and `Enable Spot & Margin Trading`
  - Save carefully your `API key` and your `Secret key` (⚠️ the last one won't be visible again at your next login)
  - Add your Binance API key to a environement variable called `API_KEY`
  - Add your Binance Secret key to a environement variable called `SECRET_KEY`

_Note: If you're using Windows, you might need to install [Microsoft Visual C++ 14.0+](https://visualstudio.microsoft.com/visual-cpp-build-tools/)_
## Installation
- Clone the repository
```
git clone https://github.com/UPetit/python-binance-profit.git
```
- Install the dependencies
```
pip install -r requirements.txt
```

- Linux version without anaconda
```bash
# restrict lib install to the local venv
python3 -m venv venv
source ./venv/bin/activate
pip install -r requirements.txt
```
## Use cases
### Run a Buy order (limit or market) followed by an OCO Sell order
#### Script logic
The script will check that both the price and the quantity are compliant with Binance rules for the selected symbol.
If both are validated, the buy order will be sent to the market and the script will wait until it's filled.
Once it's executed the OCO order will be prepared: the price with profit will be calculated according to the profit percentage that has been provided, same for the stoploss price.
The OCO order will be sent to the market and the script will return the two related orders and then quit.
#### Instructions
1. First, choose the crypto pair you want to trade. We call it the **symbol** (string).
> Example: If you want to trade BTC with USDT, the symbol will be BTCUSDT (as long as this is an available symbol in Binance).
2. For a limit buy order:
   - Define how much of the base asset you want to buy. We call it the **quantity** (Decimal).
   - Define what is the price (for 1 unit of the base asset) you want to buy the quantity defined above. We call it the **price** (Decimal).
> Example: if you trade the **symbol** BTCUSDT, you need to define the quantity of BTC (base asset) and the BTC price in USDT (quote asset) you're willing to pay.
3. For a market buy order:
  - Define the amount of quote asset you want to spend. We call it the **total** (Decimal).
> Example: if you trade with BTCUSDT, you need to define how much you want to spend in USDT for BTC.
4. Finally have to define your profit and stoploss percentages to exit the trade (this will be applied to the OCO sell order).
We call them respectively **profit** (Decimal) and **loss** (Decimal).
> If you want to make 2% of profit and put a stoploss a 1%, your profit should be 2 and the loss 1 (as Decimals between 0.0 and 100.0)

⚠️ Please not that if the quantity and/or price formats are not following Binance rules, your Limit buy order won't be validated and the script will stop before submitting to order to the market.
> How to know the prices formats ? Go to the Binance market of your **symbol** you want to trade, check the current prices and quantities going through the market to know how many decimals you can use for both of them. For instance for BTCUSDT: the BTC quantity is using 6 decimals and the USDT price is using 2 decimals.

5. Run the script using the parameters you've just defined by replacing with your values:
**Limit buy order followed by an OCO sell order:**
```
python execute_orders.py --symbol YOUR_SYMBOL --buy_type limit --quantity YOUR_QUANTITY --price YOUR_PRICE --profit YOUR_PROFIT --loss YOUR_LOSS
```
*Example: If you want to trade BTC against USDT, buy 0.251897 BTC at 31488.69 USDT (per BTC) and then you want to sell it to make a 4% profit and a potential loss of 1%, you'll execute the script like this:*
```
python execute_orders.py --symbol BTCUSDT --buy_type limit --quantity 0.251897 --price 31488.69 --profit 4 --loss 1
```
**Market buy order followed by an OCO sell order:**
```
python execute_orders.py --symbol YOUR_SYMBOL --buy_type market --total TOTAL_AMOUNT --profit YOUR_PROFIT --loss YOUR_LOSS 
```
*Example: If you want to trade BTC against USDT, buy 100 USDT of BTC and then you want to sell it to make a 4% profit and a potential loss of 1%, you'll execute the script like this:*
```
python execute_orders.py --symbol BTCUSDT --buy_type market --total 100.0 --profit 4 --loss 1 
```
---
Enjoy!
Don't hesitate to send me feedbacks and report issues :) Thank you!
