FROM python:3.10
RUN cat /etc/apt/sources.list
RUN sed -i "s@http://.*archive.ubuntu.com@https://mirrors.tuna.tsinghua.edu.cn@g" /etc/apt/sources.list
RUN sed -i "s@http://.*security.ubuntu.com@https://mirrors.tuna.tsinghua.edu.cn@g" /etc/apt/sources.list
RUN cat /etc/apt/sources.list
RUN apt-get clean
RUN apt-get update && apt-get install -y libgl1-mesa-glx
WORKDIR /app
COPY requirements.txt /app
RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
COPY . /app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]