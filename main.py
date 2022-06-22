from utils import api

if __name__ == "__main__":
    api.login()
    api.init_data()
    api.payout("现金", "其他支出", 1.23, "测试支出", "2022-06-22 16:00")
