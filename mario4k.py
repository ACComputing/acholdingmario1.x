#!/usr/bin/env python3
"""
ULTRA MARIO 2D BROS - Famicom Edition (Levels 1-1 to 8-4)
Pure Python/Pygame - No external assets required.
Requires: pip install pygame numpy
"""
import sys, math, random
try:
    import numpy as np
except ImportError:
    print("numpy required: pip install numpy"); sys.exit(1)
import pygame

# ====================================================================
# INIT
# ====================================================================
pygame.mixer.pre_init(44100, -16, 1, 1024)
pygame.init()

SW, SH = 768, 720
TS = 32
FPS = 60
SR = 44100
GRAVITY = 0.55
MAX_FALL = 12

screen = pygame.display.set_mode((SW, SH))
pygame.display.set_caption("ULTRA MARIO 2D BROS - Famicom")
clock = pygame.time.Clock()
pygame.mixer.set_num_channels(8)

# Colors
C_SKY = (92, 148, 252)
C_UNDG = (0, 0, 0)
C_GND = (200, 76, 12)
C_GNDD = (228, 156, 68)
C_BRK = (200, 76, 12)
C_BRKD = (136, 20, 0)
C_QST = (228, 172, 48)
C_QSTD = (140, 100, 20)
C_PTL = (0, 168, 0)
C_PTR = (0, 228, 0)
C_PBL = (0, 120, 0)
C_PBR = (0, 180, 0)
C_STN = (100, 100, 100)
C_STND = (60, 60, 60)
C_WHT = (255, 255, 255)
C_BLK = (0, 0, 0)
C_RED = (228, 0, 0)
C_SKIN = (252, 152, 56)
C_BROWN = (172, 80, 0)
C_DBROWN = (100, 40, 0)
C_GOLD = (255, 200, 0)
C_CAST = (180, 180, 180)
C_FLAG = (0, 200, 0)
C_POLE = (100, 100, 100)

font_hud = pygame.font.SysFont("consolas", 20, bold=True)
font_med = pygame.font.SysFont("consolas", 24, bold=True)
font_big = pygame.font.SysFont("consolas", 40, bold=True)
font_sm  = pygame.font.SysFont("consolas", 16)

# ====================================================================
# FAMICOM AUDIO ENGINE
# ====================================================================
class FamicomAudio:
    def __init__(self):
        self.ch_mus = pygame.mixer.Channel(0)
        self.ch_sfx = [pygame.mixer.Channel(i) for i in range(1, 6)]
        self.muted = False
        self.sfx = {
            'jump': self._mk_sfx_jump(), 'coin': self._mk_sfx_coin(),
            'stomp': self._mk_sfx_stomp(), 'die': self._mk_sfx_die(),
            'clear': self._mk_sfx_clear(), 'pause': self._mk_sfx_pause()
        }
        print("Generating Famicom Music...")
        self.music = {'menu': self._mk_mus_menu(), 'game': self._mk_mus_game()}
        self.cur_mus = None
        print("Audio Ready.")

    @staticmethod
    def _sq(f, d, duty=0.5, v=0.3):
        n = int(SR * d)
        if n <= 0: return np.zeros(1, dtype=np.int16)
        t = np.arange(n, dtype=np.float64) / SR
        w = np.where((t * f) % 1.0 < duty, 1.0, -1.0)
        return (w * v * 32767).astype(np.int16)

    @staticmethod
    def _tri(f, d, v=0.35):
        n = int(SR * d)
        if n <= 0: return np.zeros(1, dtype=np.int16)
        t = np.arange(n, dtype=np.float64) / SR
        p = (t * f) % 1.0
        return ((4.0 * np.abs(p - 0.5) - 1.0) * v * 32767).astype(np.int16)

    @staticmethod
    def _env(w, a=0.005, d=0.03, s=0.8, r=0.03):
        n = len(w)
        if n == 0: return w
        e = np.ones(n, dtype=np.float64)
        ia = min(int(a * SR), n)
        id_ = min(int(d * SR), n - ia)
        ir = int(r * SR)
        se = n - ir
        if se < ia + id_: se = ia + id_; ir = 0
        if ia > 0: e[:ia] = np.linspace(0, 1, ia)
        if id_ > 0: e[ia:ia + id_] = np.linspace(1, s, id_)
        if se > ia + id_: e[ia + id_:se] = s
        if ir > 0: e[se:] = np.linspace(s, 0, ir)
        return (w.astype(np.float64) * e).astype(np.int16)

    def _mix(self, *bufs):
        mx = max(len(b) for b in bufs)
        out = np.zeros(mx, dtype=np.float64)
        for b in bufs:
            if len(b):
                p = np.zeros(mx, dtype=np.float64); p[:len(b)] = b; out += p
        pk = np.max(np.abs(out))
        if pk > 32767: out *= 32767 / pk
        return out.astype(np.int16)

    def _mk_sfx_jump(self):
        b = np.concatenate([self._sq(400, 0.05, 0.25, 0.3), self._sq(600, 0.1, 0.25, 0.3)])
        return pygame.mixer.Sound(buffer=self._env(b, 0.001, 0.02, 0.9, 0.05).tobytes())

    def _mk_sfx_coin(self):
        b = np.concatenate([self._sq(988, 0.05, 0.25, 0.3), self._sq(1319, 0.2, 0.25, 0.3)])
        return pygame.mixer.Sound(buffer=self._env(b, 0.001, 0.01, 0.8, 0.1).tobytes())

    def _mk_sfx_stomp(self):
        b = self._sq(200, 0.1, 0.5, 0.3)
        return pygame.mixer.Sound(buffer=self._env(b, 0.01, 0.05, 0.5, 0.05).tobytes())

    def _mk_sfx_die(self):
        buf = np.array([], dtype=np.int16)
        for f in [600, 500, 400, 300, 200]:
            buf = np.concatenate([buf, self._sq(f, 0.15, 0.5, 0.3)])
        return pygame.mixer.Sound(buffer=self._env(buf, 0.01, 0.1, 0.5, 0.3).tobytes())

    def _mk_sfx_clear(self):
        mel = np.concatenate([self._sq(f, 0.15, 0.25, 0.3) for f in [523, 659, 784, 1047, 784, 1047]])
        return pygame.mixer.Sound(buffer=self._env(mel, 0.002, 0.02, 0.9, 0.1).tobytes())

    def _mk_sfx_pause(self):
        b = self._sq(440, 0.2, 0.5, 0.2)
        return pygame.mixer.Sound(buffer=b.tobytes())

    def _mk_mus_menu(self):
        bd = 60 / 150
        mel = np.array([], dtype=np.int16)
        for n, d in [(523, 1), (0, 0.5), (659, 0.5), (784, 1), (0, 0.5), (659, 0.5),
                     (523, 1), (0, 1), (784, 1), (0, 0.5), (1047, 0.5), (784, 1),
                     (659, 1), (523, 1), (0, 1)]:
            mel = np.concatenate([mel, self._sq(n, d * bd, 0.25, 0.15) if n
                                 else np.zeros(int(SR * d * bd), dtype=np.int16)])
        mel = self._env(mel, 0.01, 0.04, 0.7, 0.08)
        bas = np.array([], dtype=np.int16)
        for n, d in [(131, 2), (196, 2), (262, 2), (196, 2), (131, 2), (165, 2), (131, 4)]:
            bas = np.concatenate([bas, self._tri(n, d * bd, 0.2)])
        return pygame.mixer.Sound(buffer=self._mix(mel, bas).tobytes())

    def _mk_mus_game(self):
        bd = 60 / 140
        mel = np.array([], dtype=np.int16)
        seq = [
            (659, 0.5), (659, 0.5), (0, 0.5), (659, 0.5), (0, 0.5), (523, 0.5),
            (659, 0.5), (784, 1.0), (0, 1.0), (392, 1.0), (0, 1.0), (0, 1.0), (0, 1.0),
            (523, 1.0), (0, 0.5), (392, 0.5), (0, 1.0), (330, 1.0), (0, 0.5),
            (440, 1.0), (494, 0.5), (0, 0.5), (466, 0.5), (440, 1.0),
            (392, 1.5), (659, 1.0), (784, 0.5), (880, 1.0), (698, 0.5), (784, 0.5),
            (0, 0.5), (659, 1.0), (0, 0.5), (523, 0.5), (587, 0.5), (494, 0.5), (0, 2.0)
        ]
        for n, d in seq:
            mel = np.concatenate([mel, self._sq(n, d * bd, 0.25, 0.18) if n
                                 else np.zeros(int(SR * d * bd), dtype=np.int16)])
        mel = self._env(mel, 0.004, 0.02, 0.75, 0.03)
        bas = np.array([], dtype=np.int16)
        bseq = [
            (131, 2.0), (98, 2.0), (131, 2.0), (165, 2.0),
            (98, 2.0), (131, 2.0), (98, 2.0), (131, 2.0),
            (131, 2.0), (98, 2.0), (131, 2.0), (165, 2.0),
            (98, 2.0), (131, 2.0), (98, 2.0), (131, 2.0)
        ]
        for n, d in bseq:
            bas = np.concatenate([bas, self._tri(n, d * bd, 0.25)])
        return pygame.mixer.Sound(buffer=self._mix(mel, bas).tobytes())

    def play_sfx(self, name):
        if self.muted or name not in self.sfx: return
        for c in self.ch_sfx:
            if not c.get_busy(): c.play(self.sfx[name]); return
        self.ch_sfx[0].play(self.sfx[name])

    def play_mus(self, name):
        if name == self.cur_mus: return
        self.stop_mus()
        if name in self.music:
            self.cur_mus = name
            self.ch_mus.play(self.music[name], loops=-1)
            self.ch_mus.set_volume(0.0 if self.muted else 0.5)

    def stop_mus(self):
        self.ch_mus.stop(); self.cur_mus = None

    def toggle_mute(self):
        self.muted = not self.muted
        self.ch_mus.set_volume(0.0 if self.muted else 0.5)
        if self.muted:
            for c in self.ch_sfx: c.stop()
        return self.muted

# ====================================================================
# SPRITE GENERATOR
# ====================================================================
def make_sprite(data, palette):
    h = len(data); w = max(len(r) for r in data)
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    for y, row in enumerate(data):
        for x, c in enumerate(row):
            if c in palette: surf.set_at((x, y), palette[c])
    return surf

PAL_MARIO = {'R': C_RED, 'S': C_SKIN, 'B': C_BROWN, 'K': C_BLK}
PAL_GOOMBA = {'B': C_BROWN, 'D': C_DBROWN, 'W': C_WHT, 'K': C_BLK}

MARIO_STAND = [
    "...KKK.....",
    "..KRRRK....",
    "..RRRRRRR..",
    "..SSSRSRS..",
    ".SRSRRSRSR.",
    ".SRSRRSRSR.",
    "..SSSSSSSS.",
    "...RRRRRR..",
    "..BBRBRRB..",
    ".BBBRBRRRBB",
    "SSBRRRRRRSS",
    "SSS......SS",
    ".BB......BB.",
    "BBB......BBB"
]
MARIO_RUN1 = [
    "...KKK.....",
    "..KRRRK....",
    "..RRRRRRR..",
    "..SSSRSRS..",
    ".SRSRRSRSR.",
    ".SRSRRSRSR.",
    "..SSSSSSSS.",
    "...RRRRRR..",
    "..BBRBRRB..",
    ".BBBRBRRRBB",
    "SSBRRRRRRSS",
    "SSS......SS",
    "..BBB..BB..",
    "..BBBB.BBB.",
    "...BBB.BBB."
]
MARIO_JUMP = [
    "...KKK.....",
    "..KRRRK....",
    "..RRRRRRR..",
    "..SSSRSRS..",
    ".SRSRRSRSR.",
    ".SRSRRSRSR.",
    "..SSSSSSSS.",
    "...RRRRRR..",
    "..BBRBRRB..",
    ".BBBRBRRRBB",
    "SSBRRRRRRSS",
    "SSS......SS",
    "...BBB.....",
    "..BBBBBBB..",
    ".BBBB.BBB.."
]
MARIO_DIE = [
    "KKK........",
    "KRRRK......",
    "RRRRRRRR...",
    "SSSRSRS....",
    "SRSRRSRSR..",
    "SRSRRSRSR..",
    ".SSSSSSSS..",
    "..RRRRRR...",
    ".BBRBRRB...",
    "BBBRBRRRBB.",
    "SSBRRRRRRSS",
    "SSS......SS",
    "..BBB..BB..",
    "..BBBB.BBB."
]

GOOMBA_DATA = [
    "...KKK.....",
    "..KBDBBK...",
    ".KBBDBDBBK.",
    "KBBBBBBBBBK",
    "KBDDBBBBDDBK",
    "KBBBBBBBBBK",
    ".KBBWWBBBK.",
    "..KBBBBBBK..",
    "..DDDDDDDD.",
    ".DDD....DDD.",
    "DDD......DDD"
]

def get_sprites():
    m = {
        'stand': pygame.transform.scale(make_sprite(MARIO_STAND, PAL_MARIO), (TS, TS)),
        'run1': pygame.transform.scale(make_sprite(MARIO_RUN1, PAL_MARIO), (TS, TS)),
        'run2': pygame.transform.flip(pygame.transform.scale(make_sprite(MARIO_RUN1, PAL_MARIO), (TS, TS)), True, False),
        'jump': pygame.transform.scale(make_sprite(MARIO_JUMP, PAL_MARIO), (TS, TS)),
        'die': pygame.transform.scale(make_sprite(MARIO_DIE, PAL_MARIO), (TS, TS))
    }
    g = pygame.transform.scale(make_sprite(GOOMBA_DATA, PAL_GOOMBA), (TS, TS))

    t_gnd = pygame.Surface((TS, TS)); t_gnd.fill(C_GND); pygame.draw.rect(t_gnd, C_GNDD, (0, 0, TS, 4))
    t_brk = pygame.Surface((TS, TS)); t_brk.fill(C_BRK)
    for i in range(0, TS, 8):
        for j in range(0, TS, 8):
            offset = 4 if (j // 8) % 2 == 0 else 0
            pygame.draw.line(t_brk, C_BRKD, (i + offset, j), (i + offset + 8, j + 8), 2)
    t_qst = pygame.Surface((TS, TS)); t_qst.fill(C_QST); pygame.draw.rect(t_qst, C_QSTD, (0, 0, TS, TS), 3)
    t_qst_hit = pygame.Surface((TS, TS)); t_qst_hit.fill(C_BRK); pygame.draw.rect(t_qst_hit, C_BRKD, (0, 0, TS, TS), 3)
    t_stn = pygame.Surface((TS, TS)); t_stn.fill(C_STN); pygame.draw.rect(t_stn, C_STND, (0, 0, TS, TS), 2)

    t_pipe_tl = pygame.Surface((TS, TS)); t_pipe_tl.fill(C_PTL); pygame.draw.rect(t_pipe_tl, C_PBL, (0, 0, TS, TS), 3); pygame.draw.rect(t_pipe_tl, C_PTR, (0, 0, TS, 8))
    t_pipe_tr = pygame.Surface((TS, TS)); t_pipe_tr.fill(C_PTR); pygame.draw.rect(t_pipe_tr, C_PBR, (0, 0, TS, TS), 3); pygame.draw.rect(t_pipe_tr, C_PTL, (0, 0, TS, 8))
    t_pipe_bl = pygame.Surface((TS, TS)); t_pipe_bl.fill(C_PTL); pygame.draw.rect(t_pipe_bl, C_PBL, (0, 0, TS, TS), 3)
    t_pipe_br = pygame.Surface((TS, TS)); t_pipe_br.fill(C_PTR); pygame.draw.rect(t_pipe_br, C_PBR, (0, 0, TS, TS), 3)

    t_cast = pygame.Surface((TS, TS)); t_cast.fill(C_CAST); pygame.draw.rect(t_cast, C_STND, (0, 0, TS, TS), 2)
    t_flag_pole = pygame.Surface((4, TS * 4)); t_flag_pole.fill(C_POLE)
    t_flag_top = pygame.Surface((TS, TS)); t_flag_top.fill(C_GOLD)
    t_flag = pygame.Surface((TS, TS)); t_flag.fill((0, 0, 0, 0))
    pygame.draw.polygon(t_flag, C_FLAG, [(0, 0), (TS, TS // 2), (0, TS)])

    tiles = {
        'gnd': t_gnd, 'brk': t_brk, 'qst': t_qst, 'qst_hit': t_qst_hit, 'stn': t_stn,
        'ptl': t_pipe_tl, 'ptr': t_pipe_tr, 'pbl': t_pipe_bl, 'pbr': t_pipe_br,
        'castle': t_cast, 'flag_pole': t_flag_pole, 'flag_top': t_flag_top, 'flag': t_flag
    }
    return m, g, tiles

# ====================================================================
# PROCEDURAL LEVEL GENERATOR
# ====================================================================
# 0=Air, 1=Ground, 2=Brick, 3=Question, 4=PipeTL, 5=PipeTR, 6=PipeBL, 7=PipeBR, 8=Stone, 9=Castle
SOLID_TILES = {1, 2, 3, 4, 5, 6, 7, 8, 9}

def generate_level(world, level):
    w, h = 220, 15
    grid = [[0] * w for _ in range(h)]
    enemies = []
    objects = []

    gnd_y = h - 2
    tile_set = 'gnd' if world <= 4 else 'stn'
    t_g, t_b, t_q = (1, 2, 3) if world <= 4 else (8, 8, 8)

    # Base Ground — 2 rows thick
    for x in range(w):
        grid[gnd_y][x] = t_g
        grid[gnd_y + 1][x] = t_g

    # Guarantee the first 10 tiles are flat ground (no gaps/pipes/blocks)
    safe_zone = 10

    diff = world * 4 + level
    rng = random.Random(world * 100 + level)

    # Gaps — only past safe zone
    num_gaps = int(diff / 5) + 1
    for _ in range(num_gaps):
        gx = rng.randint(safe_zone + 5, w - 30)
        gap_w = rng.randint(2, min(4, 2 + diff // 10))
        for i in range(gap_w):
            if gx + i < w:
                grid[gnd_y][gx + i] = 0
                grid[gnd_y + 1][gx + i] = 0

    # Pipes — only past safe zone, not on gaps
    num_pipes = int(diff / 6) + 1
    for _ in range(num_pipes):
        px = rng.randint(safe_zone + 3, w - 20)
        if grid[gnd_y][px] == 0 or grid[gnd_y][px + 1] == 0:
            continue
        ph = rng.randint(2, min(5, 2 + diff // 8))
        pt, pb = (4, 6) if world <= 4 else (8, 8)
        grid[gnd_y - ph][px] = pt
        grid[gnd_y - ph][px + 1] = pt + 1
        for py in range(gnd_y - ph + 1, gnd_y):
            grid[py][px] = pb
            grid[py][px + 1] = pb + 1

    # Blocks — only past safe zone, only in air
    num_blocks = int(diff / 3) + 3
    for _ in range(num_blocks):
        bx = rng.randint(safe_zone + 2, w - 15)
        by = rng.randint(gnd_y - 6, gnd_y - 3)
        if grid[by][bx] == 0:
            grid[by][bx] = rng.choice([t_b, t_q, t_q])

    # Staircase at end
    sx = w - 15
    for i in range(8):
        for j in range(i + 1):
            if sx + i < w:
                grid[gnd_y - 1 - j][sx + i] = t_g

    # Flag
    flag_x = sx + 9
    if flag_x < w:
        objects.append((flag_x, gnd_y - 1, 'flag'))

    # Castle
    castle_x = flag_x + 3
    if castle_x + 4 < w:
        for cy in range(gnd_y - 4, gnd_y):
            for cx in range(castle_x, min(castle_x + 5, w)):
                grid[cy][cx] = 9

    # Enemies — only on solid ground, past safe zone
    num_enemies = int(diff / 2) + 2
    for _ in range(num_enemies):
        ex = rng.randint(safe_zone + 5, w - 20)
        if grid[gnd_y][ex] in SOLID_TILES:
            enemies.append([ex * TS, (gnd_y - 1) * TS])

    return grid, enemies, objects, w * TS, h * TS, tile_set

# ====================================================================
# TILE COLLISION HELPERS  (all in world-pixel coordinates)
# ====================================================================
def tile_at(grid, col, row):
    """Return tile type at grid[col][row], or 0 if out of bounds."""
    if 0 <= row < len(grid) and 0 <= col < len(grid[0]):
        return grid[row][col]
    return 0

def is_solid(grid, col, row):
    return tile_at(grid, col, row) in SOLID_TILES

def rect_overlaps_solid(grid, rect):
    """Check if a world-pixel rect overlaps any solid tile."""
    c1 = max(0, int(rect.left) // TS)
    c2 = min(len(grid[0]) - 1, int(rect.right - 1) // TS)
    r1 = max(0, int(rect.top) // TS)
    r2 = min(len(grid) - 1, int(rect.bottom - 1) // TS)
    for r in range(r1, r2 + 1):
        for c in range(c1, c2 + 1):
            if grid[r][c] in SOLID_TILES:
                return True
    return False

# ====================================================================
# ENTITIES
# ====================================================================
class Player:
    def __init__(self, sprites):
        self.spr = sprites
        self.rect = pygame.Rect(0, 0, TS - 4, TS - 2)
        self.vel_x, self.vel_y = 0.0, 0.0
        self.on_ground = False
        self.facing_r = True
        self.anim_timer = 0.0
        self.alive = True
        self.dying_timer = 0
        self.clearing = False
        self.clear_vel_x = 0.0

    def update(self, keys, grid, level_h):
        if not self.alive:
            self.dying_timer += 1
            self.vel_y += GRAVITY
            self.rect.y += int(self.vel_y)
            return None

        if self.clearing:
            self.clear_vel_x += 0.5
            self.rect.x += int(self.clear_vel_x)
            return None

        # Horizontal input
        acc = 0.4
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.vel_x -= acc; self.facing_r = False
        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.vel_x += acc; self.facing_r = True
        else:
            self.vel_x *= 0.85

        if abs(self.vel_x) > 6: self.vel_x = 6 * (1 if self.vel_x > 0 else -1)
        if abs(self.vel_x) < 0.2: self.vel_x = 0

        if (keys[pygame.K_SPACE] or keys[pygame.K_UP] or keys[pygame.K_w]) and self.on_ground:
            self.vel_y = -11.0
            self.on_ground = False
            audio.play_sfx('jump')

        # Gravity
        self.vel_y += GRAVITY
        if self.vel_y > MAX_FALL: self.vel_y = MAX_FALL

        # Move X + resolve
        self.rect.x += int(self.vel_x)
        result = self._collide_x(grid)
        if result: return result

        # Move Y + resolve
        self.rect.y += int(self.vel_y)
        self.on_ground = False
        result = self._collide_y(grid)
        if result: return result

        # Animation
        if abs(self.vel_x) > 0.5:
            self.anim_timer += abs(self.vel_x) * 0.1
        else:
            self.anim_timer = 0

        # Bottomless pit
        if self.rect.top > level_h + TS * 2:
            self.kill()

        return None

    def _collide_x(self, grid):
        c1 = max(0, self.rect.left // TS)
        c2 = min(len(grid[0]) - 1, (self.rect.right - 1) // TS)
        r1 = max(0, self.rect.top // TS)
        r2 = min(len(grid) - 1, (self.rect.bottom - 1) // TS)
        for r in range(r1, r2 + 1):
            for c in range(c1, c2 + 1):
                if grid[r][c] in SOLID_TILES:
                    t_rect = pygame.Rect(c * TS, r * TS, TS, TS)
                    if self.rect.colliderect(t_rect):
                        if self.vel_x > 0:
                            self.rect.right = t_rect.left
                        elif self.vel_x < 0:
                            self.rect.left = t_rect.right
                        self.vel_x = 0
        return None

    def _collide_y(self, grid):
        c1 = max(0, self.rect.left // TS)
        c2 = min(len(grid[0]) - 1, (self.rect.right - 1) // TS)
        r1 = max(0, self.rect.top // TS)
        r2 = min(len(grid) - 1, (self.rect.bottom - 1) // TS)
        for r in range(r1, r2 + 1):
            for c in range(c1, c2 + 1):
                if grid[r][c] in SOLID_TILES:
                    t_rect = pygame.Rect(c * TS, r * TS, TS, TS)
                    if self.rect.colliderect(t_rect):
                        if self.vel_y > 0:
                            self.rect.bottom = t_rect.top
                            self.vel_y = 0
                            self.on_ground = True
                        elif self.vel_y < 0:
                            self.rect.top = t_rect.bottom
                            self.vel_y = 1
                            if grid[r][c] == 3:
                                grid[r][c] = 0
                                audio.play_sfx('coin')
                                return 'coin'
                            elif grid[r][c] == 2:
                                grid[r][c] = 0
                                return 'break'
        return None

    def kill(self):
        if self.alive:
            self.alive = False
            self.vel_y = -10
            self.vel_x = 0
            audio.play_sfx('die')

    def draw(self, surf, cam_x, cam_y):
        sx = self.rect.x - cam_x
        sy = self.rect.y - cam_y
        if not (-TS < sx < SW + TS and -TS < sy < SH + TS):
            return
        if not self.alive:
            surf.blit(self.spr['die'], (sx, sy))
        elif not self.on_ground:
            spr = self.spr['jump']
            if not self.facing_r: spr = pygame.transform.flip(spr, True, False)
            surf.blit(spr, (sx, sy))
        elif abs(self.vel_x) > 0.5:
            idx = 'run1' if int(self.anim_timer) % 2 == 0 else 'run2'
            spr = self.spr[idx]
            if not self.facing_r: spr = pygame.transform.flip(spr, True, False)
            surf.blit(spr, (sx, sy))
        else:
            spr = self.spr['stand']
            if not self.facing_r: spr = pygame.transform.flip(spr, True, False)
            surf.blit(spr, (sx, sy))


class Enemy:
    def __init__(self, x, y, sprite):
        self.rect = pygame.Rect(x, y, TS, TS)
        self.vel_x = -1.5
        self.alive = True
        self.spr = sprite
        self.death_timer = 0
        self.fall_vy = 0.0

    def update(self, grid, level_h, diff_mult=1.0):
        if not self.alive:
            self.death_timer += 1
            return

        self.vel_x = -1.5 * diff_mult

        # Move X
        self.rect.x += int(self.vel_x)
        self._collide_x(grid)

        # Edge detection — reverse if about to walk off a cliff
        check_x = self.rect.left if self.vel_x < 0 else self.rect.right - 1
        check_r = int((self.rect.bottom) // TS)
        check_c = int(check_x // TS)
        if not is_solid(grid, check_c, check_r):
            self.rect.x -= int(self.vel_x)
            self.vel_x *= -1

        # Gravity
        self.fall_vy += GRAVITY
        if self.fall_vy > MAX_FALL: self.fall_vy = MAX_FALL
        self.rect.y += int(self.fall_vy)
        self._collide_y(grid)

        # Remove if fallen off world
        if self.rect.top > level_h + TS * 4:
            self.alive = False

    def _collide_x(self, grid):
        c1 = max(0, self.rect.left // TS)
        c2 = min(len(grid[0]) - 1, (self.rect.right - 1) // TS)
        r1 = max(0, self.rect.top // TS)
        r2 = min(len(grid) - 1, (self.rect.bottom - 1) // TS)
        for r in range(r1, r2 + 1):
            for c in range(c1, c2 + 1):
                if grid[r][c] in SOLID_TILES:
                    t_rect = pygame.Rect(c * TS, r * TS, TS, TS)
                    if self.rect.colliderect(t_rect):
                        if self.vel_x > 0:
                            self.rect.right = t_rect.left
                        elif self.vel_x < 0:
                            self.rect.left = t_rect.right
                        self.vel_x *= -1

    def _collide_y(self, grid):
        c1 = max(0, self.rect.left // TS)
        c2 = min(len(grid[0]) - 1, (self.rect.right - 1) // TS)
        r1 = max(0, self.rect.top // TS)
        r2 = min(len(grid) - 1, (self.rect.bottom - 1) // TS)
        for r in range(r1, r2 + 1):
            for c in range(c1, c2 + 1):
                if grid[r][c] in SOLID_TILES:
                    t_rect = pygame.Rect(c * TS, r * TS, TS, TS)
                    if self.rect.colliderect(t_rect):
                        if self.fall_vy > 0:
                            self.rect.bottom = t_rect.top
                            self.fall_vy = 0
                        elif self.fall_vy < 0:
                            self.rect.top = t_rect.bottom
                            self.fall_vy = 0

    def draw(self, surf, cam_x, cam_y):
        sx = self.rect.x - cam_x
        sy = self.rect.y - cam_y
        if not (-TS < sx < SW + TS and -TS < sy < SH + TS):
            return
        if not self.alive:
            if self.death_timer < 15:
                squish = pygame.transform.scale(self.spr, (TS, TS // 2))
                surf.blit(squish, (sx, sy + TS // 2))
        else:
            surf.blit(self.spr, (sx, sy))

# ====================================================================
# GAME CLASS
# ====================================================================
class Game:
    def __init__(self):
        global audio
        audio = FamicomAudio()
        self.spr_m, self.spr_g, self.tiles = get_sprites()

        self.state = 'menu'
        self.world = 1; self.level = 1
        self.lives = 3; self.coins = 0; self.score = 0; self.timer = 400

        self.cam_x = 0.0; self.cam_y = 0.0
        self.particles = []
        self.state_timer = 0
        self.grid = None
        self.player = None
        self.enemies = []
        self.objects = []
        self.lw = 0; self.lh = 0; self.tile_set = 'gnd'
        self.enemy_diff = 1.0
        self.flag_rect = None

        self._build_dummy_level()

    def _build_dummy_level(self):
        """Build a placeholder so draw_menu doesn't crash on tile access."""
        self.grid, _, self.objects, self.lw, self.lh, self.tile_set = generate_level(1, 1)
        self.flag_rect = None

    def load_level(self):
        self.grid, enemies_data, self.objects, self.lw, self.lh, self.tile_set = generate_level(self.world, self.level)
        self.player = Player(self.spr_m)

        # === FIX: Spawn Mario on the actual ground surface ===
        gnd_row = len(self.grid) - 2  # top row of ground
        self.player.rect.x = 3 * TS
        self.player.rect.bottom = gnd_row * TS  # snap feet to top of ground

        self.enemy_diff = 1.0 + (self.world - 1) * 0.15
        self.enemies = [Enemy(x, y, self.spr_g) for x, y in enemies_data]

        # Camera: snap to Mario so he's visible immediately
        self.cam_x = max(0.0, float(self.player.rect.x - SW // 3))
        self.cam_y = max(0.0, float(self.player.rect.bottom - SH * 0.6))

        self.timer = 400
        self.particles = []

        # Flag rect (world coords)
        self.flag_rect = None
        for obj in self.objects:
            if obj[2] == 'flag':
                # Flag pole spans from obj Y up ~8 tiles
                self.flag_rect = pygame.Rect(obj[0] * TS, (obj[1] - 8) * TS, TS, TS * 9)

    def handle_events(self):
        for e in pygame.event.get():
            if e.type == pygame.QUIT: pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_m: audio.toggle_mute()

                if self.state == 'menu':
                    if e.key in (pygame.K_RETURN, pygame.K_SPACE):
                        audio.play_sfx('coin')
                        self.state = 'playing'
                        self.world = 1; self.level = 1
                        self.lives = 3; self.score = 0; self.coins = 0
                        self.load_level()
                        audio.play_mus('game')

                elif self.state in ('game_over', 'win'):
                    if e.key in (pygame.K_RETURN, pygame.K_SPACE):
                        self.state = 'menu'; audio.play_mus('menu')

                elif self.state == 'playing':
                    if e.key == pygame.K_ESCAPE:
                        self.state = 'menu'; audio.play_mus('menu')

    def update(self):
        if self.state == 'menu': return
        self.state_timer += 1

        if self.state == 'playing':
            keys = pygame.key.get_pressed()

            # Timer
            if self.state_timer % 60 == 0 and self.timer > 0:
                self.timer -= 1
                if self.timer == 0: self.player.kill()

            # Player update (collision in world coords, no camera needed)
            res = self.player.update(keys, self.grid, self.lh)
            if res == 'coin':
                self.coins += 1; self.score += 100
            elif res == 'break':
                cx, cy = self.player.rect.centerx, self.player.rect.top
                for _ in range(4):
                    self.particles.append([cx, cy, random.uniform(-3, 3),
                                           random.uniform(-5, -1), 30, C_BRK])

            # Camera smooth follow (world coords)
            target_cx = self.player.rect.x - SW // 3
            self.cam_x += (target_cx - self.cam_x) * 0.1
            self.cam_x = max(0.0, min(self.cam_x, self.lw - SW))

            target_cy = self.player.rect.bottom - SH * 0.6
            self.cam_y += (target_cy - self.cam_y) * 0.08
            self.cam_y = max(0.0, min(self.cam_y, self.lh - SH))

            # Enemies
            for en in self.enemies:
                en.update(self.grid, self.lh, self.enemy_diff)
            self.enemies = [e for e in self.enemies if e.alive or e.death_timer < 15]

            # Player vs Enemies (world coords)
            if self.player.alive and not self.player.clearing:
                for en in self.enemies:
                    if en.alive and self.player.rect.colliderect(en.rect):
                        if self.player.vel_y > 0 and self.player.rect.bottom < en.rect.centery + 4:
                            en.alive = False; en.death_timer = 0
                            self.player.vel_y = -8
                            self.score += 100
                            audio.play_sfx('stomp')
                        else:
                            self.player.kill()

            # Flag collision (world coords)
            if self.flag_rect and self.player.alive and self.player.rect.colliderect(self.flag_rect):
                self.player.clearing = True
                self.state = 'level_clear'
                self.state_timer = 0
                self.score += self.timer * 10
                audio.play_sfx('clear'); audio.stop_mus()

            # Death
            if not self.player.alive and self.player.dying_timer > 90:
                self.lives -= 1
                if self.lives <= 0:
                    self.state = 'game_over'; self.state_timer = 0
                else:
                    self.load_level()

            # Particles
            for p in self.particles:
                p[0] += p[2]; p[1] += p[3]; p[3] += 0.2; p[4] -= 1
            self.particles = [p for p in self.particles if p[4] > 0]

        elif self.state == 'level_clear':
            self.player.update(pygame.key.get_pressed(), self.grid, self.lh)
            if self.state_timer > 180:
                self.level += 1
                if self.level > 4:
                    self.level = 1; self.world += 1
                    if self.world > 8:
                        self.state = 'win'; self.state_timer = 0; return
                self.load_level()
                self.state = 'playing'; self.state_timer = 0
                audio.play_mus('game')

    def draw(self):
        if self.state == 'menu':
            self.draw_menu(); return
        if self.state == 'game_over':
            self.draw_gameover(); return
        if self.state == 'win':
            self.draw_win(); return

        icx, icy = int(self.cam_x), int(self.cam_y)

        # Background
        bg = C_SKY if self.tile_set == 'gnd' else C_UNDG
        screen.fill(bg)

        # Decorative hills / background elements (parallax)
        hill_offset = icx // 4
        for i in range(5):
            hx = i * 300 - (hill_offset % 300)
            pygame.draw.ellipse(screen, (80, 160, 60) if self.tile_set == 'gnd' else (30, 30, 30),
                                (hx, icy + SH - TS * 4, 200, 100))
            pygame.draw.ellipse(screen, (60, 140, 40) if self.tile_set == 'gnd' else (20, 20, 20),
                                (hx + 40, icy + SH - TS * 4 - 30, 160, 80))

        # Clouds (parallax)
        cloud_off = icx // 6
        for i in range(6):
            cx = i * 220 - (cloud_off % 220)
            cy_c = icy + 80 + (i * 37) % 120
            if self.tile_set == 'gnd':
                pygame.draw.ellipse(screen, C_WHT, (cx, cy_c, 80, 35))
                pygame.draw.ellipse(screen, C_WHT, (cx + 20, cy_c - 15, 50, 35))
                pygame.draw.ellipse(screen, C_WHT, (cx + 40, cy_c, 50, 30))

        # Tiles
        start_col = max(0, icx // TS)
        end_col = min(len(self.grid[0]), (icx + SW) // TS + 2)
        start_row = max(0, icy // TS)
        end_row = min(len(self.grid), (icy + SH) // TS + 2)

        tile_map = {
            1: 'gnd', 2: 'brk', 3: 'qst', 4: 'ptl', 5: 'ptr',
            6: 'pbl', 7: 'pbr', 8: 'stn', 9: 'castle'
        }

        for r in range(start_row, end_row):
            for c in range(start_col, end_col):
                t = self.grid[r][c]
                if t == 0: continue
                key = tile_map.get(t)
                if key:
                    screen.blit(self.tiles[key], (c * TS - icx, r * TS - icy))

        # Flag objects
        for obj in self.objects:
            if obj[2] == 'flag':
                fx = obj[0] * TS - icx
                fy_base = obj[1] * TS - icy
                screen.blit(self.tiles['flag_pole'], (fx + TS // 2 - 2, fy_base - TS * 4))
                screen.blit(self.tiles['flag_top'], (fx + TS // 2 - 8, fy_base - TS * 4 - 12))
                screen.blit(self.tiles['flag'], (fx + TS // 2 - 2, fy_base - TS * 4 + 8))

        # Enemies
        for en in self.enemies:
            en.draw(screen, icx, icy)

        # Player
        self.player.draw(screen, icx, icy)

        # Particles
        for p in self.particles:
            px, py = p[0] - icx, p[1] - icy
            pygame.draw.rect(screen, p[5], (px, py, 8, 8))

        # HUD
        self.draw_hud()

        if self.state == 'level_clear':
            overlay = pygame.Surface((SW, SH), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 100))
            screen.blit(overlay, (0, 0))
            txt = font_big.render(f"WORLD {self.world}-{self.level} CLEAR!", True, C_WHT)
            screen.blit(txt, (SW // 2 - txt.get_width() // 2, SH // 2 - 50))
            sc_txt = font_med.render(f"SCORE: {self.score}", True, C_GOLD)
            screen.blit(sc_txt, (SW // 2 - sc_txt.get_width() // 2, SH // 2 + 20))

    def draw_hud(self):
        hud_bg = pygame.Surface((SW, 50), pygame.SRCALPHA)
        hud_bg.fill((0, 0, 0, 150))
        screen.blit(hud_bg, (0, 0))

        screen.blit(font_hud.render("MARIO", True, C_WHT), (20, 5))
        screen.blit(font_hud.render(f"{str(self.score).zfill(6)}", True, C_WHT), (20, 25))

        pygame.draw.circle(screen, C_GOLD, (SW // 2 - 40, 20), 8)
        screen.blit(font_hud.render(f"x{self.coins:02d}", True, C_WHT), (SW // 2 - 25, 10))

        screen.blit(font_hud.render("WORLD", True, C_WHT), (SW // 2 + 40, 5))
        screen.blit(font_hud.render(f" {self.world}-{self.level}", True, C_WHT), (SW // 2 + 40, 25))

        screen.blit(font_hud.render("TIME", True, C_WHT), (SW - 120, 5))
        screen.blit(font_hud.render(f" {self.timer:03d}", True, C_WHT), (SW - 120, 25))

        screen.blit(font_sm.render(f"x{self.lives}", True, C_WHT), (SW // 2 - 100, 25))
        screen.blit(self.spr_m['stand'], (SW // 2 - 130, 22))

    def draw_menu(self):
        screen.fill(C_SKY)
        for i in range(0, SW, TS):
            screen.blit(self.tiles['gnd'], (i, SH - TS * 2))
            screen.blit(self.tiles['gnd'], (i, SH - TS))

        for i in range(3):
            cx = (i * 250 + pygame.time.get_ticks() // 50) % (SW + 100) - 50
            pygame.draw.ellipse(screen, C_WHT, (cx, 100, 80, 40))
            pygame.draw.ellipse(screen, C_WHT, (cx + 20, 80, 60, 40))
            pygame.draw.ellipse(screen, C_WHT, (cx + 40, 100, 60, 40))

        t1 = font_big.render("ULTRA MARIO 2D", True, C_WHT)
        t2 = font_big.render("BROS", True, C_WHT)
        screen.blit(font_big.render("ULTRA MARIO 2D", True, C_BLK), (SW // 2 - t1.get_width() // 2 + 3, 203))
        screen.blit(font_big.render("BROS", True, C_BLK), (SW // 2 - t2.get_width() // 2 + 3, 253))
        screen.blit(t1, (SW // 2 - t1.get_width() // 2, 200))
        screen.blit(t2, (SW // 2 - t2.get_width() // 2, 250))

        sub = font_med.render("Famicom Edition", True, C_GOLD)
        screen.blit(sub, (SW // 2 - sub.get_width() // 2, 310))

        p = math.sin(pygame.time.get_ticks() * 0.005) * 30 + 225
        col = (255, int(p), int(p * 0.4))
        t3 = font_med.render("PRESS ENTER TO START", True, col)
        screen.blit(t3, (SW // 2 - t3.get_width() // 2, 400))

        t4 = font_sm.render("WASD/Arrows: Move | SPACE: Jump | M: Mute | ESC: Quit", True, C_WHT)
        screen.blit(t4, (SW // 2 - t4.get_width() // 2, 500))

        worlds_txt = font_sm.render("8 Worlds x 4 Levels = 32 Stages!", True, C_GOLD)
        screen.blit(worlds_txt, (SW // 2 - worlds_txt.get_width() // 2, 550))

    def draw_gameover(self):
        screen.fill(C_BLK)
        t1 = font_big.render("GAME OVER", True, C_RED)
        screen.blit(t1, (SW // 2 - t1.get_width() // 2, SH // 2 - 60))
        t1b = font_med.render(f"Final Score: {self.score}", True, C_WHT)
        screen.blit(t1b, (SW // 2 - t1b.get_width() // 2, SH // 2))
        if self.state_timer > 60:
            p = math.sin(pygame.time.get_ticks() * 0.005) * 30 + 225
            t2 = font_med.render("PRESS ENTER", True, (int(p), int(p), int(p)))
            screen.blit(t2, (SW // 2 - t2.get_width() // 2, SH // 2 + 60))

    def draw_win(self):
        screen.fill(C_SKY)
        t1 = font_big.render("CONGRATULATIONS!", True, C_GOLD)
        screen.blit(t1, (SW // 2 - t1.get_width() // 2, SH // 2 - 100))
        t2 = font_med.render("YOU SAVED THE MUSHROOM KINGDOM!", True, C_WHT)
        screen.blit(t2, (SW // 2 - t2.get_width() // 2, SH // 2 - 30))
        t3 = font_med.render(f"FINAL SCORE: {self.score}", True, C_GOLD)
        screen.blit(t3, (SW // 2 - t3.get_width() // 2, SH // 2 + 20))
        # Fireworks
        for i in range(8):
            fx = SW // 2 + int(math.sin(self.state_timer * 0.05 + i) * 200)
            fy = SH // 2 + int(math.cos(self.state_timer * 0.07 + i * 0.8) * 100) - 60
            color = [C_RED, C_GOLD, C_FLAG, C_SKIN, C_QST, C_WHT, C_PTL, C_PTR][i % 8]
            pygame.draw.circle(screen, color, (fx, fy), 6 + i % 4)
        if self.state_timer > 120:
            p = math.sin(pygame.time.get_ticks() * 0.005) * 30 + 225
            t4 = font_med.render("PRESS ENTER", True, (int(p), int(p), int(p)))
            screen.blit(t4, (SW // 2 - t4.get_width() // 2, SH // 2 + 100))

# ====================================================================
# MAIN LOOP
# ====================================================================
def main():
    game = Game()
    audio.play_mus('menu')

    while True:
        clock.tick(FPS)
        game.handle_events()
        game.update()
        game.draw()
        pygame.display.flip()

if __name__ == "__main__":
    main()
