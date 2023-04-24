FROM python:alpine

RUN pip config set global.index-url https://git.yuanfen.net:5443/api/v4/projects/230/packages/pypi/simple
RUN pip config set global.extra-index-url https://pypi.tuna.tsinghua.edu.cn/simple

WORKDIR /app

COPY requirements.txt /app
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app
CMD ["python", "-u", "main.py"]