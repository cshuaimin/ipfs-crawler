FROM ubuntu

# install Python & PostgreSQL
RUN echo "deb http://mirrors.tuna.tsinghua.edu.cn/ubuntu/ bionic main restricted universe multiverse\n\
  deb http://mirrors.tuna.tsinghua.edu.cn/ubuntu/ bionic-updates main restricted universe multiverse\n\
  deb http://mirrors.tuna.tsinghua.edu.cn/ubuntu/ bionic-backports main restricted universe multiverse\n\
  deb http://mirrors.tuna.tsinghua.edu.cn/ubuntu/ bionic-security main restricted universe multiverse" > /etc/apt/sources.list \
  && apt-get update --no-install-recommends \
  # prevent prompt from tzdata
  && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    postgresql \
    postgresql-server-dev-10 \
    python3.7 \
    python3.7-distutils \
    git \
    gcc \
    g++ \
    make \
    cmake \
    sudo \
    libmagic1 \
    wget \
    ca-certificates \
  && ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime \
  && mkdir /var/run/postgresql/10-main.pg_stat_tmp \
  && chown postgres:postgres /var/run/postgresql/10-main.pg_stat_tmp \
  && sed -i 's/local   all             postgres                                peer/local all postgres trust/' /etc/postgresql/10/main/pg_hba.conf \
  # install python3-pip via apt will install python3.6
  && wget -O- https://bootstrap.pypa.io/get-pip.py | python3.7

# install pg_jieba
RUN git clone https://github.com/jaiminpan/pg_jieba /tmp/pg_jieba \
  && cd /tmp/pg_jieba \
  && git submodule update --init --recursive \
  && mkdir build \
  && cd build \
  && cmake .. -DPostgreSQL_TYPE_INCLUDE_DIR=/usr/include/postgresql/10/server \
  && make \
  && make install \
  && cd / \
  && rm -rf /tmp/pg_jieba \
  && echo "shared_preload_libraries = 'pg_jieba.so'" >> /var/lib/postgresql/10/main/postgresql.conf

# install go-ipfs
# Don't use 'ADD', that never use cache and download everytime.
RUN wget https://github.com/ipfs/go-ipfs/releases/download/v0.4.17/go-ipfs_v0.4.17_linux-amd64.tar.gz -O /tmp/ipfs.tgz \
  && cd /tmp \
  && tar -xf ipfs.tgz \
  && mv go-ipfs/ipfs /usr/local/bin/ipfs \
  && rm -rf ipfs.tgz go-ipfs
  # Don't init ipfs repo here, otherwise everyone use this image will have the same peer ID.

# Create the  directories for fs-repo and the code and switch to a non-privileged user.
ENV IPFS_PATH /data/ipfs
RUN mkdir -p $IPFS_PATH /ipfs_crawler \
  && chown postgres:postgres $IPFS_PATH /ipfs_crawler
COPY . /ipfs_crawler/

# install requirements
RUN pip3 install -i https://pypi.douban.com/simple/ setuptools wheel \
  && pip3 install -i https://pypi.douban.com/simple/ git+https://github.com/Supervisor/supervisor \
  && pip3 install -i https://pypi.douban.com/simple/ -r /ipfs_crawler/requirements.txt

RUN apt-get remove -y \
      postgresql-server-dev-10 \
      git \
      gcc \
      g++ \
      make \
      cmake \
      wget \
  && apt-get autoremove -y \
  && rm -rf /var/lib/apt/lists/*

# init database
USER postgres
RUN PATH=/usr/lib/postgresql/10/bin:$PATH \
  && pg_ctl -D /var/lib/postgresql/10/main -o '-c config_file=/etc/postgresql/10/main/postgresql.conf' start \
  && createdb ipfs_crawler \
  && psql -d ipfs_crawler -f /ipfs_crawler/init.sql \
  && pg_ctl -D /var/lib/postgresql/10/main stop

# Ports for Swarm TCP, Swarm uTP, API, Gateway, Swarm Websockets and the WebUI.
EXPOSE 4001 4002/udp 5001 8080 8081 9000

VOLUME /var/lib/postgres/data $IPFS_PATH
CMD [ "supervisord", "-c", "/ipfs_crawler/supervisord.conf" ]
