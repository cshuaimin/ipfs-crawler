FROM ubuntu

COPY crawler/ web/ supervisord.conf requirements.txt /root/ipfs_crawler/

RUN echo "deb http://mirrors.tuna.tsinghua.edu.cn/ubuntu/ bionic main restricted universe multiverse\n\
      deb http://mirrors.tuna.tsinghua.edu.cn/ubuntu/ bionic-updates main restricted universe multiverse\n\
      deb http://mirrors.tuna.tsinghua.edu.cn/ubuntu/ bionic-backports main restricted universe multiverse\n\
      deb http://mirrors.tuna.tsinghua.edu.cn/ubuntu/ bionic-security main restricted universe multiverse" > /etc/apt/sources.list \
    && apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      postgresql \
      python3.7 \
      python3-pip \
      wget \
      git \
    && cd /root \
    && pip3 install -i https://pypi.douban.com/simple/ setuptools wheel \
    && pip3 install -i https://pypi.douban.com/simple/ git+https://github.com/Supervisor/supervisor \
    && pip3 install -i https://pypi.douban.com/simple/ -r ./ipfs_crawler/requirements.txt \
    && wget https://github.com/ipfs/go-ipfs/releases/download/v0.4.17/go-ipfs_v0.4.17_linux-amd64.tar.gz -O ipfs.tgz \
    && tar -xf ipfs.tgz \
    && mv go-ipfs/ipfs /usr/local/bin/ipfs \
    && rm -rf ipfs.tgz go-ipfs \
    && apt-get remove wget git -y \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/* \
    && ipfs init

VOLUME /var/lib/postgres/data
CMD [ "supervisord", "-c", "/root/ipfs_crawler/supervisord.conf" ]
