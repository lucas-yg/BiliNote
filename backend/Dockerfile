FROM python:3.11-slim


RUN apt-get update && \
    apt-get install -y ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# 确保 PATH 中包含 ffmpeg 路径（可选）
ENV PATH="/usr/bin:${PATH}"

# 设置 Hugging Face 镜像源环境变量
ENV HF_ENDPOINT=https://hf-mirror.com

WORKDIR /app
COPY ./backend /app
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

CMD ["python", "main.py"]
