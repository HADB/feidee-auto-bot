import requests
import json
import hashlib
from utils import config, log
from bs4 import BeautifulSoup

headers = {
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36",
}
session = requests.session()


def login():
    email = config.credentials["feideeEmail"]
    password = config.credentials["feideePassword"]
    vccode, uid = get_vccode_and_uid()
    password = hash_password(password)
    password = hash_password(email + password)
    password = hash_password(password + vccode)
    params = {"email": email, "password": password, "uid": uid, "status": "0"}
    result = session.get(
        "https://login.sui.com/login.do", params=params, headers=headers
    )
    log.info(result.text)

    auth_redirect("GET", "https://login.sui.com/auth.do", {}, 1)

    result = session.post(
        "https://www.sui.com/report_index.rmi", params={"m": "a"}, headers=headers
    )
    log.info(result.text)


def get_vccode_and_uid():
    result = json.loads(
        session.get("https://login.sui.com/login.do?opt=vccode", headers=headers).text
    )
    return (result["vccode"], result["uid"])


def hash_password(str):
    return hashlib.sha1(bytes(str, encoding="ascii")).hexdigest()


def auth_redirect(method, url, data, count):
    if count > 5:
        log.info("跳转太多次了")
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
            data = {}
            for input in inputs:
                name = input["name"]
                value = input["value"]
                data[name] = value

            auth_redirect(method, action, data, count + 1)
    else:
        log.info("认证跳转成功")
