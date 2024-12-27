import os
import openai
import cshogi
from cshogi.usi import Engine

openai.api_key = os.getenv("OPENAI_API_KEY")

ENGINE_PATH = "/path/to/your/usi/engine"  # ここに使用する将棋エンジンのパスを指定してください

def board_to_text(board: cshogi.Board) -> str:
    return str(board)

def get_engine_candidates(board: cshogi.Board, engine_path: str, multipv: int = 3) -> list:
    """
    USIエンジンを用いて、現在の局面での上位候補手と評価値、PV（読み筋）を取得する関数。
    戻り値: [{"move":"7g7f", "score": 120, "pv":["7g7f","3c3d",...], "info":"..."}, ...] のような形式のリスト
    """
    engine = Engine(engine_path)
    engine.usi()
    engine.isready()
    
    # 現局面をエンジンに設定
    sfen = board.sfen()
    engine.position(sfen=sfen)
    
    # エンジン思考コマンド
    # multipv: 上位N手まで候補手を取得（エンジンが対応している必要あり）
    # 思考時間や深さは実用上は調整が必要
    info = engine.go(movetime=1000, multipv=multipv)  # 1秒考慮（実際には調整可能）
    
    # infoは辞書で、"pv", "score", "multipv"などを含む
    # cshogiのEngine.go()の戻り値がどのような形式か公式ドキュメントやコードで要確認
    # 以下は想定例
    candidates = []
    for line in info["info"]:
        # "info"フィールドには各候補手についての情報が入っている想定
        # 例: {"multipv":1, "score": {"cp":120}, "pv":["7g7f","3c3d"], "bestmove":"7g7f"}
        if "multipv" in line:
            move_usi = line.get("bestmove")
            score = line.get("score", {}).get("cp", 0)
            pv = line.get("pv", [])
            candidates.append({
                "move": move_usi,
                "score": score,
                "pv": pv,
                "info": line
            })
    
    # スコアを昇順/降順整列
    # scoreはcpで、数値が大きいほど先手有利(先手視点)
    # candidatesをmultipv順で並んでいる前提ならそのままでも可
    candidates.sort(key=lambda x: x["info"].get("multipv", 1))
    return candidates

def explain_move_with_context_and_candidates(move_usi: str, board: cshogi.Board, previous_moves: list, candidates: list) -> str:
    """
    LLMを用いて単一手の解説を生成する関数。
    ここではcandidates（エンジン候補手）をプロンプトに組み込む。
    """
    board_text = board_to_text(board)
    # 次の手を適用した後の局面
    board.push_usi(move_usi)
    next_board_text = board_to_text(board)
    board.pop()

    # 候補手情報をテキスト化
    candidate_texts = []
    for c in candidates:
        move_line = f"候補手: {c['move']} 評価値: {c['score']} PV: {' '.join(c['pv'])}"
        candidate_texts.append(move_line)
    candidates_info = "\n".join(candidate_texts) if candidate_texts else "なし"

    prompt = f"""
以下は将棋の局面と次に指される一手に関する情報です。

【これまでの手一覧】:
{', '.join(previous_moves) if previous_moves else 'なし'}

【現在の局面】:
{board_text}

【エンジン候補手と評価値】:
{candidates_info}

【次の手】:
{move_usi}

この手は、エンジンの評価や他の候補手との比較を踏まえて、どのような狙いがあり、今後の展開にどう影響するか解説してください。
評価値や読み筋（PV）から推測できる戦術、戦略面についても言及してください。

【次の手を指した後の局面】:
{next_board_text}

以上を踏まえ、日本語でわかりやすく、専門用語を使いすぎず解説してください。
"""
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt.strip(),
        max_tokens=500,
        temperature=0.7
    )
    return response.choices[0].text.strip()


def main():
    board = cshogi.Board()
    moves = ["7g7f", "3c3d", "2g2f", "8b3b"]
    previous_moves = []
    
    # USIエンジンの初期化 (対局中何度も再起動するより、一度で済ませた方が効率的だが、ここでは簡易化)
    # 各手を解説する際に、現在の局面で上位候補手を取得し、プロンプトに組み込む
    
    for i, move in enumerate(moves, start=1):
        # 現局面での候補手を取得
        candidates = get_engine_candidates(board, ENGINE_PATH, multipv=3)
        explanation = explain_move_with_context_and_candidates(move, board, previous_moves, candidates)
        
        print(f"【{i}手目: {move}】")
        print(explanation)
        print("-" * 40)
        
        # 局面更新
        board.push_usi(move)
        previous_moves.append(move)

if __name__ == "__main__":
    main()
