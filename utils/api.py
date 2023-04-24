import hashlib
import json
import re

import requests
from bs4 import BeautifulSoup
from yuanfen import logger
from yuanfen.config import Config

credentials = Config("config/credentials.json")

headers = {
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36",
}
session = requests.session()
payout_categories = []
income_categories = []
accounts = []


def login():
    email = credentials["feideeEmail"]
    password = credentials["feideePassword"]
    vccode, uid = get_vccode_and_uid()
    password = hash_password(password)
    password = hash_password(email + password)
    password = hash_password(password + vccode)
    params = {"email": email, "password": password, "uid": uid, "status": "1"}
    result = session.get("https://login.sui.com/login.do", params=params, headers=headers)
    logger.info(result.text)

    auth_redirect("GET", "https://login.sui.com/auth.do")

    result = session.post("https://www.sui.com/report_index.rmi", params={"m": "a"}, headers=headers)
    logger.info(result.text)


def init_data():
    global payout_categories
    global income_categories
    global accounts

    result = session.get("https://www.sui.com/tally/new.do", headers=headers)
    soup = BeautifulSoup(result.text, features="html.parser")

    payoutLis = soup.find(id="levelSelect-payout").find(id="ls-ul1-payout").find_all("li", recursive=False)
    payout_categories = []
    for payoutLi in payoutLis:
        lv1Id = payoutLi["id"][13:]
        lv1Name = payoutLi.find("span")["title"]
        payoutUl2 = payoutLi.find(id="ls-ul2-payout-" + lv1Id)
        payoutLi2s = payoutUl2.find_all("li", recursive=False)[:-1]
        payoutCat = {"id": lv1Id, "name": lv1Name, "subCat": []}
        payout_categories.append(payoutCat)
        for payoutLi2 in payoutLi2s:
            lv2id = payoutLi2["id"][13:]
            lv2name = payoutLi2.find("span")["title"]
            lv2Cat = {"id": lv2id, "name": lv2name}
            payoutCat["subCat"].append(lv2Cat)

    incomeLis = soup.find(id="levelSelect-income").find(id="ls-ul1-income").find_all("li", recursive=False)
    income_categories = []
    for incomeLi in incomeLis:
        lv1Id = incomeLi["id"][13:]
        lv1Name = incomeLi.find("span")["title"]
        incomeUl2 = incomeLi.find(id="ls-ul2-income-" + lv1Id)
        incomeLi2s = incomeUl2.find_all("li", recursive=False)[:-1]
        incomeCat = {"id": lv1Id, "name": lv1Name, "subCat": []}
        income_categories.append(incomeCat)
        for incomeLi2 in incomeLi2s:
            lv2id = incomeLi2["id"][13:]
            lv2name = incomeLi2.find("span")["title"]
            lv2Cat = {"id": lv2id, "name": lv2name}
            incomeCat["subCat"].append(lv2Cat)

    accountsUl = soup.find(id="ul_tb-inAccount-5")
    accountLis = accountsUl.find_all("li", recursive=False)
    accounts = []
    for li in accountLis:
        accid = li["id"][17:]
        accName = li.text
        accounts.append({"id": accid, "name": accName})


# 支出
def payout(bill_info):
    account_id = get_account_id(bill_info["account"])
    category_id = get_category_id("payout", bill_info["category"])
    params = {
        "id": bill_info["id"] if "id" in bill_info else 0,
        "account": account_id,  # 账户
        "category": category_id,  # 分类
        "store": bill_info["store"] if "store" in bill_info else 0,  # 商家
        "time": bill_info["bill_time"],  # 时间
        "project": bill_info["project"] if "project" in bill_info else 0,  # 项目
        "member": bill_info["member"] if "member" in bill_info else 0,  # 成员
        "memo": bill_info["memo"],  # 备注
        "url": bill_info["url"],  # 图片 URL
        "out_account": 0,  # 转出账户
        "in_account": 0,  # 转入账户
        "debt_account": "",  # 欠款账户
        "price": bill_info["amount"],  # 金额
        "price2": "",
    }
    result = session.post("https://www.sui.com/tally/payout.rmi", params=params, headers=headers)
    logger.info(f"支出记录创建结果: {result.text}")


def upload(filePath):
    result = session.post("https://www.sui.com/tally/new.do?opt=upload&transId=add", files={"imagefile": open(filePath, "rb")}, headers=headers)
    m = re.match(r"^.*'(.*)'.*$", result.text)
    url = ""
    if m and len(m.groups()) == 1:
        url = m.groups()[0].strip()
        logger.info(f"上传图片成功: {url}")
    else:
        logger.info(f"上传图片失败，result: {result.text}")
    return url


def get_vccode_and_uid():
    result = json.loads(session.get("https://login.sui.com/login.do?opt=vccode", headers=headers).text)
    return (result["vccode"], result["uid"])


def hash_password(str):
    return hashlib.sha1(bytes(str, encoding="ascii")).hexdigest()


def auth_redirect(method, url, data={}, count=1):
    if count > 5:
        logger.info("跳转太多次了")
        return
    result = None
    if method.upper() == "GET":
        result = session.get(url, params=data, headers=headers)
    elif method.upper() == "POST":
        result = session.post(url, data=data, headers=headers)
    soup = BeautifulSoup(result.text, features="html.parser")
    body = soup.find("body")
    if body.has_attr("onload"):
        onload = soup.find("body")["onload"]
        if onload == "document.forms[0].submit()":
            action = soup.find("form")["action"]
            method = soup.find("form")["method"]
            inputs = soup.find("form").find_all("input")
            for input in inputs:
                name = input["name"]
                value = input["value"]
                data[name] = value

            auth_redirect(method, action, data, count + 1)
    else:
        logger.info("认证跳转成功")


def get_account_id(account_name):
    global account
    for account in accounts:
        if account["name"] == account_name:
            return account["id"]
    return None


def get_category_id(type, category_name):
    global payout_categories
    global income_categories
    categories = payout_categories if type == "payout" else income_categories
    for category in categories:
        if category["name"] == category_name:
            return category["id"]
        else:
            for sub_category in category["subCat"]:
                if sub_category["name"] == category_name:
                    return sub_category["id"]
    return None
