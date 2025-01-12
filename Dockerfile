# Python 3.9ベースイメージ (x86_64向け)
FROM --platform=linux/amd64 python:3.9

# 非対話モード
ENV DEBIAN_FRONTEND=noninteractive

# ここで Python の入出力エンコーディングを UTF-8 に固定
ENV PYTHONIOENCODING=utf-8

# 必要な依存パッケージをインストール
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    clang \
    lld \
    libopenblas-dev \
    unzip \
    zip \
    p7zip-full \
    git \
    wget \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 作業ディレクトリを /app に設定
WORKDIR /app

# Pythonライブラリをまとめてインストール: requirements.txtをコピーしてpip install
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# やねうら王のリポジトリをクローン
RUN git clone https://github.com/yaneurao/YaneuraOu.git

WORKDIR /app/YaneuraOu/source

# MakefileのTARGET_CPU=AVX2ブロックを修正
# '-DUSE_AVX2 -DUSE_BMI2 -mbmi -mbmi2 -mavx2 -march=corei7-avx' -> '-DUSE_AVX2 -march=haswell'
RUN sed -i '/^else ifeq (\$(TARGET_CPU),AVX2)/,+1 s/-DUSE_AVX2 -DUSE_BMI2 -mbmi -mbmi2 -mavx2 -march=corei7-avx/-DUSE_AVX2 -march=haswell/' Makefile

# downloadsディレクトリをコンテナにコピー(Elmo評価ファイルなど)
# 例: downloads/eval/nn.bin , engine_name.txt , book.db が含まれる
COPY downloads /app/downloads

# Elmoの評価関数・定跡を /app/eval や /app/book に配置
RUN mkdir -p /app/eval && \
    cp -r /app/downloads/eval/* /app/eval/ && \
    cp /app/downloads/engine_name.txt /app/YaneuraOu/source/ && \
    mkdir -p /app/book && \
    if [ -f /app/downloads/book.db ]; then cp /app/downloads/book.db /app/book/; fi && \
    rm -rf /app/downloads

# デバッグ: ファイル一覧を表示
RUN ls -l /app/eval || true

# やねうら王ビルド: トーナメント版 + NNUE
RUN make clean YANEURAOU_EDITION=YANEURAOU_ENGINE_NNUE && \
    make -j8 tournament COMPILER=g++ YANEURAOU_EDITION=YANEURAOU_ENGINE_NNUE \
    EXTRA_CPPFLAGS="-DHASH_KEY_BITS=128 -DTT_CLUSTER_SIZE=4 -march=haswell -Ofast -DNDEBUG -D_LINUX -DUNICODE -DNO_EXCEPTIONS -DFOR_TOURNAMENT" \
    ENGINE_NAME="YaneuraOu_tournament_haswell"

# ビルド結果を /app にコピー
RUN cp YaneuraOu-by-gcc /app/YaneuraOuNNUE_haswell

WORKDIR /app

# ベンチマーク実行 (evaluation file を /app/eval/ に置いている想定)
RUN printf "bench\nquit" | /app/YaneuraOuNNUE_haswell > benchmark_result.txt

# # PythonスクリプトとKIFファイルをコピー
# COPY demo_kif.py /app/demo_kif.py
# COPY example.kif /app/example.kif

# エントリーポイントスクリプトを作成（オプション）
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# エントリーポイントの設定（オプション）
ENTRYPOINT ["/app/entrypoint.sh"]

# コンテナ起動時に bash を立ち上げる (デバッグ用)
CMD ["/bin/bash"]
