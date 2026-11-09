import os
import random
import uuid
from typing import Dict, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Wordle API Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 簡易單字庫
WORD_BANK = ["APPLE", "TRAIN", "HOUSE", "PLANT", "SMART", "WORLD", "LIGHT", "BRAIN", "CLOUD", "WATER"]

# 全域統計數據 (任務三需求)
global_stats = {
    "total_games": 0,
    "wins": 0
}

# 記憶體儲存遊戲狀態
games_db: Dict[str, dict] = {}


class NewGameRequest(BaseModel):
    hard_mode: bool = False

class GuessRequest(BaseModel):
    game_id: str
    guess: str


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/api/stats")
def get_stats():
    """ 任務三：回傳勝率統計資訊 """
    total = global_stats["total_games"]
    wins = global_stats["wins"]
    win_rate = (wins / total * 100) if total > 0 else 0.0
    return {
        "total_games": total,
        "wins": wins,
        "win_rate": round(win_rate, 2)
    }


@app.post("/api/new-game")
def start_new_game(req: Optional[NewGameRequest] = None):
    """ 任務四：建立新一局遊戲，支援 hard_mode """
    game_id = str(uuid.uuid4())
    target_word = random.choice(WORD_BANK)
    hard_mode = req.hard_mode if req else False
    
    # 新增一局遊戲，累加總場數 (任務三)
    global_stats["total_games"] += 1

    games_db[game_id] = {
        "target": target_word,
        "status": "PLAYING",
        "attempts": 0,
        "hard_mode": hard_mode,
        "revealed_correct": {}  # 紀錄硬核模式下需維持的綠色字母 {index: char}
    }
    return {
        "game_id": game_id, 
        "message": "New game started!",
        "hard_mode": hard_mode
    }


@app.post("/api/guess")
def process_guess(req: GuessRequest):
    """ 處理猜測邏輯 (包含字典檢查、Hard Mode 驗證、揭曉答案、勝率更新) """
    game_id = req.game_id
    guess = req.guess.upper()

    if game_id not in games_db:
        raise HTTPException(status_code=404, detail="Game session not found.")

    game = games_db[game_id]

    if len(guess) != 5:
        raise HTTPException(status_code=400, detail="Word must be 5 letters.")

    # 任務二：檢查輸入的單字是否在字典中
    if guess not in WORD_BANK:
        raise HTTPException(status_code=400, detail="Word not in dictionary")

    # 任務四：Hard Mode 邏輯驗證
    if game["hard_mode"]:
        for idx, required_char in game["revealed_correct"].items():
            if guess[idx] != required_char:
                raise HTTPException(
                    status_code=400, 
                    detail="Hard Mode: Must use revealed hint at green position"
                )

    # 扣除/增加次數
    game["attempts"] += 1
    target = game["target"]
    feedback = ["absent"] * 5
    target_letter_counts = {}

    # 1. 計算目標字母數量
    for char in target:
        target_letter_counts[char] = target_letter_counts.get(char, 0) + 1

    # 2. 標記綠色 correct 並紀錄於 hard_mode 提示中
    for i in range(5):
        if guess[i] == target[i]:
            feedback[i] = "correct"
            target_letter_counts[guess[i]] -= 1
            game["revealed_correct"][i] = guess[i]  # 記錄正確位置與字母

    # 3. 標記黃色 present
    for i in range(5):
        if feedback[i] != "correct" and guess[i] in target:
            if target_letter_counts[guess[i]] > 0:
                feedback[i] = "present"
                target_letter_counts[guess[i]] -= 1

    # 檢查勝負條件
    is_correct = (guess == target)
    if is_correct:
        game["status"] = "WON"
        global_stats["wins"] += 1  # 任務三：勝場 +1

    # 任務一：判斷遊戲是否結束 (猜對 或 達到第 6 次猜測失敗)
    is_game_over = is_correct or (game["attempts"] >= 6)
    if is_game_over and not is_correct:
        game["status"] = "LOST"

    # 計算當前勝率
    total_g = global_stats["total_games"]
    wins_g = global_stats["wins"]
    win_rate = (wins_g / total_g * 100) if total_g > 0 else 0.0

    return {
        "guess": guess,
        "feedback": feedback,
        "is_correct": is_correct,
        # 任務一：第 6 次或猜對時揭曉 target_word，其餘時間為 None
        "target_word": target if is_game_over else None,
        "attempts": game["attempts"],
        "stats": {
            "total_games": total_g,
            "wins": wins_g,
            "win_rate": round(win_rate, 2)
        }
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
