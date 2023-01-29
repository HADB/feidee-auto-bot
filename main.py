from utils import api, config, log, json_utils, mail
import uvicorn
from fastapi import FastAPI
import json
import os


app = FastAPI()
monthly_bills_cache = {}


@app.on_event("startup")
def startup():
    print("startup")
    if not os.path.exists("images"):
        os.makedirs("images")
    if not os.path.exists("data"):
        os.makedirs("data")
    config.load_config()
    config.load_credentials()


@app.get("/")
def home():
    return {"Hello": "World"}


@app.get("/fetch_email")
def fetch_email(count: int = 1):
    config.load_config()
    config.load_credentials()
    bills = mail.get_latest_bills(count)
    log.info("获取邮件账单")
    api.login()
    api.init_data()
    log.info("完成随手记登录和数据更新")
    for bill_info in bills:
        bill_info = process_bill_info(bill_info)
        if find_same_bill(bill_info) is None:
            log.info(f"账单信息: {bill_info}")
            api.payout(bill_info)
            save_bill(bill_info)
        else:
            log.info(f"跳过重复账单")
    return {"result": "OK"}


def process_bill_info(bill_info):
    monthly_bills = get_monthly_bills(bill_info["bill_time"].strftime("%Y-%m"))
    bill_info["memo"] = get_memo(bill_info)
    bill_info["category"] = get_category(bill_info)
    bill_info["account"] = "招行信用卡"

    # 特殊场景
    if ("全家" in bill_info["memo"] or "罗森" in bill_info["memo"]) and bill_info["bill_time"].hour < 10:
        bill_info["category"] = "早午晚餐"
    elif "美团" in bill_info["memo"] and bill_info["amount"] == 1.50:
        bill_info["category"] = "共享单车"

    # 若为退款（退款的分类一般无法识别），则分类取最近一笔等额消费的分类
    if bill_info["amount"] < 0 and bill_info["category"] == "未分类支出":
        for bill in monthly_bills:
            if bill["amount"] == -bill_info["amount"]:
                bill_info["category"] = bill["category"]
                break
    return bill_info


def get_category(bill_info):
    for category in config.config["categories"]:
        for keyword in category["keywords"]:
            if keyword in bill_info["memo"]:
                return category["name"]
    return "未分类支出"


def get_memo(bill_info):
    for memo in config.config["memos"]:
        for keyword in memo["keywords"]:
            if keyword in bill_info["memo"]:
                return f"{memo['name']} {bill_info['memo']}"
    return bill_info["memo"]


def get_monthly_bills(key):
    global monthly_bills_cache
    if key in monthly_bills_cache:
        return monthly_bills_cache[key]
    else:
        monthly_bills_cache[key] = []
        monthly_bills_file_path = f"data/{key}.json"
        if os.path.exists(monthly_bills_file_path):
            with open(monthly_bills_file_path, "r", encoding="utf-8") as monthly_bills_file:
                monthly_bills_cache[key] = json.load(monthly_bills_file, object_hook=json_utils.datetime_hook)
        return monthly_bills_cache[key]


def find_same_bill(bill_info):
    monthly_bills = get_monthly_bills(bill_info["bill_time"].strftime("%Y-%m"))
    for index, item in enumerate(monthly_bills):
        if (
            item["account"] == bill_info["account"]
            and item["category"] == bill_info["category"]
            and item["bill_time"].strftime("%Y%m%d%H%M") == bill_info["bill_time"].strftime("%Y%m%d%H%M")
            and item["amount"] == bill_info["amount"]
            and item["memo"] == bill_info["memo"]
        ):
            return (index, item)
    return None


def save_bill(bill_info):
    global monthly_bills_cache
    key = bill_info["bill_time"].strftime("%Y-%m")
    monthly_bills_file_path = f"data/{key}.json"
    same_bill = find_same_bill(bill_info)
    if same_bill:
        monthly_bills_cache[key][same_bill[0]] = bill_info
    else:
        monthly_bills_cache[key].append(
            {
                "account": bill_info["account"],
                "category": bill_info["category"],
                "bill_time": bill_info["bill_time"],
                "amount": bill_info["amount"],
                "memo": bill_info["memo"],
                "url": bill_info["url"],
            }
        )
    monthly_bills_cache[key].sort(key=lambda b: b["bill_time"], reverse=True)
    with open(monthly_bills_file_path, "w", encoding="utf-8") as file:
        json.dump(monthly_bills_cache[key], file, indent=4, ensure_ascii=False, default=json_utils.json_serial)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
