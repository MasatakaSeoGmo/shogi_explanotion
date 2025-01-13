# Docker を使った将棋解説スクリプトの実行方法

このドキュメントでは、Dockerfile を利用して将棋解説スクリプト（`demo_kif.py`）を実行するための手順を解説します。以下の手順に従うことで、Docker コンテナ内で Python 環境と将棋エンジン、必要ライブラリを整えた状態でスクリプトを動かすことができます。

---

## 1. Docker イメージのビルド
```bash
docker build -t myapp:latest .
```

## 2. Dockerコンテナの実行
```bash
docker run --rm \
    --platform=linux/amd64 \
    -e OPENAI_API_KEY="sk-xxxx" \
    -v "$(pwd)/demo_kif.py":/app/demo_kif.py \
    -v "$(pwd)/example.kif":/app/example.kif \
    myapp:latest run_demo
```
