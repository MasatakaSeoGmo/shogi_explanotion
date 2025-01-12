#!/bin/bash
# entrypoint.sh

# デフォルトでは bash を起動
# オプションとしてスクリプトを実行
if [ "$1" = "run_demo" ]; then
    python /app/demo_kif.py /app/example.kif /app/YaneuraOuNNUE_haswell
else
    exec "$@"
fi
