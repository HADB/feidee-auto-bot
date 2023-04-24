FROM python:3

WORKDIR /app
COPY requirements.txt /app
RUN pip install --no-cache-dir -r requirements.txt -i https://git.yuanfen.net:5443/api/v4/projects/230/packages/pypi/simple --extra-index-url=https://pypi.tuna.tsinghua.edu.cn/simple

COPY . /app
CMD ["python", "-u", "main.py"]