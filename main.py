from utils import api, color, config, log
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
def startup():
    print("startup")
    if not os.path.exists("images"):
        os.makedirs("images")
    if not os.path.exists("data"):
        os.makedirs("data")


@app.get("/")
def home():
    return {"Hello": "World"}


@app.get("/images/{file_name}")
def get_image(file_name: str):
    if not os.path.exists(f"images/{file_name}"):
        raise HTTPException(status_code=404, detail="Not Found")
    return FileResponse(f"images/{file_name}", media_type="image/png")


@app.post("/upload/screenshot/cmb-life-bill")
async def uploadCmbLifeBillScreenshot(file: UploadFile, token: str = Form(), ignore_pending: int = Form(1), ignore_same: int = Form(1)):
    log.info("收到请求")
    if token != config.app["token"]:
        raise HTTPException(status_code=403, detail="Forbidden")
    if ignore_pending:
        log.info("ignore_pending")
    if ignore_same:
        log.info("ignore_same")

    api.login()
    api.init_data()
    log.info("完成随手记登录和数据更新")

    file_bytes = await file.read()
    bills_img = Image.open(io.BytesIO(file_bytes))
    lines = get_lines(bills_img)

    last_y = 0

    monthly_bills = get_monthly_bills()
    added_count = 0
    for y in lines:
        if last_y != 0:
            bill_img, bill_info = read_bill_info(bills_img, last_y, y)
            if bill_info is not None:
                # 忽略入账中
                if not (ignore_pending and bill_info["pending"] == "入账中"):
                    if "掌上生活还款" in bill_info["memo"]:
                        # 转账
                        todo = 1
                    else:
                        # 消费
                        bill_info = process_bill_info(bill_info)

                        if not ignore_same or find_same_bill(monthly_bills, bill_info) is None:
                            filename = f"images/{datetime.now().strftime('%Y%m%d%H%M%S%f')}.png"
                            bill_img.save(filename)
                            bill_info["url"] = api.upload(filename)
                            log.info(f"准备上传: {bill_info}")
                            api.payout(bill_info)
                            added_count += 1
                            monthly_bills = save_bill(monthly_bills, bill_info)
                        else:
                            log.info(f"忽略重复: {bill_info}")
                else:
                    log.info(f"忽略未入账: {bill_info}")

        last_y = y
    return {"result": "success", "count": added_count}


def get_lines(bills_img):
    rgb_img = bills_img.convert("RGB")
    point_counts = {}
    for y in range(0, bills_img.height):
        for x in range(0, bills_img.width // 2):
            rgb = rgb_img.getpixel((x, y))
            if color.is_same_color(rgb, (238, 238, 238), 1) or color.is_same_color(rgb, (246, 246, 246), 1):
                if y not in point_counts:
                    point_counts[y] = 0
                else:
                    point_counts[y] += 1
    lines = []
    for y, count in point_counts.items():
        if count > bills_img.width / 2 * 0.9:
            lines.append(y)
    log.info("完成图片扫描获得切割坐标")
    return lines


def process_bill_info(bill_info):
    if "悠饭" in bill_info["memo"] or "叮咚" in bill_info["memo"]:
        bill_info["category"] = "早午晚餐"
    elif "全家" in bill_info["memo"]:
        if bill_info["bill_time"].hour < 10:
            bill_info["category"] = "早午晚餐"
        else:
            bill_info["category"] = "茶水饮料"
    elif "星巴克" in bill_info["memo"]:
        bill_info["category"] = "茶水饮料"
    elif "饿了么" in bill_info["memo"] or "拉扎斯" in bill_info["memo"]:
        bill_info["category"] = "早午晚餐"
    elif "百果园" in bill_info["memo"]:
        bill_info["category"] = "水果零食"
    elif "京东" in bill_info["memo"]:
        bill_info["category"] = "家庭公共"
    elif "云上艾珀" in bill_info["memo"]:
        bill_info["category"] = "各类会员"
        bill_info["memo"] = "iCloud 会员"
    elif "网之易" in bill_info["memo"] or "App Store" in bill_info["memo"]:
        bill_info["category"] = "游戏"
    elif "电力公司" in bill_info["memo"]:
        bill_info["category"] = "水电煤气"
        bill_info["memo"] = "电费"
    elif "城投水务" in bill_info["memo"]:
        bill_info["category"] = "水电煤气"
        bill_info["memo"] = "水费"
    elif "美团" in bill_info["memo"] and bill_info["amount"] == "1.50":
        bill_info["category"] = "共享单车"
    elif "GOOGLE*CLOUD" in bill_info["memo"]:
        bill_info["category"] = "虚拟产品"
        bill_info["memo"] = "GCP"
    else:
        bill_info["category"] = "未分类支出"

    bill_info["account"] = "招行信用卡"
    bill_info["bill_time"] = bill_info["bill_time"].strftime("%Y-%m-%d %H:%M")
    return bill_info


def read_bill_info(bills_img, top, bottom):
    if abs(bottom - top - 200) > 10:
        return None

    bill_img = bills_img.crop((0, top, bills_img.width, bottom))

    memo_img = bill_img.crop((140, 40, 900, 100))
    memo = normal_ocr.ocr_for_single_line(numpy.array(memo_img.convert("RGB")))[0]

    amount_img = bill_img.crop((800, 100, bill_img.width - 30, 190))
    amount = float(amount_ocr.ocr_for_single_line(numpy.array(amount_img.convert("RGB")))[0].replace("¥", ""))

    category_time_img = bill_img.crop((140, 120, 800, 180))
    category_time = category_time_ocr.ocr_for_single_line(numpy.array(category_time_img.convert("RGB")))[0]

    m = re.match(r"^([^0-9a-zA-Z ]+)([\d/\s:]+)([\D]*)$", category_time)
    if len(m.groups()) == 3:
        category = m.groups()[0].strip()
        bill_time = m.groups()[1].strip()
        pending = m.groups()[2].strip()
        return (
            bill_img,
            {
                "category": category,
                "amount": amount,
                "memo": memo,
                "bill_time": datetime.strptime(f"{datetime.today().year}/{bill_time}", "%Y/%m/%d %H:%M"),
                "pending": pending,
            },
        )
    return None


def get_monthly_bills():
    monthly_bills = []
    monthly_bills_file_path = f"data/{datetime.now().strftime('%Y%m')}.json"
    if os.path.exists(monthly_bills_file_path):
        with open(monthly_bills_file_path, "r", encoding="utf-8") as monthly_bills_file:
            monthly_bills = json.load(monthly_bills_file)
    return monthly_bills


def find_same_bill(list, bill_info):
    for index, item in enumerate(list):
        if (
            item["account"] == bill_info["account"]
            and item["category"] == bill_info["category"]
            and item["bill_time"] == bill_info["bill_time"]
            and item["amount"] == bill_info["amount"]
            and item["memo"] == bill_info["memo"]
        ):
            return (index, item)
    return None


def save_bill(list, bill_info):
    monthly_bills_file_path = f"data/{datetime.now().strftime('%Y%m')}.json"
    same_bill = find_same_bill(list, bill_info)
    if same_bill:
        list[same_bill[0]] = bill_info
    else:
        list.append(
            {
                "account": bill_info["account"],
                "category": bill_info["category"],
                "bill_time": bill_info["bill_time"],
                "amount": bill_info["amount"],
                "memo": bill_info["memo"],
                "url": bill_info["url"],
            }
        )
    with open(monthly_bills_file_path, "w", encoding="utf-8") as file:
        json.dump(list, file, indent=4, ensure_ascii=False)
    return list
