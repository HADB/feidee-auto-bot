from utils import api, color, config
from fastapi import FastAPI, Form, UploadFile, HTTPException
from fastapi.responses import FileResponse
import json
from PIL import Image
import io
import os
from cnocr import CnOcr
from datetime import datetime
import numpy
import re

app = FastAPI()
normal_ocr = CnOcr()
amount_ocr = CnOcr(cand_alphabet="¥0123456789.")
category_time_ocr = CnOcr(cand_alphabet="-0123456789/: 餐饮美食购物百货交通出行休闲娱乐生活服务其他还款退款入账中")


@app.on_event("startup")
async def startup():
    print("startup")
    if not os.path.exists("images"):
        os.makedirs("images")
    if not os.path.exists("data"):
        os.makedirs("data")


@app.get("/")
async def home():
    return {"Hello": "World"}


@app.get("/images/{file_name}")
async def get_image(file_name: str):
    if not os.path.exists(f"images/{file_name}"):
        raise HTTPException(status_code=404, detail="Not Found")
    return FileResponse(f"images/{file_name}", media_type="image/png")


@app.post("/upload/screenshot/cmb-life-bill")
async def uploadCmbLifeBillScreenshot(file: UploadFile, token: str = Form(), ignore_pending: int = Form(1), ignore_same: int = Form(1)):
    if token != config.app["token"]:
        raise HTTPException(status_code=403, detail="Forbidden")
    if ignore_pending:
        print("ignore_pending")
    if ignore_same:
        print("ignore_same")
    api.login()
    api.init_data()

    file_bytes = await file.read()
    bills_img = Image.open(io.BytesIO(file_bytes))
    rgb_img = bills_img.convert("RGB")
    point_counts = {}
    for y in range(0, bills_img.height):
        for x in range(0, bills_img.width):
            rgb = rgb_img.getpixel((x, y))
            if color.is_same_color(rgb, (238, 238, 238), 1) or color.is_same_color(rgb, (246, 246, 246), 1):
                if y not in point_counts:
                    point_counts[y] = 0
                else:
                    point_counts[y] += 1
    # print(point_counts)
    lines = []
    for y, count in point_counts.items():
        if count > 1000:
            lines.append(y)
    last_y = 0
    monthly_bills = get_monthly_bills()
    added_count = 0
    for y in lines:
        if last_y != 0 and abs(y - last_y - 200) < 10:
            filename = f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
            current_bill_img = bills_img.crop((0, last_y, bills_img.width, y))

            memo_img = current_bill_img.crop((140, 40, 900, 100))
            memo = normal_ocr.ocr_for_single_line(numpy.array(memo_img.convert("RGB")))[0]

            amount_img = current_bill_img.crop((800, 100, current_bill_img.width - 30, 190))
            amount = float(amount_ocr.ocr_for_single_line(numpy.array(amount_img.convert("RGB")))[0].replace("¥", ""))

            category_time_img = current_bill_img.crop((140, 120, 800, 180))
            category_time = category_time_ocr.ocr_for_single_line(numpy.array(category_time_img.convert("RGB")))[0]
            m = re.match(r"^([^0-9a-zA-Z ]+)([\d/\s:]+)([\D]*)$", category_time)
            if len(m.groups()) < 3:
                last_y = y
                continue
            category = m.groups()[0].strip()
            bill_time = m.groups()[1].strip()
            pending = m.groups()[2].strip()

            # 忽略入账中
            if not (ignore_pending and pending == "入账中"):
                bill_time = datetime.strptime(f"{datetime.today().year}/{bill_time}", "%Y/%m/%d %H:%M")
                if "掌上生活还款" in memo:
                    # 转账
                    todo = 1
                else:
                    # 消费
                    if "悠饭" in memo or "叮咚" in memo:
                        category = "早午晚餐"
                    elif "全家" in memo:
                        if bill_time.hour < 10:
                            category = "早午晚餐"
                        else:
                            category = "茶水饮料"
                    elif "星巴克" in memo:
                        category = "茶水饮料"
                    elif "饿了么" in memo or "拉扎斯" in memo:
                        category = "早午晚餐"
                    elif "百果园" in memo:
                        category = "水果零食"
                    elif "京东" in memo:
                        category = "家庭公共"
                    elif "云上艾珀" in memo:
                        category = "各类会员"
                        memo = "iCloud 会员"
                    elif "网之易" in memo or "App Store" in memo:
                        category = "游戏"
                    elif "电力公司" in memo:
                        category = "水电煤气"
                        memo = "电费"
                    elif "城投水务" in memo:
                        category = "水电煤气"
                        memo = "水费"
                    elif "美团" in memo and amount == "1.50":
                        category = "共享单车"
                    elif "GOOGLE*CLOUD" in memo:
                        category = "虚拟产品"
                        memo = "GCP"
                    else:
                        category = "未分类支出"

                    if ignore_same and find_same_bill(monthly_bills, "招行信用卡", category, bill_time, amount, memo):
                        print("HAS", "招行信用卡", category, bill_time, amount, memo)
                    else:
                        print("NEW", "招行信用卡", category, bill_time, amount, memo)
                        current_bill_img.save(f"images/{filename}.png")
                        api.payout(
                            "招行信用卡",
                            category,
                            bill_time,
                            amount,
                            memo,
                            f"https://fab.yuanfen.net:5443/images/{filename}.png",
                        )
                        added_count += 1
                        monthly_bills = save_bill(monthly_bills, "招行信用卡", category, bill_time, amount, memo, f"https://fab.yuanfen.net:5443/images/{filename}.png")

        last_y = y
    return {"result": "success", "count": added_count}


def get_monthly_bills():
    monthly_bills = []
    monthly_bills_file_path = f"data/{datetime.now().strftime('%Y%m')}.json"
    if os.path.exists(monthly_bills_file_path):
        with open(monthly_bills_file_path, "r", encoding="utf-8") as monthly_bills_file:
            monthly_bills = json.load(monthly_bills_file)
    return monthly_bills


def find_same_bill(list, account, category, bill_time, amount, memo):
    for item in list:
        if (
            item["account"] == account
            and item["category"] == category
            and item["bill_time"] == bill_time.strftime("%Y-%m-%d %H:%M")
            and item["amount"] == amount
            and item["memo"] == memo
        ):
            return item
    return None


def save_bill(list, account, category, bill_time, amount, memo, url):
    monthly_bills_file_path = f"data/{datetime.now().strftime('%Y%m')}.json"
    list.append({"account": account, "category": category, "bill_time": bill_time.strftime("%Y-%m-%d %H:%M"), "amount": amount, "memo": memo, "url": url})
    with open(monthly_bills_file_path, "w", encoding="utf-8") as file:
        json.dump(list, file, indent=4, ensure_ascii=False)
    return list
