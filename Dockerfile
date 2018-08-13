FROM ubuntu

COPY . /root/ipfs_crawler/

RUN echo "deb http://mirrors.tuna.tsinghua.edu.cn/ubuntu/ bionic main restricted universe multiverse\n\
  deb http://mirrors.tuna.tsinghua.edu.cn/ubuntu/ bionic-updates main restricted universe multiverse\n\
  deb http://mirrors.tuna.tsinghua.edu.cn/ubuntu/ bionic-backports main restricted universe multiverse\n\
  deb http://mirrors.tuna.tsinghua.edu.cn/ubuntu/ bionic-security main restricted universe multiverse" > /etc/apt/sources.list \
  && apt-get update \
  && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    postgresql \
    python3.7 \
    python3-pip \
    git \
  && cd /root \
  && pip3 install -i https://pypi.douban.com/simple/ setuptools wheel \
  && pip3 install -i https://pypi.douban.com/simple/ git+https://github.com/Supervisor/supervisor \
  && pip3 install -i https://pypi.douban.com/simple/ -r ./ipfs_crawler/requirements.txt \
  && apt-get remove git -y \
  && apt-get autoremove -y \
  && rm -rf /var/lib/apt/lists/*

RUN echo "shared_preload_libraries = 'pg_jieba.so'" >> /var/lib/postgresql/10/main

ADD https://github.com/ipfs/go-ipfs/releases/download/v0.4.17/go-ipfs_v0.4.17_linux-amd64.tar.gz /tmp/ipfs.tgz
RUN cd /tmp \
  && tar -xf ipfs.tgz \
  && mv go-ipfs/ipfs /usr/local/bin/ipfs \
  && rm -rf ipfs.tgz go-ipfs 

# Ports for Swarm TCP, Swarm uTP, API, Gateway, Swarm Websockets
EXPOSE 4001 4002/udp 5001 8080 8081

VOLUME /var/lib/postgres/data
VOLUME /root/.ipfs
CMD [ "supervisord", "-c", "/root/ipfs_crawler/supervisord.conf" ]