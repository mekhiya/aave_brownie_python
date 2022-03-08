from sre_constants import SUCCESS
from brownie import config, interface, network
from scripts.get_weth import get_weth
from scripts.helpful_scripts import get_account
from web3 import Web3

amount = Web3.toWei(0.1, "ether")


def main():
    account = get_account()
    erc20_address = config["networks"][network.show_active()]["weth_token"]
    print(f"Network active is {network.show_active()}")
    if network.show_active() in ["mainnet-fork-dev"]:
        get_weth()
        print(f"Received 0.1 ETH")

    lending_pool_address = get_lending_pool()
    lending_pool = interface.ILendingPool(lending_pool_address)

    approve_erc20(amount, lending_pool.address, erc20_address, account)
    print("Depositing...")
    tx = lending_pool.deposit(
        erc20_address, amount, account.address, 0, {"from": account}
    )
    tx.wait(1)
    print("Deposited!")
    borrowable_eth, total_eth = get_borrowable_data(lending_pool, account)
    print("Let's borrow...")
    # Dai in terms of ETH value
    dai_eth_price = get_asset_price(
        config["networks"][network.show_active()]["dai_eth_price_feed"]
    )
    # beow lin converts borrowable eth to borrow dai & using just 95%
    amount_dai_to_borrow = (1 / dai_eth_price) * (borrowable_eth * 0.095)
    print(f"We are goign to borrow {amount_dai_to_borrow} DAI")
    # Now we will borrow
    dai_token_address = config["networks"][network.show_active()]["dai_token"]
    borrow_tx = lending_pool.borrow(
        dai_token_address,
        Web3.toWei(amount_dai_to_borrow, "ether"),
        1,
        0,
        account.address,
        {"from": account},
    )
    borrow_tx.wait(1)
    print("We borrowed some DAI")
    get_borrowable_data(lending_pool, account)
    repay_all(amount, lending_pool, account)
    get_borrowable_data(lending_pool, account)


def repay_all(amount, lending_pool, account):
    approve_erc20(
        Web3.toWei(amount, "ether"),
        lending_pool,
        config["networks"][network.show_active()]["dai_token"],
        account,
    )
    repay_tx = lending_pool.repay(
        config["networks"][network.show_active()]["dai_token"],
        amount,
        1,
        account.address,
        {"from": account},
    )
    repay_tx.wait(1)
    print("Your just deposited,  borrowed amd repayed with Aave, brownie & Checklink ")


def get_asset_price(price_feed_address):
    dai_eth_priceFeed = interface.AggregatorV3Interface(price_feed_address)
    latest_price = dai_eth_priceFeed.latestRoundData()[1]
    converted_latest_price = Web3.fromWei(latest_price, "ether")
    print(f"DAI / ETH price is {converted_latest_price}")
    return float(converted_latest_price)


def get_borrowable_data(lending_pool, account):
    (
        totalCollateralETH,
        totalDebtETH,
        availableBorrowsETH,
        currentLiquidationThreshold,
        ltv,
        healthFactor,
    ) = lending_pool.getUserAccountData(account.address)
    available_Borrow_ETH = Web3.fromWei(availableBorrowsETH, "ether")
    total_Collateral_ETH = Web3.fromWei(totalCollateralETH, "ether")
    total_Debt_ETH = Web3.fromWei(totalDebtETH, "ether")
    print(f"You have {total_Collateral_ETH} ETH deposited.")
    print(f"You have {total_Debt_ETH} ETH borrowed.")
    print(f"You can borrow {available_Borrow_ETH} worth of ETH.")
    return (float(available_Borrow_ETH), float(total_Debt_ETH))


def approve_erc20(amount, spender, erc20_address, account):
    print("Approving ERC20 token...")
    erc20 = interface.IERC20(erc20_address)
    tx = erc20.approve(spender, amount, {"from": account})
    tx.wait(1)
    print("Approved")
    return tx


def get_lending_pool():
    lending_pool_addresses_provider = interface.ILendingPoolAddressesProvider(
        config["networks"][network.show_active()]["lending_pool_addresses_provider"]
    )
    lending_pool_address = lending_pool_addresses_provider.getLendingPool()
    return lending_pool_address
