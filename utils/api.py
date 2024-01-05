import hashlib
import json
import re

import requests
from yuanfen import Config, Logger

credentials = Config("config/credentials.yaml")
logger = Logger()

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Device": '{"model":"browser","platform":"MacIntel","os_version":"","device_id":"fed-kKleNtOQJzIaDiOg2rjUgIDX5cfw","product_name":"cab-web","product_version":"1.0","locale":"zh-CN","time_zone":"Asia/Shanghai"}',
}
session = requests.session()
expense_categories = []
income_categories = []
accounts = []


def login():
    global accounts, expense_categories, income_categories
    email = credentials["feideeEmail"]
    password = credentials["feideePassword"]
    vccode, uid = get_vccode_and_uid()
    password = hash_password(password)
    password = hash_password(email + password)
    password = hash_password(password + vccode)
    params = {"email": email, "password": password, "uid": uid, "status": "1"}

    # login
    session.get("https://login.sui.com/login.do", params=params, headers=headers, timeout=10)

    # auth
    headers["Accept"] = "application/json, text/plain, */*"
    headers["Content-Type"] = "application/json;charset=UTF-8"
    headers["Origin"] = "https://yunres.sui.com"
    auth = session.get("https://login.sui.com/auth", headers={**headers, "Client-Key": "1FE29E0EC821473D8B81226FD516F798"}, timeout=10).json()
    headers["Authorization"] = f"Bearer {auth['object']['token']}"

    # init data
    headers["Client-Key"] = "PiVEoJM9OHFS8xFlnD3CuSrJgRgyVLwS"
    headers["Trading-Entity"] = credentials["accountBookId"]
    accounts = session.get("https://yun.feidee.net/cab-config-ws/v2/account-book/accounts?scene=Common", headers=headers, timeout=10).json()["data"]
    expense_categories = session.get("https://yun.feidee.net/cab-config-ws/v2/account-book/categories?trade_type=Expense", headers=headers, timeout=10).json()["data"]
    income_categories = session.get("https://yun.feidee.net/cab-config-ws/v2/account-book/categories?trade_type=Income", headers=headers, timeout=10).json()["data"]

    logger.info("login success")


# 支出
def expense(bill_info):
    account_id = get_account_id(bill_info["account"])
    category_id = get_category_id(expense_categories, bill_info["category"])
    data = {
        "account": {"id": account_id},  # 账户
        "amount": str(bill_info["amount"]),  # 金额
        "category": {"id": category_id},  # 分类
        "images": [],
        "member": {"id": ""},
        "merchant": {"id": ""},
        "project": {"id": ""},
        "remark": bill_info["memo"],  # 备注
        "transaction_time": int(bill_info["bill_time"].timestamp() * 1000),  # 时间
    }
    session.post("https://yun.feidee.net/cab-accounting-ws/v2/account-book/transaction/expense", data=json.dumps(data), headers=headers, timeout=10).json()
    logger.info(f"支出记录创建成功")


def get_vccode_and_uid():
    result = session.get("https://login.sui.com/login.do?opt=vccode", headers=headers, timeout=10).json()
    return (result["vccode"], result["uid"])


def hash_password(str):
    return hashlib.sha1(bytes(str, encoding="ascii")).hexdigest()


def get_account_id(account_name):
    for account_group in accounts:
        for account in account_group["accounts"]:
            if account["name"] == account_name:
                return account["id"]
    return None


def get_category_id(categories, category_name):
    for category in categories:
        for sub_category in category["sub_categories"]:
            if sub_category["name"] == category_name:
                return sub_category["id"]
    return None
