import os
import sys
import re
import cshogi
from cshogi.usi import Engine

from openai import OpenAI

# ---------------------------------------------------
# OpenAI クライアントインスタンスの作成
# (APIキーは環境変数 OPENAI_API_KEY を利用する想定)
# ---------------------------------------------------
client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),  # 必要に応じて明示的に指定可能
)

def kif_move_to_usi(kif_move: str, last_to_square: str = None) -> (str, str):
    """
    KIFの指し手をUSI形式に変換する。
    例: '７六歩(77)' -> '7g7f'
    「同」指し手の場合はlast_to_squareを使用。
    """
    # 日本語数字を英数字に変換
    num_map = {'１': '1', '２': '2', '３': '3', '４': '4', '５': '5',
               '６': '6', '７': '7', '８': '8', '９': '9'}
    rank_num_to_usi = {
        1: 'a', 2: 'b', 3: 'c', 4: 'd', 5: 'e',
        6: 'f', 7: 'g', 8: 'h', 9: 'i'
    }

    # 「同」の処理
    if kif_move.startswith("同"):
        if not last_to_square:
            raise ValueError("「同」指し手が前の指し手の情報を必要とします。")
        return f"*{last_to_square}", last_to_square

    # 通常の指し手の処理
    match = re.match(r'^([１２３４５６７８９])([一二三四五六七八九])([歩香桂銀金角飛王玉と馬竜]*)?\((\d)(\d)\)$', kif_move)
    if not match:
        raise ValueError(f"無効な指し手フォーマット: {kif_move}")
    
    # 目的地の筋と段を変換
    to_file = num_map[match.group(1)]  # 筋（例: "７" -> "7"）
    to_rank_num = "一二三四五六七八九".index(match.group(2)) + 1  # 段を数値化（例: "六" -> 6）
    to_rank = rank_num_to_usi[to_rank_num]  # 段をUSI形式に変換（例: 6 -> "f")
    
    # 元の位置（from_square）の筋と段
    from_file = match.group(4)
    from_rank = match.group(5)
    from_square = f"{from_file}{rank_num_to_usi[int(from_rank)]}"
    
    # 成りの処理
    piece = match.group(3) or ''
    if "成" in piece:
        usi_move = f"{from_square}{to_file}{to_rank}+"
    else:
        usi_move = f"{from_square}{to_file}{to_rank}"
    
    return usi_move, f"{to_file}{to_rank}"

def parse_kif_from_text(kif_text: str):
    """
    KIFファイルのテキスト内容をリスト化し、指し手を抽出する。
    """
    moves = []
    last_to_square = None
    lines = kif_text.splitlines()
    move_section = False
    for line in lines:
        line = line.strip()
        if line.startswith('手数----指手'):
            move_section = True
            continue
        if move_section:
            if line.startswith(('投了', '持将棋', '千日手')):
                break
            move_parts = line.split()
            if len(move_parts) >= 2:
                kif_move = move_parts[1]
                try:
                    usi_move, to_square = kif_move_to_usi(kif_move, last_to_square)
                    moves.append(usi_move)
                    last_to_square = to_square
                except ValueError as e:
                    print(f"警告: {e}")
    return moves

def parse_kif(file_path: str):
    """
    KIFファイルからテキストを読み込んでparse_kif_from_textに渡す。
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        kif_text = f.read()
    return parse_kif_from_text(kif_text)

########################################
# 追加: LLMでコメントを生成する関数
########################################
def generate_llm_comment(
    move_number: int,
    played_move: str,
    engine_best_move: str,
    next_best_line: str
) -> str:
    """
    OpenAIの新しいAPI(v1系)を用いてコメント文を生成する。
    """
    # 生成したいコメントの内容を一つの文字列にまとめる (例として将棋の解説用プロンプト)
    prompt_text = f"""
【状況説明】
- 手数: 第{move_number}手
- 指された手: {played_move}
- エンジン最善手: {engine_best_move}
- エンジン読み筋: {next_best_line}

【お願い】
上記情報を踏まえ、将棋の文脈で分かりやすく解説コメントを書いてください。
1. 指された手と最善手を比較し、どのような意味や違いがあるか説明する
2. エンジンが読み上げている次の展開(最善手の読み筋)の内容・意図を解説する
"""

    try:
        # ---------------------------------------------------
        # 新しい ChatCompletion API の呼び出し
        # ---------------------------------------------------
        response = client.chat.completions.create(
            model="gpt-4o",  # モデル名はご利用の環境に合わせて変更
            messages=[
                {
                    "role": "user",
                    "content": prompt_text,
                }
            ],
            max_tokens=300,    # 出力トークンの上限
            temperature=0.7,   # 生成のランダム性
        )

        # ---------------------------------------------------
        # レスポンスから生成されたメッセージ本文を取得
        # ---------------------------------------------------
        return response.choices[0].message.content.strip()

    except Exception as e:
        return f"LLMコメント生成中にエラーが発生しました: {e}"


def main(kif_path: str, engine_path: str, move_time: int = 2000):
    moves = parse_kif(kif_path)
    if not moves:
        print(f"KIFファイル({kif_path})から指し手が取得できませんでした。")
        return

    engine = Engine(engine_path)
    engine.connect()
    engine.isready()

    board = cshogi.Board()
    board.reset()

    for i, usi_move in enumerate(moves):
        move_number = i + 1
        print(f"指し手 {move_number}: {usi_move}")
        try:
            board.push_usi(usi_move)
        except ValueError as e:
            print(f"エラー: 指し手 {usi_move} の適用に失敗しました。 {e}")
            break

        ################################################################
        # エンジンに現在局面を設定して思考させる
        ################################################################
        engine.position(sfen=board.sfen())
        # goコマンドで思考 (シンプルに bestmove のみ取得)
        result = engine.go(btime=move_time, wtime=move_time)
        bestmove = result[0]

        ################################################################
        # 追加: 次の先読み手順(読み筋)を文字列化 (簡易的にbestmoveをもう1手読ませる例)
        ################################################################
        # 実際にはmultiPVなどを使ってより深い読み筋を取得する方法もあるが、
        # ここでは簡易サンプルとして bestmove を指した局面を1手だけ確認する。
        next_board = cshogi.Board(board.sfen())
        try:
            next_board.push_usi(bestmove)
            engine.position(sfen=next_board.sfen())
            next_result = engine.go(btime=move_time, wtime=move_time)
            next_best_move = next_result[0]
            next_best_line = f"{bestmove} -> {next_best_move}"
        except ValueError:
            next_best_line = f"{bestmove}"

        print(f"  エンジン推奨手: {bestmove}")

        ################################################################
        # 追加: LLMを用いてコメントを生成
        ################################################################
        llm_comment = generate_llm_comment(
            move_number=move_number,
            played_move=usi_move,
            engine_best_move=bestmove,
            next_best_line=next_best_line
        )
        print(f"  コメント:\n{llm_comment}\n")

    engine.quit()
    print("棋譜の読み込みとエンジンでの簡易評価、およびLLMを用いた解説コメントを完了しました。")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python demo_kif.py <kif_file> <engine_path>")
        sys.exit(1)
    kif_file = sys.argv[1]
    engine_file = sys.argv[2]
    main(kif_file, engine_file)
