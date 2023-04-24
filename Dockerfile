FROM python:3

WORKDIR /app
COPY requirements.txt /app
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

COPY . /app
CMD ["python", "-u", "main.py"]