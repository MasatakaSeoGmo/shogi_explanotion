# ベースイメージとしてgcc:11を使用し、x86_64プラットフォームを指定
FROM --platform=linux/amd64 gcc:11

# 非対話モードでのビルド設定
ENV DEBIAN_FRONTEND=noninteractive

# 必要なツールと依存関係をインストール
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

# 作業ディレクトリを設定
WORKDIR /app

# やねうら王のリポジトリをクローン
RUN git clone https://github.com/yaneurao/YaneuraOu.git

WORKDIR /app/YaneuraOu/source

# MakefileのTARGET_CPU=AVX2ブロックを修正
# '-DUSE_AVX2 -DUSE_BMI2 -mbmi -mbmi2 -mavx2 -march=corei7-avx' を '-DUSE_AVX2 -march=haswell' に置き換える
RUN sed -i '/^else ifeq (\$(TARGET_CPU),AVX2)/,+1 s/-DUSE_AVX2 -DUSE_BMI2 -mbmi -mbmi2 -mavx2 -march=corei7-avx/-DUSE_AVX2 -march=haswell/' Makefile

# Makefileの修正を確認（オプション、必要に応じてコメントアウト）
# RUN grep -A1 "^else ifeq (\$(TARGET_CPU),AVX2)" Makefile

# downloadsディレクトリをコンテナにコピー
#   downloads/ 内に eval/nn.bin , engine_name.txt , (book.db がある場合) が存在すると想定
COPY downloads /app/downloads

# elmoの評価関数と定跡を適切な場所に配置
RUN mkdir -p /app/eval && \
    cp -r /app/downloads/eval/* /app/eval/ && \
    # engine_name.txt は必要なら/source以下でもOKだが、とりあえずsource直下に置く
    cp /app/downloads/engine_name.txt /app/YaneuraOu/source/ && \
    # 定跡ファイルが存在する場合は /app/book にコピー
    mkdir -p /app/book && \
    if [ -f /app/downloads/book.db ]; then cp /app/downloads/book.db /app/book/; fi && \
    # 不要なファイルを削除
    rm -rf /app/downloads

# デバッグ: ファイル一覧を表示
RUN ls -l /app/eval || true

# ビルドを実行
RUN make clean YANEURAOU_EDITION=YANEURAOU_ENGINE_NNUE && \
    make -j8 tournament COMPILER=g++ YANEURAOU_EDITION=YANEURAOU_ENGINE_NNUE \
    EXTRA_CPPFLAGS="-DHASH_KEY_BITS=128 -DTT_CLUSTER_SIZE=4 -march=haswell -Ofast -DNDEBUG -D_LINUX -DUNICODE -DNO_EXCEPTIONS -DFOR_TOURNAMENT" \
    ENGINE_NAME="YaneuraOu_tournament_haswell"

# ビルドされた実行ファイルをコピー
RUN cp YaneuraOu-by-gcc /app/YaneuraOuNNUE_haswell

WORKDIR /app

# ベンチマーク実行
#   YaneuraOuが "EvalDirectory = /app/eval" を使えるように
RUN printf "bench\nquit" | /app/YaneuraOuNNUE_haswell > benchmark_result.txt

# コンテナ起動時にやねうら王エンジンを実行（対局などに使用）
CMD ["./YaneuraOuNNUE_haswell"]
