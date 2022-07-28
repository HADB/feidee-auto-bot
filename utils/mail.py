import imaplib
from utils import config, log
import email
import base64
from bs4 import BeautifulSoup
from datetime import datetime


def open_connection():
    hostname = config.credentials["emailImapHost"]
    username = config.credentials["emailUsername"]
    password = config.credentials["emailPassword"]
    connection = imaplib.IMAP4_SSL(hostname)
    connection.login(username, password)
    connection.select("INBOX", readonly=True)
    return connection


def get_latest_bills():
    with open_connection() as connection:
        typ, [msg_ids] = connection.search(None, "SUBJECT", "每日信用管家".encode("utf-8"))
        latest_msg_id = msg_ids.split()[-1]
        log.info(f"{latest_msg_id}")
        typ, msg_data = connection.fetch(latest_msg_id, "(RFC822)")
        raw = email.message_from_bytes(msg_data[0][1])
        for part in raw.walk():
            if part.get_content_type() == "text/html":
                html_str = str(base64.b64decode(part.get_payload()), encoding="gbk")
                with open("logs/latest-bills.html", "w", encoding="utf-8") as html_file:
                    html_file.write(html_str)
                soup = BeautifulSoup(html_str, "html.parser")
                bill_date = soup.select("#loopHeader1 font")[1].get_text()[:10]
                items = soup.select("#fixBand4")
                bills = []
                for item in items:
                    bill_time = item.select("#fixBand5 font")[0].get_text()
                    bills.append(
                        {
                            "amount": float(item.select("#fixBand12 font")[0].get_text()[4:]),
                            "memo": item.select("#fixBand12 font")[1].get_text()[10:],
                            "bill_time": datetime.strptime(f"{bill_date} {bill_time}", "%Y/%m/%d %H:%M:%S"),
                            "pending": False,
                        }
                    )
                return bills
