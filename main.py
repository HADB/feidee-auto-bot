from utils import api, color, config
from fastapi import FastAPI, File, UploadFile
import json
from PIL import Image
import io
import os
from cnocr import CnOcr
from datetime import datetime
import numpy
import shutil
import re

app = FastAPI()


@app.on_event("startup")
async def startup():
    print("startup")
    print("ignore_pending_bill", config.getboolean("app", "ignore_pending_bill"))
    if not os.path.exists("images"):
        os.makedirs("images")


# api.login()
# api.init_data()
# api.payout("现金", "其他支出", 1.23, "测试支出", "2022-06-22 16:00")


@app.get("/")
async def home():
    return {"Hello": "World"}


@app.post("/upload/screenshot/cmb-life-bill")
async def uploadCmbLifeBillScreenshot(file: UploadFile):
    shutil.rmtree("images")
    os.makedirs("images")
    ocr = CnOcr()
    amount_ocr = CnOcr(cand_alphabet="¥0123456789.")
    category_and_time_ocr = CnOcr(cand_alphabet="-0123456789/: 餐饮美食购物百货交通出行休闲娱乐生活服务其他还款退款入账中")
    contents = await file.read()
    image = Image.open(io.BytesIO(contents))
    rgb_img = image.convert("RGB")
    point_counts = {}
    for h in range(0, image.height):
        for w in range(0, image.width):
            rgb = rgb_img.getpixel((w, h))
            if color.is_same_color(rgb, (238, 238, 238), 1) or color.is_same_color(rgb, (246, 246, 246), 1):
                if h not in point_counts:
                    point_counts[h] = 0
                else:
                    point_counts[h] += 1
    # print(point_counts)
    line_heights = []
    for h, count in point_counts.items():
        if count > 1000:
            print(h, count)
            line_heights.append(h)
    last_height = 0
    for h in line_heights:
        if last_height != 0 and h - last_height > 190 and h - last_height < 210:
            filename = f"images/{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"
            cropped = image.crop((0, last_height, image.width, h))
            cropped.save(f"{filename}.png")
            memo = cropped.crop((140, 40, 900, 100))
            memo.save(f"{filename}-momo.png")
            memo_text = ocr.ocr_for_single_line(numpy.array(memo.convert("RGB")))[0]

            amount = cropped.crop((800, 100, cropped.width - 30, 190))
            amount.save(f"{filename}-amount.png")
            amount_text = amount_ocr.ocr_for_single_line(numpy.array(amount.convert("RGB")))[0].replace("¥", "")

            category_and_time = cropped.crop((140, 120, 800, 180))
            category_and_time.save(f"{filename}-time.png")
            category_and_time_text = category.ocr_for_single_line(numpy.array(category_and_time.convert("RGB")))[0]
            m = re.match(r"^([^0-9a-zA-Z ]+)([\d/\s:]+)([\D]*)$", category_and_time_text)
            if len(m.groups()) < 3:
                last_height = h
                continue
            category = m.groups()[0].strip()
            bill_time = m.groups()[1].strip()
            pending = m.groups()[2].strip()
            # print(m.groups()[0].strip(), m.groups()[1].strip(), m.groups()[2].strip())

            # 忽略入账中
            if not (config.getboolean("app", "ignore_pending_bill") and pending == "入账中"):

                bill_time = datetime.strptime(f"{datetime.today().year}/{bill_time}", "%Y/%m/%d %H:%M")
                if "掌上生活还款" in memo_text:
                    # 转账
                    todo = 1
                else:
                    # 消费
                    if "悠饭" in memo_text or "叮咚" in memo_text:
                        category = "早午晚餐"
                    elif "全家" in memo_text:
                        if bill_time.hour < 10:
                            category = "早午晚餐"
                        else:
                            category = "茶水饮料"
                    elif "星巴克" in memo_text:
                        category = "茶水饮料"
                    elif "饿了么" in memo_text or "拉扎斯" in memo_text:
                        category = "早午晚餐"
                    elif "京东" in memo_text:
                        category = "家庭公共"
                    elif "云上艾珀" in memo_text:
                        category = "各类会员"
                        memo_text = "iCloud 会员"
                    elif "网之易" in memo_text or "App Store" in memo_text:
                        category = "游戏"
                    elif "电力公司" in memo_text:
                        category = "水电煤气"
                        memo_text = "电费"
                    elif "城投水务" in memo_text:
                        category = "水电煤气"
                        memo_text = "水费"
                    elif "美团" in memo_text and amount == "1.50":
                        category = "共享单车"
                    elif "GOOGLE*CLOUD" in memo_text:
                        category = "虚拟产品"
                        memo_text = "GCP"
                    else:
                        category = "未分类支出"

                    # api.payout("招行信用卡", category, amount_text, memo_text, bill_time)
                    print("招行信用卡", category, amount_text, memo_text, bill_time)
        last_height = h
    return {"width": image.width, "height": image.height, "rows": line_heights}
