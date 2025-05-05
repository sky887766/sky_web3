import json
import random
import time
from decimal import Decimal

import requests
from eth_account import Account
from loguru import logger
from web3 import Web3

url = "https://api.jager.meme/api/holder/claimReward"

private_key = ""  # 请替换为你的实际私钥
wallet_address = Account.from_key(private_key).address
limit_jagerbnb = 150000  # 自己设置达到多少jagerbnb就去领取，太少了gas不划算

payload = {"address": wallet_address}
headers = {
    "accept": "application/json",
    "accept-language": "zh-CN,zh;q=0.9",
    "authorization": "Bearer undefined",
    "content-type": "application/json",
    "origin": "https://jager.meme",
    "priority": "u=1, i",
    "referer": "https://jager.meme/",
}

bsc_rpc = "" # 替换一个你常用的BSC RPC
w3 = Web3(Web3.HTTPProvider(bsc_rpc))

abi = [
    {
        "inputs": [
            {"internalType": "address", "name": "account", "type": "address"},
            {"internalType": "uint256", "name": "jagerAmount", "type": "uint256"},
            {"internalType": "uint256", "name": "jagerBnbAmount", "type": "uint256"},
            {"internalType": "uint256", "name": "deadline", "type": "uint256"},
            {"internalType": "bytes", "name": "sign", "type": "bytes"}
        ],
        "name": "claim",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

while True:
    try:
        response = requests.request("POST", url, data=json.dumps(payload), headers=headers)
        if response.status_code == 200 and response.json()['message'] == 'OK':
            data = response.json()
            jager = data['data']['jager']
            jagerBNB = data['data']['jagerBNB']
            deadline = data['data']['deadline']
            sign = data['data']['sign']
            logger.info(f'当前待领取Jager: {jager}')
            logger.info(f'当前待领取JagerBNB: {jagerBNB}')
            if int(float(jagerBNB)) >= limit_jagerbnb:
                logger.info('JagerBNB待领取达到设定的目标,准备领取...')
                contract_address = "0x0b29e8FdA0a77abD089c23736efA9E269bA101f5"
                contract = w3.eth.contract(address=w3.to_checksum_address(contract_address), abi=abi)
                tx = contract.functions.claim(
                    wallet_address,
                    int(f"{Decimal(jager) * 10 ** 18:.0f}"),
                    int(f"{Decimal(jagerBNB) * 10 ** 18:.0f}"),
                    deadline,
                    bytes.fromhex(sign[2:])
                ).build_transaction({
                    'from': wallet_address,
                    'nonce': w3.eth.get_transaction_count(w3.to_checksum_address(wallet_address)),
                    'gas': random.randint(300000, 500000),
                    'gasPrice': w3.to_wei(1.5, 'gwei'),
                    'chainId': 56,
                })
                signed_tx = w3.eth.account.sign_transaction(tx, private_key)
                tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
                logger.info(f"交易已提交,等待交易状态返回 > Hash: 0x{tx_hash.hex()}")
                receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
                if receipt['status'] == 1:
                    logger.success(f"领取成功,10分钟后再次查询...")
                else:
                    logger.error(f"领取失败,10分钟后再次查询...")
            else:
                logger.warning('JagerBNB待领取太少了,10分钟后再次查询...')
            time.sleep(10 * 60)
        else:
            logger.error(f'获取分红数据出错,10秒后获取...{response.text}')
            time.sleep(10)
    except Exception as e:
        logger.error(e)
        time.sleep(10)
