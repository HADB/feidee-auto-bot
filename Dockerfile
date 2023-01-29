FROM python:3.10
RUN mv /etc/apt/sources.list /etc/apt/sources.list.bak && \
    touch /etc/apt/sources.list && \
    echo "\
deb http://mirrors.tuna.tsinghua.edu.cn/debian/ bullseye main contrib non-free \
deb http://mirrors.tuna.tsinghua.edu.cn/debian/ bullseye-updates main contrib non-free \
deb http://mirrors.tuna.tsinghua.edu.cn/debian/ bullseye-backports main contrib non-free \
deb http://mirrors.tuna.tsinghua.edu.cn/debian-security bullseye-security main contrib non-free \
" > /etc/apt/sources.list && \
    apt update && \
    apt install -y apt-transport-https ca-certificates && \
    sed -i 's/http:\/\//https:\/\//g' /etc/apt/sources.list && \
    apt update

WORKDIR /app
COPY requirements.txt /app
RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
COPY . /app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]