import sys
import os
import pygame
import requests

# API 伺服器網址
API_BASE_URL = "https://wordle-finalexam.onrender.com"

# 顏色定義
COLOR_BG = (18, 18, 19)
COLOR_TEXT = (255, 255, 255)
COLOR_EMPTY = (58, 58, 60)
COLOR_CORRECT = (83, 141, 78)   # 綠色
COLOR_PRESENT = (181, 159, 59)  # 黃色
COLOR_ABSENT = (58, 58, 60)     # 灰色
COLOR_LINE = (100, 100, 100)    # 分隔線顏色

pygame.init()
# 任務三：擴大視窗寬度至 700 (原 500)
WIDTH, HEIGHT = 700, 650
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Pygame Wordle + FastAPI Client")
font = pygame.font.SysFont("Arial", 36, bold=True)
small_font = pygame.font.SysFont("Arial", 18)
history_font = pygame.font.SysFont("Arial", 22, bold=True)

class WordleGame:
    def __init__(self):
        self.game_id = None
        self.grid = [["" for _ in range(5)] for _ in range(6)]
        self.colors = [[COLOR_EMPTY for _ in range(5)] for _ in range(6)]
        self.row = 0
        self.col = 0
        self.game_over = False
        self.hard_mode = False          # 任務四：預設為 Normal 模式
        self.history_words = []         # 任務三：側邊欄歷史紀錄
        self.stats = {"total_games": 0, "wins": 0, "win_rate": 0.0}  # 勝率統計
        self.message = "Press ENTER to submit, R to restart, H for Hard Mode"
        self.start_new_game()

    def start_new_game(self):
        """ 向 FastAPI 伺服器請求建立新的一局 """
        try:
            payload = {"hard_mode": self.hard_mode}
            res = requests.post(f"{API_BASE_URL}/api/new-game", json=payload, timeout=60)
            if res.status_code == 200:
                data = res.json()
                self.game_id = data["game_id"]
                self.grid = [["" for _ in range(5)] for _ in range(6)]
                self.colors = [[COLOR_EMPTY for _ in range(5)] for _ in range(6)]
                self.row = 0
                self.col = 0
                self.game_over = False
                self.history_words = []
                self.message = "New game started!"
                self.fetch_stats()  # 獲取最新統計資料
            else:
                self.message = "Server error starting new game."
        except requests.exceptions.RequestException:
            self.message = "Cannot connect to FastAPI server!"

    def fetch_stats(self):
        """ 任務三：取得全域統計數據 """
        try:
            res = requests.get(f"{API_BASE_URL}/api/stats", timeout=5)
            if res.status_code == 200:
                self.stats = res.json()
        except requests.exceptions.RequestException:
            pass

    def submit_guess(self):
        """ 將當前行單字發送至 FastAPI 驗證 """
        if self.col < 5:
            self.message = "Not enough letters!"
            return

        guess_word = "".join(self.grid[self.row])
        try:
            payload = {"game_id": self.game_id, "guess": guess_word}
            res = requests.post(f"{API_BASE_URL}/api/guess", json=payload, timeout=60)
            
            if res.status_code == 200:
                data = res.json()
                feedback = data["feedback"]
                
                # 更新格子顏色
                for i in range(5):
                    if feedback[i] == "correct":
                        self.colors[self.row][i] = COLOR_CORRECT
                    elif feedback[i] == "present":
                        self.colors[self.row][i] = COLOR_PRESENT
                    else:
                        self.colors[self.row][i] = COLOR_ABSENT

                # 任務三：紀錄猜過的單字
                self.history_words.append(guess_word)

                # 更新後端回傳的統計資訊
                if "stats" in data:
                    self.stats = data["stats"]

                if data["is_correct"]:
                    self.message = "Congratulations! You won! Press R to restart."
                    self.game_over = True
                else:
                    self.row += 1
                    self.col = 0
                    if self.row == 6:
                        # 任務一：失敗時顯示正確答案
                        target = data.get("target_word", "")
                        self.message = f"Game Over! The word was {target}. Press R to restart."
                        self.game_over = True
                    else:
                        # 任務一：顯示剩餘次數 (6 - row)
                        tries_left = 6 - self.row
                        self.message = f"Keep guessing! ({tries_left} tries left)"

            elif res.status_code == 400:
                detail = res.json().get("detail", "")
                if detail == "Word not in dictionary":
                    # 任務二：不在字典時顯示特定訊息，且不消耗猜測次數（不推進 row）
                    self.message = "Not in word list!"
                else:
                    self.message = detail
            else:
                self.message = res.json().get("detail", "Error processing guess")
        except requests.exceptions.RequestException:
            self.message = "Network error during guess!"

    def handle_keydown(self, event):
        if event.key == pygame.K_r:
            self.start_new_game()
            return

        # 任務四：按 H 切換 Hard Mode 並重開新局
        if event.key == pygame.K_h:
            self.hard_mode = not self.hard_mode
            self.start_new_game()
            return

        if self.game_over:
            return

        if event.key == pygame.K_BACKSPACE:
            if self.col > 0:
                self.col -= 1
                self.grid[self.row][self.col] = ""
        elif event.key == pygame.K_RETURN:
            self.submit_guess()
        elif event.unicode.isalpha() and len(event.unicode) == 1:
            if self.col < 5:
                self.grid[self.row][self.col] = event.unicode.upper()
                self.col += 1

    def draw(self, surface):
        surface.fill(COLOR_BG)

        # ---------------- 任務四：右上角顯示模式 ----------------
        mode_str = "Mode: HARD" if self.hard_mode else "Mode: Normal"
        mode_surface = small_font.render(mode_str, True, (255, 200, 0) if self.hard_mode else COLOR_TEXT)
        surface.blit(mode_surface, (WIDTH - 130, 15))

        # ---------------- 任務三：繪製右側分隔線與歷史紀錄面板 ----------------
        pygame.draw.line(surface, COLOR_LINE, (500, 0), (500, HEIGHT), 2)

        # 任務三：顯示勝率資訊 Total: X | Wins: Y | Win Rate: Z%
        total = self.stats.get("total_games", 0)
        wins = self.stats.get("wins", 0)
        win_rate = self.stats.get("win_rate", 0.0)
        stats_str = f"Total: {total} | Wins: {wins} | Win Rate: {win_rate}%"
        stats_surface = small_font.render(stats_str, True, COLOR_TEXT)
        surface.blit(stats_surface, (20, 15))

        # 任務三：右側歷史單字列表
        history_title = small_font.render("History:", True, COLOR_TEXT)
        surface.blit(history_title, (520, 50))
        for idx, word in enumerate(self.history_words):
            word_surface = history_font.render(f"{idx + 1}. {word}", True, COLOR_TEXT)
            surface.blit(word_surface, (520, 80 + idx * 30))

        # ---------------- 繪製 6x5 網格 (左側 0-500 區域) ----------------
        margin_x, margin_y = 75, 50
        box_size = 60
        gap = 10

        for r in range(6):
            for c in range(5):
                x = margin_x + c * (box_size + gap)
                y = margin_y + r * (box_size + gap)
                rect = pygame.Rect(x, y, box_size, box_size)
                
                # 畫背景框
                pygame.draw.rect(surface, self.colors[r][c], rect, border_radius=4)
                if self.colors[r][c] == COLOR_EMPTY:
                    pygame.draw.rect(surface, (80, 80, 80), rect, width=2, border_radius=4)

                # 畫字母
                char = self.grid[r][c]
                if char:
                    text_surface = font.render(char, True, COLOR_TEXT)
                    text_rect = text_surface.get_rect(center=rect.center)
                    surface.blit(text_surface, text_rect)

        # ---------------- 畫底部提示訊息 ----------------
        msg_surface = small_font.render(self.message, True, COLOR_TEXT)
        msg_rect = msg_surface.get_rect(center=(250, HEIGHT - 40))  # 置中於遊戲盤主區域 (0-500)
        surface.blit(msg_surface, msg_rect)


def main():
    clock = pygame.time.Clock()
    game = WordleGame()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                game.handle_keydown(event)

        game.draw(screen)
        pygame.display.flip()
        clock.tick(30)

if __name__ == "__main__":
    main()
