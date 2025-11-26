import pygame
import math
import os

# --- 定数 ---
SCREEN_WIDTH, SCREEN_HEIGHT = 800, 600
FPS = 60
NOTE_SPEED = 9
JUDGEMENT_LINE_Y = 450
GAME_TIME_LIMIT = 30  # 制限時間（秒）

# --- 色定義 ---
C = {
    'BLACK': (0, 0, 0), 'WHITE': (255, 255, 255), 'RED': (255, 100, 100),
    'BLUE': (100, 150, 255), 'GREEN': (100, 255, 100), 'YELLOW': (255, 255, 100),
    'BG': (20, 20, 40), 'GRAY': (128, 128, 128)
}
NOTE_COLORS = [C['RED'], C['BLUE'], C['GREEN'], C['YELLOW']]

# --- 判定とスコア定義 (距離の閾値, 判定名, スコア, 色) ---
JUDGEMENTS = sorted([
    (20, "PERFECT", 300, C['YELLOW']),
    (40, "GREAT", 200, C['GREEN']),
    (60, "GOOD", 100, C['BLUE']),
    (80, "OK", 50, C['WHITE'])
])

class Note:
    """ノーツ（丸）のクラス"""
    def __init__(self, x_pos, color):
        self.x, self.y, self.color, self.size = x_pos, -60, color, 40
    
    def update(self):
        self.y += NOTE_SPEED

    def draw(self, surface):
        pygame.draw.circle(surface, self.color, (self.x, self.y), self.size)
        pygame.draw.circle(surface, C['WHITE'], (self.x, self.y), self.size, 4)

class Game:
    """ゲーム全体の管理クラス"""
    def __init__(self):
        pygame.init()
        # 安定性のため、mixerの初期化に引数を追加
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 40)
        self.big_font = pygame.font.Font(None, 60)  # 大きなフォント追加
        self.is_running, self.game_state = True, "MENU"
        self.reset_stats()

    def reset_stats(self):
        self.score, self.combo, self.max_combo = 0, 0, 0
        self.notes, self.beat_times, self.current_beat_idx = [], [], 0
        self.music_start_time, self.music_duration = 0, 0
        self.game_start_time = 0  # ゲーム開始時刻を追加

    def run(self):
        """メインループ"""
        while self.is_running:
            self.handle_events()
            if self.game_state == "PLAYING": 
                self.update()
                self.check_time_limit()  # 制限時間チェック
            self.draw()
            self.clock.tick(FPS)
        pygame.quit()

    def check_time_limit(self):
        """制限時間をチェック"""
        if self.game_start_time > 0:
            current_time = (pygame.time.get_ticks() - self.game_start_time) / 1000.0
            if current_time >= GAME_TIME_LIMIT:
                self.game_state = "GAME_OVER"
                # 音楽を停止
                pygame.mixer.music.stop()

    def get_remaining_time(self):
        """残り時間を取得"""
        if self.game_start_time > 0:
            current_time = (pygame.time.get_ticks() - self.game_start_time) / 1000.0
            remaining = max(0, GAME_TIME_LIMIT - current_time)
            return remaining
        return GAME_TIME_LIMIT

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT: self.is_running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE: self.is_running = False
            
            if self.game_state == "MENU" and event.type == pygame.KEYDOWN:
                # SPACEとMキーを明示的にチェックし、それ以外は無視する
                if event.key == pygame.K_SPACE:
                    self.start_game() # デモモード
                elif event.key == pygame.K_m:
                    music_files = self.find_music_files()
                    # クラッシュ防止のため、ファイルが存在するかチェック
                    if music_files:
                        self.start_game(music_files[0])

            elif self.game_state == "PLAYING" and event.type == pygame.MOUSEBUTTONDOWN:
                self.check_hit(event.pos)
            
            elif self.game_state == "GAME_OVER" and event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    self.game_state = "MENU"  # メニューに戻る

    def update(self):
        if self.music_start_time > 0 and not pygame.mixer.music.get_busy():
            # 音楽が終了したが、制限時間内ならゲームを続ける
            remaining_time = self.get_remaining_time()
            if remaining_time <= 0:
                self.game_state = "GAME_OVER"
                return
        
        if self.current_beat_idx < len(self.beat_times):
            fall_time = (JUDGEMENT_LINE_Y + 60) / NOTE_SPEED / FPS
            current_time = (pygame.time.get_ticks() - self.music_start_time) / 1000.0
            if current_time >= self.beat_times[self.current_beat_idx] - fall_time:
                x = SCREEN_WIDTH // 2 + (self.current_beat_idx % 3 - 1) * 150
                self.notes.append(Note(x, NOTE_COLORS[self.current_beat_idx % len(NOTE_COLORS)]))
                self.current_beat_idx += 1
        
        missed = False
        for note in self.notes:
            note.update()
            if note.y > JUDGEMENT_LINE_Y + JUDGEMENTS[-1][0]:
                missed = True
        
        if missed: self.combo = 0
        self.notes = [n for n in self.notes if n.y <= JUDGEMENT_LINE_Y + JUDGEMENTS[-1][0]]

    def draw(self):                  
        self.screen.fill(C['BG'])
        if self.game_state == "MENU":
            self.draw_text("SPACE: DEMO / M: Start with a music", 180, SCREEN_HEIGHT / 2)
        elif self.game_state == "PLAYING":
            pygame.draw.line(self.screen, C['WHITE'], (0, JUDGEMENT_LINE_Y), (SCREEN_WIDTH, JUDGEMENT_LINE_Y), 3)
            for note in self.notes: note.draw(self.screen)
            
            # スコアとコンボ表示
            self.draw_text(f"Score: {self.score}  Combo: {self.combo}", 20, 20)
            
            # 残り時間表示
            remaining_time = self.get_remaining_time()
            time_text = f"Time: {remaining_time:.1f}s"
            if remaining_time <= 5:  # 残り5秒以下は赤色で警告
                self.draw_text_colored(time_text, SCREEN_WIDTH - 200, 20, C['RED'])
            else:
                self.draw_text(time_text, SCREEN_WIDTH - 200, 20)
        
        elif self.game_state == "GAME_OVER":
            # ゲーム終了画面
            self.draw_game_over_screen()
        
        pygame.display.flip()

    def draw_game_over_screen(self):
        """ゲーム終了画面を描画"""
        # タイトル
        title_text = self.big_font.render("GAME OVER", True, C['WHITE'])
        title_rect = title_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 120))
        self.screen.blit(title_text, title_rect)
        
        # 結果表示
        result_texts = [
            f"Final Score: {self.score}",
            f"Max Combo: {self.max_combo}",
            "",
            "Press SPACE to return to menu"
        ]
        
        y_offset = SCREEN_HEIGHT//2 - 40
        for i, text in enumerate(result_texts):
            if text:  # 空文字列でない場合のみ描画
                if i < 2:  # スコアとコンボは大きく表示
                    rendered_text = self.big_font.render(text, True, C['YELLOW'])
                else:  # 操作説明は通常サイズ
                    rendered_text = self.font.render(text, True, C['WHITE'])
                text_rect = rendered_text.get_rect(center=(SCREEN_WIDTH//2, y_offset + i * 50))
                self.screen.blit(rendered_text, text_rect)

    def draw_text(self, text, x, y):
        self.screen.blit(self.font.render(text, True, C['WHITE']), (x, y))

    def draw_text_colored(self, text, x, y, color):
        """指定した色でテキストを描画"""
        self.screen.blit(self.font.render(text, True, color), (x, y))

    def check_hit(self, mouse_pos):
        click_anything = False
        #ループ中にリストを削除しないよう、リストのコピーでループを回す
        for note in self.notes[:]: 
            dist_mouse = math.hypot(mouse_pos[0] - note.x, mouse_pos[1] - note.y)
            
            if dist_mouse < note.size:
                click_anything = True # 円の内側をクリックした
                dist_line = abs(note.y - JUDGEMENT_LINE_Y)
                
                for dist_thresh, name, score, color in JUDGEMENTS:
                    if dist_line < dist_thresh:
                        self.combo += 1
                        self.max_combo = max(self.max_combo, self.combo)
                        self.score += score + self.combo * 10
                        self.notes.remove(note)
                        return # ヒットしたので処理終了
                
                #円の内側だがどの判定にも入らなかった場合（空振り）
                self.combo = 0
                print("miss")
                return
        
        # どのノーツにも触れなかった場合もミスではない（空振り）

    def start_game(self, music_file=None):
        self.reset_stats()
        if music_file:
            pygame.mixer.music.load(music_file)
            self.beat_times, self.music_duration = self.analyze_beats()
            pygame.mixer.music.play()
        else: # デモモード
            # デモモードでも30秒間ノーツが出続けるように調整
            self.beat_times = [i * 0.5 for i in range(int(GAME_TIME_LIMIT * 2))]
        
        self.music_start_time = pygame.time.get_ticks()
        self.game_start_time = pygame.time.get_ticks()  # ゲーム開始時刻を記録
        self.game_state = "PLAYING"

    @staticmethod
    def find_music_files():
        formats = ['.mp3', '.wav', '.ogg']
        files = [f for f in os.listdir('.') if any(f.lower().endswith(ext) for ext in formats)]
        if not files: print("音楽ファイルが見つかりません。")
        return files

    @staticmethod
    def analyze_beats():
        BPM, DURATION = 240, GAME_TIME_LIMIT  # 制限時間に合わせて調整
        interval = 60.0 / BPM
        return [i * interval for i in range(int(DURATION / interval))], DURATION

if __name__ == '__main__':
    Game().run()