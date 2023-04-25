import base64
import email
import imaplib
from datetime import datetime
import chardet

from bs4 import BeautifulSoup
from yuanfen import logger
from yuanfen.config import Config

credentials = Config("config/credentials.json")


def open_connection():
    hostname = credentials["emailImapHost"]
    username = credentials["emailUsername"]
    password = credentials["emailPassword"]
    connection = imaplib.IMAP4_SSL(hostname)
    connection.login(username, password)
    connection.select("INBOX", readonly=True)
    return connection


def get_latest_bills(count):
    with open_connection() as connection:
        _, [msg_ids] = connection.search(None, "SUBJECT", "每日信用管家".encode("utf-8"))
        latest_msg_ids = msg_ids.split()[-count:]
        logger.info(f"{latest_msg_ids}")
        bills = []
        for msg_id in latest_msg_ids:
            _, msg_data = connection.fetch(msg_id, "(RFC822)")
            raw = email.message_from_bytes(msg_data[0][1])
            for part in raw.walk():
                if part.get_content_type() == "text/html":
                    payload = part.get_payload(decode=True)
                    charset = chardet.detect(payload)["encoding"]
                    html_str = payload.decode(charset)
                    with open("logs/latest-bills.html", "w", encoding="utf-8") as html_file:
                        html_file.write(html_str)
                    soup = BeautifulSoup(html_str, "html.parser")
                    bill_date = soup.select("#loopHeader1 font")[1].get_text()[:10]
                    items = soup.select("#fixBand4")

                    for item in items:
                        bill_time = item.select("#fixBand5 font")[0].get_text()
                        currency = item.select("#fixBand12 font")[0].get_text()[:3]
                        amount = float(item.select("#fixBand12 font")[0].get_text()[4:])
                        memo = item.select("#fixBand12 font")[1].get_text()[10:]
                        if currency != "CNY":
                            logger.warn(f"非人民币账单: {bill_date} {bill_time} {currency} {amount} {memo}")
                            continue
                        bills.append(
                            {
                                "amount": amount,
                                "memo": memo,
                                "bill_time": datetime.strptime(f"{bill_date} {bill_time}", "%Y/%m/%d %H:%M:%S"),
                                "pending": False,
                                "url": "",
                            }
                        )
        return bills
