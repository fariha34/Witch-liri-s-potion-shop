#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Witch Liri's Magical Potion Shop
================================
A 3D fantasy potion-crafting / time-management game in a single file.
Python + PyOpenGL (GL / GLU / GLUT). All models are built from geometric
primitives and animated with hierarchical transformations.

Install:
    pip install PyOpenGL PyOpenGL_accelerate numpy pygame
    (pygame is only used for the generated sound effects and music - without it the game runs silently)
    (Linux: sudo apt install freeglut3-dev   |  macOS: GLUT is built in
     Windows: if you get "NullFunctionError: glutInit", install a PyOpenGL
     wheel that bundles freeglut, or put freeglut.dll next to this file.)

Run:
    python witch_liri_potion_shop.py

Controls:
    WASD/Arrows  move (relative to the camera)
    Mouse drag   rotate camera      Mouse wheel   zoom      Z / C   rotate camera
    E            interact (hold to keep collecting / recipe book / serve / upgrade desk)
    1 - 8        add ingredient to the cauldron (or choose an item in an open menu)
    Space        stir the cauldron (start brewing / timed stir for a Perfect brew)
    Enter        confirm brewing at the cauldron, serve at the counter
    X/Backspace  empty the cauldron
    I            inventory          R   recipe book        H   help
    Esc          pause menu (or close an open window)
"""

import sys
import os
import math
import random
import time
import json

try:
    from OpenGL.GL import *
    from OpenGL.GLU import *
    from OpenGL.GLUT import *
except ImportError:
    print("PyOpenGL is required:  pip install PyOpenGL PyOpenGL_accelerate numpy")
    sys.exit(1)


# =============================================================================
# SETTINGS
# =============================================================================
WIN_W, WIN_H = 1280, 760
TITLE = b"Witch Liri's Magical Potion Shop"
SAVE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "liri_save.json")

PLAYER_SPEED = 4.3
PLAYER_RADIUS = 0.4
PLAYER_BOUNDS = (-9.5, 9.5, -7.6, 3.1)          # xmin, xmax, zmin, zmax

BASE_CAPACITY = 10
BIG_SHELF_CAPACITY = 15
BASE_BREW_TIME = 4.0
FAST_BREW_TIME = 2.4
BASE_REGROW = 5.0
BASE_MAX_STOCK = 3
POTION_CAP = 8
MAX_CAULDRON = 4
BONUS_WINDOW = (0.55, 0.78)                      # fraction of brew progress
ROYAL_REP_REQUIRED = 40
DELIVERY_COST = 12

CAULDRON_POS = (0.0, -1.5)
CAULDRON2_POS = (-4.3, -2.3)
RACK_POS = (2.4, -1.5)
DESK_POS = (7.0, -6.0)
DOOR_IN = (8.8, 6.6)
SPAWN_POINT = (8.8, 11.0)
OUTSIDE_POINT = (8.8, 12.5)
QUEUE_SLOTS = [(1.0 + 1.55 * i, 5.3) for i in range(6)]

OBSTACLE_BOXES = [
    (-8.4, -0.8, -8.0, -6.95),   # ingredient shelves (back wall)
    (5.5, 8.5, -7.0, -5.0),      # recipe & upgrade desk
    (-9.8, -7.5, -4.6, 2.6),     # garden planter
    (1.9, 2.9, -1.95, -1.05),    # bottle rack
    (8.9, 10.0, -1.4, 2.4),      # bookshelf on the right wall
]
OBSTACLE_CIRCLES = [(CAULDRON_POS[0], CAULDRON_POS[1], 1.1)]


# =============================================================================
# GAME DATA
# =============================================================================
INGREDIENTS = [
    # name,             color,               kind,       unlock stage, location, x,    z
    ("Red Flower",      (0.92, 0.12, 0.15), "flower",   1, "garden", -8.65, -3.7),
    ("Healing Herb",    (0.25, 0.75, 0.25), "herb",     1, "garden", -8.65, -1.9),
    ("Moonflower",      (0.70, 0.85, 1.00), "flower",   2, "garden", -8.65, -0.1),
    ("Shadow Mushroom", (0.50, 0.20, 0.65), "mushroom", 2, "shelf",  -5.5,  -6.5),
    ("Skyflower",       (0.45, 0.70, 1.00), "flower",   3, "garden", -8.65, 1.7),
    ("Crystal Dust",    (0.30, 0.60, 1.00), "crystal",  3, "shelf",  -3.7,  -6.5),
    ("Red Mushroom",    (0.88, 0.15, 0.10), "mushroom", 2, "shelf",  -7.3,  -6.5),
    ("Fire Crystal",    (1.00, 0.50, 0.10), "crystal",  2, "shelf",  -1.9,  -6.5),
]
ING_NAMES = [i[0] for i in INGREDIENTS]
ING = {i[0]: {"name": i[0], "color": i[1], "kind": i[2], "stage": i[3],
              "loc": i[4], "x": i[5], "z": i[6]} for i in INGREDIENTS}

RECIPES = [
    {"name": "Healing Potion", "seq": ["Red Flower", "Healing Herb"], "price": 10,
     "color": (0.95, 0.25, 0.35), "stage": 1, "tier": 1},
    {"name": "Strength Potion", "seq": ["Red Mushroom", "Fire Crystal"], "price": 18,
     "color": (1.00, 0.55, 0.10), "stage": 2, "tier": 2},
    {"name": "Invisibility Potion", "seq": ["Moonflower", "Shadow Mushroom"], "price": 15,
     "color": (0.70, 0.60, 0.95), "stage": 2, "tier": 2},
    {"name": "Flying Potion", "seq": ["Skyflower", "Crystal Dust"], "price": 20,
     "color": (0.45, 0.85, 1.00), "stage": 3, "tier": 2},
    {"name": "Starlight Tonic", "seq": ["Skyflower", "Moonflower", "Crystal Dust"], "price": 28,
     "color": (0.95, 0.95, 0.55), "stage": 3, "tier": 3},
    {"name": "Dragonfire Brew", "seq": ["Red Flower", "Red Mushroom", "Fire Crystal"], "price": 30,
     "color": (0.90, 0.20, 0.05), "stage": 4, "tier": 3},
    {"name": "Royal Aegis Elixir", "seq": ["Moonflower", "Healing Herb", "Fire Crystal", "Crystal Dust"],
     "price": 120, "color": (1.00, 0.85, 0.30), "stage": 5, "tier": 4},
]
# Secret recipes are not in the book until you discover them by experimenting.
SECRET_RECIPES = [
    {"name": "Potion of Luck", "seq": ["Healing Herb", "Moonflower", "Healing Herb"], "price": 35,
     "color": (0.45, 0.95, 0.45), "stage": 2, "tier": 3, "secret": True,
     "hint": "Moonlight wrapped between two healing leaves brings good fortune..."},
    {"name": "Giant's Draught", "seq": ["Red Mushroom", "Red Mushroom", "Fire Crystal"], "price": 40,
     "color": (0.75, 0.30, 0.15), "stage": 2, "tier": 3, "secret": True,
     "hint": "Twice the mushroom, once the fire - and you'll grow ten feet higher."},
    {"name": "Shadow Step Elixir", "seq": ["Shadow Mushroom", "Skyflower"], "price": 32,
     "color": (0.30, 0.25, 0.55), "stage": 3, "tier": 3, "secret": True,
     "hint": "A shadow that learns to fly moves without a sound..."},
    {"name": "Phoenix Potion", "seq": ["Moonflower", "Fire Crystal", "Skyflower"], "price": 45,
     "color": (1.00, 0.45, 0.20), "stage": 3, "tier": 3, "secret": True,
     "hint": "Fire born from moonlight rises into the sky..."},
    {"name": "Dream Tonic", "seq": ["Moonflower", "Moonflower", "Crystal Dust", "Healing Herb"], "price": 50,
     "color": (0.80, 0.70, 1.00), "stage": 3, "tier": 3, "secret": True,
     "hint": "Two moons, a pinch of stars, and something soothing to sleep on..."},
]
RECIPES += SECRET_RECIPES
RECIPE = {r["name"]: r for r in RECIPES}

# Regular customers who come back and continue their little stories.
REGULARS = {
    "Sir Bram": {"type": "Adventurer", "lines": [
        "Off to the Goblin Caves! Got anything to keep me alive?",
        "Ha! Your potion saved me from a goblin chief! I need another.",
        "An ogre this time. Big one. Potions, please - quickly!",
        "Heroes talk, Liri. Your shop is famous in every tavern.",
        "Retiring after this quest. Your potions made my legend!"],
        "thanks": "Thanks, Liri! Off I go!"},
    "Old Fennick": {"type": "Village Wizard", "lines": [
        "Your grandmother made the best potions. Let's see yours.",
        "Hmm! Just like hers. My old knees thank you.",
        "I told the whole village about you. Expect a crowd!",
        "She would be proud of you, little witch."],
        "thanks": "Splendid, splendid."},
    "Pip": {"type": "Fairy Visitor", "lines": [
        "Hi hi! Can I fly faster with this? Please say yes!",
        "I flew over the castle! The guards were SO confused!",
        "The fairy queen wants to meet the witch who brews sky-magic!",
        "You're famous in the fairy ring now. Everyone sparkles about you!"],
        "thanks": "Yay! Sparkle sparkle!"},
    "Madame Hazel": {"type": "Impatient Witch", "lines": [
        "Hurry up, girl. I haven't got all century.",
        "...Acceptable. Barely. Don't let it go to your head.",
        "Fine. Your potions are better than mine. Tell no one.",
        "I'm opening a rival shop! ...Kidding. I'll keep buying yours."],
        "thanks": "Hmph. Adequate."},
}

COMBO_TIME = 30.0                 # seconds to make the next sale and keep the combo
FRESH_TIME = 45.0                 # potions stay fresh this long on the rack...
DECAY_RATE = 0.8                  # ...then lose this much quality (0-100) per second
EVENT_TYPES = ["crow", "boilover", "rush", "rain", "surge"]
EVENT_INFO = {
    "crow": ("A crow is after your ingredients!", "Run over and press E to shoo it away"),
    "boilover": ("The cauldron boiled over!", "Press E at the cauldron to scrub it clean"),
    "rush": ("Rush hour!", "A crowd of customers is arriving"),
    "rain": ("It's raining!", "The garden grows twice as fast for a while"),
    "surge": ("Magic surge!", "All gold is doubled for 30 seconds"),
}

CUSTOMER_TYPES = {
    "Village Wizard": {"patience": 80, "mult": 1.0, "stage": 1, "weight": 3, "difficulty": "Easy",
                       "wants": ["Healing Potion"],
                       "robe": (0.20, 0.30, 0.75), "trim": (0.95, 0.85, 0.30), "skin": (0.96, 0.80, 0.68)},
    "Adventurer": {"patience": 60, "mult": 1.1, "stage": 2, "weight": 2, "difficulty": "Medium",
                   "wants": ["Healing Potion", "Strength Potion", "Dragonfire Brew"],
                   "robe": (0.50, 0.33, 0.18), "trim": (0.30, 0.20, 0.10), "skin": (0.88, 0.70, 0.55)},
    "Fairy Visitor": {"patience": 55, "mult": 1.0, "stage": 2, "weight": 2, "difficulty": "Medium",
                      "wants": ["Invisibility Potion", "Flying Potion", "Starlight Tonic"],
                      "precise_bonus": 8,
                      "robe": (0.95, 0.55, 0.80), "trim": (0.55, 0.95, 0.85), "skin": (1.00, 0.88, 0.85)},
    "Impatient Witch": {"patience": 38, "mult": 1.6, "stage": 3, "weight": 1, "difficulty": "Hard",
                        "wants": ["Flying Potion", "Starlight Tonic", "Dragonfire Brew",
                                  "Invisibility Potion", "Strength Potion"],
                        "robe": (0.15, 0.40, 0.20), "trim": (0.10, 0.10, 0.10), "skin": (0.80, 0.92, 0.72)},
    "Royal Magician": {"patience": 200, "mult": 1.0, "stage": 5, "weight": 0, "difficulty": "Final",
                       "wants": ["Royal Aegis Elixir"], "special": True,
                       "robe": (0.35, 0.10, 0.50), "trim": (1.00, 0.80, 0.20), "skin": (0.95, 0.82, 0.70)},
}

STAGES = [
    {"name": "The Little Shop", "goal": "Complete 3 orders", "type": "orders", "target": 3,
     "day_len": 210, "spawn": (14, 18)},
    {"name": "Busy Brewing", "goal": "Earn 100 gold today", "type": "gold", "target": 100,
     "day_len": 300, "spawn": (10, 14)},
    {"name": "The Enchanted Cauldron", "goal": "Brew 5 advanced potions", "type": "advanced", "target": 5,
     "day_len": 280, "spawn": (10, 13)},
    {"name": "The Popular Shop", "goal": "Reach 50 reputation", "type": "reputation", "target": 50,
     "day_len": 330, "spawn": (6, 9)},
    {"name": "The Royal Order", "goal": "Complete the royal commission", "type": "royal", "target": 1,
     "day_len": 300, "spawn": (12, 16)},
]

UPGRADES = [
    {"key": "shelf", "name": "Bigger Ingredient Shelf", "cost": 50, "desc": "Ingredient storage 10 -> 15"},
    {"key": "cauldron", "name": "Improved Cauldron", "cost": 100, "desc": "Brewing time 4.0s -> 2.4s"},
    {"key": "garden", "name": "Magical Garden", "cost": 150, "desc": "Ingredients regrow 2x faster, +2 stock"},
    {"key": "space", "name": "Extra Customer Space", "cost": 200, "desc": "Customer queue 3 -> 5"},
    {"key": "decor", "name": "Enchanted Shop Decoration", "cost": 250, "desc": "Prestige: +1 rep/sale, +20% patience"},
    {"key": "cauldron2", "name": "Second Cauldron", "cost": 180, "desc": "Brew two potions at the same time"},
]

DEFAULT_LIQUID = (0.20, 0.55, 0.50)
MURKY_LIQUID = (0.33, 0.36, 0.18)


# =============================================================================
# SMALL UTILITIES
# =============================================================================
def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def lerp(a, b, t):
    return a + (b - a) * t


def lerp3(a, b, t):
    return (lerp(a[0], b[0], t), lerp(a[1], b[1], t), lerp(a[2], b[2], t))


def approach_angle(cur, target, max_step):
    diff = (target - cur + 180.0) % 360.0 - 180.0
    if abs(diff) <= max_step:
        return target
    return cur + (max_step if diff > 0 else -max_step)


def fmt_time(s):
    s = max(0, int(s))
    return "%d:%02d" % (s // 60, s % 60)


def push_out_box(x, z, r, b):
    x0, x1, z0, z1 = b
    cx, cz = clamp(x, x0, x1), clamp(z, z0, z1)
    dx, dz = x - cx, z - cz
    d2 = dx * dx + dz * dz
    if d2 < r * r:
        if d2 > 1e-9:
            d = math.sqrt(d2)
            return cx + dx / d * r, cz + dz / d * r
        pens = [(x - x0 + r, -1, 0), (x1 - x + r, 1, 0), (z - z0 + r, 0, -1), (z1 - z + r, 0, 1)]
        p, sx, sz = min(pens)
        return x + sx * p, z + sz * p
    return x, z


def push_out_circle(x, z, r, c):
    cx, cz, cr = c
    dx, dz = x - cx, z - cz
    d = math.hypot(dx, dz)
    if d < r + cr:
        if d < 1e-6:
            dx, dz, d = 0.0, 1.0, 1.0
        return cx + dx / d * (r + cr), cz + dz / d * (r + cr)
    return x, z


def short_name(potion):
    return potion.replace(" Potion", "").replace(" Elixir", "")


# =============================================================================
# ENTITIES
# =============================================================================
class Source:
    """A garden patch or shelf crate that produces one ingredient."""

    def __init__(self, name):
        d = ING[name]
        self.name = name
        self.x, self.z = d["x"], d["z"]
        self.loc = d["loc"]
        self.stock = 2
        self.regrow = 0.0


class Witch:
    """Liri - the player character. Animated by hierarchical transforms."""

    def __init__(self):
        self.reset()

    def reset(self, x=0.0, z=1.5):
        self.x, self.z = x, z
        self.yaw = 180.0
        self.target_yaw = 180.0
        self.walking = False
        self.walk_phase = 0.0
        self.action = None
        self.action_t = 0.0
        self.action_dur = 0.0
        self.held_color = None
        self.t = 0.0
        self.blink_t = 2.0

    def play(self, name, dur, held=None):
        self.action, self.action_t, self.action_dur, self.held_color = name, 0.0, dur, held

    def face(self, x, z):
        self.target_yaw = math.degrees(math.atan2(x - self.x, z - self.z))

    def update(self, dt):
        self.t += dt
        if self.action:
            self.action_t += dt
            if self.action_t >= self.action_dur:
                self.action, self.held_color = None, None
        if self.walking:
            self.walk_phase += dt * 9.0
        self.yaw = approach_angle(self.yaw, self.target_yaw, 600.0 * dt)
        self.blink_t -= dt
        if self.blink_t < -0.12:
            self.blink_t = random.uniform(2.0, 4.5)

    def pose(self, stirring=False):
        t = self.t
        p = {"y": 0.0, "lean": 0.0, "leg_l": 0.0, "leg_r": 0.0,
             "arm_l": -4.0 + 3 * math.sin(t * 1.7), "arm_r": -4.0 - 3 * math.sin(t * 1.7),
             "arm_l_z": -9.0, "arm_r_z": 9.0, "head_pitch": 0.0, "head_bob": 0.015 * math.sin(t * 2.0),
             "shake": 0.0, "expr": "normal", "blink": self.blink_t < 0.0}
        p["y"] = 0.012 * math.sin(t * 2.0)                    # idle breathing

        if self.walking:
            s = math.sin(self.walk_phase)
            p["leg_l"], p["leg_r"] = 32 * s, -32 * s
            p["arm_r"], p["arm_l"] = -5 + 26 * s, -5 - 26 * s
            p["y"] = abs(math.cos(self.walk_phase)) * 0.05
            p["lean"] = 4

        if self.action:
            u = clamp(self.action_t / max(self.action_dur, 1e-3), 0, 1)
            k = math.sin(math.pi * u)
            a = self.action
            if a == "collect":
                p["lean"] = 18 * k
                p["arm_r"] = -75 * k - 5
                p["arm_l"] = -25 * k - 5
                p["head_pitch"] = 18 * k
            elif a == "brew":
                stirring = True
            elif a == "serve":
                p["arm_r"] = -85 * k - 5
                p["arm_l"] = -60 * k - 5
                p["lean"] = 8 * k
            elif a == "success":
                p["y"] = abs(math.sin(u * math.pi * 3)) * 0.45
                p["arm_l"] = p["arm_r"] = -165 * min(1, k * 2.5)
                p["arm_l_z"], p["arm_r_z"] = -25, 25
                p["expr"] = "happy"
            elif a == "fail":
                p["head_pitch"] = 28 * min(1, k * 2)
                p["arm_l"] = p["arm_r"] = -10
                p["arm_l_z"], p["arm_r_z"] = -4, 4
                p["shake"] = 10 * math.sin(t * 28) * (1 - u)
                p["lean"] = 6
                p["expr"] = "sad"

        if stirring and self.action not in ("success", "fail", "serve", "collect"):
            p["arm_r"] = -58 + 14 * math.sin(t * 7)
            p["arm_r_z"] = 10 + 22 * math.cos(t * 7)
            p["arm_l"] = -30
            p["lean"] = 10
            p["head_pitch"] = 18
        return p


class Customer:
    _ids = 0

    def __init__(self, ctype, request, patience, order=None, name=None, line=None):
        Customer._ids += 1
        self.id = Customer._ids
        self.type = ctype
        self.request = request
        self.order = order            # None / "strong" (needs a Perfect brew) / "double" (wants two)
        self.qty = 2 if order == "double" else 1
        self.name = name              # named regular, e.g. "Sir Bram"
        self.line = line              # what the regular says when reaching the counter
        self.said = False
        self.say_t = 0.0
        self.patience = patience
        self.max_patience = patience
        self.x, self.z = SPAWN_POINT
        self.path = [DOOR_IN]
        self.state = "queue"          # queue -> leaving
        self.mood = None              # "happy" / "angry"
        self.yaw = 0.0
        self.t = random.uniform(0, 10)
        self.walking = True
        self.arrived = False
        self.react_t = 0.0
        self.slot = 0

    @property
    def frac(self):
        return clamp(self.patience / self.max_patience, 0, 1)

    @property
    def label(self):
        return self.name or self.type


class Cauldron:
    def __init__(self, pos, index=0):
        self.pos = pos
        self.index = index
        self.contents = []
        self.brewing = False
        self.brew_t = 0.0
        self.brew_dur = BASE_BREW_TIME
        self.stir_tried = False
        self.bonus = False
        self.recipe_name = None       # what the current brew will become (None = unknown mix)
        self.liquid = DEFAULT_LIQUID
        self.liquid_target = DEFAULT_LIQUID
        self.reset_timer = 0.0
        self.bubbles = []             # [x, y, z, r, speed]
        self.flash = 0.0
        self.dirty = False            # boiled over - must be scrubbed before brewing
        self.clean = 0                # scrub progress (0..4)

    @property
    def progress(self):
        return clamp(self.brew_t / self.brew_dur, 0, 1) if self.brewing else 0.0

    def reset(self):
        self.contents, self.brewing, self.liquid_target = [], False, DEFAULT_LIQUID
        self.dirty, self.clean, self.recipe_name = False, 0, None


class Crow:
    """Random event: a crow flies in, lands on an ingredient and steals it unless shooed."""
    FLY_IN, STEAL_AFTER, FLY_OUT = 2.5, 9.0, 2.0

    def __init__(self, src):
        self.src = src
        if src.loc == "garden":
            self.tx, self.ty, self.tz = src.x + 0.2, 0.72, src.z
        else:
            self.tx, self.ty, self.tz = src.x, 0.9, -7.15
        self.sx, self.sy, self.sz = -15.0, 6.5, self.tz
        self.x, self.y, self.z = self.sx, self.sy, self.sz
        self.state = "in"
        self.t = 0.0
        self.yaw = math.degrees(math.atan2(self.tx - self.sx, self.tz - self.sz))
        self.done = False

    @property
    def threat(self):
        return self.state in ("in", "perched")

    def leave(self):
        self.state, self.t = "out", 0.0
        self.ox, self.oy, self.oz = self.x, self.y, self.z
        self.yaw = math.degrees(math.atan2(self.sx - self.x, self.sz - self.z))

    def update(self, dt):
        self.t += dt
        if self.state == "in":
            u = clamp(self.t / self.FLY_IN, 0, 1)
            self.x = lerp(self.sx, self.tx, u)
            self.z = lerp(self.sz, self.tz, u)
            self.y = lerp(self.sy, self.ty, u) + 2.5 * math.sin(math.pi * u)
            if u >= 1:
                self.state, self.t = "perched", 0.0
        elif self.state == "perched":
            self.y = self.ty
            if self.t >= self.STEAL_AFTER:
                return "steal"
        elif self.state == "out":
            u = clamp(self.t / self.FLY_OUT, 0, 1)
            self.x = lerp(self.ox, self.sx, u)
            self.z = lerp(self.oz, self.sz, u)
            self.y = lerp(self.oy, 8.0, u) + 1.5 * math.sin(math.pi * u)
            if u >= 1:
                self.done = True
        return None


# =============================================================================
# GAME LOGIC
# =============================================================================
class Game:
    def __init__(self):
        self.W, self.H = WIN_W, WIN_H
        self.state = "title"            # title / play / summary / victory
        self.paused = False
        self.show_recipes = False
        self.show_inventory = False
        self.show_upgrades = False
        self.show_help = False
        self.day_night = True
        self.mouse_sens = 0.30
        self.show_fps = False
        self.outlines = True
        self.guide_on = True
        self.music_on = True
        self.sfx_on = True
        self.e_hold_t = 0.0
        self.upgrade_hinted = False
        self.mouse_pos = (0, 0)
        self.fps = 0.0
        self.time = 0.0
        self.keys = set()
        self.special = set()
        self.mouse_down = False
        self.mouse_last = (0, 0)
        self.mouse_moved = False
        self.click_rects = []
        self.toasts = []                # [text, life, color]
        self.floaters = []              # [x, y, z, text, color, life]
        self.particles = []
        self.static_dirty = True
        self.cam_yaw, self.cam_pitch, self.cam_dist = 0.0, 0.55, 11.5
        self.cam_tx, self.cam_tz = 0.0, 1.5
        self.save_exists = os.path.exists(SAVE_FILE)
        self.liri = Witch()
        self.cauldrons = [Cauldron(CAULDRON_POS, 0), Cauldron(CAULDRON2_POS, 1)]
        self.new_game_state()

    # ------------------------------------------------------------------ setup
    def new_game_state(self):
        self.stage = 1
        self.day = 1
        self.gold = 20
        self.rep = 0
        self.upgrades = {u["key"]: False for u in UPGRADES}
        self.inventory = {n: 0 for n in ING_NAMES}
        self.inventory["Red Flower"] = 2
        self.inventory["Healing Herb"] = 2
        self.items = []                 # finished potions: {"name", "q" (0-100), "perfect", "age"}
        self.discovered = set()         # secret recipes found
        self.regular_visits = {n: 0 for n in REGULARS}
        self.stars = {}
        self.sources = [Source(n) for n in ING_NAMES]
        self.customers = []
        self.summary = None
        self.snapshot = None
        self.reset_day_vars()

    def reset_day_vars(self):
        self.upgrade_hinted = False
        self.day_time = 0.0
        self.spawn_timer = 6.0
        self.royal_spawned = False
        self.combo = 0
        self.combo_t = 0.0
        self.combo_pop = 0.0
        self.rain_t = 0.0
        self.surge_t = 0.0
        self.crow = None
        self.event_banner = None        # [title, subtitle, time_left]
        self.events_pending = []
        self.stats = {"orders": 0, "lost": 0, "gold_earned": 0, "consumed": 0, "brewed": 0,
                      "failed": 0, "advanced": 0, "perfect": 0, "royal": 0, "secrets": 0,
                      "best_combo": 0, "events": 0}

    def schedule_events(self):
        self.events_pending = []
        if self.stage < 2:
            return
        n = 1 if self.stage == 2 else 2
        types = random.sample(EVENT_TYPES, n)
        day_len = self.stage_data["day_len"]
        times = []
        for _ in range(n):
            for _try in range(20):
                t = random.uniform(30, day_len - 45)
                if all(abs(t - o) > 45 for o in times):
                    times.append(t)
                    break
        times.sort()
        self.events_pending = [[t, e] for t, e in zip(times, types)]

    def start_new_game(self):
        self.new_game_state()
        self.start_day(advance_day=False)
        self.show_help = True
        self.state = "play"

    def continue_game(self):
        if not self.load():
            self.toast("No save found - starting a new game", (1, 0.6, 0.6))
            self.start_new_game()
            return
        self.start_day(advance_day=False)
        self.state = "play"

    def start_day(self, advance_day=True):
        if advance_day:
            self.day += 1
        self.reset_day_vars()
        self.rep_start = self.rep
        self.customers = []
        for c in self.cauldrons:
            c.reset()
        self.liri.reset()
        self.cam_tx, self.cam_tz = self.liri.x, self.liri.z
        self.paused = False
        self.show_upgrades = self.show_recipes = self.show_inventory = False
        for s in self.sources:
            if self.unlocked_ing(s.name):
                s.stock = max(s.stock, 2)
        self.schedule_events()
        self.snapshot = self.make_snapshot()
        self.save()
        st = self.stage_data
        self.toast("Day %d - Stage %d: %s" % (self.day, self.stage, st["name"]), (1, 0.9, 0.5), 5)
        self.toast("Goal: " + self.goal_text(), (0.8, 1, 0.8), 5)
        unlocked_now = [r["name"] for r in RECIPES if r["stage"] == self.stage and not r.get("secret")]
        if unlocked_now and self.stage > 1:
            self.toast("New recipes: " + ", ".join(unlocked_now), (0.7, 0.9, 1), 6)
        if self.stage == 2 and self.stats["orders"] == 0:
            self.toast("Serve customers quickly in a row to build a COMBO and multiply your gold!", (1, 0.8, 0.4), 7)
        self.static_dirty = True

    def make_snapshot(self):
        return {"stage": self.stage, "day": self.day, "gold": self.gold, "rep": self.rep,
                "upgrades": dict(self.upgrades), "inventory": dict(self.inventory),
                "items": [dict(it) for it in self.items], "stars": dict(self.stars),
                "discovered": sorted(self.discovered), "regulars": dict(self.regular_visits),
                "stock": {s.name: s.stock for s in self.sources}}

    def restore_snapshot(self, snap):
        self.stage = snap["stage"]
        self.day = snap["day"]
        self.gold = snap["gold"]
        self.rep = snap["rep"]
        self.upgrades.update(snap["upgrades"])
        self.inventory.update(snap["inventory"])
        if "items" in snap:
            self.items = [dict(it) for it in snap["items"] if it.get("name") in RECIPE]
        else:                                           # saves from older versions
            self.items = []
            for name, k in snap.get("potions", {}).items():
                if name in RECIPE:
                    self.items += [{"name": name, "q": 100.0, "perfect": False, "age": 0.0} for _ in range(k)]
        self.discovered = set(n for n in snap.get("discovered", []) if n in RECIPE)
        self.regular_visits.update(snap.get("regulars", {}))
        self.stars = {int(k): v for k, v in snap.get("stars", {}).items()}
        for s in self.sources:
            s.stock = snap.get("stock", {}).get(s.name, 2)

    def restart_day(self):
        if self.snapshot:
            self.restore_snapshot(self.snapshot)
        self.start_day(advance_day=False)
        self.toast("Day restarted", (1, 1, 0.6))

    def save(self):
        try:
            with open(SAVE_FILE, "w") as f:
                json.dump(self.snapshot or self.make_snapshot(), f, indent=1)
            self.save_exists = True
        except OSError:
            pass

    def load(self):
        try:
            with open(SAVE_FILE) as f:
                snap = json.load(f)
            self.new_game_state()
            self.restore_snapshot(snap)
            return True
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            return False

    # ------------------------------------------------------------ properties
    @property
    def stage_data(self):
        return STAGES[self.stage - 1]

    @property
    def capacity(self):
        return BIG_SHELF_CAPACITY if self.upgrades["shelf"] else BASE_CAPACITY

    @property
    def brew_time(self):
        return FAST_BREW_TIME if self.upgrades["cauldron"] else BASE_BREW_TIME

    @property
    def max_queue(self):
        return 5 if self.upgrades["space"] else 3

    @property
    def max_stock(self):
        return BASE_MAX_STOCK + (2 if self.upgrades["garden"] else 0)

    @property
    def regrow_time(self):
        return BASE_REGROW * (0.5 if self.upgrades["garden"] else 1.0)

    @property
    def potions(self):
        counts = {r["name"]: 0 for r in RECIPES}
        for it in self.items:
            counts[it["name"]] += 1
        return counts

    def active_cauldrons(self):
        return self.cauldrons if self.upgrades.get("cauldron2") else self.cauldrons[:1]

    @property
    def cauldron(self):
        """The cauldron Liri is standing at (or the main one)."""
        return self.near_cauldron() or self.cauldrons[0]

    def obstacle_circles(self):
        return [(c.pos[0], c.pos[1], 1.1) for c in self.active_cauldrons()]

    def unlocked_ing(self, name):
        return ING[name]["stage"] <= self.stage

    def unlocked_recipe(self, name):
        r = RECIPE[name]
        if r.get("secret"):
            return name in self.discovered and r["stage"] <= self.stage
        return r["stage"] <= self.stage

    def brewable(self, r):
        return r["stage"] <= self.stage

    def total_potions(self):
        return len(self.items)

    def queue(self):
        return [c for c in self.customers if c.state == "queue"]

    def combo_mult(self, combo=None):
        k = self.combo if combo is None else combo
        return 3.0 if k >= 5 else 2.0 if k >= 3 else 1.5 if k >= 2 else 1.0

    def goal_progress(self):
        st = self.stage_data
        t = st["type"]
        if t == "orders":
            v = self.stats["orders"]
        elif t == "gold":
            v = self.stats["gold_earned"]
        elif t == "advanced":
            v = self.stats["advanced"]
        elif t == "reputation":
            return self.rep, max(st["target"], getattr(self, "rep_start", 0) + 20)
        else:
            v = self.stats["royal"]
        return v, st["target"]

    def goal_text(self):
        st = self.stage_data
        if st["type"] == "reputation":
            return "Reach %d reputation" % self.goal_progress()[1]
        return st["goal"]

    # ---------------------------------------------------------- messaging
    def toast(self, text, color=(1, 1, 1), life=3.0):
        self.toasts.append([text, life, color])
        if len(self.toasts) > 6:
            self.toasts.pop(0)

    def floater(self, x, y, z, text, color):
        self.floaters.append([x, y, z, text, color, 1.6])

    def emit(self, x, y, z, color, n, speed=1.5, life=1.0, up=1.0, gravity=-1.5, size=6, spread=0.1):
        for _ in range(n):
            a = random.uniform(0, math.tau)
            e = random.uniform(-0.3, 1.0)
            sp = speed * random.uniform(0.4, 1.0)
            vx = math.cos(a) * math.cos(e) * sp
            vz = math.sin(a) * math.cos(e) * sp
            vy = math.sin(e) * sp + up
            l = life * random.uniform(0.6, 1.2)
            col = (clamp(color[0] + random.uniform(-0.1, 0.1), 0, 1),
                   clamp(color[1] + random.uniform(-0.1, 0.1), 0, 1),
                   clamp(color[2] + random.uniform(-0.1, 0.1), 0, 1))
            self.particles.append([x + random.uniform(-spread, spread), y, z + random.uniform(-spread, spread),
                                   vx, vy, vz, l, l, col, size, gravity])
        if len(self.particles) > 1200:
            del self.particles[:len(self.particles) - 1200]

    # ------------------------------------------------------------- potions
    def matching_items(self, c):
        """Potions that can fill customer c's order, best choice first (or None if not enough)."""
        cands = [it for it in self.items if it["name"] == c.request]
        if c.order == "strong":
            cands = [it for it in cands if it["perfect"]]
            cands.sort(key=lambda it: -it["q"])
        else:
            cands.sort(key=lambda it: (it["perfect"], it["q"]))    # use plain + oldest first
        return cands[:c.qty] if len(cands) >= c.qty else None

    def have_for(self, c):
        cands = [it for it in self.items if it["name"] == c.request]
        if c.order == "strong":
            cands = [it for it in cands if it["perfect"]]
        return len(cands)

    def can_serve(self, c):
        if self.matching_items(c) is None:
            return False
        return not (CUSTOMER_TYPES[c.type].get("special") and self.rep < ROYAL_REP_REQUIRED)

    # --------------------------------------------------------- interaction
    def nearest_interactable(self):
        lx, lz = self.liri.x, self.liri.z
        if self.crow and self.crow.threat and math.hypot(lx - self.crow.x, lz - self.crow.z) < 2.4:
            return ("crow", self.crow)
        best, best_d = None, 1e9
        for s in self.sources:
            r = 1.95 if s.loc == "garden" else 1.25
            d = math.hypot(lx - s.x, lz - s.z)
            if d < r and d < best_d:
                best, best_d = ("source", s), d
        for c in self.active_cauldrons():
            d = math.hypot(lx - c.pos[0], lz - c.pos[1])
            if d < 2.5 and d < best_d:
                best, best_d = ("cauldron", c), d
        d = math.hypot(lx - DESK_POS[0], lz - (DESK_POS[1] + 1.4))
        if d < 1.7 and d < best_d:
            best, best_d = ("desk", None), d
        if lz > 2.0 and -3.2 < lx < 5.2:
            best = ("counter", None)
        return best

    def near_cauldron(self):
        n = self.nearest_interactable()
        return n[1] if n is not None and n[0] == "cauldron" else None

    def guide(self):
        """Next step for the player: (x, y, z, text) or None."""
        if self.crow and self.crow.threat:
            return (self.crow.x, self.crow.y + 0.4, self.crow.z, "Shoo the crow! Run to it and press E")
        q = self.queue()
        for c in q:
            if self.can_serve(c):
                return (1.0, 2.0, 3.2, "Serve %s at the counter (press E there)" % c.label)
        cs = self.active_cauldrons()
        near = self.near_cauldron()
        strong_needed = any(c.order == "strong" and self.have_for(c) < c.qty for c in q)
        if near and near.brewing and not near.stir_tried and near.progress < BONUS_WINDOW[1]:
            extra = " - an order needs a PERFECT brew!" if strong_needed else ""
            return (near.pos[0], 2.6, near.pos[1], "Tap SPACE when the white marker is in the GOLD zone" + extra)
        known = [r for r in RECIPES if self.unlocked_recipe(r["name"])]
        for c in cs:
            if c.contents and not c.brewing and not c.dirty:
                if any(r["seq"] == c.contents for r in known):
                    return (c.pos[0], 2.6, c.pos[1], "Press SPACE at the cauldron to stir and brew")
                if not any(r["seq"][:len(c.contents)] == c.contents for r in known):
                    return (c.pos[0], 2.6, c.pos[1], "Unknown mix! SPACE to experiment, or X to empty it")
        # first order that isn't covered by finished or brewing potions
        brewing = {}
        for c in cs:
            if c.brewing and c.recipe_name:
                brewing[c.recipe_name] = brewing.get(c.recipe_name, 0) + 1
        want, cust = None, None
        for c in q:
            if self.have_for(c) + brewing.get(c.request, 0) < c.qty:
                want, cust = c.request, c
                break
        if want is None and not q and self.stage == 1 and not self.items and not brewing:
            want = "Healing Potion"
        if want is None:
            busy = [c for c in cs if c.brewing]
            if busy:
                return (busy[0].pos[0], 2.6, busy[0].pos[1], "Brewing... get ingredients ready for the next order")
            return None
        r = RECIPE[want]
        # choose a cauldron: one already holding a matching start, else an idle empty one
        target = None
        for c in cs:
            if not c.brewing and not c.dirty and c.contents and r["seq"][:len(c.contents)] == c.contents:
                target = c
                break
        if target is None:
            for c in sorted(cs, key=lambda c: math.hypot(self.liri.x - c.pos[0], self.liri.z - c.pos[1])):
                if not c.brewing and not c.contents:
                    target = c
                    break
        if target is None:
            busy = [c for c in cs if c.brewing]
            if busy:
                return (busy[0].pos[0], 2.6, busy[0].pos[1], "Cauldron busy - wait for it to finish")
            c0 = cs[0]
            return (c0.pos[0], 2.6, c0.pos[1], "Empty the cauldron (X) to start the %s" % want)
        if target.dirty:
            return (target.pos[0], 2.6, target.pos[1], "Scrub the boiled-over cauldron: press E there")
        remaining = r["seq"][len(target.contents):]
        need = {}
        for n in remaining:
            need[n] = need.get(n, 0) + 1
        for n in remaining:
            if self.inventory[n] < need[n]:
                src = [s for s in self.sources if s.name == n][0]
                where = "garden" if src.loc == "garden" else "shelf"
                extra = " (regrowing - wait, or buy a delivery at the desk)" if src.stock <= 0 else ""
                y = 1.2 if src.loc == "garden" else 1.6
                z = src.z if src.loc == "garden" else -7.45
                return (src.x, y, z, "Collect %s from the %s for the %s%s" % (n, where, want, extra))
        keys = " then ".join("%d" % (ING_NAMES.index(n) + 1) for n in remaining)
        perfect = " (needs PERFECT: tap SPACE again in the gold zone)" if cust and cust.order == "strong" else ""
        return (target.pos[0], 2.6, target.pos[1],
                "Make a %s: at the cauldron press %s, then SPACE%s" % (want, keys, perfect))

    def interact(self):
        n = self.nearest_interactable()
        if not n:
            self.toast("Nothing to interact with here", (0.8, 0.8, 0.8), 1.5)
            return
        kind, obj = n
        if kind == "crow":
            self.shoo_crow()
        elif kind == "source":
            self.collect(obj)
        elif kind == "cauldron":
            if obj.dirty:
                self.scrub(obj)
            else:
                self.show_recipes = not self.show_recipes
                self.show_upgrades = False
        elif kind == "counter":
            self.serve()
        elif kind == "desk":
            self.liri.face(DESK_POS[0], DESK_POS[1])
            self.show_upgrades = not self.show_upgrades
            self.show_recipes = False

    def collect(self, src):
        if src.loc == "garden":
            self.liri.face(src.x, src.z)
        else:
            self.liri.face(src.x, -7.4)
        if not self.unlocked_ing(src.name):
            self.toast("%s unlocks at Stage %d" % (src.name, ING[src.name]["stage"]), (0.8, 0.8, 0.8))
            return
        if self.inventory[src.name] >= self.capacity:
            self.toast("%s storage is full (%d/%d)" % (src.name, self.capacity, self.capacity), (1, 0.6, 0.4))
            return
        if src.stock <= 0:
            self.toast("%s is regrowing... come back soon" % src.name, (0.9, 0.9, 0.6))
            return
        src.stock -= 1
        self.inventory[src.name] += 1
        self.liri.play("collect", 0.55)
        sfx("pickup")
        y = 0.5 if src.loc == "garden" else 0.8
        self.emit(src.x, y, src.z if src.loc == "garden" else -7.3, ING[src.name]["color"], 14, 1.2, 0.8, 1.0, -1.0, 5)
        self.floater(self.liri.x, 2.4, self.liri.z, "+1 %s" % src.name, ING[src.name]["color"])

    def add_ingredient(self, idx):
        if idx < 0 or idx >= len(ING_NAMES):
            return
        name = ING_NAMES[idx]
        c = self.near_cauldron()
        if not c:
            self.toast("Walk to a cauldron to add ingredients", (0.9, 0.9, 0.7), 2)
            return
        if c.dirty:
            self.toast("This cauldron boiled over - press E to scrub it first!", (1, 0.7, 0.5), 2)
            return
        if c.brewing:
            self.toast("The cauldron is already brewing!", (1, 0.7, 0.5), 2)
            return
        if not self.unlocked_ing(name):
            self.toast("%s is not unlocked yet" % name, (0.8, 0.8, 0.8), 2)
            return
        if self.inventory[name] <= 0:
            self.toast("You have no %s" % name, (1, 0.6, 0.5), 2)
            return
        if len(c.contents) >= MAX_CAULDRON:
            self.toast("The cauldron is full - stir it or empty it (X)", (1, 0.7, 0.5), 2)
            return
        self.inventory[name] -= 1
        self.stats["consumed"] += 1
        c.contents.append(name)
        cols = [ING[n]["color"] for n in c.contents]
        c.liquid_target = tuple(sum(cc[i] for cc in cols) / len(cols) * 0.85 for i in range(3))
        c.reset_timer = 0.0
        self.liri.face(*c.pos)
        self.liri.play("collect", 0.45)
        sfx("splash")
        self.emit(c.pos[0], 1.5, c.pos[1], ING[name]["color"], 18, 1.4, 0.8, 1.2, -1.2, 6)

    def load_recipe(self, idx):
        known = [r for r in RECIPES if self.unlocked_recipe(r["name"])]
        if idx < 0 or idx >= len(known):
            return
        r = known[idx]
        c = self.near_cauldron()
        if not c:
            self.toast("Stand at a cauldron to prepare %s" % r["name"], (0.9, 0.9, 0.7), 2)
            return
        if c.dirty:
            self.toast("Scrub the cauldron first (press E)", (1, 0.7, 0.5), 2)
            return
        if c.brewing:
            self.toast("The cauldron is busy brewing", (1, 0.7, 0.5), 2)
            return
        if c.contents:
            self.toast("Empty the cauldron first (X)", (1, 0.7, 0.5), 2)
            return
        need = {}
        for n in r["seq"]:
            need[n] = need.get(n, 0) + 1
        missing = [n for n, k in need.items() if self.inventory[n] < k]
        if missing:
            self.toast("Missing ingredients: " + ", ".join(missing), (1, 0.55, 0.45), 3)
            return
        for n in r["seq"]:
            self.add_ingredient(ING_NAMES.index(n))
        self.show_recipes = False
        self.toast("Ingredients added - press SPACE to stir!", (0.8, 1, 0.8), 2.5)

    def empty_cauldron(self):
        c = self.near_cauldron()
        if not c:
            return
        if c.brewing:
            self.toast("You can't empty a brewing cauldron!", (1, 0.7, 0.5), 2)
            return
        if not c.contents:
            return
        c.contents = []
        c.liquid_target = DEFAULT_LIQUID
        self.emit(c.pos[0], 1.5, c.pos[1], (0.5, 0.5, 0.5), 20, 1.0, 1.0, 1.5, -0.3, 7)
        self.toast("Cauldron emptied (ingredients wasted)", (0.85, 0.85, 0.85), 2)

    def scrub(self, c):
        self.liri.face(*c.pos)
        self.liri.play("brew", 0.5)
        c.clean += 1
        sfx("scrub")
        self.emit(c.pos[0], 1.3, c.pos[1], (0.8, 1.0, 0.9), 18, 1.6, 0.7, 1.5, -1.0, 6)
        if c.clean >= 4:
            c.dirty, c.clean = False, 0
            c.liquid_target = DEFAULT_LIQUID
            self.emit(c.pos[0], 1.6, c.pos[1], (1, 1, 1), 40, 2.4, 1.0, 2.0, -1.0, 6)
            self.toast("Sparkling clean! Back to brewing.", (0.7, 1, 0.9), 2.5)
            sfx("sparkle")
        else:
            self.toast("Scrubbing... %d/4" % c.clean, (0.8, 1, 0.9), 1.2)

    def stir(self):
        c = self.near_cauldron()
        if not c:
            return
        self.liri.face(*c.pos)
        if c.dirty:
            self.toast("This cauldron boiled over - press E to scrub it clean!", (1, 0.7, 0.5), 2)
            return
        if not c.brewing:
            if not c.contents:
                self.toast("Add ingredients first (keys 1-8)", (0.9, 0.9, 0.7), 2)
                return
            brewing_n = sum(1 for k in self.cauldrons if k.brewing)
            if self.total_potions() + brewing_n >= POTION_CAP:
                self.toast("Bottle rack is full - serve some potions first!", (1, 0.6, 0.4), 2.5)
                return
            c.brewing = True
            c.brew_t = 0.0
            c.brew_dur = self.brew_time
            c.stir_tried = False
            c.bonus = False
            c.recipe_name = None
            for r in RECIPES:
                if r["seq"] == c.contents and self.brewable(r):
                    c.recipe_name = r["name"]
                    break
            self.liri.play("brew", c.brew_dur)
            sfx("bubble")
            self.toast("Brewing... press SPACE in the GOLD zone for a Perfect brew", (0.95, 0.85, 0.4), 2.5)
            return
        if c.stir_tried:
            return
        c.stir_tried = True
        u = c.progress
        self.liri.play("brew", max(0.6, c.brew_dur - c.brew_t))
        if BONUS_WINDOW[0] <= u <= BONUS_WINDOW[1]:
            c.bonus = True
            self.emit(c.pos[0], 1.6, c.pos[1], (1, 0.9, 0.3), 40, 2.2, 1.0, 1.5, -1.5, 7)
            self.toast("Perfect stir!", (1, 0.9, 0.3), 1.5)
            sfx("sparkle")
        else:
            self.toast("Stirred too %s - no bonus" % ("early" if u < BONUS_WINDOW[0] else "late"), (0.9, 0.8, 0.7), 1.5)

    def finish_brew(self, c):
        seq = c.contents
        c.brewing = False
        c.contents = []
        c.reset_timer = 3.0
        recipe = RECIPE.get(c.recipe_name) if c.recipe_name else None
        c.recipe_name = None
        cx, cz = c.pos
        if recipe:
            new_secret = recipe.get("secret") and recipe["name"] not in self.discovered
            self.items.append({"name": recipe["name"], "q": 100.0, "perfect": bool(c.bonus), "age": 0.0})
            self.stats["brewed"] += 1
            if recipe["tier"] >= 2:
                self.stats["advanced"] += 1
            c.liquid_target = recipe["color"]
            c.flash = 1.5
            self.emit(cx, 1.6, cz, recipe["color"], 70, 2.6, 1.3, 2.0, -1.2, 7)
            self.emit(cx, 1.6, cz, (1, 1, 1), 20, 1.5, 0.9, 2.5, -0.5, 4)
            self.liri.play("success", 1.3)
            if new_secret:
                self.discovered.add(recipe["name"])
                self.stats["secrets"] += 1
                self.gold += 30
                self.rep += 3
                self.emit(cx, 2.0, cz, (1, 0.9, 0.4), 120, 3.5, 1.8, 3.0, -1.5, 8)
                self.event_banner = ["SECRET RECIPE DISCOVERED!", "%s  =  %s   (+30 gold, +3 rep)"
                                     % (recipe["name"], " -> ".join(recipe["seq"])), 4.5]
                self.toast("Collectors will now ask for the %s - it sells for %d gold!"
                           % (recipe["name"], recipe["price"]), (1, 0.9, 0.5), 6)
                sfx("fanfare")
            elif c.bonus:
                self.stats["perfect"] += 1
                self.rep += 1
                self.toast("PERFECT %s! (+1 reputation)" % recipe["name"], (1, 0.9, 0.3), 3)
                self.floater(cx, 2.6, cz, "Perfect! +1 rep", (1, 0.9, 0.3))
                sfx("success")
            else:
                self.toast("Brewed a %s!" % recipe["name"], recipe["color"], 2.5)
                sfx("success")
            if c.bonus and new_secret:
                self.stats["perfect"] += 1
        else:
            self.stats["failed"] += 1
            c.liquid_target = MURKY_LIQUID
            self.emit(cx, 1.6, cz, (0.25, 0.25, 0.22), 60, 1.2, 2.0, 1.4, 0.2, 9)
            self.emit(cx, 1.6, cz, (0.45, 0.6, 0.2), 25, 2.0, 0.8, 1.5, -1.0, 6)
            self.liri.play("fail", 1.3)
            sfx("fail")
            self.toast("Failed experiment... the ingredients are wasted.", (1, 0.5, 0.4), 3)
            for r in RECIPES:
                if self.unlocked_recipe(r["name"]) and sorted(r["seq"]) == sorted(seq):
                    self.toast("Right ingredients, wrong order! %s = %s" % (r["name"], " -> ".join(r["seq"])),
                               (1, 0.85, 0.5), 6)
                    break
            else:
                self.toast("Tip: check the recipe book (R) - it also lists rumours of secret recipes",
                           (1, 0.85, 0.5), 5)
            self.floater(cx, 2.6, cz, "Fizzle!", (0.6, 0.8, 0.3))

    def serve(self):
        q = self.queue()
        self.liri.face(self.liri.x, 6.0)
        if not q:
            self.toast("No customers waiting", (0.8, 0.8, 0.8), 1.5)
            return
        for c in q:
            if not c.arrived:
                continue
            if self.matching_items(c) is not None:
                if CUSTOMER_TYPES[c.type].get("special") and self.rep < ROYAL_REP_REQUIRED:
                    self.toast("The Royal Magician requires %d reputation (you have %d)"
                               % (ROYAL_REP_REQUIRED, self.rep), (1, 0.6, 0.4), 3)
                    continue
                self.complete_order(c)
                return
        f = q[0]
        need = {"strong": "a PERFECT %s" % f.request, "double": "TWO %ss" % f.request}.get(f.order, "a %s" % f.request)
        self.toast("No matching potion. %s wants %s (you have %d)" % (f.label, need, self.have_for(f)),
                   (1, 0.7, 0.5), 2.5)
        sfx("deny")

    def complete_order(self, c):
        ct = CUSTOMER_TYPES[c.type]
        r = RECIPE[c.request]
        used = self.matching_items(c)
        for it in used:
            self.items.remove(it)
        unit = r["price"] * ct["mult"]
        base = sum(unit * (0.5 + 0.5 * it["q"] / 100.0) for it in used)
        tip = 0
        rep_gain = 2
        fast = c.frac > 0.5
        if fast:
            tip += 3 + ct.get("precise_bonus", 0)
            rep_gain += 1
        if c.order == "strong":
            base *= 1.5
            rep_gain += 1
        elif c.order == "double":
            tip += 5
        if self.upgrades["decor"]:
            rep_gain += 1
        if c.name:
            rep_gain += 1
        # combo: sales in quick succession multiply the gold
        self.combo = self.combo + 1 if self.combo_t > 0 else 1
        self.combo_t = COMBO_TIME
        self.combo_pop = 1.0
        self.stats["best_combo"] = max(self.stats["best_combo"], self.combo)
        mult = self.combo_mult()
        if self.surge_t > 0:
            mult *= 2
        earned = int(round((base + tip) * mult))
        self.gold += earned
        self.rep += rep_gain
        self.stats["orders"] += 1
        self.stats["gold_earned"] += earned
        if ct.get("special"):
            self.stats["royal"] = 1
        c.state, c.mood, c.react_t = "leaving", "happy", 0.0
        c.path = [DOOR_IN, OUTSIDE_POINT]
        self.liri.play("serve", 0.7, r["color"])
        sfx("coin")
        self.emit(c.x, 2.0, c.z, (1, 0.85, 0.2), 30 + 10 * min(5, self.combo), 2.0, 1.0, 2.0, -2.0, 6)
        tags = []
        if tip and fast:
            tags.append("tip")
        if mult > 1:
            tags.append("x%g" % mult)
        self.floater(c.x, 2.8, c.z, "+%d gold%s" % (earned, (" (" + ", ".join(tags) + ")") if tags else ""),
                     (1, 0.9, 0.3))
        self.floater(c.x, 2.4, c.z, "+%d rep" % rep_gain, (0.6, 1, 0.6))
        if self.combo >= 2:
            self.floater(self.liri.x, 3.0, self.liri.z, "COMBO x%g!" % self.combo_mult(), (1, 0.6, 1.0))
            sfx("combo", self.combo)
        if c.name:
            self.regular_visits[c.name] = self.regular_visits.get(c.name, 0) + 1
            self.toast("%s: \"%s\"" % (c.name, REGULARS[c.name]["thanks"]), (0.85, 0.95, 1), 3)
        self.toast("Served %s to %s: +%d gold" % (c.request if c.qty == 1 else "2x " + c.request, c.label, earned),
                   (1, 0.9, 0.4), 2.5)

    def buy_upgrade(self, idx):
        if idx == len(UPGRADES):
            self.buy_delivery()
            return
        if idx < 0 or idx > len(UPGRADES):
            return
        u = UPGRADES[idx]
        if self.upgrades[u["key"]]:
            self.toast("%s already owned" % u["name"], (0.8, 0.8, 0.8), 2)
            return
        if self.gold < u["cost"]:
            self.toast("Not enough gold for %s (%d needed)" % (u["name"], u["cost"]), (1, 0.6, 0.4), 2)
            sfx("deny")
            return
        self.gold -= u["cost"]
        self.upgrades[u["key"]] = True
        self.static_dirty = True
        self.emit(self.liri.x, 1.5, self.liri.z, (0.9, 0.6, 1.0), 50, 2.5, 1.2, 2.0, -1.0, 7)
        self.liri.play("success", 1.2)
        sfx("fanfare")
        self.toast("Upgrade purchased: %s!" % u["name"], (0.85, 0.7, 1), 3)
        if u["key"] == "cauldron2":
            self.cauldrons[1].reset()
            self.toast("Your new cauldron is by the garden - brew two potions at once!", (0.85, 0.9, 1), 5)

    def buy_delivery(self):
        if self.gold < DELIVERY_COST:
            self.toast("Not enough gold for a delivery (%d)" % DELIVERY_COST, (1, 0.6, 0.4), 2)
            return
        added = 0
        for n in ING_NAMES:
            if self.unlocked_ing(n):
                k = min(2, self.capacity - self.inventory[n])
                self.inventory[n] += k
                added += k
        if added == 0:
            self.toast("Your shelves are already full", (0.8, 0.8, 0.8), 2)
            return
        self.gold -= DELIVERY_COST
        sfx("coin")
        self.toast("Ingredient delivery arrived (+%d items)" % added, (0.7, 1, 0.8), 2.5)

    # ----------------------------------------------------------- customers
    def spawn_customer(self, royal=False):
        order, name, line = None, None, None
        if royal:
            ctype = "Royal Magician"
            req = "Royal Aegis Elixir"
        else:
            options = []
            for nm, ct in CUSTOMER_TYPES.items():
                if ct.get("special") or ct["stage"] > self.stage:
                    continue
                reqs = [w for w in ct["wants"] if self.unlocked_recipe(w)]
                if reqs:
                    w = ct["weight"] + (1 if nm == "Impatient Witch" and self.stage >= 4 else 0)
                    options.append((nm, reqs, w))
            if not options:
                return
            total = sum(o[2] for o in options)
            pick = random.uniform(0, total)
            for nm, reqs, w in options:
                pick -= w
                if pick <= 0:
                    break
            ctype = nm
            if ctype == "Impatient Witch":
                top = max(RECIPE[r]["tier"] for r in reqs)
                rare = [r for r in reqs if RECIPE[r]["tier"] >= top - 1]
                req = random.choice(rare)
            else:
                req = random.choice(reqs)
            secrets = [r["name"] for r in SECRET_RECIPES if self.unlocked_recipe(r["name"])]
            if secrets and random.random() < 0.3:
                req = random.choice(secrets)               # a collector who heard about your secret brew
            # named regulars continue their stories
            in_shop = set(c.name for c in self.customers if c.name)
            for rn, rd in REGULARS.items():
                if rd["type"] == ctype and rn not in in_shop and self.regular_visits.get(rn, 0) < len(rd["lines"]) \
                        and random.random() < 0.45:
                    name, line = rn, rd["lines"][self.regular_visits.get(rn, 0)]
                    break
            if self.stage >= 2:
                roll = random.random()
                if roll < 0.18:
                    order = "strong"
                elif roll < 0.33:
                    order = "double"
        pat = CUSTOMER_TYPES[ctype]["patience"] * (1.2 if self.upgrades["decor"] else 1.0)
        if order == "strong":
            pat *= 1.15
        elif order == "double":
            pat *= 1.4
        c = Customer(ctype, req, pat, order, name, line)
        self.customers.append(c)
        sfx("bell")
        if royal:
            self.toast("The Royal Magician has arrived with a royal commission!", (1, 0.85, 0.3), 5)
            self.toast("Recipe: Moonflower -> Healing Herb -> Fire Crystal -> Crystal Dust", (1, 0.95, 0.7), 7)

    def break_combo(self, reason):
        if self.combo >= 2:
            self.toast("Combo broken! (%s)" % reason, (1, 0.5, 0.6), 2.5)
            sfx("deny")
        self.combo, self.combo_t = 0, 0.0

    def update_customers(self, dt):
        q = self.queue()
        for i, c in enumerate(q):
            c.slot = i
        for c in list(self.customers):
            c.t += dt
            c.say_t = max(0.0, c.say_t - dt)
            if c.state == "queue":
                c.patience -= dt * (1.0 if c.slot == 0 else 0.5)   # waiting in line drains slower
                if c.slot == 0 and c.arrived and c.line and not c.said:
                    c.said, c.say_t = True, 6.0
                    self.toast("%s: \"%s\"" % (c.name, c.line), (0.85, 0.95, 1), 6)
                if c.patience <= 0:
                    c.state, c.mood, c.react_t = "leaving", "angry", 0.0
                    c.path = [DOOR_IN, OUTSIDE_POINT]
                    loss = 3 if CUSTOMER_TYPES[c.type].get("special") else 1
                    self.rep = max(0, self.rep - loss)
                    self.stats["lost"] += 1
                    self.emit(c.x, 2.3, c.z, (0.9, 0.15, 0.1), 20, 1.2, 0.8, 1.5, -0.5, 7)
                    self.floater(c.x, 2.6, c.z, "-%d rep" % loss, (1, 0.4, 0.3))
                    self.toast("%s left without a potion! (-%d reputation)" % (c.label, loss), (1, 0.5, 0.4), 3)
                    sfx("angry")
                    self.break_combo("a customer left")
                    if CUSTOMER_TYPES[c.type].get("special"):
                        self.end_day(False, "The Royal Magician ran out of patience...")
                        return
            # movement
            if c.state == "queue" and not c.path:
                tx, tz = QUEUE_SLOTS[min(c.slot, len(QUEUE_SLOTS) - 1)]
            elif c.path:
                tx, tz = c.path[0]
            else:
                tx, tz = c.x, c.z
            if c.state == "leaving" and c.react_t < 0.9:
                c.react_t += dt
                c.walking = False
                continue
            dx, dz = tx - c.x, tz - c.z
            d = math.hypot(dx, dz)
            speed = 2.4 if c.mood != "angry" else 3.0
            if d > 0.05:
                step = min(d, speed * dt)
                c.x += dx / d * step
                c.z += dz / d * step
                c.walking = True
                c.yaw = approach_angle(c.yaw, math.degrees(math.atan2(dx, dz)), 500 * dt)
            else:
                c.walking = False
                if c.path:
                    c.path.pop(0)
                    if not c.path and c.state == "leaving":
                        self.customers.remove(c)
                        continue
                elif c.state == "queue":
                    c.arrived = True
                    c.yaw = approach_angle(c.yaw, 180.0, 400 * dt)

        # spawning
        st = self.stage_data
        time_left = st["day_len"] - self.day_time
        if self.stage == 5 and not self.royal_spawned and self.day_time > 10 and len(self.queue()) < self.max_queue:
            self.spawn_customer(royal=True)
            self.royal_spawned = True
        self.spawn_timer -= dt
        if self.spawn_timer <= 0:
            self.spawn_timer = random.uniform(*st["spawn"])
            if len(self.queue()) < self.max_queue and time_left > 15:
                self.spawn_customer()

    # -------------------------------------------------------------- events
    def start_event(self, kind):
        if kind == "crow":
            srcs = [s for s in self.sources if self.unlocked_ing(s.name)]
            if not srcs or self.crow:
                return
            withstock = [s for s in srcs if s.stock > 0 or self.inventory[s.name] > 0]
            self.crow = Crow(random.choice(withstock or srcs))
            sfx("caw")
        elif kind == "boilover":
            idle = [c for c in self.active_cauldrons() if not c.brewing and not c.dirty]
            if not idle:
                self.events_pending.append([self.day_time + 6, kind])
                self.events_pending.sort()
                return
            c = random.choice(idle)
            if c.contents:
                self.toast("The ingredients in the cauldron were lost!", (1, 0.6, 0.5), 3)
            c.contents = []
            c.dirty, c.clean = True, 0
            c.liquid_target = MURKY_LIQUID
            self.emit(c.pos[0], 1.5, c.pos[1], (0.4, 0.75, 0.2), 90, 3.0, 1.4, 2.5, -2.5, 8)
            sfx("boil")
        elif kind == "rush":
            room = min(len(QUEUE_SLOTS), self.max_queue + 2) - len(self.queue())
            for _ in range(max(0, min(3, room))):
                self.spawn_customer()
            self.spawn_timer = max(self.spawn_timer, 14.0)
        elif kind == "rain":
            self.rain_t = 40.0
        elif kind == "surge":
            self.surge_t = 30.0
        title, sub = EVENT_INFO[kind]
        self.event_banner = [title, sub, 3.5]
        self.stats["events"] += 1
        if kind != "crow":
            sfx("event")

    def shoo_crow(self):
        cr = self.crow
        if not cr or not cr.threat:
            return
        cr.leave()
        self.rep += 1
        self.liri.face(cr.x, cr.z)
        self.liri.play("serve", 0.5)
        self.emit(cr.x, cr.y + 0.2, cr.z, (0.15, 0.15, 0.2), 25, 2.0, 0.8, 1.0, -1.0, 6)
        self.floater(cr.x, cr.y + 1.0, cr.z, "Shoo! +1 rep", (0.8, 0.9, 1))
        self.toast("Shoo! The crow flew away empty-beaked (+1 reputation)", (0.8, 0.9, 1), 3)
        sfx("caw")

    def update_events(self, dt):
        while self.events_pending and self.day_time >= self.events_pending[0][0]:
            _, kind = self.events_pending.pop(0)
            self.start_event(kind)
        if self.event_banner:
            self.event_banner[2] -= dt
            if self.event_banner[2] <= 0:
                self.event_banner = None
        if self.rain_t > 0:
            self.rain_t = max(0.0, self.rain_t - dt)
            if self.rain_t == 0:
                self.toast("The rain has stopped.", (0.8, 0.9, 1), 2)
        if self.surge_t > 0:
            self.surge_t = max(0.0, self.surge_t - dt)
            if random.random() < dt * 12:
                a = random.uniform(0, math.tau)
                self.emit(self.liri.x + math.cos(a) * 0.6, random.uniform(0.3, 2.0), self.liri.z + math.sin(a) * 0.6,
                          random.choice([(0.8, 0.4, 1.0), (1.0, 0.8, 0.3)]), 1, 0.3, 1.2, 0.8, 0.0, 6, 0.0)
            if self.surge_t == 0:
                self.toast("The magic surge has faded.", (0.8, 0.7, 1), 2)
        cr = self.crow
        if cr:
            if cr.update(dt) == "steal":
                n = cr.src.name
                took = min(2, self.inventory[n])
                if took:
                    self.inventory[n] -= took
                    msg = "The crow stole %d %s from your stock!" % (took, n)
                else:
                    took = cr.src.stock
                    cr.src.stock = 0
                    msg = "The crow ate the %s patch bare!" % n
                self.toast(msg, (1, 0.5, 0.4), 4)
                self.floater(cr.x, cr.y + 1.0, cr.z, "Stolen!", (1, 0.4, 0.4))
                sfx("caw")
                cr.leave()
            elif cr.state == "perched" and random.random() < dt * 0.8:
                sfx("caw", quiet=True)
            if cr.done:
                self.crow = None
        for c in self.active_cauldrons():
            if c.dirty and random.random() < dt * 6:
                self.emit(c.pos[0] + random.uniform(-0.6, 0.6), 1.5, c.pos[1] + random.uniform(-0.6, 0.6),
                          (0.35, 0.5, 0.2), 1, 0.3, 1.5, 0.7, 0.0, 9, 0.0)
        # combo timer
        if self.combo_t > 0:
            self.combo_t = max(0.0, self.combo_t - dt)
            if self.combo_t == 0 and self.combo >= 2:
                self.toast("Combo ended (best this run: %d in a row)" % self.combo, (0.9, 0.75, 1), 2.5)
            if self.combo_t == 0:
                self.combo = 0
        self.combo_pop = max(0.0, self.combo_pop - dt * 2)
        # potions on the rack slowly lose quality
        spoiled = []
        for it in self.items:
            it["age"] += dt
            if it["age"] > FRESH_TIME and RECIPE[it["name"]]["stage"] < 5:
                it["q"] -= DECAY_RATE * dt
                if it["q"] <= 0:
                    spoiled.append(it)
        for it in spoiled:
            self.items.remove(it)
            self.toast("A %s spoiled on the rack - sell potions while they're fresh!" % it["name"], (1, 0.6, 0.4), 3.5)

    # ------------------------------------------------------------ day flow
    def end_day(self, success, reason=""):
        v, target = self.goal_progress()
        stars = 0
        if success:
            stars = 1
            if self.stats["lost"] <= 2:
                stars = 2
            if self.stats["lost"] == 0 and self.stats["failed"] == 0:
                stars = 3
            self.stars[self.stage] = max(self.stars.get(self.stage, 0), stars)
        self.summary = {"success": success, "reason": reason, "stats": dict(self.stats), "stars": stars,
                        "stage": self.stage, "day": self.day, "goal": self.goal_text(),
                        "progress": (v, target)}
        for c in self.customers:
            if c.state == "queue":
                c.state, c.mood, c.path = "leaving", None, [DOOR_IN, OUTSIDE_POINT]
        self.state = "summary"
        self.summary_t = 0.0
        self.keys.clear()
        self.special.clear()
        self.paused = False
        self.show_upgrades = self.show_recipes = self.show_inventory = self.show_help = False
        if success:
            self.emit(self.liri.x, 2.0, self.liri.z, (1, 0.85, 0.3), 80, 3.0, 1.5, 2.5, -1.5, 7)
            self.liri.play("success", 1.5)

    def next_from_summary(self):
        s = self.summary
        if s["success"]:
            if self.stage >= 5:
                self.state = "victory"
                sfx("fanfare")
                self.victory_t = 0.0
                self.liri.reset(0.0, 1.5)
                self.customers = []
                self.toast("Liri is now the kingdom's Official Royal Potion Maker!", (1, 0.9, 0.4), 8)
                return
            self.stage += 1
            gift = [n for n in ING_NAMES if ING[n]["stage"] == self.stage]
            for n in gift:
                self.inventory[n] = min(self.capacity, self.inventory[n] + 3)
        self.start_day(advance_day=True)
        if s["success"] and self.stage > 1:
            gift = [n for n in ING_NAMES if ING[n]["stage"] == self.stage]
            if gift:
                self.toast("Grandmother sent 3 of each new ingredient: " + ", ".join(gift), (0.8, 1, 0.8), 7)
        self.state = "play"

    # --------------------------------------------------------------- update
    def update(self, dt):
        self.time += dt
        for tst in self.toasts:
            tst[1] -= dt
        self.toasts = [t for t in self.toasts if t[1] > 0]
        for f in self.floaters:
            f[1] += dt * 0.6
            f[5] -= dt
        self.floaters = [f for f in self.floaters if f[5] > 0]
        self.update_particles(dt)
        self.update_cauldron_visuals(dt)

        if self.state == "title":
            self.cam_yaw = 0.55 * math.sin(self.time * 0.15)
            self.cam_pitch = 0.5
            self.cam_dist = 15.0
            self.cam_tx = lerp(self.cam_tx, 0.0, dt)
            self.cam_tz = lerp(self.cam_tz, 0.0, dt)
            self.liri.walking = False
            self.liri.update(dt)
            if random.random() < dt * 0.6:
                self.liri.play(random.choice(["brew", "success"]), 1.5)
            self.ambient_sparkles(dt)
            if random.random() < dt * 6:
                a = random.uniform(0, math.tau)
                self.emit(CAULDRON_POS[0] + math.cos(a) * 1.2, 1.4, CAULDRON_POS[1] + math.sin(a) * 1.2,
                          random.choice([(1, 0.85, 0.4), (0.8, 0.5, 1.0), (0.5, 0.9, 1.0)]), 2, 0.4, 2.0, 0.6, -0.1, 6)
            return

        if self.state in ("summary", "victory"):
            self.summary_t = getattr(self, "summary_t", 0.0) + dt
            self.liri.walking = False
            self.liri.update(dt)
            self.update_customers_leaving_only(dt)
            if self.state == "victory":
                self.victory_t = getattr(self, "victory_t", 0.0) + dt
                if self.liri.action is None:
                    self.liri.play("success", 1.4)
                if random.random() < dt * 3.0:
                    x, z = random.uniform(-8, 8), random.uniform(-6, 2)
                    col = random.choice([(1, 0.3, 0.3), (1, 0.85, 0.2), (0.4, 0.8, 1), (0.8, 0.4, 1), (0.4, 1, 0.5)])
                    self.emit(x, random.uniform(5, 8), z, col, 70, 3.5, 1.6, 0.5, -2.0, 6)
                self.cam_yaw += dt * 0.15
            return

        if self.paused or self.show_help:
            return

        self.day_time += dt
        self.update_camera_keys(dt)
        self.update_player(dt)
        self.liri.update(dt)
        for s in self.sources:
            if self.unlocked_ing(s.name) and s.stock < self.max_stock:
                s.regrow += dt * (2.0 if self.rain_t > 0 and s.loc == "garden" else 1.0)
                if s.regrow >= self.regrow_time:
                    s.regrow = 0.0
                    s.stock += 1
            elif s.stock >= self.max_stock:
                s.regrow = 0.0
        self.update_cauldron(dt)
        self.update_customers(dt)
        if self.state != "play":
            return
        self.update_events(dt)
        if "e" in self.keys:
            self.e_hold_t -= dt
            if self.e_hold_t <= 0:
                self.e_hold_t = 0.3
                n = self.nearest_interactable()
                if n and n[0] == "source":
                    src = n[1]
                    if self.unlocked_ing(src.name) and src.stock > 0 and self.inventory[src.name] < self.capacity:
                        self.collect(src)
        if not self.upgrade_hinted:
            costs = [u["cost"] for u in UPGRADES if not self.upgrades[u["key"]]]
            if costs and self.gold >= min(costs) and self.day_time > 5:
                self.upgrade_hinted = True
                self.toast("You can afford an upgrade! Visit the desk in the back-right corner", (0.85, 0.7, 1), 5)
        self.ambient_sparkles(dt)

        v, target = self.goal_progress()
        if v >= target and self.day_time > 2.0:
            self.end_day(True)
            return
        if self.day_time >= self.stage_data["day_len"]:
            self.end_day(False, "The day ended before the goal was reached.")

    def update_customers_leaving_only(self, dt):
        for c in list(self.customers):
            if c.state != "leaving":
                continue
            c.t += dt
            if not c.path:
                self.customers.remove(c)
                continue
            tx, tz = c.path[0]
            dx, dz = tx - c.x, tz - c.z
            d = math.hypot(dx, dz)
            if d < 0.05:
                c.path.pop(0)
                if not c.path:
                    self.customers.remove(c)
                continue
            step = min(d, 2.8 * dt)
            c.x += dx / d * step
            c.z += dz / d * step
            c.walking = True
            c.yaw = math.degrees(math.atan2(dx, dz))

    def update_camera_keys(self, dt):
        if "z" in self.keys:
            self.cam_yaw -= 1.8 * dt
        if "c" in self.keys:
            self.cam_yaw += 1.8 * dt

    def update_player(self, dt):
        w = self.liri
        fx, fz = -math.sin(self.cam_yaw), -math.cos(self.cam_yaw)
        rx, rz = math.cos(self.cam_yaw), -math.sin(self.cam_yaw)
        mx = mz = 0.0
        k, sp = self.keys, self.special
        if "w" in k or "up" in sp:
            mx += fx; mz += fz
        if "s" in k or "down" in sp:
            mx -= fx; mz -= fz
        if "d" in k or "right" in sp:
            mx += rx; mz += rz
        if "a" in k or "left" in sp:
            mx -= rx; mz -= rz
        m = math.hypot(mx, mz)
        if m > 1e-6 and w.action not in ("success", "fail"):
            mx, mz = mx / m, mz / m
            nx = w.x + mx * PLAYER_SPEED * dt
            nz = w.z + mz * PLAYER_SPEED * dt
            for b in OBSTACLE_BOXES:
                nx, nz = push_out_box(nx, nz, PLAYER_RADIUS, b)
            for c in self.obstacle_circles():
                nx, nz = push_out_circle(nx, nz, PLAYER_RADIUS, c)
            x0, x1, z0, z1 = PLAYER_BOUNDS
            w.x, w.z = clamp(nx, x0, x1), clamp(nz, z0, z1)
            w.walking = True
            w.target_yaw = math.degrees(math.atan2(mx, mz))
            if w.action in ("brew", "collect"):
                w.action = None
        else:
            w.walking = False
        self.cam_tx = lerp(self.cam_tx, w.x, min(1.0, dt * 6))
        self.cam_tz = lerp(self.cam_tz, w.z, min(1.0, dt * 6))

    def update_cauldron(self, dt):
        for c in self.active_cauldrons():
            if c.brewing:
                c.brew_t += dt
                if random.random() < dt * 8:
                    self.emit(c.pos[0] + random.uniform(-0.5, 0.5), 1.55, c.pos[1] + random.uniform(-0.5, 0.5),
                              lerp3(c.liquid, (1, 1, 1), 0.4), 2, 0.4, 1.4, 0.9, 0.0, 8, 0.0)
                if random.random() < dt * 2.5:
                    sfx("bubble", quiet=True)
                if c.brew_t >= c.brew_dur:
                    self.finish_brew(c)
            elif c.reset_timer > 0:
                c.reset_timer -= dt
                if c.reset_timer <= 0 and not c.contents and not c.dirty:
                    c.liquid_target = DEFAULT_LIQUID

    def update_cauldron_visuals(self, dt):
        for c in self.active_cauldrons():
            c.liquid = lerp3(c.liquid, c.liquid_target, min(1.0, dt * 2.5))
            c.flash = max(0.0, c.flash - dt)
            rate = 9.0 if c.brewing else 2.0
            if random.random() < dt * rate:
                a = random.uniform(0, math.tau)
                r = random.uniform(0, 0.6)
                c.bubbles.append([math.cos(a) * r, 0.0, math.sin(a) * r, random.uniform(0.04, 0.09),
                                  random.uniform(0.25, 0.6)])
            for b in c.bubbles:
                b[1] += b[4] * dt
            popped = [b for b in c.bubbles if b[1] > 0.35]
            for b in popped:
                if self.state == "play" and random.random() < 0.5:
                    self.emit(c.pos[0] + b[0], 1.45 + b[1], c.pos[1] + b[2], lerp3(c.liquid, (1, 1, 1), 0.3),
                              3, 0.5, 0.4, 0.4, -1.0, 4, 0.0)
            c.bubbles = [b for b in c.bubbles if b[1] <= 0.35]

    def update_particles(self, dt):
        alive = []
        for p in self.particles:
            p[6] -= dt
            if p[6] <= 0:
                continue
            p[4] += p[10] * dt
            p[0] += p[3] * dt
            p[1] += p[4] * dt
            p[2] += p[5] * dt
            alive.append(p)
        self.particles = alive

    def ambient_sparkles(self, dt):
        night = self.night_factor()
        if night < 0.8 and random.random() < dt * 5:            # dust motes in the sunbeams
            if random.random() < 0.7:
                x, y, z = random.uniform(-9.6, -6.8), random.uniform(0.4, 2.8), random.uniform(-6.5, 0.0)
            else:
                x, y, z = random.uniform(2.6, 5.0), random.uniform(0.3, 2.8), random.uniform(-7.5, -4.8)
            self.emit(x, y, z, (0.55, 0.5, 0.4), 1, 0.06, 5.0, 0.02, 0.0, 3, 0.0)
        if random.random() < dt * 2.5:                              # rising cauldron sparkles
            self.emit(CAULDRON_POS[0] + random.uniform(-0.6, 0.6), 1.5, CAULDRON_POS[1] + random.uniform(-0.6, 0.6),
                      lerp3(self.cauldrons[0].liquid, (1, 1, 1), 0.5), 1, 0.15, 2.0, 0.5, 0.0, 5, 0.0)
        for s in self.sources:
            if not self.unlocked_ing(s.name) or s.stock <= 0:
                continue
            kind = ING[s.name]["kind"]
            glowing = kind == "crystal" or s.name == "Moonflower"
            if glowing and random.random() < dt * 1.5:
                y = 0.9 if s.loc == "shelf" else 0.7
                z = -7.4 if s.loc == "shelf" else s.z
                self.emit(s.x + random.uniform(-0.4, 0.4), y, z, ING[s.name]["color"], 1, 0.2, 1.2, 0.4, 0.0, 4, 0.0)
        if self.upgrades["decor"] and random.random() < dt * 4:
            self.emit(random.uniform(-9, 9), random.uniform(2.5, 3.8), random.uniform(-7, 3),
                      random.choice([(1, 0.9, 0.5), (0.7, 0.8, 1), (1, 0.6, 0.9)]), 1, 0.15, 2.5, 0.05, 0.0, 5, 0.0)

    # -------------------------------------------------------------- input
    def on_key(self, k):
        if self.state == "title":
            if k in ("n", "\r", " "):
                self.start_new_game()
            elif k == "c" and self.save_exists:
                self.continue_game()
            elif k == "\x1b":
                quit_game()
            return
        if self.state == "summary":
            if k == "\r" and self.summary_t > 0.8:      # Enter only, so stray Space taps don't skip it
                self.next_from_summary()
            return
        if self.state == "victory":
            if k in ("\r", "\x1b"):
                self.state = "title"
                self.new_game_state()
            return

        # --- play state ---
        if self.paused:
            if k in ("\x1b", "1", "p"):
                self.paused = False
            elif k == "2":
                self.restart_day()
            elif k == "3":
                self.day_night = not self.day_night
            elif k == "4":
                self.mouse_sens = {0.15: 0.3, 0.3: 0.5, 0.5: 0.15}.get(self.mouse_sens, 0.3)
            elif k == "5":
                self.show_fps = not self.show_fps
            elif k == "6":
                self.outlines = not self.outlines
            elif k == "7":
                self.guide_on = not self.guide_on
            elif k == "8":
                self.music_on = not self.music_on
                AUDIO.set_music(self.music_on)
            elif k == "9":
                self.sfx_on = not self.sfx_on
                AUDIO.sfx_on = self.sfx_on
            elif k == "0":
                quit_game()
            return

        if k == "\x1b":
            if self.show_upgrades or self.show_recipes or self.show_inventory or self.show_help:
                self.show_upgrades = self.show_recipes = self.show_inventory = self.show_help = False
            else:
                self.paused = True
                self.keys.clear()
            return
        if k in ("w", "a", "s", "d", "z", "c"):
            self.keys.add(k)
            return
        if k == "e":
            self.keys.add("e")
            self.e_hold_t = 0.45
            self.interact()
        elif k == "r":
            self.show_recipes = not self.show_recipes
            self.show_upgrades = False
        elif k == "i":
            self.show_inventory = not self.show_inventory
        elif k == "h":
            self.show_help = not self.show_help
        elif k == "u":
            n = self.nearest_interactable()
            if n and n[0] == "desk":
                self.show_upgrades = not self.show_upgrades
            else:
                self.toast("Visit the upgrade desk (back right corner) to buy upgrades", (0.9, 0.9, 0.7), 2)
        elif k == " ":
            self.stir()
        elif k == "\r":
            n = self.nearest_interactable()
            if n and n[0] == "cauldron":
                self.stir()
            elif n and n[0] == "counter":
                self.serve()
        elif k in ("x", "\x08", "\x7f"):
            self.empty_cauldron()
        elif k.isdigit() and k != "0":
            idx = int(k) - 1
            if self.show_upgrades:
                self.buy_upgrade(idx)
            elif self.show_recipes:
                self.load_recipe(idx)
            else:
                self.add_ingredient(idx)

    def on_key_up(self, k):
        self.keys.discard(k)


# =============================================================================
# RENDERING PRIMITIVES
# =============================================================================
_QUAD = None
_OUTLINE = False        # True while the cartoon-outline pass is drawing
_GLOW = 0               # > 0 while inside an additive glow section
_BOX_TEX = None         # when set, box() is drawn with this texture
TEX = {}                # procedural textures: wood, plaster, grass, glow
CAM_R = (1.0, 0.0, 0.0)  # camera right / up vectors (for billboards)
CAM_U = (0.0, 1.0, 0.0)
CAM_EYE = (0.0, 6.0, 11.0)


def quadric():
    global _QUAD
    if _QUAD is None:
        _QUAD = gluNewQuadric()
        gluQuadricNormals(_QUAD, GLU_SMOOTH)
        gluQuadricTexture(_QUAD, GL_FALSE)
    return _QUAD


def col(c, a=1.0):
    if _OUTLINE:
        return
    if len(c) == 4:
        glColor4f(*c)
    else:
        glColor4f(c[0], c[1], c[2], a)


def _skip(size):
    """During the outline pass skip glowing parts and tiny details."""
    return _OUTLINE and (_GLOW > 0 or size < 0.045)


def unlit():
    if not _OUTLINE:
        glDisable(GL_LIGHTING)


def lit():
    if not _OUTLINE and _GLOW == 0:
        glEnable(GL_LIGHTING)


# ------------------------------------------------------------ textures
def _make_texture(size, data, repeat=True, mip=True):
    tid = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, tid)
    wrap = GL_REPEAT if repeat else GL_CLAMP_TO_EDGE
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, wrap)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, wrap)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    if mip:
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
        gluBuild2DMipmaps(GL_TEXTURE_2D, GL_RGBA, size, size, GL_RGBA, GL_UNSIGNED_BYTE, data)
    else:
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, size, size, 0, GL_RGBA, GL_UNSIGNED_BYTE, data)
    return tid


def _noise_fn(size, cells, rnd):
    """Tileable smooth value noise in [0, 1]."""
    grid = [[rnd.random() for _ in range(cells)] for _ in range(cells)]
    k = cells / float(size)

    def f(x, y):
        fx, fy = x * k, y * k
        ix, iy = int(fx), int(fy)
        tx, ty = fx - ix, fy - iy
        tx, ty = tx * tx * (3 - 2 * tx), ty * ty * (3 - 2 * ty)
        x0, x1 = ix % cells, (ix + 1) % cells
        y0, y1 = iy % cells, (iy + 1) % cells
        a = grid[y0][x0] + (grid[y0][x1] - grid[y0][x0]) * tx
        b = grid[y1][x0] + (grid[y1][x1] - grid[y1][x0]) * tx
        return a + (b - a) * ty
    return f


def _pack(pixels):
    out = bytearray()
    for r, g, b, a in pixels:
        out += bytes((int(clamp(r, 0, 1) * 255), int(clamp(g, 0, 1) * 255),
                      int(clamp(b, 0, 1) * 255), int(clamp(a, 0, 1) * 255)))
    return bytes(out)


def build_textures():
    rnd = random.Random(11)
    S = 128
    n4, n16, n32 = _noise_fn(S, 4, rnd), _noise_fn(S, 16, rnd), _noise_fn(S, 32, rnd)

    # wood planks: 4 planks per tile, running along u
    tones = [rnd.uniform(0.82, 1.0) for _ in range(4)]
    seams = [rnd.randint(0, S - 1) for _ in range(4)]
    px = []
    for y in range(S):
        row, ly = divmod(y, 32)
        for x in range(S):
            grain = 0.5 + 0.5 * math.sin((ly + n16(x, y) * 9.0) * 0.85 + row * 2.0)
            v = tones[row] * (0.80 + 0.12 * grain + 0.14 * (n32(x * 3 % S, y) - 0.5))
            if ly < 2 or ly > 29:
                v *= 0.55
            if (x - seams[row]) % S < 2:
                v *= 0.6
            px.append((v, v * 0.97, v * 0.93, 1.0))
    TEX["wood"] = _make_texture(S, _pack(px))

    # plaster
    px = []
    for y in range(S):
        for x in range(S):
            v = 0.86 + 0.10 * (n4(x, y) - 0.5) + 0.07 * (n16(x, y) - 0.5) + 0.04 * (n32(x, y) - 0.5)
            if rnd.random() < 0.01:
                v -= 0.06
            px.append((v, v * 0.98, v * 0.94, 1.0))
    TEX["plaster"] = _make_texture(S, _pack(px))

    # grass
    px = []
    for y in range(S):
        for x in range(S):
            v = 0.72 + 0.22 * (n4(x, y) - 0.5) + 0.16 * (n16(x, y) - 0.5)
            r = rnd.random()
            if r < 0.06:
                v += 0.18
            elif r < 0.12:
                v -= 0.15
            px.append((v * 0.95, v, v * 0.9, 1.0))
    TEX["grass"] = _make_texture(S, _pack(px))

    # soft radial glow sprite (also used for soft shadows and particles)
    G = 64
    px = []
    for y in range(G):
        for x in range(G):
            d = math.hypot(x - G / 2 + 0.5, y - G / 2 + 0.5) / (G / 2)
            a = max(0.0, 1.0 - d) ** 2.0
            px.append((1.0, 1.0, 1.0, a))
    TEX["glow"] = _make_texture(G, _pack(px), repeat=False, mip=False)


def tex_box(x0, x1, y0, y1, z0, z1, tex, tint=(1, 1, 1), s=1.0):
    """Axis-aligned textured box with world-space texture coordinates."""
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, tex)
    col(tint)
    glBegin(GL_QUADS)
    glNormal3f(0, 1, 0)
    glTexCoord2f(x0 * s, z0 * s); glVertex3f(x0, y1, z0)
    glTexCoord2f(x0 * s, z1 * s); glVertex3f(x0, y1, z1)
    glTexCoord2f(x1 * s, z1 * s); glVertex3f(x1, y1, z1)
    glTexCoord2f(x1 * s, z0 * s); glVertex3f(x1, y1, z0)
    glNormal3f(0, -1, 0)
    glTexCoord2f(x0 * s, z0 * s); glVertex3f(x0, y0, z0)
    glTexCoord2f(x1 * s, z0 * s); glVertex3f(x1, y0, z0)
    glTexCoord2f(x1 * s, z1 * s); glVertex3f(x1, y0, z1)
    glTexCoord2f(x0 * s, z1 * s); glVertex3f(x0, y0, z1)
    glNormal3f(1, 0, 0)
    glTexCoord2f(z0 * s, y0 * s); glVertex3f(x1, y0, z0)
    glTexCoord2f(z0 * s, y1 * s); glVertex3f(x1, y1, z0)
    glTexCoord2f(z1 * s, y1 * s); glVertex3f(x1, y1, z1)
    glTexCoord2f(z1 * s, y0 * s); glVertex3f(x1, y0, z1)
    glNormal3f(-1, 0, 0)
    glTexCoord2f(z0 * s, y0 * s); glVertex3f(x0, y0, z0)
    glTexCoord2f(z1 * s, y0 * s); glVertex3f(x0, y0, z1)
    glTexCoord2f(z1 * s, y1 * s); glVertex3f(x0, y1, z1)
    glTexCoord2f(z0 * s, y1 * s); glVertex3f(x0, y1, z0)
    glNormal3f(0, 0, 1)
    glTexCoord2f(x0 * s, y0 * s); glVertex3f(x0, y0, z1)
    glTexCoord2f(x1 * s, y0 * s); glVertex3f(x1, y0, z1)
    glTexCoord2f(x1 * s, y1 * s); glVertex3f(x1, y1, z1)
    glTexCoord2f(x0 * s, y1 * s); glVertex3f(x0, y1, z1)
    glNormal3f(0, 0, -1)
    glTexCoord2f(x0 * s, y0 * s); glVertex3f(x0, y0, z0)
    glTexCoord2f(x0 * s, y1 * s); glVertex3f(x0, y1, z0)
    glTexCoord2f(x1 * s, y1 * s); glVertex3f(x1, y1, z0)
    glTexCoord2f(x1 * s, y0 * s); glVertex3f(x1, y0, z0)
    glEnd()
    glDisable(GL_TEXTURE_2D)


def tbox(x, y, z, sx, sy, sz, tint, tex, s=1.0):
    tex_box(x - sx / 2, x + sx / 2, y - sy / 2, y + sy / 2, z - sz / 2, z + sz / 2, tex, tint, s)


def box(x, y, z, sx, sy, sz, c):
    if _skip(max(sx, sy, sz)):
        return
    if _BOX_TEX is not None and not _OUTLINE:
        tbox(x, y, z, sx, sy, sz, c, _BOX_TEX, 1.2)
        return
    glPushMatrix()
    glTranslatef(x, y, z)
    glScalef(sx, sy, sz)
    col(c)
    glutSolidCube(1.0)
    glPopMatrix()


def cyl(x, y, z, rb, rt, h, c, slices=18, caps=True):
    """Cylinder standing on (x, y, z), growing upward along +y."""
    if _skip(max(rb, rt)):
        return
    glPushMatrix()
    glTranslatef(x, y, z)
    glRotatef(-90, 1, 0, 0)
    col(c)
    q = quadric()
    gluCylinder(q, rb, rt, h, slices, 1)
    if caps:
        glPushMatrix()
        glRotatef(180, 1, 0, 0)
        gluDisk(q, 0, rb, slices, 1)
        glPopMatrix()
        glTranslatef(0, 0, h)
        gluDisk(q, 0, rt, slices, 1)
    glPopMatrix()


def sph(x, y, z, r, c, sx=1.0, sy=1.0, sz=1.0, slices=18, stacks=12):
    if _skip(r * max(sx, sy, sz)):
        return
    glPushMatrix()
    glTranslatef(x, y, z)
    if sx != 1.0 or sy != 1.0 or sz != 1.0:
        glScalef(sx, sy, sz)
    col(c)
    gluSphere(quadric(), r, slices, stacks)
    glPopMatrix()


def cone(x, y, z, r, h, c, slices=18):
    if _skip(r):
        return
    glPushMatrix()
    glTranslatef(x, y, z)
    glRotatef(-90, 1, 0, 0)
    col(c)
    glutSolidCone(r, h, slices, 4)
    glPopMatrix()


def disk_y(x, y, z, r_in, r_out, c, slices=32):
    if _OUTLINE:
        return
    glPushMatrix()
    glTranslatef(x, y, z)
    glRotatef(-90, 1, 0, 0)
    col(c)
    gluDisk(quadric(), r_in, r_out, slices, 1)
    glPopMatrix()


def torus_y(x, y, z, minor, major, c):
    if _skip(major):
        return
    glPushMatrix()
    glTranslatef(x, y, z)
    glRotatef(90, 1, 0, 0)
    col(c)
    glutSolidTorus(minor, major, 12, 32)
    glPopMatrix()


def glow_begin():
    global _GLOW
    _GLOW += 1
    if _OUTLINE:
        return
    glDisable(GL_LIGHTING)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE)
    glDepthMask(GL_FALSE)


def glow_end():
    global _GLOW
    _GLOW = max(0, _GLOW - 1)
    if _OUTLINE or _GLOW > 0:
        return
    glDepthMask(GL_TRUE)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glEnable(GL_LIGHTING)


def _sprite_verts(x, y, z, s):
    rx, ry, rz = CAM_R[0] * s, CAM_R[1] * s, CAM_R[2] * s
    ux, uy, uz = CAM_U[0] * s, CAM_U[1] * s, CAM_U[2] * s
    glTexCoord2f(0, 0); glVertex3f(x - rx - ux, y - ry - uy, z - rz - uz)
    glTexCoord2f(1, 0); glVertex3f(x + rx - ux, y + ry - uy, z + rz - uz)
    glTexCoord2f(1, 1); glVertex3f(x + rx + ux, y + ry + uy, z + rz + uz)
    glTexCoord2f(0, 1); glVertex3f(x - rx + ux, y - ry + uy, z - rz + uz)


def halo(x, y, z, size, c, additive=True):
    """Soft camera-facing glow sprite."""
    if _OUTLINE:
        return
    glDisable(GL_LIGHTING)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE if additive else GL_ONE_MINUS_SRC_ALPHA)
    glDepthMask(GL_FALSE)
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, TEX.get("glow", 0))
    glColor4f(c[0], c[1], c[2], c[3] if len(c) == 4 else 1.0)
    glBegin(GL_QUADS)
    _sprite_verts(x, y, z, size)
    glEnd()
    glDisable(GL_TEXTURE_2D)
    if _GLOW > 0:
        glBlendFunc(GL_SRC_ALPHA, GL_ONE)
        return
    glDepthMask(GL_TRUE)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glEnable(GL_LIGHTING)


def floor_shadow(x, z, sx, sz, alpha=0.45, y=0.014):
    """Soft blob shadow on the floor (radial texture stretched to sx * sz)."""
    if _OUTLINE:
        return
    glDisable(GL_LIGHTING)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glDepthMask(GL_FALSE)
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, TEX.get("glow", 0))
    glColor4f(0.06, 0.02, 0.08, alpha)
    glBegin(GL_QUADS)
    glNormal3f(0, 1, 0)
    glTexCoord2f(0, 0); glVertex3f(x - sx, y, z - sz)
    glTexCoord2f(0, 1); glVertex3f(x - sx, y, z + sz)
    glTexCoord2f(1, 1); glVertex3f(x + sx, y, z + sz)
    glTexCoord2f(1, 0); glVertex3f(x + sx, y, z - sz)
    glEnd()
    glDisable(GL_TEXTURE_2D)
    glDepthMask(GL_TRUE)
    if _GLOW == 0:
        glEnable(GL_LIGHTING)


def draw_outlined(fn, *args):
    """Toon look: draw normally, then draw enlarged back faces as dark lines."""
    global _OUTLINE
    fn(*args)
    if not getattr(GAME, "outlines", True):
        return
    _OUTLINE = True
    try:
        glDisable(GL_LIGHTING)
        glDisable(GL_TEXTURE_2D)
        glDisable(GL_BLEND)
        glEnable(GL_CULL_FACE)
        glCullFace(GL_FRONT)
        glPolygonMode(GL_BACK, GL_LINE)
        glLineWidth(2.6)
        glDepthFunc(GL_LEQUAL)
        glColor4f(0.10, 0.04, 0.12, 1.0)
        fn(*args)
    finally:
        _OUTLINE = False
        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
        glCullFace(GL_BACK)
        glDisable(GL_CULL_FACE)
        glDepthFunc(GL_LESS)
        glLineWidth(1.0)
        glEnable(GL_BLEND)
        glEnable(GL_LIGHTING)


# =============================================================================
# 3D MODELS
# =============================================================================
def draw_bottle(x, y, z, c, s=1.0, glow=0.0):
    glPushMatrix()
    glTranslatef(x, y, z)
    glScalef(s, s, s)
    sph(0, 0.13, 0, 0.13, c)
    glEnable(GL_BLEND)
    sph(0, 0.135, 0, 0.145, (0.85, 0.95, 1.0, 0.22))           # glass shell
    cyl(0, 0.2, 0, 0.045, 0.04, 0.13, (0.8, 0.88, 0.95))
    cyl(0, 0.32, 0, 0.05, 0.05, 0.06, (0.55, 0.35, 0.2))
    unlit()
    sph(-0.05, 0.17, 0.08, 0.03, (1, 1, 1))     # glass highlight
    lit()
    if glow > 0:
        glow_begin()
        sph(0, 0.14, 0, 0.28, (c[0], c[1], c[2], 0.35 * glow))
        glow_end()
    glPopMatrix()


def draw_mushroom(x, y, z, cap, s, t=0.0):
    glPushMatrix()
    glTranslatef(x, y, z)
    glScalef(s, s, s)
    cyl(0, 0, 0, 0.06, 0.05, 0.16, (0.95, 0.92, 0.82), 10)
    sph(0, 0.17, 0, 0.14, cap, 1, 0.6, 1)
    for a in range(0, 360, 90):
        r = math.radians(a + 20)
        sph(math.cos(r) * 0.08, 0.22, math.sin(r) * 0.08, 0.025, (1, 1, 0.95))
    sph(0, 0.25, 0, 0.025, (1, 1, 0.95))
    glPopMatrix()


def draw_crystal(x, y, z, c, s, t):
    b = 0.75 + 0.25 * math.sin(t * 3.0 + x * 2.0 + z)
    unlit()
    for i, (ox, oz, tilt, h) in enumerate(((0, 0, 0, 1.0), (0.08, 0.03, 22, 0.7), (-0.07, -0.02, -18, 0.6))):
        glPushMatrix()
        glTranslatef(x + ox * s, y, z + oz * s)
        glRotatef(tilt, 0, 0, 1)
        glTranslatef(0, 0.2 * h * s, 0)
        glScalef(0.07 * s, 0.2 * h * s, 0.07 * s)
        col((c[0] * b, c[1] * b, c[2] * b))
        glutSolidOctahedron()
        glPopMatrix()
    lit()
    halo(x, y + 0.2 * s, z, 0.5 * s, (c[0], c[1], c[2], 0.45 * b))


def draw_flower(x, y, z, petal, s, t, glowing=False):
    glPushMatrix()
    glTranslatef(x, y, z)
    glScalef(s, s, s)
    glRotatef(5 * math.sin(t * 1.5 + x * 3 + z), 0, 0, 1)
    cyl(0, 0, 0, 0.018, 0.015, 0.38, (0.2, 0.55, 0.2), 6, False)
    sph(0.06, 0.15, 0, 0.06, (0.25, 0.6, 0.25), 1.6, 0.35, 0.8)
    if glowing:
        unlit()
        b = 0.8 + 0.2 * math.sin(t * 2.5 + x)
        pc = (petal[0] * b, petal[1] * b, petal[2] * b)
    else:
        pc = petal
    for a in range(0, 360, 60):
        glPushMatrix()
        glTranslatef(0, 0.4, 0)
        glRotatef(a, 0, 1, 0)
        glTranslatef(0.075, 0, 0)
        glRotatef(20, 0, 0, 1)
        sph(0, 0, 0, 0.06, pc, 1.5, 0.35, 0.8, 8, 6)
        glPopMatrix()
    if glowing:
        lit()
    sph(0, 0.41, 0, 0.045, (1.0, 0.85, 0.2))
    glPopMatrix()
    if glowing:
        halo(x, y + 0.4 * s, z, 0.42 * s, (petal[0], petal[1], petal[2], 0.4))


def draw_herb(x, y, z, c, s, t):
    glPushMatrix()
    glTranslatef(x, y, z)
    glScalef(s, s, s)
    glRotatef(4 * math.sin(t * 1.3 + x * 2), 1, 0, 0)
    for i, a in enumerate(range(0, 360, 72)):
        glPushMatrix()
        glRotatef(a + 10, 0, 1, 0)
        glRotatef(-35 - (i % 2) * 15, 0, 0, 1)
        glTranslatef(0.12, 0.0, 0)
        shade = 0.85 + 0.15 * (i % 2)
        sph(0, 0, 0, 0.12, (c[0] * shade, c[1] * shade, c[2] * shade), 1.3, 0.25, 0.55, 8, 6)
        glPopMatrix()
    sph(0, 0.12, 0, 0.05, (c[0] * 0.7, c[1] * 0.9, c[2] * 0.7))
    glPopMatrix()


def draw_ingredient_item(name, x, y, z, s, t):
    d = ING[name]
    k = d["kind"]
    if k == "flower":
        draw_flower(x, y, z, d["color"], s, t, glowing=(name in ("Moonflower", "Skyflower")))
    elif k == "herb":
        draw_herb(x, y, z, d["color"], s, t)
    elif k == "mushroom":
        draw_mushroom(x, y, z, d["color"], s * 1.2, t)
    else:
        draw_crystal(x, y, z, d["color"], s, t)


# ------------------------------------------------------------------- Liri
SKIN = (0.98, 0.84, 0.74)
DRESS = (0.30, 0.12, 0.45)
HAT = (0.45, 0.20, 0.65)
HAIR = (0.55, 0.22, 0.12)
GLOVE = (0.22, 0.10, 0.30)
BOOT = (0.18, 0.10, 0.08)
STOCK = (0.20, 0.15, 0.25)


def draw_liri(w, stirring=False):
    p = w.pose(stirring)
    floor_shadow(w.x, w.z, 0.62 - p["y"] * 0.3, 0.62 - p["y"] * 0.3, 0.5 - min(0.25, p["y"] * 0.5))
    glPushMatrix()
    glTranslatef(w.x, p["y"], w.z)
    glRotatef(w.yaw + p["shake"], 0, 1, 0)

    glRotatef(p["lean"], 1, 0, 0)

    # legs + boots (hierarchical: hip -> leg -> boot)
    for side, ang in ((-1, p["leg_l"]), (1, p["leg_r"])):
        glPushMatrix()
        glTranslatef(0.13 * side, 0.7, 0)
        glRotatef(ang, 1, 0, 0)
        cyl(0, -0.62, 0, 0.07, 0.08, 0.62, STOCK, 10, False)
        sph(0, -0.64, 0.05, 0.1, BOOT, 1.0, 0.7, 1.6)
        glPopMatrix()

    # dress (cone-ish) + torso
    cyl(0, 0.42, 0, 0.5, 0.2, 0.85, DRESS, 20)
    torus_y(0, 0.44, 0, 0.035, 0.49, (0.65, 0.45, 0.85))       # hem trim
    cyl(0, 1.2, 0, 0.21, 0.18, 0.3, DRESS, 14)
    # belt with potion bottles
    torus_y(0, 1.15, 0, 0.04, 0.235, (0.40, 0.25, 0.12))
    box(0, 1.15, 0.26, 0.09, 0.08, 0.03, (0.95, 0.8, 0.25))
    draw_bottle(0.24, 0.98, 0.05, (0.95, 0.25, 0.35), 0.45)
    draw_bottle(-0.24, 0.98, 0.05, (0.45, 0.85, 1.0), 0.45)
    # magical emblem (glowing star)
    unlit()
    glPushMatrix()
    glTranslatef(0, 1.37, 0.195)
    glRotatef(w.t * 60, 0, 0, 1)
    glScalef(0.05, 0.05, 0.02)
    col((1.0, 0.85, 0.3))
    glutSolidOctahedron()
    glPopMatrix()
    lit()
    # collar
    torus_y(0, 1.5, 0, 0.04, 0.16, (0.65, 0.45, 0.85))

    # arms (shoulder -> arm -> glove -> spoon)
    for side, ang, az in ((-1, p["arm_l"], p["arm_l_z"]), (1, p["arm_r"], p["arm_r_z"])):
        glPushMatrix()
        glTranslatef(0.25 * side, 1.45, 0)
        glRotatef(az, 0, 0, 1)
        glRotatef(ang, 1, 0, 0)
        sph(0, 0, 0, 0.08, DRESS)
        cyl(0, -0.46, 0, 0.065, 0.08, 0.46, DRESS, 10, False)
        sph(0, -0.5, 0, 0.075, GLOVE)
        if side == 1:
            if w.held_color is not None:
                draw_bottle(0, -0.62, 0.05, w.held_color, 0.7, 0.8)
            else:
                # wooden stirring spoon
                glPushMatrix()
                glTranslatef(0, -0.5, 0.04)
                glRotatef(-10, 1, 0, 0)
                cyl(0, -0.55, 0, 0.022, 0.022, 0.7, (0.6, 0.4, 0.2), 8)
                sph(0, -0.6, 0, 0.07, (0.6, 0.4, 0.2), 1.0, 1.3, 0.5)
                glPopMatrix()
        glPopMatrix()

    # head
    glPushMatrix()
    glTranslatef(0, 1.55, 0)
    cyl(0, 0, 0, 0.07, 0.07, 0.12, SKIN, 10, False)
    glTranslatef(0, 0.24 + p["head_bob"], 0)
    glRotatef(p["head_pitch"], 1, 0, 0)
    sph(0, 0, 0, 0.27, SKIN, slices=18, stacks=14)
    # hair + braids
    sph(0, 0.05, -0.08, 0.28, HAIR)
    for side in (-1, 1):
        sph(0.24 * side, -0.12, -0.06, 0.08, HAIR)
        sph(0.27 * side, -0.26, -0.06, 0.07, HAIR)
        sph(0.28 * side, -0.38, -0.05, 0.05, (0.85, 0.5, 0.9))
    # eyes
    expr = p["expr"]
    for side in (-1, 1):
        if expr == "happy" or p["blink"]:
            sph(0.09 * side, 0.03, 0.245, 0.055, (0.15, 0.08, 0.15), 1.0, 0.22, 0.4)
        else:
            sph(0.09 * side, 0.03, 0.235, 0.06, (1, 1, 1), 1.0, 1.15, 0.5)
            sph(0.09 * side, 0.025, 0.262, 0.036, (0.35, 0.15, 0.45), 1.0, 1.1, 0.5)
            unlit()
            sph(0.09 * side + 0.012, 0.042, 0.275, 0.012, (1, 1, 1))
            lit()
        if expr == "sad":
            glPushMatrix()
            glTranslatef(0.09 * side, 0.11, 0.24)
            glRotatef(-18 * side, 0, 0, 1)
            box(0, 0, 0, 0.09, 0.015, 0.02, (0.4, 0.2, 0.1))
            glPopMatrix()
        sph(0.155 * side, -0.07, 0.205, 0.04, (1.0, 0.6, 0.65), 1, 0.6, 0.4)   # cheeks
    if expr == "sad":
        sph(0, -0.12, 0.25, 0.03, (0.5, 0.15, 0.15), 1.0, 1.2, 0.5)
    else:
        sph(0, -0.11, 0.25, 0.04, (0.75, 0.25, 0.25), 1.4, 0.45, 0.5)
    # witch hat (brim -> band -> cone -> bent tip)
    glPushMatrix()
    glTranslatef(0, 0.17, -0.02)
    glRotatef(-8, 1, 0, 0)
    cyl(0, 0, 0, 0.5, 0.5, 0.03, HAT, 24)
    cyl(0, 0.03, 0, 0.29, 0.27, 0.08, (0.95, 0.8, 0.25), 18, False)
    cone(0, 0.03, 0, 0.29, 0.5, HAT, 18)
    glTranslatef(0, 0.42, 0)
    glRotatef(-28, 1, 0, 0)
    cone(0, 0, 0, 0.11, 0.38, HAT, 12)
    unlit()
    sph(0, 0.38, 0, 0.035, (1, 0.9, 0.4))
    lit()
    glPopMatrix()
    glPopMatrix()  # head

    glPopMatrix()


# --------------------------------------------------------------- customers
def draw_customer(c, t):
    ct = CUSTOMER_TYPES[c.type]
    robe, trim, skin = ct["robe"], ct["trim"], ct["skin"]
    anger = 0.0
    if c.state == "queue" and c.frac < 0.35:
        anger = (0.35 - c.frac) / 0.35
    if c.mood == "angry":
        anger = 1.0
    skin = lerp3(skin, (0.95, 0.35, 0.3), anger * 0.6)
    fairy = c.type == "Fairy Visitor"
    royal = c.type == "Royal Magician"
    scale = 0.72 if fairy else (1.12 if royal else 1.0)

    y = 0.0
    swing = 0.0
    if c.walking:
        swing = math.sin(c.t * 9) * 28
        y = abs(math.cos(c.t * 9)) * 0.05
    if fairy:
        y += 0.45 + 0.12 * math.sin(c.t * 3)
    if c.mood == "happy" and c.react_t < 0.9 and c.state == "leaving":
        y += abs(math.sin(c.react_t * 10)) * 0.35
    shake = 0.0
    if anger > 0.5 and not c.walking:
        shake = math.sin(c.t * 30) * 6 * anger

    floor_shadow(c.x, c.z, 0.55 * scale, 0.55 * scale, 0.42 if not fairy else 0.25)
    glPushMatrix()
    glTranslatef(c.x, 0, c.z)
    glTranslatef(0, y, 0)
    glRotatef(c.yaw + shake, 0, 1, 0)
    glScalef(scale, scale, scale)

    # legs
    tap = 0.0
    if c.type == "Impatient Witch" and not c.walking and c.state == "queue":
        tap = max(0.0, math.sin(c.t * 12)) * -25
    for side, ang in ((-1, swing), (1, -swing + tap)):
        glPushMatrix()
        glTranslatef(0.12 * side, 0.55, 0)
        glRotatef(ang, 1, 0, 0)
        cyl(0, -0.5, 0, 0.07, 0.08, 0.5, (0.25, 0.2, 0.18), 8, False)
        sph(0, -0.52, 0.05, 0.09, (0.25, 0.15, 0.1), 1, 0.7, 1.5)
        glPopMatrix()

    # body
    if c.type == "Adventurer":
        cyl(0, 0.45, 0, 0.3, 0.26, 0.9, robe, 16)
        torus_y(0, 0.9, 0, 0.045, 0.29, trim)
        box(0, 1.0, -0.33, 0.45, 0.55, 0.22, (0.45, 0.3, 0.15))              # backpack
        glPushMatrix()                                                        # sword on back
        glTranslatef(0.1, 1.1, -0.46)
        glRotatef(30, 0, 0, 1)
        box(0, 0.25, 0, 0.06, 0.8, 0.02, (0.8, 0.82, 0.85))
        box(0, -0.18, 0, 0.22, 0.05, 0.05, (0.6, 0.45, 0.15))
        glPopMatrix()
    else:
        cyl(0, 0.2, 0, 0.46, 0.22, 1.15, robe, 18)
        torus_y(0, 0.22, 0, 0.04, 0.45, trim)
        torus_y(0, 0.95, 0, 0.035, 0.3, trim)
    if royal:
        glPushMatrix()                                                        # cape
        glTranslatef(0, 0.85, -0.32)
        glRotatef(-12, 1, 0, 0)
        box(0, 0, 0, 0.75, 1.2, 0.05, (0.75, 0.1, 0.15))
        glPopMatrix()
    if fairy:
        glow_begin()
        flap = 35 * math.sin(c.t * 18)
        for side in (-1, 1):
            for up, sc in ((0.25, 1.0), (-0.1, 0.7)):
                glPushMatrix()
                glTranslatef(0.08 * side, 1.15 + up * 0.6, -0.22)
                glRotatef(side * (25 + flap), 0, 1, 0)
                glTranslatef(0.3 * side * sc, 0, 0)
                sph(0, 0, 0, 0.3 * sc, (0.6, 0.95, 1.0, 0.35), 1.0, 0.6, 0.08)
                glPopMatrix()
        glow_end()

    # arms
    for side in (-1, 1):
        glPushMatrix()
        glTranslatef(0.25 * side, 1.28, 0)
        glRotatef(10 * side, 0, 0, 1)
        arm = -swing * side * 0.8 - 5
        if c.mood == "happy" and c.state == "leaving" and c.react_t < 0.9:
            arm = -150
        if c.mood == "angry" and c.react_t < 0.9:
            arm = -40 + 20 * math.sin(c.t * 25)
        glRotatef(arm, 1, 0, 0)
        cyl(0, -0.42, 0, 0.07, 0.08, 0.42, robe, 8, False)
        sph(0, -0.46, 0, 0.07, skin)
        glPopMatrix()

    # staff for wizards
    if c.type in ("Village Wizard", "Royal Magician"):
        cyl(0.42, 0.0, 0.15, 0.03, 0.03, 1.9, (0.45, 0.3, 0.15), 8)
        if royal:
            glow_begin()
            sph(0.42, 1.98, 0.15, 0.22, (1, 0.8, 0.3, 0.35))
            glow_end()
            unlit()
            sph(0.42, 1.98, 0.15, 0.1, (1, 0.95, 0.6))
            lit()
        else:
            unlit()
            sph(0.42, 1.95, 0.15, 0.08, (0.5, 0.8, 1.0))
            lit()

    # head
    glPushMatrix()
    glTranslatef(0, 1.62, 0)
    sph(0, 0, 0, 0.25, skin, slices=16, stacks=12)
    for side in (-1, 1):
        sph(0.08 * side, 0.03, 0.215, 0.045, (1, 1, 1), 1, 1.1, 0.5)
        sph(0.08 * side, 0.03, 0.24, 0.026, (0.1, 0.1, 0.15), 1, 1, 0.5)
        if anger > 0.3:
            glPushMatrix()
            glTranslatef(0.08 * side, 0.1, 0.225)
            glRotatef(20 * side, 0, 0, 1)
            box(0, 0, 0, 0.08, 0.015, 0.02, (0.2, 0.1, 0.05))
            glPopMatrix()
    sph(0, -0.1, 0.22, 0.035, (0.6, 0.2, 0.2), 1.4 if anger < 0.5 else 0.8, 0.4, 0.5)

    if c.type == "Village Wizard":
        glPushMatrix()                                       # beard
        glTranslatef(0, -0.12, 0.12)
        glRotatef(180, 1, 0, 0)
        glRotatef(-10, 1, 0, 0)
        cone(0, 0, 0, 0.17, 0.45, (0.95, 0.95, 0.95), 12)
        glPopMatrix()
        cyl(0, 0.15, 0, 0.42, 0.42, 0.03, robe, 20)
        cone(0, 0.17, 0, 0.24, 0.75, robe, 16)
        unlit()
        sph(0, 0.45, 0.17, 0.05, (1, 0.9, 0.3))
        lit()
    elif c.type == "Fairy Visitor":
        sph(0, 0.08, -0.04, 0.25, (0.95, 0.85, 0.4))                 # golden hair
        for a in range(0, 360, 45):
            r = math.radians(a)
            sph(math.cos(r) * 0.22, 0.18, math.sin(r) * 0.22, 0.05,
                (1, 0.5 + 0.5 * (a % 90 == 0), 0.7))                   # flower crown
    elif c.type == "Adventurer":
        sph(0, 0.06, -0.02, 0.26, (0.35, 0.25, 0.15), 1, 0.75, 1)   # leather cap
        box(0, 0.1, 0.24, 0.42, 0.06, 0.1, (0.7, 0.15, 0.15))        # bandana
    elif c.type == "Impatient Witch":
        sph(0, 0.05, -0.06, 0.26, (0.1, 0.1, 0.1))
        cyl(0, 0.13, 0, 0.45, 0.45, 0.03, (0.08, 0.08, 0.1), 20)
        glPushMatrix()
        glTranslatef(0, 0.15, 0)
        cone(0, 0, 0, 0.24, 0.45, (0.08, 0.08, 0.1), 14)
        glTranslatef(0, 0.4, 0)
        glRotatef(35, 0, 0, 1)
        cone(0, 0, 0, 0.1, 0.35, (0.08, 0.08, 0.1), 10)
        glPopMatrix()
    elif royal:
        sph(0, -0.12, 0.12, 0.17, (0.85, 0.85, 0.88), 1, 1.3, 0.8)   # grey beard
        cyl(0, 0.16, 0, 0.21, 0.23, 0.14, (1.0, 0.8, 0.2), 16)       # crown
        for a in range(0, 360, 72):
            r = math.radians(a)
            cone(math.cos(r) * 0.2, 0.3, math.sin(r) * 0.2, 0.05, 0.13, (1.0, 0.8, 0.2), 8)
        unlit()
        sph(0, 0.23, 0.22, 0.04, (0.9, 0.1, 0.3))
        lit()
    glPopMatrix()
    glPopMatrix()


# --------------------------------------------------------------- cauldron
def draw_cauldron(g, c):
    cx, cz = c.pos
    t = g.time
    # legs & logs
    for a in (90, 210, 330):
        r = math.radians(a)
        cyl(cx + math.cos(r) * 0.62, 0, cz + math.sin(r) * 0.62, 0.08, 0.06, 0.45, (0.12, 0.12, 0.14), 8)
    for a in (0, 60, 120):
        glPushMatrix()
        glTranslatef(cx, 0.08, cz)
        glRotatef(a, 0, 1, 0)
        box(0, 0, 0, 0.9, 0.12, 0.12, (0.4, 0.25, 0.12))
        glPopMatrix()
    # fire: rising soft flame sprites + cones
    heat = 1.4 if c.brewing else 1.0
    glow_begin()
    for i in range(6):
        a = i * math.tau / 6 + t * 0.5
        fl = 0.25 + 0.12 * math.sin(t * 13 + i * 2.1)
        cone(cx + math.cos(a) * 0.18, 0.1, cz + math.sin(a) * 0.18, 0.11, fl * heat, (1.0, 0.45, 0.08, 0.6), 8)
    glow_end()
    for i in range(12):
        ph = (t * 1.7 + i / 12.0) % 1.0
        a = i * 2.4
        fx = cx + math.cos(a) * 0.2 * (1 - ph) + 0.05 * math.sin(t * 9 + i)
        fz = cz + math.sin(a) * 0.2 * (1 - ph)
        cc = lerp3((1.0, 0.85, 0.35), (1.0, 0.25, 0.05), ph)
        halo(fx, 0.15 + ph * 0.55 * heat, fz, (0.28 - 0.18 * ph) * heat, (cc[0], cc[1], cc[2], 0.75 * (1 - ph)))
    halo(cx, 0.25, cz, 1.3 * heat, (1.0, 0.5, 0.15, 0.35 + 0.08 * math.sin(t * 11)))
    # body: clipped sphere (bowl)
    glPushMatrix()
    glTranslatef(cx, 1.0, cz)
    glClipPlane(GL_CLIP_PLANE0, (0.0, -1.0, 0.0, 0.45))
    glEnable(GL_CLIP_PLANE0)
    glScalef(1.0, 0.85, 1.0)
    rim_col = (0.85, 0.7, 0.25) if g.upgrades["cauldron"] else (0.22, 0.22, 0.25)
    col((0.16, 0.16, 0.19))
    gluSphere(quadric(), 1.0, 28, 18)
    glDisable(GL_CLIP_PLANE0)
    glPopMatrix()
    torus_y(cx, 1.45, cz, 0.08, 0.86, rim_col)
    if g.upgrades["cauldron"]:
        for a in range(0, 360, 45):
            r = math.radians(a)
            unlit()
            b = 0.7 + 0.3 * math.sin(t * 3 + a)
            sph(cx + math.cos(r) * 0.99, 1.15, cz + math.sin(r) * 0.99, 0.05, (0.4 * b, 0.9 * b, 1.0 * b))
            lit()
    # liquid
    lc = c.liquid
    wob = 0.025 * math.sin(t * 3)
    unlit()
    b = 0.8 + 0.2 * math.sin(t * 2.2) + (0.6 * c.flash)
    disk_y(cx, 1.38 + wob, cz, 0, 0.86, (min(1, lc[0] * b), min(1, lc[1] * b), min(1, lc[2] * b)), 32)
    # swirl when brewing
    if c.brewing:
        for i in range(10):
            a = t * 4 + i * 0.6
            r = 0.1 + i * 0.065
            sph(cx + math.cos(a) * r, 1.4 + wob, cz + math.sin(a) * r, 0.04,
                lerp3(lc, (1, 1, 1), 0.5), 1, 0.4, 1)
    lit()
    # bubbles
    glEnable(GL_BLEND)
    for bb in c.bubbles:
        sph(cx + bb[0], 1.4 + bb[1], cz + bb[2], bb[3], lerp3(lc, (1, 1, 1), 0.35) + (0.75,), slices=8, stacks=6)
    if c.dirty:                                  # boiled over: goo puddle + drips
        for i in range(9):
            a = i * 0.7 + 0.3
            r = 1.05 + 0.25 * math.sin(i * 2.3)
            sph(cx + math.cos(a) * r, 0.03, cz + math.sin(a) * r, 0.32 + 0.1 * math.sin(i * 1.7),
                (0.35, 0.6, 0.15), 1.0, 0.12, 1.0)
        for i in range(6):
            a = i * 1.05
            d = 0.25 + 0.15 * math.sin(t * 2 + i)
            sph(cx + math.cos(a) * 0.95, 1.3 - d, cz + math.sin(a) * 0.95, 0.07, (0.4, 0.7, 0.2), 1, 1.6, 1)
        halo(cx, 1.6, cz, 1.2, (0.4, 0.8, 0.2, 0.25))
    # glow above the liquid + drifting surface sparkles
    pulse = 0.25 + 0.08 * math.sin(t * 2) + (0.3 if c.brewing else 0) + 0.45 * c.flash
    halo(cx, 1.6, cz, 1.6, (lc[0], lc[1], lc[2], pulse))
    for i in range(5):
        a = t * (0.6 + i * 0.13) + i * 1.3
        r = 0.25 + 0.4 * ((i * 0.37) % 1)
        tw = 0.5 + 0.5 * math.sin(t * 5 + i * 2)
        halo(cx + math.cos(a) * r, 1.42 + wob, cz + math.sin(a) * r, 0.12, (1, 1, 1, 0.35 * tw))


def draw_rack(g):
    global _BOX_TEX
    x, z = RACK_POS
    _BOX_TEX = TEX.get("wood")
    box(x, 0.6, z, 0.9, 1.2, 0.08, (0.45, 0.28, 0.14))            # back board on the left side
    for yy in (0.35, 0.95):
        box(x, yy, z, 0.9, 0.06, 0.7, (0.55, 0.35, 0.18))
    _BOX_TEX = None
    cols = []
    for it in sorted(g.items, key=lambda it: [r["name"] for r in RECIPES].index(it["name"])):
        q = it["q"] / 100.0
        cols.append(lerp3(MURKY_LIQUID, RECIPE[it["name"]]["color"], 0.35 + 0.65 * q))
    for i, c in enumerate(cols[:POTION_CAP]):
        row, k = divmod(i, 4)
        bx = x - 0.3 + k * 0.2
        by = 0.38 if row == 0 else 0.98
        glowing = 0.0
        flash = max(k.flash for k in g.cauldrons)
        if i == len(cols) - 1 and flash > 0:
            glowing = flash
        draw_bottle(bx, by, z + 0.15, c, 0.75, glowing)


# ------------------------------------------------------------ garden/shelf
def draw_sources(g):
    t = g.time
    offs = [(0, 0), (0.32, 0.3), (-0.32, 0.3), (0.32, -0.3), (-0.32, -0.3)]
    for s in g.sources:
        d = ING[s.name]
        unlocked = g.unlocked_ing(s.name)
        if s.loc == "garden":
            # marker stake with ingredient-colored flag
            cyl(s.x + 0.75, 0.3, s.z + 0.5, 0.025, 0.025, 0.55, (0.5, 0.35, 0.2), 6)
            box(s.x + 0.75, 0.78, s.z + 0.5, 0.25, 0.16, 0.03, d["color"] if unlocked else (0.4, 0.4, 0.4))
            if not unlocked:
                sph(s.x, 0.42, s.z, 0.12, (0.3, 0.22, 0.15), 1.2, 0.4, 1.2)
                continue
            for i in range(min(s.stock, len(offs))):
                ox, oz = offs[i]
                draw_ingredient_item(s.name, s.x + ox, 0.42, s.z + oz, 1.0, t)
            if s.stock < g.max_stock:     # sprout regrowing
                k = s.regrow / g.regrow_time
                sph(s.x + 0.55, 0.42, s.z - 0.45, 0.06 + 0.06 * k, (0.3, 0.7, 0.3), 1, 1.4, 1)
        else:
            # plaque on the shelf
            box(s.x, 0.48, -6.93, 0.5, 0.14, 0.03, d["color"] if unlocked else (0.35, 0.35, 0.35))
            if not unlocked:
                box(s.x, 0.75, -7.45, 0.6, 0.25, 0.5, (0.35, 0.25, 0.15))
                continue
            box(s.x, 0.68, -7.45, 0.9, 0.12, 0.6, (0.5, 0.33, 0.18))        # crate
            for i in range(min(s.stock, len(offs))):
                ox, oz = offs[i]
                draw_ingredient_item(s.name, s.x + ox * 0.9, 0.74, -7.45 + oz * 0.55, 0.9, t)


# ------------------------------------------------------------- static room
def _grid_quads(x0, x1, z0, z1, step, y, tex, tint, s):
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, tex)
    col(tint)
    glBegin(GL_QUADS)
    glNormal3f(0, 1, 0)
    x = x0
    while x < x1 - 1e-6:
        xa = min(x1, x + step)
        z = z0
        while z < z1 - 1e-6:
            za = min(z1, z + step)
            glTexCoord2f(x * s, z * s); glVertex3f(x, y, z)
            glTexCoord2f(x * s, za * s); glVertex3f(x, y, za)
            glTexCoord2f(xa * s, za * s); glVertex3f(xa, y, za)
            glTexCoord2f(xa * s, z * s); glVertex3f(xa, y, z)
            z = za
        x = xa
    glEnd()
    glDisable(GL_TEXTURE_2D)


def build_static_scene(g):
    global _BOX_TEX
    rnd = random.Random(7)
    WOOD, PLASTER, GRASS = TEX.get("wood", 0), TEX.get("plaster", 0), TEX.get("grass", 0)

    # ---- outside: grass, hills, trees, village houses
    _grid_quads(-70, 70, -70, 70, 10, -0.02, GRASS, (0.55, 0.80, 0.42), 0.25)
    for (hx, hz, hr, hc) in ((-55, -45, 22, (0.35, 0.62, 0.35)), (-10, -62, 28, (0.30, 0.58, 0.36)),
                             (40, -55, 24, (0.38, 0.64, 0.34)), (62, 5, 20, (0.33, 0.6, 0.4)),
                             (-62, 20, 22, (0.36, 0.63, 0.36)), (20, 62, 25, (0.34, 0.6, 0.35))):
        sph(hx, -2.0, hz, hr, hc, 1.0, 0.28, 1.0, 24, 12)
    for i in range(9):                                        # stone path from the door
        tbox(8.8 + rnd.uniform(-0.2, 0.2), 0.0, 8.8 + i * 1.1, 1.2, 0.06, 0.8, (0.72, 0.70, 0.68), PLASTER, 1.5)
    for (tx, tz, s) in ((-14, -4, 1.2), (-16, 6, 1.0), (15, -6, 1.3), (17, 4, 1.0), (-6, 16, 1.1),
                        (2, 18, 1.3), (14, 15, 0.9), (-14, -14, 1.2), (6, -14, 1.0), (-2, -16, 1.4),
                        (-24, -10, 1.6), (24, -14, 1.5), (-22, 18, 1.3), (26, 20, 1.4)):
        cyl(tx, 0, tz, 0.25 * s, 0.2 * s, 1.6 * s, (0.45, 0.3, 0.15), 10)
        sph(tx, 2.2 * s, tz, 1.3 * s, (0.22, 0.52, 0.26), 1, 0.9, 1)
        sph(tx + 0.5 * s, 2.9 * s, tz + 0.2 * s, 0.95 * s, (0.28, 0.6, 0.3), 1, 0.9, 1)
        sph(tx - 0.4 * s, 3.2 * s, tz - 0.3 * s, 0.8 * s, (0.32, 0.65, 0.32), 1, 0.9, 1)
    for (hx, hz, rc) in ((-4, 15, (0.7, 0.25, 0.2)), (18, 11, (0.25, 0.3, 0.6)), (-18, 12, (0.55, 0.35, 0.6))):
        tbox(hx, 1.2, hz, 3.0, 2.4, 3.0, (0.95, 0.9, 0.82), PLASTER, 0.6)
        tbox(hx, 0.75, hz + 1.51, 0.7, 1.5, 0.04, (0.5, 0.3, 0.15), WOOD, 1.0)
        glPushMatrix()
        glTranslatef(hx, 2.4, hz)
        glRotatef(-90, 1, 0, 0)
        glRotatef(45, 0, 0, 1)
        col(rc)
        glutSolidCone(2.4, 1.8, 4, 1)
        glPopMatrix()
        cyl(hx + 0.8, 2.6, hz - 0.5, 0.2, 0.2, 1.0, (0.55, 0.45, 0.4), 8)

    # ---- wooden floor (textured, subdivided for nice lighting)
    _grid_quads(-10, 10, -8, 8, 1.0, 0.0, WOOD, (0.78, 0.56, 0.36), 0.5)

    # rug under the cauldron
    disk_y(CAULDRON_POS[0], 0.01, CAULDRON_POS[1], 0, 2.3, (0.45, 0.15, 0.35), 48)
    disk_y(CAULDRON_POS[0], 0.012, CAULDRON_POS[1], 1.9, 2.1, (0.9, 0.75, 0.3), 48)
    disk_y(CAULDRON_POS[0], 0.012, CAULDRON_POS[1], 1.3, 1.38, (0.9, 0.75, 0.3), 48)
    for i in range(8):
        a = i * math.tau / 8
        glPushMatrix()
        glTranslatef(CAULDRON_POS[0] + math.cos(a) * 1.65, 0.013, CAULDRON_POS[1] + math.sin(a) * 1.65)
        glRotatef(-math.degrees(a), 0, 1, 0)
        glScalef(0.09, 0.01, 0.09)
        col((0.95, 0.8, 0.35))
        glutSolidOctahedron()
        glPopMatrix()
    if g.upgrades.get("cauldron2"):
        c2x, c2z = CAULDRON2_POS
        disk_y(c2x, 0.01, c2z, 0, 1.75, (0.2, 0.3, 0.55), 48)
        disk_y(c2x, 0.012, c2z, 1.45, 1.6, (0.9, 0.75, 0.3), 48)
        floor_shadow(c2x, c2z, 1.5, 1.5, 0.55)
    # rug by the counter
    tbox(1.0, 0.006, 2.6, 5.5, 0.012, 1.4, (0.25, 0.35, 0.55), PLASTER, 2.0)
    tbox(1.0, 0.008, 2.6, 5.2, 0.012, 1.1, (0.35, 0.5, 0.7), PLASTER, 2.0)

    # soft contact shadows under furniture
    for (sx, sz, ex, ez, a) in ((CAULDRON_POS[0], CAULDRON_POS[1], 1.5, 1.5, 0.55), (1.0, 4.0, 4.4, 1.2, 0.45),
                                (-4.6, -7.3, 4.6, 1.2, 0.5), (DESK_POS[0], DESK_POS[1], 2.1, 1.3, 0.4),
                                (-8.65, -1.0, 1.6, 4.6, 0.4), (RACK_POS[0], RACK_POS[1], 0.8, 0.7, 0.35),
                                (9.4, 0.5, 0.9, 2.4, 0.4)):
        floor_shadow(sx, sz, ex, ez, a)
    for (wx0, wx1, wz0, wz1) in ((-10, 10, -8.2, -7.6), (-10.2, -9.5, -8, 8), (9.5, 10.2, -8, 8)):
        floor_shadow((wx0 + wx1) / 2, (wz0 + wz1) / 2, (wx1 - wx0) / 2 + 0.6, (wz1 - wz0) / 2 + 0.6, 0.3, 0.016)

    # ---- walls (plaster upper, wood wainscot, timber frame)
    wall = (0.98, 0.92, 0.82)
    wain = (0.55, 0.35, 0.2)
    beam = (0.42, 0.25, 0.13)
    tbox(0, 2.0, -8.1, 20.4, 4.0, 0.2, wall, PLASTER, 0.35)
    tbox(-10.1, 2.0, 0, 0.2, 4.0, 16.4, wall, PLASTER, 0.35)
    tbox(10.1, 2.0, 0, 0.2, 4.0, 16.4, wall, PLASTER, 0.35)
    _BOX_TEX = WOOD
    box(0, 0.5, -7.98, 20.0, 1.0, 0.06, wain)
    box(-9.98, 0.5, 0, 0.06, 1.0, 16.0, wain)
    box(9.98, 0.5, 0, 0.06, 1.0, 16.0, wain)
    box(0, 1.03, -7.94, 20.0, 0.07, 0.12, beam)
    box(-9.94, 1.03, 0, 0.12, 0.07, 16.0, beam)
    box(9.94, 1.03, 0, 0.12, 0.07, 16.0, beam)
    for x in (-10, -5, 0, 5, 10):                              # timber beams
        box(x, 2.0, -7.95, 0.3, 4.0, 0.15, beam)
    for z in (-8, -4, 0, 4, 8):
        box(-9.95, 2.0, z, 0.15, 4.0, 0.3, beam)
        box(9.95, 2.0, z, 0.15, 4.0, 0.3, beam)
    for x0 in (-10, -5, 0, 5):                                  # diagonal braces
        glPushMatrix()
        glTranslatef(x0 + 2.5, 2.9, -7.96)
        glRotatef(20, 0, 0, 1)
        box(0, 0, 0, 5.2, 0.12, 0.1, beam)
        glPopMatrix()
    box(0, 4.0, -8.0, 20.4, 0.25, 0.4, beam)
    box(-10.0, 4.0, 0, 0.4, 0.25, 16.4, beam)
    box(10.0, 4.0, 0, 0.4, 0.25, 16.4, beam)
    # windows (glowing glass)
    _BOX_TEX = None
    unlit()
    for (wx, wz) in ((-9.97, -1.0), (-9.97, -5.5)):
        box(wx + 0.03, 2.3, wz, 0.02, 1.5, 1.8, (0.80, 0.93, 1.0))
    box(3.5, 2.5, -7.97, 2.0, 1.4, 0.02, (0.80, 0.93, 1.0))
    lit()
    _BOX_TEX = WOOD
    for (wx, wz) in ((-9.94, -1.0), (-9.94, -5.5)):
        box(wx, 2.3, wz, 0.06, 0.08, 1.8, beam)
        box(wx, 2.3, wz, 0.06, 1.5, 0.08, beam)
        box(wx, 1.52, wz, 0.3, 0.08, 2.1, beam)
        box(wx, 3.08, wz, 0.12, 0.1, 2.0, beam)
        box(wx + 0.25, 1.42, wz, 0.3, 0.14, 1.6, (0.5, 0.32, 0.18))
    box(3.5, 2.5, -7.94, 0.08, 1.4, 0.06, beam)
    box(3.5, 2.5, -7.94, 2.0, 0.08, 0.06, beam)
    box(3.5, 1.77, -7.9, 2.2, 0.08, 0.2, beam)
    box(3.5, 3.23, -7.9, 2.2, 0.08, 0.14, beam)
    _BOX_TEX = None
    for (wx, wz) in ((-9.94, -1.0), (-9.94, -5.5)):
        for k in range(5):
            zz = wz - 0.6 + k * 0.3
            c = ((0.95, 0.4, 0.6), (1.0, 0.85, 0.3), (0.6, 0.5, 1.0))[k % 3]
            sph(wx + 0.25, 1.55, zz, 0.08, (0.3, 0.6, 0.3), 1, 0.7, 1)
            sph(wx + 0.27, 1.62, zz, 0.05, c)
    # curtains
    for (wx, wz) in ((-9.94, -1.0), (-9.94, -5.5)):
        for side in (-1, 1):
            glPushMatrix()
            glTranslatef(wx + 0.12, 2.45, wz + side * 1.05)
            sph(0, 0, 0, 0.5, (0.65, 0.25, 0.45), 0.12, 1.6, 0.35)
            glPopMatrix()
    _BOX_TEX = WOOD
    # front half-wall with door frame
    tbox(-1.1, 0.5, 8.1, 17.8, 1.0, 0.2, wall, PLASTER, 0.35)
    box(-1.1, 1.02, 8.1, 17.9, 0.08, 0.3, beam)
    tbox(9.9, 0.5, 8.1, 0.2, 1.0, 0.2, wall, PLASTER, 0.35)
    for px in (7.75, 9.85):
        box(px, 1.7, 8.1, 0.25, 3.4, 0.3, beam)
    box(8.8, 3.45, 8.1, 2.5, 0.25, 0.35, beam)
    _BOX_TEX = None
    box(8.8, 4.0, 8.15, 2.4, 0.8, 0.1, (0.3, 0.12, 0.45))         # shop sign
    box(8.8, 4.0, 8.2, 2.2, 0.62, 0.02, (0.42, 0.2, 0.6))
    draw_bottle(8.8, 3.68, 8.25, (0.95, 0.4, 0.7), 1.3)
    for sx in (7.9, 8.3, 9.3, 9.7):
        sph(sx, 4.0 + 0.15 * math.sin(sx * 7), 8.22, 0.07, (1, 0.85, 0.3))
    _BOX_TEX = WOOD
    # railing that separates the customer area
    for x0, x1 in ((-10, -2.5), (4.5, 7.6)):
        n = int((x1 - x0) / 0.8) + 1
        for i in range(n):
            px = x0 + (x1 - x0) * i / max(1, n - 1)
            cyl(px, 0, 4.0, 0.05, 0.05, 0.95, (0.45, 0.28, 0.15), 8)
            sph(px, 0.98, 4.0, 0.07, (0.5, 0.32, 0.16))
        box((x0 + x1) / 2, 0.97, 4.0, x1 - x0, 0.08, 0.12, (0.5, 0.3, 0.15))

    # ---- counter
    box(1.0, 0.55, 4.0, 7.0, 1.1, 1.0, (0.62, 0.38, 0.2))
    box(1.0, 1.14, 4.0, 7.3, 0.08, 1.2, (0.82, 0.58, 0.34))
    box(1.0, 0.06, 4.0, 7.15, 0.12, 1.1, (0.4, 0.24, 0.12))
    for x in (-2.0, 0.0, 2.0, 4.0):
        box(x, 0.55, 4.51, 0.12, 1.0, 0.04, (0.42, 0.25, 0.12))
    _BOX_TEX = None
    for x in (-1.0, 1.0, 3.0):                                  # carved star panels
        glPushMatrix()
        glTranslatef(x, 0.6, 4.52)
        glScalef(0.18, 0.18, 0.02)
        col((0.95, 0.78, 0.3))
        glutSolidOctahedron()
        glPopMatrix()
    for i in range(6):                                          # coin pile
        cyl(3.6 + rnd.uniform(-0.15, 0.15), 1.18 + i * 0.025, 4.0 + rnd.uniform(-0.15, 0.15), 0.08, 0.08, 0.025,
            (1.0, 0.82, 0.25), 12)
    cyl(-1.8, 1.18, 4.0, 0.12, 0.05, 0.12, (0.85, 0.7, 0.3), 12)  # service bell
    sph(-1.8, 1.32, 4.0, 0.03, (0.85, 0.7, 0.3))
    for (px, pz, k) in ((-9.3, 7.3, 1.0), (-9.3, -7.3, 1.2), (9.3, -7.3, 1.1), (6.9, 3.3, 0.8)):   # potted plants
        cyl(px, 0, pz, 0.32 * k, 0.4 * k, 0.55 * k, (0.75, 0.4, 0.25), 14)
        torus_y(px, 0.55 * k, pz, 0.04, 0.4 * k, (0.8, 0.45, 0.3))
        for j in range(7):
            a = j * math.tau / 7
            sph(px + math.cos(a) * 0.22 * k, (0.75 + 0.15 * (j % 3)) * k, pz + math.sin(a) * 0.22 * k,
                0.25 * k, (0.25 + 0.05 * (j % 2), 0.55 + 0.08 * (j % 3), 0.28), 1, 0.8, 1)
    for i, hx in enumerate((0.4, 1.3, 5.0, 8.9, 9.6)):         # dried herb bundles on the back beam
        cyl(hx, 3.4, -7.75, 0.01, 0.01, 0.47, (0.3, 0.25, 0.2), 4, False)
        glPushMatrix()
        glTranslatef(hx, 3.4, -7.75)
        glRotatef(180, 1, 0, 0)
        cone(0, 0, 0, 0.14, 0.5, ((0.45, 0.55, 0.25), (0.6, 0.45, 0.6), (0.7, 0.6, 0.3))[i % 3], 10)
        glPopMatrix()
        torus_y(hx, 3.38, -7.75, 0.02, 0.06, (0.75, 0.3, 0.3))
    _BOX_TEX = WOOD

    # ---- ingredient shelves
    sh_col = (0.48, 0.30, 0.16)
    levels = (0.6, 1.5, 2.4, 3.3) if g.upgrades["shelf"] else (0.6, 1.5, 2.4)
    top = levels[-1] + 0.1
    for x in (-8.3, -4.6, -0.9):
        box(x, top / 2, -7.45, 0.12, top, 1.0, sh_col)
    for yv in levels:
        box(-4.6, yv, -7.45, 7.5, 0.08, 1.0, (0.58, 0.38, 0.2))
    _BOX_TEX = None
    for yv in levels[1:]:
        x = -8.0
        while x < -1.2:                                         # decorative jars & books
            kind = rnd.random()
            if kind < 0.55:
                h = rnd.uniform(0.25, 0.45)
                c = (rnd.uniform(0.3, 0.9), rnd.uniform(0.3, 0.9), rnd.uniform(0.3, 0.9))
                cyl(x, yv + 0.04, -7.45 + rnd.uniform(-0.2, 0.2), 0.12, 0.11, h, c, 12)
                cyl(x, yv + 0.04 + h, -7.45, 0.07, 0.07, 0.06, (0.6, 0.45, 0.3), 8)
                x += 0.35
            else:
                for _ in range(rnd.randint(2, 4)):
                    h = rnd.uniform(0.35, 0.55)
                    c = (rnd.uniform(0.2, 0.7), rnd.uniform(0.1, 0.4), rnd.uniform(0.1, 0.5))
                    box(x, yv + 0.04 + h / 2, -7.5, 0.1, h, 0.5, c)
                    x += 0.12
                x += 0.2
    _BOX_TEX = WOOD

    # ---- garden planter (indoor, under the window)
    box(-8.65, 0.2, -1.0, 2.3, 0.4, 7.2, (0.45, 0.28, 0.14))
    box(-8.65, 0.405, -1.0, 2.0, 0.02, 6.9, (0.25, 0.16, 0.1))
    if g.upgrades["garden"]:
        unlit()
        for i in range(12):
            z = -4.3 + i * 0.62
            sph(-9.65, 0.45, z, 0.06, (0.5, 1.0, 0.6))
            sph(-7.65, 0.45, z, 0.06, (0.5, 1.0, 0.6))
        lit()

    # ---- recipe & upgrade desk
    dx, dz = DESK_POS
    box(dx, 0.9, dz, 3.0, 0.12, 1.6, (0.55, 0.34, 0.18))
    for ox in (-1.35, 1.35):
        for oz in (-0.65, 0.65):
            box(dx + ox, 0.45, dz + oz, 0.12, 0.9, 0.12, (0.4, 0.24, 0.12))
    _BOX_TEX = None
    box(dx - 0.3, 0.99, dz + 0.1, 1.0, 0.06, 0.75, (0.45, 0.15, 0.5))      # recipe book cover
    glPushMatrix()
    glTranslatef(dx - 0.55, 1.04, dz + 0.1)
    glRotatef(8, 0, 0, 1)
    box(0, 0, 0, 0.48, 0.04, 0.68, (0.97, 0.94, 0.82))
    glPopMatrix()
    glPushMatrix()
    glTranslatef(dx - 0.05, 1.04, dz + 0.1)
    glRotatef(-8, 0, 0, 1)
    box(0, 0, 0, 0.48, 0.04, 0.68, (0.97, 0.94, 0.82))
    glPopMatrix()
    for i in range(4):
        box(dx - 0.55, 1.07, dz - 0.1 + i * 0.12, 0.35, 0.005, 0.03, (0.3, 0.25, 0.3))
    cyl(dx + 0.9, 0.96, dz - 0.3, 0.06, 0.06, 0.25, (0.95, 0.92, 0.8), 10)  # candle
    cyl(dx + 0.7, 0.96, dz + 0.3, 0.07, 0.05, 0.12, (0.15, 0.15, 0.2), 10)  # ink pot
    glPushMatrix()
    glTranslatef(dx + 0.7, 1.15, dz + 0.3)
    glRotatef(25, 0, 0, 1)
    sph(0, 0, 0, 0.18, (0.95, 0.95, 0.95), 0.12, 1.0, 0.35)
    glPopMatrix()
    tbox(dx, 2.5, -7.92, 2.6, 1.6, 0.06, (0.6, 0.4, 0.22), WOOD, 1.2)      # upgrade notice board
    for i, (ox, oy) in enumerate(((-0.8, 0.3), (0.0, 0.4), (0.8, 0.25), (-0.4, -0.35), (0.5, -0.4))):
        box(dx + ox, 2.5 + oy, -7.88, 0.55, 0.5, 0.02, (0.97, 0.93, 0.8))

    # ---- bookshelf on the right wall
    tbox(9.4, 1.4, 0.5, 1.0, 2.8, 3.6, (0.55, 0.34, 0.18), WOOD, 1.2)
    for yv in (0.35, 1.05, 1.75, 2.45):
        z = -1.1
        while z < 2.0:
            h = rnd.uniform(0.4, 0.6)
            c = (rnd.uniform(0.2, 0.8), rnd.uniform(0.1, 0.5), rnd.uniform(0.1, 0.6))
            box(8.9, yv + h / 2, z, 0.5, h, 0.11, c)
            box(8.64, yv + h * 0.75, z, 0.01, 0.04, 0.112, (0.95, 0.8, 0.35))
            z += 0.13
    _BOX_TEX = None

    # ---- decorations upgrade (banners)
    if g.upgrades["decor"]:
        for i, x in enumerate((-7.5, -2.5, 2.5, 7.5)):
            c = ((0.6, 0.2, 0.7), (0.2, 0.4, 0.8))[i % 2]
            box(x, 3.0, -7.9, 1.0, 1.6, 0.04, c)
            glPushMatrix()
            glTranslatef(x, 2.15, -7.88)
            glRotatef(45, 0, 0, 1)
            box(0, 0, 0, 0.5, 0.5, 0.04, c)
            glPopMatrix()
            sph(x, 3.0, -7.85, 0.15, (1, 0.85, 0.3), 1, 1, 0.3)
        for i in range(24):                                     # bunting flags
            x = -9.5 + i * 0.8
            cone(x, 3.45, 7.9, 0.15, -0.35, ((0.9, 0.3, 0.4), (1, 0.85, 0.3), (0.4, 0.7, 1.0))[i % 3], 3)
    _BOX_TEX = None


def _light_shaft(corners, d, k, c, a0):
    """Additive volumetric-looking beam from a window: 4 faces fading to 0."""
    far = [(p[0] + d[0] * k, p[1] + d[1] * k, p[2] + d[2] * k) for p in corners]
    glBegin(GL_QUADS)
    for i in range(4):
        j = (i + 1) % 4
        glColor4f(c[0], c[1], c[2], a0); glVertex3f(*corners[i]); glVertex3f(*corners[j])
        glColor4f(c[0], c[1], c[2], 0.0); glVertex3f(*far[j]); glVertex3f(*far[i])
    glEnd()


def draw_dynamic_decor(g):
    t = g.time
    dx, dz = DESK_POS
    fl = 0.8 + 0.2 * math.sin(t * 15) + 0.1 * math.sin(t * 23)
    halo(dx + 0.9, 1.3, dz - 0.3, 0.09 * fl, (1, 0.9, 0.6, 1.0))
    halo(dx + 0.9, 1.3, dz - 0.3, 0.5 * fl, (1, 0.65, 0.25, 0.45))
    night = g.night_factor()
    day = 1.0 - night
    # sunbeams through the windows
    if day > 0.05 and not _OUTLINE:
        f = day_fraction(g)
        warm = lerp3((1.0, 0.95, 0.8), (1.0, 0.7, 0.45), clamp((f - 0.6) / 0.3, 0, 1))
        glow_begin()
        for wz in (-1.0, -5.5):
            corners = [(-9.92, 3.05, wz - 0.9), (-9.92, 3.05, wz + 0.9), (-9.92, 1.55, wz + 0.9), (-9.92, 1.55, wz - 0.9)]
            _light_shaft(corners, (1.0, -0.72, 0.18), 3.4, warm, 0.16 * day)
        corners = [(2.5, 3.2, -7.92), (4.5, 3.2, -7.92), (4.5, 1.8, -7.92), (2.5, 1.8, -7.92)]
        _light_shaft(corners, (0.25, -0.7, 1.0), 3.2, warm, 0.13 * day)
        glow_end()
    # hanging lanterns (brighter at night)
    for (lx, lz) in ((-5, -3), (5, -3), (-5, 2), (5, 2)):
        cyl(lx, 3.3, lz, 0.015, 0.015, 0.7, (0.2, 0.2, 0.2), 6, False)
        cyl(lx, 3.0, lz, 0.14, 0.12, 0.3, (0.3, 0.22, 0.15), 8)
        cone(lx, 3.3, lz, 0.17, 0.12, (0.3, 0.22, 0.15), 8)
        unlit()
        b = 0.65 + 0.35 * night
        sph(lx, 3.15, lz, 0.1, (1.0 * b, 0.85 * b, 0.5 * b))
        lit()
        flick = 1.0 + 0.06 * math.sin(t * 9 + lx)
        halo(lx, 3.15, lz, (0.55 + 0.5 * night) * flick, (1, 0.72, 0.3, 0.25 + 0.4 * night))
    # sleeping cat on top of the bookshelf
    br = 1.0 + 0.04 * math.sin(t * 2.2)
    cx, cy, cz = 9.35, 2.85, 1.2
    sph(cx, cy + 0.16, cz, 0.3, (0.15, 0.13, 0.17), 1.0, 0.55 * br, 1.35)
    sph(cx - 0.05, cy + 0.2, cz - 0.42, 0.17, (0.15, 0.13, 0.17))
    for side in (-1, 1):
        glPushMatrix()
        glTranslatef(cx - 0.05 + side * 0.09, cy + 0.32, cz - 0.45)
        glRotatef(side * -15, 0, 0, 1)
        cone(0, 0, 0, 0.055, 0.12, (0.15, 0.13, 0.17), 6)
        glPopMatrix()
        sph(cx - 0.17, cy + 0.22, cz - 0.42 + side * 0.06, 0.02, (0.9, 0.8, 0.4), 1, 0.25, 1)
    glPushMatrix()
    glTranslatef(cx + 0.05, cy + 0.07, cz + 0.2)
    glRotatef(90, 1, 0, 0)
    glRotatef(15 * math.sin(t * 0.7), 0, 0, 1)
    col((0.15, 0.13, 0.17))
    glutSolidTorus(0.05, 0.28, 8, 16)
    glPopMatrix()
    if night > 0.2 or g.state == "title":
        z = (t * 0.4) % 1.0
        text_halo = 0.6 * (1 - z)
        halo(cx - 0.3, cy + 0.5 + z * 0.4, cz - 0.4, 0.08, (0.8, 0.85, 1.0, text_halo))   # "zzz" bubble
    if g.upgrades["decor"]:
        unlit()
        for i in range(10):                                     # floating enchanted candles
            a = i * 0.63 + t * 0.2
            x = math.cos(a) * 6.0
            z = -2.0 + math.sin(a) * 4.0
            y = 3.0 + 0.2 * math.sin(t * 1.5 + i)
            cyl(x, y, z, 0.05, 0.05, 0.22, (0.95, 0.92, 0.85), 8, False)
            halo(x, y + 0.29, z, 0.06, (1, 0.9, 0.6, 1))
            halo(x, y + 0.29, z, 0.3, (1, 0.7, 0.3, 0.35))
        lit()
        glow_begin()                                            # glowing rune circle
        for i in range(12):
            a = i * math.tau / 12 + t * 0.3
            sph(CAULDRON_POS[0] + math.cos(a) * 1.7, 0.03, CAULDRON_POS[1] + math.sin(a) * 1.7, 0.12,
                (0.7, 0.5, 1.0, 0.5), 1, 0.1, 1)
        glow_end()


def draw_highlight(g):
    n = g.nearest_interactable()
    if not n:
        return
    kind, obj = n
    if kind == "source":
        x, z, r = obj.x, (obj.z if obj.loc == "garden" else -6.5), 0.7
        y = 0.43 if obj.loc == "garden" else 0.02
    elif kind == "cauldron":
        x, z, r, y = obj.pos[0], obj.pos[1], 1.5, 0.03
    elif kind == "crow":
        x, z, r, y = obj.x, obj.z, 0.6, 0.03
    elif kind == "desk":
        x, z, r, y = DESK_POS[0], DESK_POS[1] + 1.2, 0.8, 0.02
    else:
        x, z, r, y = g.liri.x, 3.0, 0.8, 0.02
    a = 0.35 + 0.2 * math.sin(g.time * 5)
    glow_begin()
    disk_y(x, y, z, r * 0.82, r, (1.0, 0.9, 0.4, a), 48)
    disk_y(x, y, z, r * 0.6, r * 0.82, (1.0, 0.8, 0.3, a * 0.25), 48)
    for i in range(6):
        ang = g.time * 1.5 + i * math.tau / 6
        halo(x + math.cos(ang) * r, y + 0.1 + 0.08 * math.sin(g.time * 4 + i), z + math.sin(ang) * r, 0.1,
             (1, 0.9, 0.5, 0.8))
    glow_end()


def draw_crow(cr, t):
    """Crow built from primitives, wings flap while flying."""
    flying = cr.state != "perched"
    glPushMatrix()
    glTranslatef(cr.x, cr.y + (0.0 if flying else 0.04 * abs(math.sin(t * 9))), cr.z)
    glRotatef(cr.yaw, 0, 1, 0)
    if not flying:
        glRotatef(20 * max(0.0, math.sin(t * 6)), 1, 0, 0)          # pecking
    black = (0.08, 0.08, 0.11)
    sph(0, 0.18, 0, 0.17, black, 0.85, 0.8, 1.35)
    sph(0, 0.33, 0.2, 0.11, black)
    glPushMatrix()
    glTranslatef(0, 0.32, 0.29)                  # beak points forward (+z)
    col((0.95, 0.65, 0.15))
    glutSolidCone(0.045, 0.14, 8, 2)
    glPopMatrix()
    for side in (-1, 1):
        sph(0.06 * side, 0.37, 0.27, 0.025, (1, 1, 1))
        sph(0.065 * side, 0.37, 0.29, 0.013, (0, 0, 0))
        glPushMatrix()
        glTranslatef(0.12 * side, 0.24, 0.0)
        ang = (35 * math.sin(t * 18) + 10) if flying else 8
        glRotatef(side * -ang, 0, 0, 1)
        glTranslatef(0.18 * side, 0, 0)
        sph(0, 0, 0, 0.2, (0.12, 0.12, 0.16), 1.2 if flying else 0.45, 0.12, 0.8 if flying else 1.0)
        glPopMatrix()
    box(0, 0.16, -0.27, 0.14, 0.04, 0.25, black)
    if not flying:
        for side in (-1, 1):
            cyl(0.05 * side, 0.0, 0.03, 0.012, 0.012, 0.06, (0.9, 0.6, 0.15), 5, False)
    glPopMatrix()


_RAIN = [(random.Random(i).uniform(-30, 30), random.Random(i + 999).uniform(-22, 28),
          random.Random(i + 77).uniform(0, 14)) for i in range(520)]


def rain_strength(g):
    if g.state != "play" or g.rain_t <= 0:
        return 0.0
    return clamp(min((40.0 - g.rain_t) / 3.0, g.rain_t / 3.0), 0.0, 1.0)


def draw_rain(g):
    k = rain_strength(g)
    if k <= 0.01:
        return
    glDisable(GL_LIGHTING)
    glEnable(GL_BLEND)
    glDepthMask(GL_FALSE)
    glLineWidth(1.3)
    glBegin(GL_LINES)
    fall = g.time * 14.0
    for (x, z, y0) in _RAIN:
        if -10.4 < x < 10.4 and -8.4 < z < 8.4:
            continue                                # the shop keeps the rain off
        y = 14.0 - ((y0 + fall) % 14.0)
        glColor4f(0.75, 0.82, 0.95, 0.0)
        glVertex3f(x + 0.08, y + 0.7, z)
        glColor4f(0.75, 0.82, 0.95, 0.55 * k)
        glVertex3f(x, y, z)
    glEnd()
    glLineWidth(1.0)
    glDepthMask(GL_TRUE)
    glEnable(GL_LIGHTING)


def draw_guide_arrow(g):
    t = g.guide() if g.guide_on else None
    if not t:
        return
    x, y, z, _ = t
    b = 0.22 * abs(math.sin(g.time * 3.2))
    glPushMatrix()
    glTranslatef(x, y + 0.75 + b, z)
    glRotatef(g.time * 120, 0, 1, 0)
    glRotatef(180, 1, 0, 0)
    cone(0, 0, 0, 0.22, 0.5, (1.0, 0.82, 0.25), 4)
    glPopMatrix()
    halo(x, y + 0.55 + b, z, 0.6, (1.0, 0.85, 0.35, 0.45))


def draw_particles(g):
    if not g.particles:
        return
    glDisable(GL_LIGHTING)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE)
    glDepthMask(GL_FALSE)
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, TEX.get("glow", 0))
    rx, ry, rz = CAM_R
    ux, uy, uz = CAM_U
    glBegin(GL_QUADS)
    for p in g.particles:
        life = p[6] / p[7]
        a = life if life < 0.85 else (1.0 - life) / 0.15     # quick fade-in, slow fade-out
        c = p[8]
        s = p[9] * 0.02 * (0.6 + 0.4 * life)
        glColor4f(c[0], c[1], c[2], a)
        x, y, z = p[0], p[1], p[2]
        ax, ay, az = (rx + ux) * s, (ry + uy) * s, (rz + uz) * s
        bx, by, bz = (rx - ux) * s, (ry - uy) * s, (rz - uz) * s
        glTexCoord2f(0, 0); glVertex3f(x - ax, y - ay, z - az)
        glTexCoord2f(1, 0); glVertex3f(x + bx, y + by, z + bz)
        glTexCoord2f(1, 1); glVertex3f(x + ax, y + ay, z + az)
        glTexCoord2f(0, 1); glVertex3f(x - bx, y - by, z - bz)
    glEnd()
    glDisable(GL_TEXTURE_2D)
    glDepthMask(GL_TRUE)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glEnable(GL_LIGHTING)


# =============================================================================
# SCENE + LIGHTING
# =============================================================================
SKY_KEYS = [(0.0, (0.98, 0.78, 0.60)), (0.2, (0.70, 0.85, 0.98)), (0.65, (0.68, 0.84, 0.97)),
            (0.85, (0.98, 0.62, 0.42)), (1.0, (0.18, 0.15, 0.34))]
SKY_TOP_KEYS = [(0.0, (0.45, 0.55, 0.88)), (0.2, (0.28, 0.52, 0.92)), (0.65, (0.26, 0.50, 0.90)),
                (0.85, (0.42, 0.32, 0.65)), (1.0, (0.03, 0.03, 0.12))]
_rs = random.Random(5)
STARS = []
while len(STARS) < 220:
    a, e = _rs.uniform(0, math.tau), _rs.uniform(0.08, 1.5)
    STARS.append((math.cos(e) * math.cos(a), math.sin(e), math.cos(e) * math.sin(a), _rs.uniform(0.4, 1.0),
                  _rs.uniform(0, 6.28)))
CLOUDS = [(_rs.uniform(-90, 90), _rs.uniform(24, 36), _rs.uniform(-70, -20) if i % 3 else _rs.uniform(25, 60),
           [(_rs.uniform(-6, 6), _rs.uniform(-1.2, 1.5), _rs.uniform(-2, 2), _rs.uniform(4, 7)) for _ in range(6)])
          for i in range(9)]


def _keyed(keys, f):
    for i in range(len(keys) - 1):
        f0, c0 = keys[i]
        f1, c1 = keys[i + 1]
        if f <= f1:
            return lerp3(c0, c1, (f - f0) / (f1 - f0))
    return keys[-1][1]


def sky_color(f):
    return _keyed(SKY_KEYS, f)


def day_fraction(g):
    if g.state == "play" and g.day_night:
        return clamp(g.day_time / g.stage_data["day_len"], 0, 1)
    return 0.35


def _night_factor(g):
    f = day_fraction(g)
    return clamp((f - 0.75) / 0.25, 0, 1)


Game.night_factor = _night_factor

_static_list = None


def draw_sky(g, eye, f, night):
    hor, top = sky_color(f), _keyed(SKY_TOP_KEYS, f)
    rk = rain_strength(g)
    hor = lerp3(hor, (0.55, 0.58, 0.62), 0.7 * rk)
    top = lerp3(top, (0.42, 0.45, 0.52), 0.7 * rk)
    glDisable(GL_LIGHTING)
    glDisable(GL_FOG)
    glDisable(GL_DEPTH_TEST)
    glDepthMask(GL_FALSE)
    glPushMatrix()
    glTranslatef(eye[0], eye[1], eye[2])
    R = 150.0
    elev = [-0.25, 0.0, 0.08, 0.2, 0.4, 0.7, 1.0, 1.35, 1.5708]
    for i in range(len(elev) - 1):
        glBegin(GL_QUAD_STRIP)
        for j in range(33):
            a = j * math.tau / 32
            for e in (elev[i + 1], elev[i]):
                k = clamp(math.sin(e) * 1.8, 0, 1) ** 0.8
                c = lerp3(hor, top, k) if e >= 0 else lerp3(hor, (hor[0] * 0.8, hor[1] * 0.85, hor[2] * 0.8), -e * 4)
                glColor4f(c[0], c[1], c[2], 1)
                glVertex3f(R * math.cos(e) * math.cos(a), R * math.sin(e), R * math.cos(e) * math.sin(a))
        glEnd()
    # stars
    if night > 0.01:
        glEnable(GL_BLEND)
        glEnable(GL_POINT_SMOOTH)
        glPointSize(2.2)
        glBegin(GL_POINTS)
        for (x, y, z, b, ph) in STARS:
            tw = b * (0.7 + 0.3 * math.sin(g.time * 3 + ph)) * night
            glColor4f(1, 1, 0.95, tw)
            glVertex3f(x * 140, y * 140, z * 140)
        glEnd()
    # sun / moon
    az = math.pi * (0.1 + 0.8 * clamp(f / 0.9, 0, 1))
    sd = (math.cos(az) * 0.75, 0.12 + math.sin(az) * 0.55, -0.6)
    sun_col = lerp3((1.0, 1.0, 0.9), (1.0, 0.6, 0.3), clamp((f - 0.6) / 0.3, 0, 1))
    glow_begin()
    if night < 0.95:
        halo(sd[0] * 120, sd[1] * 120, sd[2] * 120, 22, (sun_col[0], sun_col[1], sun_col[2], 0.5 * (1 - night)))
        halo(sd[0] * 120, sd[1] * 120, sd[2] * 120, 6, (1, 1, 0.95, 1.0 * (1 - night)))
    if night > 0.05:
        md = (-0.5, 0.5, -0.7)
        halo(md[0] * 120, md[1] * 120, md[2] * 120, 14, (0.6, 0.7, 1.0, 0.35 * night))
        halo(md[0] * 120, md[1] * 120, md[2] * 120, 4.5, (0.95, 0.95, 1.0, 1.0 * night))
    glow_end()
    glPopMatrix()
    # clouds (soft sprites, normal blending)
    cloud_c = lerp3(lerp3((1, 1, 1), (1.0, 0.75, 0.6), clamp((f - 0.65) / 0.25, 0, 1)), (0.3, 0.3, 0.45), night)
    for (cx, cy, cz, puffs) in CLOUDS:
        x = ((cx + g.time * 0.6 + 90) % 180) - 90
        for (ox, oy, oz, r) in puffs:
            halo(x + ox, cy + oy, cz + oz, r, (cloud_c[0], cloud_c[1], cloud_c[2], 0.55), additive=False)
    glDepthMask(GL_TRUE)
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_FOG)
    glEnable(GL_LIGHTING)


def render_world(g):
    global _static_list, CAM_R, CAM_U, CAM_EYE
    f = day_fraction(g)
    sky = lerp3(sky_color(f), (0.55, 0.58, 0.62), 0.7 * rain_strength(g))
    night = g.night_factor()
    glClearColor(sky[0], sky[1], sky[2], 1)
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(55.0, g.W / float(max(1, g.H)), 0.1, 220.0)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    tx, tz = g.cam_tx, g.cam_tz
    ty = 1.2
    ex = tx + g.cam_dist * math.sin(g.cam_yaw) * math.cos(g.cam_pitch)
    ey = ty + g.cam_dist * math.sin(g.cam_pitch)
    ez = tz + g.cam_dist * math.cos(g.cam_yaw) * math.cos(g.cam_pitch)
    ex = clamp(ex, -9.6, 9.6)
    ez = max(ez, -7.6)
    gluLookAt(ex, ey, ez, tx, ty, tz, 0, 1, 0)
    # camera basis for billboards
    fx, fy, fz = tx - ex, ty - ey, tz - ez
    fl = math.sqrt(fx * fx + fy * fy + fz * fz) or 1.0
    fx, fy, fz = fx / fl, fy / fl, fz / fl
    rx, ry, rz = -fz, 0.0, fx                     # forward x world-up
    rl = math.hypot(rx, rz) or 1.0
    rx, rz = rx / rl, rz / rl
    CAM_R = (rx, ry, rz)
    CAM_U = (ry * fz - rz * fy, rz * fx - rx * fz, rx * fy - ry * fx)
    CAM_EYE = (ex, ey, ez)

    # lights
    sun = 0.35 + 0.65 * (1.0 - night)
    warm = lerp3((1.0, 0.96, 0.86), (0.55, 0.6, 0.95), night)
    if f > 0.7:
        warm = lerp3(warm, (1.0, 0.75, 0.55), clamp((f - 0.7) / 0.15, 0, 1) * (1 - night))
    glLightfv(GL_LIGHT0, GL_POSITION, (0.35, 1.0, 0.55, 0.0))
    glLightfv(GL_LIGHT0, GL_DIFFUSE, (warm[0] * sun, warm[1] * sun, warm[2] * sun, 1))
    glLightfv(GL_LIGHT0, GL_AMBIENT, (0, 0, 0, 1))
    amb = 0.30 + 0.12 * (1 - night)
    glLightModelfv(GL_LIGHT_MODEL_AMBIENT, (amb * 1.02, amb * 0.95, amb * 1.08, 1))
    c0 = g.cauldrons[0]
    lc = c0.liquid
    k = 1.0 + (0.7 if c0.brewing else 0) + c0.flash + 0.08 * math.sin(g.time * 11)
    glLightfv(GL_LIGHT1, GL_POSITION, (c0.pos[0], 2.2, c0.pos[1], 1.0))
    glLightfv(GL_LIGHT1, GL_DIFFUSE, (lc[0] * k, lc[1] * k, lc[2] * k, 1))
    glLightf(GL_LIGHT1, GL_QUADRATIC_ATTENUATION, 0.07)
    glLightfv(GL_LIGHT2, GL_POSITION, (0.0, 3.2, 0.0, 1.0))
    lan = 0.25 + 0.65 * night
    glLightfv(GL_LIGHT2, GL_DIFFUSE, (lan, lan * 0.78, lan * 0.45, 1))
    glLightf(GL_LIGHT2, GL_QUADRATIC_ATTENUATION, 0.018)
    if g.upgrades.get("cauldron2"):
        c1 = g.cauldrons[1]
        k1 = 0.9 + (0.7 if c1.brewing else 0) + c1.flash
        glEnable(GL_LIGHT3)
        glLightfv(GL_LIGHT3, GL_POSITION, (c1.pos[0], 2.2, c1.pos[1], 1.0))
        glLightfv(GL_LIGHT3, GL_DIFFUSE, (c1.liquid[0] * k1, c1.liquid[1] * k1, c1.liquid[2] * k1, 1))
        glLightf(GL_LIGHT3, GL_QUADRATIC_ATTENUATION, 0.09)
    else:
        glDisable(GL_LIGHT3)
    rk = rain_strength(g)
    if rk > 0:                                    # overcast while it rains
        d = 1.0 - 0.4 * rk
        glLightfv(GL_LIGHT0, GL_DIFFUSE, (warm[0] * sun * d, warm[1] * sun * d, warm[2] * sun * d, 1))

    glFogfv(GL_FOG_COLOR, (sky[0], sky[1], sky[2], 1))
    draw_sky(g, CAM_EYE, f, night)

    if g.static_dirty or _static_list is None:
        if _static_list is None:
            _static_list = glGenLists(1)
        glNewList(_static_list, GL_COMPILE)
        build_static_scene(g)
        glEndList()
        g.static_dirty = False
    glCallList(_static_list)

    draw_dynamic_decor(g)
    draw_sources(g)
    for cau in g.active_cauldrons():
        draw_outlined(draw_cauldron, g, cau)
    draw_rack(g)
    if g.state == "play":
        draw_highlight(g)
        draw_guide_arrow(g)
    for c in g.customers:
        draw_outlined(draw_customer, c, g.time)
    near = g.near_cauldron() if g.state == "play" else None
    stirring = bool(near and near.brewing and not g.liri.walking)
    if g.crow:
        draw_outlined(draw_crow, g.crow, g.time)
    draw_rain(g)
    draw_outlined(draw_liri, g.liri, stirring or (g.state == "title" and g.liri.action == "brew"))
    draw_particles(g)

    # save matrices for projecting 3D labels in the HUD
    g.mv = glGetDoublev(GL_MODELVIEW_MATRIX)
    g.pj = glGetDoublev(GL_PROJECTION_MATRIX)
    g.vp = glGetIntegerv(GL_VIEWPORT)


def project(g, x, y, z):
    try:
        sx, sy, sz = gluProject(x, y, z, g.mv, g.pj, g.vp)
    except Exception:
        return None
    if sz < 0 or sz > 1:
        return None
    return sx, g.H - sy


# =============================================================================
# HUD (2D orthographic overlay)
# =============================================================================
F_BIG = GLUT_BITMAP_TIMES_ROMAN_24
F_MED = GLUT_BITMAP_HELVETICA_18
F_SM = GLUT_BITMAP_HELVETICA_12
PANEL = (0.10, 0.05, 0.16, 0.80)
GOLD = (1.0, 0.85, 0.35, 1.0)


def _rr_pts(g, x, y, w, h, r, seg=6):
    r = max(0.0, min(r, w / 2.0, h / 2.0))
    top, bot = g.H - y, g.H - y - h
    pts = []
    for (cx, cy, a0) in ((x + w - r, top - r, 0), (x + r, top - r, 90), (x + r, bot + r, 180), (x + w - r, bot + r, 270)):
        for i in range(seg + 1):
            a = math.radians(a0 + 90.0 * i / seg)
            pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
    return pts


def _shade(c, k):
    a = c[3] if len(c) == 4 else 1.0
    if k >= 0:
        return (c[0] + (1 - c[0]) * k, c[1] + (1 - c[1]) * k, c[2] + (1 - c[2]) * k, a)
    return (c[0] * (1 + k), c[1] * (1 + k), c[2] * (1 + k), a)


def rrect(g, x, y, w, h, c, r=8, c2=None):
    """Rounded rectangle with an optional vertical gradient (c top, c2 bottom)."""
    c2 = c2 or c
    top, bot = g.H - y, g.H - y - h
    pts = _rr_pts(g, x, y, w, h, r)
    glBegin(GL_TRIANGLE_FAN)
    mid = lerp(0, 1, 0.5)
    cm = [lerp(c[i], c2[i], mid) for i in range(3)] + [lerp(c[3] if len(c) == 4 else 1, c2[3] if len(c2) == 4 else 1, mid)]
    glColor4f(*cm)
    glVertex2f(x + w / 2.0, g.H - y - h / 2.0)
    for (px, py) in pts + pts[:1]:
        t = (top - py) / max(1.0, h)
        cc = [lerp(c[i], c2[i], t) for i in range(3)]
        glColor4f(cc[0], cc[1], cc[2], lerp(c[3] if len(c) == 4 else 1, c2[3] if len(c2) == 4 else 1, t))
        glVertex2f(px, py)
    glEnd()


def rframe(g, x, y, w, h, c, r=8, width=1.5):
    glLineWidth(width)
    col(c)
    glBegin(GL_LINE_LOOP)
    for (px, py) in _rr_pts(g, x, y, w, h, r):
        glVertex2f(px, py)
    glEnd()
    glLineWidth(1.0)


def text_w(s, font=F_SM):
    return sum(glutBitmapWidth(font, ord(ch)) for ch in s)


def text(g, x, y, s, font=F_SM, c=(1, 1, 1, 1), center=False, shadow=True):
    if center:
        x -= text_w(s, font) / 2
    if shadow:
        glColor4f(0, 0, 0, 0.6 * (c[3] if len(c) == 4 else 1))
        for (ox, oy) in ((1, 1), (2, 2)):
            glRasterPos2f(x + ox, g.H - y - oy)
            for ch in s:
                glutBitmapCharacter(font, ord(ch))
    col(c)
    glRasterPos2f(x, g.H - y)
    for ch in s:
        glutBitmapCharacter(font, ord(ch))


def stroke_w(s):
    return sum(glutStrokeWidth(GLUT_STROKE_ROMAN, ord(ch)) for ch in s)


def stroke_text(g, cx, y, s, height, c=GOLD, width=3.0, glow=True, shadow=True):
    """Big smooth vector text (GLUT stroke font); y is the baseline (from top)."""
    sc = height / 119.05
    x = cx - stroke_w(s) * sc / 2.0
    glEnable(GL_LINE_SMOOTH)
    passes = []
    if shadow:
        passes.append((3, -3, width + 2.5, (0.05, 0.0, 0.08, 0.6 * (c[3] if len(c) == 4 else 1))))
    if glow:
        passes.append((0, 0, width + 6.0, (c[0], c[1], c[2], 0.18)))
        passes.append((0, 0, width + 3.0, (c[0], c[1], c[2], 0.25)))
    passes.append((0, 0, width, c))
    passes.append((0, 1.2, max(1.0, width * 0.4), _shade(c, 0.55)))     # highlight
    for (ox, oy, lw, cc) in passes:
        glLineWidth(lw)
        col(cc)
        glPushMatrix()
        glTranslatef(x + ox, g.H - y + oy, 0)
        glScalef(sc, sc, 1)
        for ch in s:
            glutStrokeCharacter(GLUT_STROKE_ROMAN, ord(ch))
        glPopMatrix()
    glLineWidth(1.0)


def rect(g, x, y, w, h, c):
    col(c)
    glBegin(GL_QUADS)
    glVertex2f(x, g.H - y); glVertex2f(x + w, g.H - y)
    glVertex2f(x + w, g.H - y - h); glVertex2f(x, g.H - y - h)
    glEnd()


def frame(g, x, y, w, h, c=GOLD):
    rframe(g, x, y, w, h, c, 4, 1.5)


def panel(g, x, y, w, h, c=PANEL, border=GOLD):
    """Rounded gradient panel with a soft drop shadow and a double gold border."""
    a = c[3] if len(c) == 4 else 1.0
    for i, (o, sa) in enumerate(((7, 0.10), (4, 0.16), (2, 0.20))):
        rrect(g, x - o / 2 + 3, y - o / 2 + 5, w + o, h + o, (0, 0, 0, sa * a), 12 + o)
    rrect(g, x, y, w, h, _shade(c, 0.10), 12, _shade(c, -0.35))
    rrect(g, x + 3, y + 3, w - 6, min(22, h / 3), (1, 1, 1, 0.07), 9, (1, 1, 1, 0.0))     # top sheen
    rframe(g, x, y, w, h, border, 12, 2.0)
    rframe(g, x + 4, y + 4, w - 8, h - 8, (border[0], border[1], border[2], 0.28), 9, 1.0)
    for (px, py) in ((x + 7, y + 7), (x + w - 7, y + 7), (x + 7, y + h - 7), (x + w - 7, y + h - 7)):
        star_icon(g, px, py, 3.2, (border[0], border[1], border[2], 0.8))


def bar(g, x, y, w, h, frac, c, bg=(0.12, 0.07, 0.14, 0.92)):
    r = h / 2.0
    rrect(g, x, y, w, h, bg, r)
    f = clamp(frac, 0, 1)
    fw = w * f
    if fw > 1:
        cc = c if len(c) == 4 else c + (1,)
        rrect(g, x, y, max(fw, min(w, h)), h, _shade(cc, 0.25), r, _shade(cc, -0.25))
        rrect(g, x + 2, y + 1, max(1, max(fw, min(w, h)) - 4), h * 0.42, (1, 1, 1, 0.35), r * 0.6, (1, 1, 1, 0.05))
    rframe(g, x, y, w, h, (1, 1, 1, 0.35), r, 1.0)


def button(g, x, y, w, h, c, fn=None, enabled=True):
    """Rounded row/button that brightens and gets a gold rim when hovered."""
    mx, my = g.mouse_pos
    hover = x <= mx <= x + w and y <= my <= y + h
    cc = c if len(c) == 4 else c + (1,)
    if hover and enabled:
        cc = _shade(cc, 0.18)
    rrect(g, x, y, w, h, _shade(cc, 0.08), 7, _shade(cc, -0.2))
    if hover and enabled:
        rframe(g, x, y, w, h, GOLD, 7, 2.0)
    else:
        rframe(g, x, y, w, h, (1, 1, 1, 0.18), 7, 1.0)
    if fn is not None:
        add_click(g, x, y, w, h, fn)
    return hover


def star_icon(g, cx, cy, r, c):
    col(c)
    glBegin(GL_TRIANGLE_FAN)
    glVertex2f(cx, g.H - cy)
    for i in range(11):
        a = math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        glVertex2f(cx + math.cos(a) * rr, g.H - cy + math.sin(a) * rr)
    glEnd()


def coin_icon(g, cx, cy, r):
    pts = 20
    for (rr, c) in ((r, (0.75, 0.5, 0.1, 1)), (r * 0.82, (1.0, 0.82, 0.3, 1)), (r * 0.5, (1.0, 0.92, 0.55, 1))):
        col(c)
        glBegin(GL_TRIANGLE_FAN)
        glVertex2f(cx, g.H - cy)
        for i in range(pts + 1):
            a = i * math.tau / pts
            glVertex2f(cx + math.cos(a) * rr, g.H - cy + math.sin(a) * rr)
        glEnd()


def bottle_icon(g, x, y, c, s=1.0):
    cc = c + (1,) if len(c) == 3 else c
    rrect(g, x + 4 * s, y, 6 * s, 5 * s, (0.65, 0.42, 0.25, 1), 1.5 * s)
    rect(g, x + 5 * s, y + 5 * s, 4 * s, 4 * s, (0.85, 0.92, 0.98, 1))
    rrect(g, x, y + 8 * s, 14 * s, 12 * s, _shade(cc, 0.3), 5 * s, _shade(cc, -0.3))
    rrect(g, x + 2.5 * s, y + 10 * s, 3 * s, 5 * s, (1, 1, 1, 0.55), 1.5 * s)


def patience_color(f):
    if f > 0.5:
        return (0.3, 0.9, 0.35, 1)
    if f > 0.25:
        return (1.0, 0.8, 0.2, 1)
    return (1.0, 0.3, 0.25, 1)


def add_click(g, x, y, w, h, fn):
    g.click_rects.append((x, y, w, h, fn))


def screen_grade(g):
    """Evening / night colour grade plus a soft vignette."""
    W, H = g.W, g.H
    f = day_fraction(g)
    night = g.night_factor()
    eve = clamp((f - 0.65) / 0.2, 0, 1) * (1 - night)
    if eve > 0:
        rect(g, 0, 0, W, H, (1.0, 0.5, 0.2, 0.07 * eve))
    if night > 0:
        rect(g, 0, 0, W, H, (0.08, 0.1, 0.35, 0.2 * night))
    ix, iy = W * 0.22, H * 0.22
    edge = (0.06, 0.0, 0.1, 0.55)
    clear = (0.06, 0.0, 0.1, 0.0)
    o = [(0, 0), (W, 0), (W, H), (0, H)]
    i = [(ix, iy), (W - ix, iy), (W - ix, H - iy), (ix, H - iy)]
    glBegin(GL_QUADS)
    for k in range(4):
        j = (k + 1) % 4
        col(edge); glVertex2f(*o[k]); glVertex2f(*o[j])
        col(clear); glVertex2f(*i[j]); glVertex2f(*i[k])
    glEnd()


def begin_2d(g):
    glDisable(GL_LIGHTING)
    glDisable(GL_DEPTH_TEST)
    glDisable(GL_FOG)
    glDisable(GL_TEXTURE_2D)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glEnable(GL_LINE_SMOOTH)
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    glOrtho(0, g.W, 0, g.H, -1, 1)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()


def end_2d(g):
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)
    glPopMatrix()
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING)
    glEnable(GL_FOG)


def render_hud(g):
    g.click_rects = []
    begin_2d(g)
    screen_grade(g)
    if g.state == "title":
        hud_title(g)
    elif g.state == "play":
        hud_world_labels(g)
        hud_play(g)
        if g.show_recipes:
            hud_recipes(g)
        if g.show_upgrades:
            hud_upgrades(g)
        if g.show_inventory:
            hud_inventory(g)
        if g.show_help:
            hud_help(g)
        if g.paused:
            hud_pause(g)
    elif g.state == "summary":
        hud_summary(g)
    elif g.state == "victory":
        hud_victory(g)
    hud_toasts(g)
    if g.show_fps:
        text(g, g.W - 80, g.H - 8, "%d FPS" % g.fps, F_SM, (0.8, 1, 0.8, 1))
    end_2d(g)


def hud_world_labels(g):
    # order bubbles above customers
    q = g.queue()
    for qi, c in enumerate(q):
        s = project(g, c.x, 2.55 if c.type != "Fairy Visitor" else 2.3, c.z)
        if not s:
            continue
        x, y = s
        r = RECIPE[c.request]
        if qi > 0:                               # compact bubble: potion icon + patience bar
            w, h = 44, 34
            bx, by = x - w / 2, y - 26
            urgent = c.frac < 0.25
            pulse = 0.5 + 0.5 * math.sin(g.time * 10)
            rrect(g, bx + 2, by + 3, w, h, (0, 0, 0, 0.22), 9)
            rrect(g, bx, by, w, h, (1.0, 0.98, 0.92, 0.92), 9, (0.93, 0.88, 0.76, 0.92))
            rframe(g, bx, by, w, h, (1, 0.25, 0.2, 0.6 + 0.4 * pulse) if urgent else (0.45, 0.3, 0.45, 1), 9,
                   2.0 if urgent else 1.2)
            bottle_icon(g, x - 7, by + 3, r["color"], 0.75)
            if g.can_serve(c):
                star_icon(g, bx + w - 7, by + 7, 5, (0.2, 0.75, 0.3, 1))
            if c.order:
                tag = "x2" if c.order == "double" else "P!"
                text(g, bx + 3, by + 13, tag, F_SM, (0.75, 0.2, 0.5, 1), shadow=False)
            bar(g, bx + 5, by + h - 10, w - 10, 6, c.frac, patience_color(c.frac))
            continue
        name = short_name(c.request)
        if c.order == "double":
            name = "2x " + name
        elif c.order == "strong":
            name = "PERFECT " + name
        w = max(110, text_w(name, F_SM) + 40)
        if c.name:
            nw = text_w(c.name, F_SM) + 16
            rrect(g, x - nw / 2, y - 52, nw, 18, (0.3, 0.45, 0.75, 0.95), 9)
            text(g, x, y - 39, c.name, F_SM, (1, 1, 1, 1), center=True, shadow=False)
        if c.say_t > 0 and c.line:
            a = clamp(c.say_t / 0.5, 0, 1)
            sw = min(420, text_w(c.line, F_SM) + 24)
            sx0 = clamp(x - sw / 2, 8, g.W - sw - 8)
            rrect(g, sx0 + 2, y - 86, sw, 26, (0, 0, 0, 0.25 * a), 12)
            rrect(g, sx0, y - 88, sw, 26, (1, 1, 1, 0.97 * a), 12)
            rframe(g, sx0, y - 88, sw, 26, (0.3, 0.45, 0.75, a), 12, 1.5)
            text(g, sx0 + 12, y - 70, c.line, F_SM, (0.15, 0.15, 0.3, a), shadow=False)
        royal = CUSTOMER_TYPES[c.type].get("special")
        bx, by = x - w / 2, y - 30
        rrect(g, bx + 2, by + 4, w, 38, (0, 0, 0, 0.25), 10)
        rrect(g, bx, by, w, 38, (1.0, 0.98, 0.92, 0.96), 10, (0.93, 0.88, 0.76, 0.96))
        urgent = c.frac < 0.25
        pulse = 0.5 + 0.5 * math.sin(g.time * 10)
        border = (1, 0.25, 0.2, 0.6 + 0.4 * pulse) if urgent else (GOLD if royal else (0.45, 0.3, 0.45, 1))
        rframe(g, bx, by, w, 38, border, 10, 2.5 if urgent or royal else 1.5)
        if royal:
            star_icon(g, bx + w - 8, by + 4, 6, GOLD)
        bottle_icon(g, x - w / 2 + 6, y - 26, r["color"], 0.8)
        text(g, x - w / 2 + 24, y - 14, name, F_SM, (0.15, 0.08, 0.2, 1), shadow=False)
        have = g.have_for(c)
        if have:
            text(g, x + w / 2 - 22, y - 14, "x%d" % have, F_SM,
                 (0.1, 0.55, 0.15, 1) if have >= c.qty else (0.7, 0.5, 0.1, 1), shadow=False)
        bar(g, x - w / 2 + 24, y - 6, w - 32, 7, c.frac, patience_color(c.frac))
        col((0.93, 0.88, 0.76, 0.96))
        glBegin(GL_TRIANGLES)
        glVertex2f(x - 6, g.H - (y + 8)); glVertex2f(x + 6, g.H - (y + 8)); glVertex2f(x, g.H - (y + 16))
        glEnd()
    cr = g.crow
    if cr and cr.threat:
        sp = project(g, cr.x, cr.y + 0.9, cr.z)
        if sp:
            pulse = 0.6 + 0.4 * math.sin(g.time * 12)
            rrect(g, sp[0] - 34, sp[1] - 30, 68, 34, (1, 0.3, 0.25, 0.9 * pulse + 0.1), 10)
            text(g, sp[0], sp[1] - 12, "CROW!", F_SM, (1, 1, 1, 1), center=True)
            left = 1.0 - (cr.t / cr.STEAL_AFTER if cr.state == "perched" else 0.0)
            bar(g, sp[0] - 28, sp[1] - 7, 56, 6, left, (1, 0.85, 0.3, 1))
    near_c = g.near_cauldron()
    for cau in g.active_cauldrons():
        if cau is near_c:
            continue
        if cau.brewing or cau.dirty:
            sp = project(g, cau.pos[0], 2.7, cau.pos[1])
            if sp:
                if cau.dirty:
                    rrect(g, sp[0] - 50, sp[1] - 16, 100, 20, (0.35, 0.55, 0.15, 0.9), 10)
                    text(g, sp[0], sp[1] - 2, "Needs scrubbing", F_SM, (1, 1, 1, 1), center=True)
                else:
                    rrect(g, sp[0] - 46, sp[1] - 20, 92, 26, (0.1, 0.05, 0.16, 0.8), 10)
                    text(g, sp[0], sp[1] - 7, "Brewing", F_SM, (1, 1, 1, 1), center=True)
                    bar(g, sp[0] - 38, sp[1] - 4, 76, 6, cau.progress, cau.liquid + (1,))
    # station name labels (fade in as Liri gets closer)
    rack_y = 1.75
    stations = [("Cauldron", 0.0, 2.9, -1.5), ("Counter - serve here", 1.0, 1.9, 4.0),
                ("Cauldron 2", CAULDRON2_POS[0], 2.9, CAULDRON2_POS[1]),
                ("Upgrade Desk", DESK_POS[0], 2.0, DESK_POS[1]), ("Herb Garden", -8.65, 1.7, -1.0),
                ("Ingredient Shelf", -4.6, 3.0 if not g.upgrades["shelf"] else 3.9, -7.4),
                ("Potion Rack", RACK_POS[0], rack_y, RACK_POS[1])]
    for (name, x, y, z) in stations:
        if name.startswith("Counter") and q:
            continue
        if name == "Cauldron 2" and not g.upgrades.get("cauldron2"):
            continue                             # customers' bubbles already mark the counter
        d = math.hypot(g.liri.x - x, g.liri.z - z)
        a = clamp((11.0 - d) / 6.0, 0.0, 0.9)
        if a <= 0.02:
            continue
        sp = project(g, x, y, z)
        if not sp:
            continue
        tw = text_w(name, F_SM) + 16
        rrect(g, sp[0] - tw / 2, sp[1] - 15, tw, 20, (0.1, 0.04, 0.16, 0.6 * a), 10)
        text(g, sp[0], sp[1], name, F_SM, (1, 0.93, 0.7, a), center=True)
    # floating texts
    for f in g.floaters:
        s = project(g, f[0], f[1], f[2])
        if s:
            a = clamp(f[5] / 0.6, 0, 1)
            text(g, s[0], s[1], f[3], F_MED, f[4] + (a,) if len(f[4]) == 3 else f[4], center=True)


def hud_play(g):
    W, H = g.W, g.H
    st = g.stage_data
    # --- top-left: day & stage
    panel(g, 12, 12, 400, 108)
    text(g, 24, 36, "Day %d  -  Stage %d: %s" % (g.day, g.stage, st["name"]), F_MED, GOLD)
    v, target = g.goal_progress()
    text(g, 24, 58, "Goal: %s   (%d / %d)" % (g.goal_text(), min(v, target), target), F_SM, (0.9, 1, 0.9, 1))
    bar(g, 24, 66, 376, 9, v / float(target), (0.55, 0.85, 1.0, 1))
    left = st["day_len"] - g.day_time
    f = day_fraction(g)
    text(g, 24, 94, "Time left: %s" % fmt_time(left), F_SM, (1, 0.6, 0.5, 1) if left < 30 else (1, 1, 1, 1))
    phase = "Morning" if f < 0.3 else "Afternoon" if f < 0.7 else "Evening" if f < 0.88 else "Night"
    text(g, 160, 94, phase, F_SM, (1, 0.9, 0.6, 1))
    text(g, 250, 94, "H: help   Esc: pause", F_SM, (0.75, 0.75, 0.85, 1))
    if g.stage == 1:
        text(g, 24, 112, "Move: WASD / arrows    Interact: E    Camera: drag mouse / Z C", F_SM, (1, 0.95, 0.6, 1))

    # --- top-right: gold & reputation
    panel(g, W - 252, 12, 240, 82)
    coin_icon(g, W - 227, 34, 10)
    text(g, W - 210, 40, "Gold: %d" % g.gold, F_MED, GOLD)
    star_icon(g, W - 227, 66, 10, (0.6, 0.9, 1.0, 1))
    text(g, W - 210, 72, "Reputation: %d" % g.rep, F_MED, (0.7, 0.92, 1, 1))
    owned = sum(1 for u in UPGRADES if g.upgrades[u["key"]])
    text(g, W - 236, 88, "Upgrades: %d/%d" % (owned, len(UPGRADES)), F_SM, (0.85, 0.8, 0.95, 1))

    # --- bottom-left: inventory
    ph = 22 + 18 * len(ING_NAMES) + 30
    py = H - ph - 12
    panel(g, 12, py, 260, ph)
    text(g, 24, py + 18, "Ingredients  (cap %d)" % g.capacity, F_SM, GOLD)
    for i, n in enumerate(ING_NAMES):
        y = py + 24 + i * 18
        unlocked = g.unlocked_ing(n)
        c = ING[n]["color"]
        if unlocked and i % 2 == 0:
            rrect(g, 18, y, 248, 17, (1, 1, 1, 0.04), 4)
        rrect(g, 24, y + 2, 12, 12, (c[0], c[1], c[2], 1) if unlocked else (0.3, 0.3, 0.3, 1), 4,
              _shade(c + (1,), -0.35) if unlocked else (0.2, 0.2, 0.2, 1))
        label = "[%d] %s" % (i + 1, n)
        if unlocked:
            cnt = g.inventory[n]
            text(g, 42, y + 13, label, F_SM, (1, 1, 1, 1))
            text(g, 210, y + 13, "%d/%d" % (cnt, g.capacity), F_SM, (1, 0.6, 0.5, 1) if cnt == 0 else (0.9, 1, 0.9, 1))
        else:
            text(g, 42, y + 13, label, F_SM, (0.5, 0.5, 0.55, 1))
            text(g, 195, y + 13, "Stage %d" % ING[n]["stage"], F_SM, (0.5, 0.5, 0.55, 1))
    y = py + 24 + len(ING_NAMES) * 18 + 4
    text(g, 24, y + 12, "Potions %d/%d:" % (g.total_potions(), POTION_CAP), F_SM, GOLD)
    x = 110
    for r in RECIPES:
        k = g.potions[r["name"]]
        if k:
            bottle_icon(g, x, y, r["color"], 0.7)
            text(g, x + 12, y + 13, "%d" % k, F_SM)
            x += 30

    # --- bottom-right: current order & queue
    q = g.queue()
    pw, phh = 300, 112
    px, py2 = W - pw - 12, H - phh - 12
    panel(g, px, py2, pw, phh)
    text(g, px + 12, py2 + 20, "Customer queue: %d/%d" % (len(q), g.max_queue), F_SM, GOLD)
    if q:
        c = q[0]
        r = RECIPE[c.request]
        who = c.name + " (regular)" if c.name else "%s (%s)" % (c.type, CUSTOMER_TYPES[c.type]["difficulty"])
        text(g, px + 12, py2 + 42, who, F_MED, (0.75, 0.88, 1, 1) if c.name else (1, 1, 1, 1))
        bottle_icon(g, px + 12, py2 + 50, r["color"], 1.0)
        want = {"double": "TWO %ss" % c.request, "strong": "a PERFECT %s" % c.request}.get(c.order, c.request)
        text(g, px + 34, py2 + 66, "Wants: %s  (%d g)" % (want, int(r["price"] * CUSTOMER_TYPES[c.type]["mult"])),
             F_SM, (1, 0.7, 0.95, 1) if c.order else (1, 0.95, 0.75, 1))
        text(g, px + 12, py2 + 88, "Patience", F_SM, (0.9, 0.9, 0.9, 1))
        bar(g, px + 76, py2 + 78, pw - 90, 12, c.frac, patience_color(c.frac))
        text(g, px + 12, py2 + 104, " -> ".join(r["seq"]), F_SM, (0.75, 0.75, 0.9, 1))
    else:
        text(g, px + 12, py2 + 50, "No customers right now.", F_SM, (0.8, 0.8, 0.8, 1))
        text(g, px + 12, py2 + 70, "Gather ingredients and brew ahead!", F_SM, (0.8, 0.8, 0.8, 1))

    # --- top-centre layout: fit between the corner panels, otherwise drop below them
    reg_l, reg_r = 424.0, W - 264.0
    avail = reg_r - reg_l
    reg_c = (reg_l + reg_r) / 2.0
    # --- brewing panel (top center)
    c = g.cauldron
    brew_bottom = 0
    if g.near_cauldron() or c.brewing:
        cw = 440
        if cw <= avail:
            cx, oy = reg_c - cw / 2, 0
        else:
            cx, oy = W / 2 - cw / 2, 118
        brew_bottom = 86 + oy
        glPushMatrix()
        glTranslatef(0, -oy, 0)
        panel(g, cx, 12, cw, 74)
        if c.contents:
            seq = " -> ".join(c.contents)
        else:
            q0 = g.queue()
            if q0:
                rq = RECIPE[q0[0].request]
                seq = "(empty)   Order %s = %s" % (short_name(rq["name"]), "  ".join(
                    "[%d] %s" % (ING_NAMES.index(n) + 1, n) for n in rq["seq"]))
            else:
                seq = "(empty)   press 1-8 to add ingredients, R for recipes"
        text(g, cx + 12, 32, "Cauldron: " + seq, F_SM, (1, 1, 1, 1))
        match = None
        for r in RECIPES:
            if g.unlocked_recipe(r["name"]) and r["seq"][:len(c.contents)] == c.contents and c.contents:
                match = r
                break
        if match and not c.brewing:
            ok = match["seq"] == c.contents
            if ok:
                hint = "Ready: %s - press SPACE to stir!" % match["name"]
            else:
                nx = match["seq"][len(c.contents)]
                hint = "Looks like %s... next press [%d] %s" % (match["name"], ING_NAMES.index(nx) + 1, nx)
            text(g, cx + 12, 50, hint, F_SM, (0.6, 1, 0.6, 1) if ok else (0.9, 0.9, 0.6, 1))
        elif c.contents and not c.brewing:
            text(g, cx + 12, 50, "This doesn't match any known recipe - press X to empty it", F_SM, (1, 0.6, 0.5, 1))
        bx, by, bw = cx + 12, 58, cw - 24
        rrect(g, bx, by, bw, 16, (0.12, 0.07, 0.14, 0.95), 8)
        zp = 0.55 + 0.25 * math.sin(g.time * 6) if c.brewing else 0.55
        rrect(g, bx + bw * BONUS_WINDOW[0], by, bw * (BONUS_WINDOW[1] - BONUS_WINDOW[0]), 16,
              (1.0, 0.82, 0.25, zp), 6, (0.85, 0.55, 0.1, zp))
        if c.brewing:
            pw2 = max(10, bw * c.progress)
            lq = c.liquid + (1,)
            rrect(g, bx + 1, by + 3, pw2, 10, _shade(lq, 0.3), 5, _shade(lq, -0.2))
            rrect(g, bx + 3, by + 4, max(2, pw2 - 4), 4, (1, 1, 1, 0.35), 2)
            mx = bx + bw * c.progress
            rrect(g, mx - 3, by - 4, 6, 24, (1, 1, 1, 1), 3, (0.8, 0.8, 0.9, 1))
            if c.stir_tried:
                text(g, bx + bw - 90, by - 4, "PERFECT!" if c.bonus else "stirred", F_SM,
                     GOLD if c.bonus else (0.8, 0.8, 0.8, 1))
        frame(g, bx, by, bw, 16, (1, 1, 1, 0.5))
        glPopMatrix()

    # --- next-step guide banner + off-screen arrow
    gt = g.guide() if g.guide_on else None
    if gt:
        msg = "NEXT:  " + gt[3]
        font, bh = F_MED, 32
        gw = text_w(msg, font) + 44
        if gw > avail:
            font, bh = F_SM, 26
            gw = text_w(msg, font) + 36
        if gw <= avail:
            gcx = reg_c
            gy = (brew_bottom + 8) if brew_bottom else 14
        else:
            gcx = W / 2.0
            gy = max(brew_bottom + 8, 132)
        gx = gcx - gw / 2
        rrect(g, gx + 2, gy + 4, gw, bh, (0, 0, 0, 0.3), bh / 2)
        rrect(g, gx, gy, gw, bh, (0.98, 0.84, 0.35, 0.95), bh / 2, (0.85, 0.6, 0.15, 0.95))
        rframe(g, gx, gy, gw, bh, (1, 1, 1, 0.6), bh / 2, 1.5)
        text(g, gcx, gy + (22 if font == F_MED else 17), msg, font, (0.22, 0.08, 0.2, 1), center=True, shadow=False)
        sp = project(g, gt[0], gt[1], gt[2])
        m = 46
        if sp and not (m < sp[0] < W - m and m < sp[1] < H - m):
            cxs, cys = W / 2.0, H / 2.0
            dx, dy = sp[0] - cxs, sp[1] - cys
            k = min((W / 2.0 - m) / max(1e-3, abs(dx)), (H / 2.0 - m) / max(1e-3, abs(dy)))
            ax, ay = cxs + dx * k, cys + dy * k
            ang = math.atan2(-(dy), dx)
            pul = 1.0 + 0.15 * math.sin(g.time * 6)
            col((1.0, 0.82, 0.25, 0.95))
            glBegin(GL_TRIANGLES)
            for (r_, da) in ((22 * pul, 0.0), (12 * pul, 2.4), (12 * pul, -2.4)):
                glVertex2f(ax + math.cos(ang + da) * r_, (H - ay) + math.sin(ang + da) * r_)
            glEnd()

    # --- combo meter (under gold panel)
    if g.combo >= 1 or g.surge_t > 0:
        cx0, cy0 = W - 252, 102
        panel(g, cx0, cy0, 240, 58, (0.22, 0.06, 0.26, 0.88), (1.0, 0.55, 0.9, 1))
        m = g.combo_mult() * (2 if g.surge_t > 0 else 1)
        pop = 1.0 + 0.35 * g.combo_pop
        stroke_text(g, cx0 + 64, cy0 + 36, "x%g" % m, 26 * pop, (1.0, 0.6, 1.0, 1), 2.6, glow=True, shadow=True)
        if g.combo >= 1:
            text(g, cx0 + 118, cy0 + 24, "COMBO: %d in a row" % g.combo, F_SM, (1, 0.85, 1, 1))
            bar(g, cx0 + 118, cy0 + 32, 108, 8, g.combo_t / COMBO_TIME, (1.0, 0.55, 0.9, 1))
            nxt = {1: "next: x1.5", 2: "next: x2", 3: "x2 (x3 at 5)", 4: "next: x3"}.get(g.combo, "MAX!")
            text(g, cx0 + 118, cy0 + 52, nxt, F_SM, (0.85, 0.75, 0.95, 1))
        else:
            text(g, cx0 + 118, cy0 + 30, "Serve fast in a row", F_SM, (0.85, 0.75, 0.95, 1))
            text(g, cx0 + 118, cy0 + 46, "for a COMBO", F_SM, (0.85, 0.75, 0.95, 1))
    # --- active event chips (under the day panel)
    chips = []
    if g.surge_t > 0:
        chips.append(("Magic surge: gold x2  %s" % fmt_time(g.surge_t), (0.55, 0.25, 0.75, 0.9)))
    if g.rain_t > 0:
        chips.append(("Rain: garden grows 2x  %s" % fmt_time(g.rain_t), (0.25, 0.4, 0.6, 0.9)))
    if g.crow and g.crow.threat:
        chips.append(("Crow on the %s!" % g.crow.src.name, (0.7, 0.2, 0.2, 0.9)))
    for c_ in g.active_cauldrons():
        if c_.dirty:
            chips.append(("Cauldron needs scrubbing (%d/4)" % c_.clean, (0.35, 0.5, 0.15, 0.9)))
    for i, (txt, cc) in enumerate(chips):
        cw_ = text_w(txt, F_SM) + 24
        rrect(g, 14, 130 + i * 28, cw_, 22, cc, 11, _shade(cc, -0.3))
        rframe(g, 14, 130 + i * 28, cw_, 22, (1, 1, 1, 0.35), 11, 1.0)
        text(g, 26, 145 + i * 28, txt, F_SM, (1, 1, 1, 1))
    # --- big event banner
    if g.event_banner:
        title, sub, tl = g.event_banner
        a = clamp(tl / 0.6, 0, 1) * clamp((4.6 - tl) / 0.3 + 0.2, 0, 1)
        by0 = H * 0.30
        sw = max(stroke_w(title) * 34 / 119.05, text_w(sub, F_MED)) + 80
        rrect(g, W / 2 - sw / 2, by0 - 52, sw, 90, (0.12, 0.05, 0.2, 0.8 * a), 20)
        rframe(g, W / 2 - sw / 2, by0 - 52, sw, 90, (1, 0.85, 0.35, a), 20, 2.0)
        stroke_text(g, W / 2, by0, title, 34, (1, 0.88, 0.4, a), 3.0)
        text(g, W / 2, by0 + 26, sub, F_MED, (1, 1, 1, a), center=True)

    # --- bottom-center: interaction prompt
    prompt = interaction_prompt(g)
    if prompt:
        w = text_w(prompt, F_MED) + 40
        bob = 2 * math.sin(g.time * 3)
        panel(g, W / 2 - w / 2, H - 60 + bob, w, 38, (0.16, 0.08, 0.24, 0.9))
        H2 = H + bob
        text(g, W / 2, H2 - 35, prompt, F_MED, (1, 1, 1, 1), center=True)


def stage1_tip(g):
    if g.stage != 1:
        return None
    if g.potions["Healing Potion"] > 0:
        return "Serve the wizard at the counter (walk to it, press E)."
    if g.cauldron.brewing:
        return "Press SPACE when the marker is in the gold zone!"
    if g.cauldron.contents:
        return "Press SPACE at the cauldron to stir and brew."
    if g.inventory["Red Flower"] > 0 and g.inventory["Healing Herb"] > 0:
        return "At the cauldron press 1 (Red Flower) then 2 (Healing Herb)."
    return "Collect a Red Flower and a Healing Herb in the garden (left)."


def interaction_prompt(g):
    n = g.nearest_interactable()
    if not n:
        return ""
    kind, obj = n
    if kind == "source":
        if not g.unlocked_ing(obj.name):
            return "%s - unlocks at Stage %d" % (obj.name, ING[obj.name]["stage"])
        if obj.stock <= 0:
            return "%s is regrowing..." % obj.name
        return "Press E to collect %s  (%d left)" % (obj.name, obj.stock)
    if kind == "crow":
        return "Press E to shoo the crow!"
    if kind == "cauldron" and obj.dirty:
        return "Press E to scrub the cauldron (%d/4)" % obj.clean
    if kind == "cauldron":
        if obj.brewing:
            return "Brewing...  SPACE in the gold zone = Perfect brew"
        if g.cauldron.contents:
            return "1-8 add  |  SPACE / ENTER brew  |  X empty"
        return "Press 1-8 to add ingredients  |  E or R: recipe book"
    if kind == "counter":
        q = g.queue()
        if not q:
            return "The counter - waiting for customers"
        return "Press E or ENTER to serve"
    if kind == "desk":
        return "Press E to open the upgrade book"
    return ""


def hud_toasts(g):
    y = g.H - 80 if g.state == "play" else g.H - 40
    for tst in reversed(g.toasts):
        txt, life, c = tst
        a = clamp(life / 0.5, 0, 1)
        w = text_w(txt, F_MED) + 36
        rrect(g, g.W / 2 - w / 2 + 2, y - 19, w, 28, (0, 0, 0, 0.25 * a), 14)
        rrect(g, g.W / 2 - w / 2, y - 22, w, 28, (0.18, 0.09, 0.26, 0.82 * a), 14, (0.08, 0.03, 0.12, 0.82 * a))
        rframe(g, g.W / 2 - w / 2, y - 22, w, 28, (c[0], c[1], c[2], 0.55 * a), 14, 1.5)
        text(g, g.W / 2, y - 2, txt, F_MED, (c[0], c[1], c[2], a), center=True)
        y -= 32


def hud_recipes(g):
    W, H = g.W, g.H
    normal = [r for r in RECIPES if not r.get("secret")]
    found = [r for r in SECRET_RECIPES if g.unlocked_recipe(r["name"])]
    rumours = [r for r in SECRET_RECIPES if r["name"] not in g.discovered and r["stage"] <= g.stage]
    RH = 38
    rows = len(normal) + len(found)
    h = 96 + RH * rows + (30 + 18 * len(rumours) if rumours else 0) + 36
    w = 600
    x, y = W / 2 - w / 2, max(8, H / 2 - h / 2)
    panel(g, x, y, w, h, (0.96, 0.92, 0.80, 0.97), (0.45, 0.25, 0.1, 1))
    stroke_text(g, W / 2, y + 40, "Grandmother's Recipe Book", 26, (0.38, 0.14, 0.45, 1), 2.4, glow=False, shadow=False)
    text(g, W / 2, y + 62, "At a cauldron, press a number (or click) to add a recipe's ingredients",
         F_SM, (0.35, 0.25, 0.2, 1), center=True, shadow=False)
    yy = y + 74
    num = 0
    for r in normal + found:
        unlocked = g.unlocked_recipe(r["name"])
        if unlocked:
            num += 1
            secret = r.get("secret")
            bg = (1.0, 0.93, 0.75, 0.8) if secret else (1.0, 0.98, 0.9, 0.7)
            button(g, x + 14, yy, w - 28, RH - 4, bg, (lambda i=num - 1: g.load_recipe(i)))
            bottle_icon(g, x + 22, yy + 7, r["color"], 0.95)
            label = ("%d. " % num if num <= 9 else "") + r["name"] + ("   (secret!)" if secret else "")
            text(g, x + 46, yy + 15, label, F_MED, (0.45, 0.2, 0.05, 1) if secret else (0.2, 0.1, 0.25, 1), shadow=False)
            text(g, x + w - 82, yy + 15, "%d gold" % r["price"], F_SM, (0.55, 0.4, 0.05, 1), shadow=False)
            sx = x + 46
            for i, n in enumerate(r["seq"]):
                have = g.inventory[n] > 0
                rrect(g, sx, yy + 21, 9, 9, ING[n]["color"] + (1,), 4)
                lab = n + (" ->" if i < len(r["seq"]) - 1 else "")
                text(g, sx + 12, yy + 30, lab, F_SM, (0.2, 0.2, 0.2, 1) if have else (0.7, 0.2, 0.2, 1), shadow=False)
                sx += text_w(lab, F_SM) + 18
        else:
            text(g, x + 46, yy + 22, "???  (unlocks at Stage %d)" % r["stage"], F_MED, (0.55, 0.5, 0.45, 1), shadow=False)
        yy += RH
    if rumours:
        yy += 8
        text(g, x + 24, yy + 12, "Rumours of secret recipes (%d found of %d) - experiment at the cauldron!"
             % (len(g.discovered), len(SECRET_RECIPES)), F_SM, (0.45, 0.2, 0.5, 1), shadow=False)
        yy += 22
        for r in rumours:
            text(g, x + 34, yy + 10, "- %s" % r["hint"], F_SM, (0.35, 0.3, 0.25, 1), shadow=False)
            yy += 18
    text(g, W / 2, y + h - 12, "R or Esc to close", F_SM, (0.4, 0.3, 0.3, 1), center=True, shadow=False)


def hud_upgrades(g):
    W, H = g.W, g.H
    w, h = 600, 120 + 52 * (len(UPGRADES) + 1)
    x, y = W / 2 - w / 2, H / 2 - h / 2
    panel(g, x, y, w, h, (0.15, 0.08, 0.22, 0.96))
    stroke_text(g, W / 2, y + 44, "Shop Upgrades", 30, GOLD, 2.6)
    text(g, W / 2, y + 56, "Gold: %d   -   press 1-6 or click to buy" % g.gold, F_SM, (0.9, 0.9, 1, 1), center=True)
    yy = y + 74
    items = [(u["name"], u["cost"], u["desc"], g.upgrades[u["key"]]) for u in UPGRADES]
    items.append(("Ingredient Delivery", DELIVERY_COST, "+2 of every unlocked ingredient (repeatable)", False))
    for i, (name, cost, desc, owned) in enumerate(items):
        afford = g.gold >= cost
        bg = (0.2, 0.45, 0.25, 0.6) if owned else ((0.35, 0.22, 0.45, 0.7) if afford else (0.25, 0.2, 0.25, 0.6))
        button(g, x + 14, yy, w - 28, 46, bg, (lambda k=i: g.buy_upgrade(k)), not owned)
        if not owned:
            coin_icon(g, x + w - 122, yy + 23, 7)
        text(g, x + 26, yy + 20, "%d. %s" % (i + 1, name), F_MED, (1, 1, 1, 1))
        text(g, x + 26, yy + 38, desc, F_SM, (0.85, 0.85, 0.95, 1))
        tag = "OWNED" if owned else "%d gold" % cost
        text(g, x + w - 110, yy + 28, tag, F_MED, (0.6, 1, 0.6, 1) if owned else (GOLD if afford else (0.7, 0.5, 0.5, 1)))
        yy += 52
    text(g, W / 2, y + h - 12, "E or Esc to close", F_SM, (0.8, 0.8, 0.9, 1), center=True)


def hud_inventory(g):
    W, H = g.W, g.H
    w, h = 520, 420
    x, y = W / 2 - w / 2, H / 2 - h / 2
    panel(g, x, y, w, h, (0.12, 0.07, 0.18, 0.96))
    stroke_text(g, W / 2, y + 40, "Inventory", 28, GOLD, 2.6)
    yy = y + 56
    text(g, x + 20, yy, "Ingredients", F_MED, (0.9, 0.9, 1, 1))
    yy += 8
    for i, n in enumerate(ING_NAMES):
        unlocked = g.unlocked_ing(n)
        rrect(g, x + 20, yy + 6, 12, 12, ING[n]["color"] + (1,) if unlocked else (0.3, 0.3, 0.3, 1), 4)
        text(g, x + 40, yy + 17, n, F_SM, (1, 1, 1, 1) if unlocked else (0.5, 0.5, 0.5, 1))
        if unlocked:
            bar(g, x + 160, yy + 7, 80, 10, g.inventory[n] / float(g.capacity), ING[n]["color"] + (1,))
            text(g, x + 246, yy + 17, "%d/%d" % (g.inventory[n], g.capacity), F_SM)
        yy += 20
    yy = y + 56
    text(g, x + 300, yy, "Potions", F_MED, (0.9, 0.9, 1, 1))
    yy += 8
    if not g.items:
        text(g, x + 300, yy + 17, "(none yet)", F_SM, (0.7, 0.7, 0.8, 1))
    for it in sorted(g.items, key=lambda it: -it["q"])[:POTION_CAP]:
        r = RECIPE[it["name"]]
        bottle_icon(g, x + 300, yy + 2, r["color"], 0.8)
        text(g, x + 318, yy + 15, short_name(r["name"]) + (" (P)" if it["perfect"] else ""), F_SM)
        qc = (0.4, 0.9, 0.4, 1) if it["q"] > 66 else (1, 0.8, 0.25, 1) if it["q"] > 33 else (1, 0.35, 0.3, 1)
        bar(g, x + 430, yy + 6, 60, 8, it["q"] / 100.0, qc)
        yy += 22
    text(g, x + 300, y + 262, "Potions lose quality after %ds on the rack." % int(FRESH_TIME), F_SM, (0.75, 0.75, 0.85, 1))
    s = g.stats
    yy = y + 270
    text(g, x + 20, yy, "Today", F_MED, (0.9, 0.9, 1, 1))
    lines = ["Orders completed: %d" % s["orders"], "Customers lost: %d" % s["lost"],
             "Gold earned: %d" % s["gold_earned"], "Potions brewed: %d  (perfect %d, failed %d)"
             % (s["brewed"], s["perfect"], s["failed"]), "Ingredients used: %d" % s["consumed"]]
    for i, l in enumerate(lines):
        text(g, x + 30, yy + 22 + i * 18, l, F_SM, (0.9, 0.9, 0.9, 1))
    text(g, W / 2, y + h - 12, "I or Esc to close", F_SM, (0.8, 0.8, 0.9, 1), center=True)


HELP_LINES = [
    ("W A S D / Arrows", "Move Liri (relative to the camera)"),
    ("Mouse drag / Z C", "Rotate camera   (mouse wheel = zoom)"),
    ("E  (hold)", "Collect (hold to keep picking) / serve / upgrades"),
    ("1 - 8", "Add an ingredient to the cauldron"),
    ("Space", "Stir: start brewing, then tap in the GOLD zone"),
    ("Enter", "Brew at the cauldron / serve at the counter"),
    ("X / Backspace", "Empty the cauldron"),
    ("R / I", "Recipe book / inventory"),
    ("Esc", "Pause menu or close a window"),
    ("Combo", "Serve again within 30s to multiply gold (x1.5 / x2 / x3)"),
    ("Events", "Crows, boil-overs, rush hour, rain and magic surges!"),
]


def hud_help(g):
    W, H = g.W, g.H
    w, h = 580, 70 + 24 * len(HELP_LINES) + 88
    x, y = W / 2 - w / 2, H / 2 - h / 2
    panel(g, x, y, w, h, (0.12, 0.07, 0.18, 0.95))
    stroke_text(g, W / 2, y + 40, "How to Run the Shop", 28, GOLD, 2.6)
    for i, (k, d) in enumerate(HELP_LINES):
        yy = y + 62 + i * 24
        kw = text_w(k, F_SM) + 16
        rrect(g, x + 22, yy - 15, kw, 20, (0.95, 0.9, 0.8, 1), 5, (0.7, 0.62, 0.5, 1))
        text(g, x + 30, yy - 1, k, F_SM, (0.2, 0.1, 0.2, 1), shadow=False)
        text(g, x + 210, yy, d, F_SM, (1, 1, 1, 1))
    yy = y + 62 + len(HELP_LINES) * 24 + 6
    text(g, x + 24, yy, "Loop: gather -> brew in order -> serve before patience runs out -> upgrade.",
         F_SM, (0.8, 1, 0.8, 1))
    text(g, x + 24, yy + 18, "Lost? Follow the gold arrow and the NEXT banner at the top of the screen.",
         F_SM, (1, 0.9, 0.6, 1))
    text(g, W / 2, y + h - 12, "Game is paused  -  press H or Esc to start playing", F_SM, GOLD, center=True)


def hud_pause(g):
    W, H = g.W, g.H
    rect(g, 0, 0, W, H, (0, 0, 0, 0.5))
    w, h = 470, 488
    x, y = W / 2 - w / 2, max(8, H / 2 - h / 2)
    panel(g, x, y, w, h, (0.14, 0.08, 0.22, 0.97))
    stroke_text(g, W / 2, y + 48, "Paused", 34, GOLD, 3.0)
    items = [("1", "Resume", lambda: setattr(g, "paused", False)),
             ("2", "Restart day", g.restart_day),
             ("3", "Day-night cycle: %s" % ("ON" if g.day_night else "OFF"),
              lambda: setattr(g, "day_night", not g.day_night)),
             ("4", "Mouse sensitivity: %s" % {0.15: "Low", 0.3: "Medium", 0.5: "High"}.get(g.mouse_sens, "Medium"),
              lambda: g.on_key("4")),
             ("5", "Show FPS: %s" % ("ON" if g.show_fps else "OFF"), lambda: setattr(g, "show_fps", not g.show_fps)),
             ("6", "Cartoon outlines: %s" % ("ON" if g.outlines else "OFF"),
              lambda: setattr(g, "outlines", not g.outlines)),
             ("7", "Guide arrow & next-step hints: %s" % ("ON" if g.guide_on else "OFF"),
              lambda: setattr(g, "guide_on", not g.guide_on)),
             ("8", "Music: %s" % ("ON" if g.music_on else "OFF") + ("" if AUDIO.ok else "  (needs pygame)"),
              lambda: g.on_key("8")),
             ("9", "Sound effects: %s" % ("ON" if g.sfx_on else "OFF") + ("" if AUDIO.ok else "  (needs pygame)"),
              lambda: g.on_key("9")),
             ("0", "Quit (progress saved at the start of each day)", quit_game)]
    for i, (k, label, fn) in enumerate(items):
        yy = y + 62 + i * 41
        button(g, x + 20, yy, w - 40, 34, (0.34, 0.22, 0.46, 0.8), fn)
        text(g, x + 34, yy + 23, "%s.  %s" % (k, label), F_MED if i < 9 else F_SM, (1, 1, 1, 1))


def hud_summary(g):
    W, H = g.W, g.H
    s = g.summary
    st = s["stats"]
    rect(g, 0, 0, W, H, (0, 0, 0, 0.45))
    w, h = 520, 410
    x, y = W / 2 - w / 2, H / 2 - h / 2
    panel(g, x, y, w, h, (0.12, 0.07, 0.18, 0.96))
    title = "Day %d Complete!" % s["day"] if s["success"] else "Day %d Is Over" % s["day"]
    stroke_text(g, W / 2, y + 48, title, 34, GOLD if s["success"] else (1, 0.6, 0.5, 1), 3.0)
    text(g, W / 2, y + 64, "Stage %d: %s  -  %s" % (s["stage"], STAGES[s["stage"] - 1]["name"], s["goal"]),
         F_SM, (0.9, 0.9, 1, 1), center=True)
    for i in range(3):
        on = i < s["stars"]
        sx, sy = W / 2 - 55 + i * 55, y + 102
        sc = 1.0 + (0.08 * math.sin(g.time * 4 + i) if on else 0)
        star_icon(g, sx + 2, sy + 3, 23 * sc, (0, 0, 0, 0.35))
        star_icon(g, sx, sy, 23 * sc, (0.75, 0.5, 0.1, 1) if on else (0.25, 0.2, 0.3, 1))
        star_icon(g, sx, sy, 17 * sc, GOLD if on else (0.35, 0.3, 0.42, 1))
    lines = [("Orders completed", st["orders"]), ("Customers lost", st["lost"]), ("Gold earned", st["gold_earned"]),
             ("Potions brewed", st["brewed"]), ("Perfect brews", st["perfect"]), ("Failed brews", st["failed"]),
             ("Best combo", st.get("best_combo", 0)), ("Secret recipes found", st.get("secrets", 0))]
    for i, (k, v) in enumerate(lines):
        yy = y + 146 + i * 24
        if i % 2 == 0:
            rrect(g, x + 90, yy - 17, w - 180, 22, (1, 1, 1, 0.05), 6)
        text(g, x + 110, yy, k, F_MED, (1, 1, 1, 1))
        text(g, x + w - 140, yy, str(v), F_MED, (1, 0.95, 0.7, 1))
    msg = s["reason"] if not s["success"] else (
        "The Royal Magician is delighted!" if s["stage"] == 5 else "Next: Stage %d - %s" % (s["stage"] + 1, STAGES[s["stage"]]["name"]))
    text(g, W / 2, y + h - 52, msg, F_SM, (0.8, 1, 0.8, 1) if s["success"] else (1, 0.7, 0.6, 1), center=True)
    nxt = "Press ENTER to continue" if s["success"] else "Press ENTER to try the stage again (gold & reputation kept)"
    text(g, W / 2, y + h - 22, nxt, F_MED, GOLD, center=True)
    if g.summary_t > 0.8:
        add_click(g, x, y, w, h, g.next_from_summary)


def hud_title(g):
    W, H = g.W, g.H
    rect(g, 0, 0, W, H, (0.05, 0.0, 0.1, 0.2))
    w, h = 700, 360
    x, y = W / 2 - w / 2, 60
    panel(g, x, y, w, h, (0.14, 0.06, 0.22, 0.82))
    for i in range(14):                                      # twinkling stars around the title
        a = i * math.tau / 14 + g.time * 0.15
        tw = 0.5 + 0.5 * math.sin(g.time * 3 + i * 1.7)
        star_icon(g, W / 2 + math.cos(a) * 320, y + 70 + math.sin(a) * 42, 3 + 3 * tw, (1, 0.9, 0.5, 0.3 + 0.6 * tw))
    stroke_text(g, W / 2, y + 62, "Witch Liri's", 34, (0.85, 0.7, 1.0, 1), 3.0)
    stroke_text(g, W / 2, y + 118, "Magical Potion Shop", 46, GOLD, 4.0)
    text(g, W / 2, y + 150, "One little shop. A thousand magical possibilities.", F_MED, (0.95, 0.9, 1, 1), center=True)
    text(g, W / 2, y + 170, "And a cauldron that doesn't always cooperate.", F_SM, (0.82, 0.76, 0.92, 1), center=True)
    items = [("N", "New Game", g.start_new_game)]
    if g.save_exists:
        items.append(("C", "Continue", g.continue_game))
    items.append(("Esc", "Quit", quit_game))
    for i, (k, label, fn) in enumerate(items):
        yy = y + 190 + i * 46
        button(g, W / 2 - 150, yy, 300, 38, (0.45, 0.25, 0.6, 0.9), fn)
        text(g, W / 2, yy + 25, "[%s]  %s" % (k, label), F_MED, (1, 1, 1, 1), center=True)
    text(g, W / 2, y + h - 18, "WASD/arrows move  |  E interact  |  1-8 ingredients  |  Space stir  |  R recipes",
         F_SM, (0.8, 0.8, 0.9, 1), center=True)


def hud_victory(g):
    W, H = g.W, g.H
    w, h = 680, 200
    x, y = W / 2 - w / 2, 60
    panel(g, x, y, w, h, (0.18, 0.07, 0.26, 0.85))
    stroke_text(g, W / 2, y + 56, "The Kingdom Is Saved!", 40, GOLD, 3.6)
    text(g, W / 2, y + 80, "Liri brewed the Royal Aegis Elixir and restored the protective enchantment.",
         F_SM, (1, 1, 1, 1), center=True)
    text(g, W / 2, y + 102, "She is now the Official Royal Potion Maker of the kingdom!", F_MED, (0.9, 0.85, 1, 1), center=True)
    total = sum(g.stars.values())
    for i in range(5):
        star_icon(g, W / 2 - 100 + i * 50, y + 136, 16, GOLD if g.stars.get(i + 1, 0) > 0 else (0.3, 0.25, 0.35, 1))
    text(g, W / 2, y + 176, "Stars: %d / 15   -   Gold: %d   Reputation: %d   -   ENTER for title" % (total, g.gold, g.rep),
         F_SM, (0.9, 0.9, 0.9, 1), center=True)


# =============================================================================
# SOUND  (procedurally generated - needs numpy + pygame, otherwise silent)
# =============================================================================
class Audio:
    def __init__(self):
        self.ok = False
        self.sfx_on = True
        self.music_on = True
        self.sounds = {}
        self.last = {}
        self.music = None
        self.rain = None

    def start(self):
        try:
            import numpy as np
            import pygame
            pygame.mixer.pre_init(22050, -16, 2, 512)
            pygame.mixer.init()
            rate, _size, ch = pygame.mixer.get_init()
            self.np, self.pg, self.rate, self.ch = np, pygame, rate, ch
            pygame.mixer.set_num_channels(20)
            pygame.mixer.set_reserved(2)               # 0 = music, 1 = rain
            self._build()
            self.ok = True
            self.set_music(self.music_on)
        except Exception as e:                         # no pygame / no audio device
            print("Sound disabled (%s). For sound and music: pip install pygame" % e)
            self.ok = False

    # ---- synthesis helpers
    def _t(self, dur):
        return self.np.arange(int(self.rate * dur)) / float(self.rate)

    def _tone(self, f0, dur, f1=None, vol=0.5, decay=6.0, attack=0.005, harm=0.25, wave="sine"):
        np = self.np
        t = self._t(dur)
        f = np.linspace(f0, f1 if f1 else f0, len(t))
        ph = 2 * np.pi * np.cumsum(f) / self.rate
        if wave == "tri":
            w = 2 / np.pi * np.arcsin(np.sin(ph))
        elif wave == "square":
            w = np.tanh(np.sin(ph) * 4) * 0.6
        else:
            w = np.sin(ph) + harm * np.sin(2 * ph)
        env = np.minimum(1.0, t / max(attack, 1e-4)) * np.exp(-decay * t)
        return w * env * vol

    def _noise(self, dur, vol=0.3, decay=8.0, smooth=6):
        np = self.np
        n = np.random.uniform(-1, 1, int(self.rate * dur))
        if smooth > 1:
            n = np.convolve(n, np.ones(smooth) / smooth, mode="same")
        t = self._t(dur)
        return n * np.exp(-decay * t) * vol

    def _cat(self, *parts, gap=0.0):
        np = self.np
        out = []
        for p in parts:
            out.append(p)
            if gap:
                out.append(np.zeros(int(self.rate * gap)))
        return np.concatenate(out)

    def _add(self, *parts):
        n = max(len(p) for p in parts)
        out = self.np.zeros(n)
        for p in parts:
            out[:len(p)] += p
        return out

    def _mix(self, base, part, at):
        i = int(at * self.rate)
        end = min(len(base), i + len(part))
        if i < len(base):
            base[i:end] += part[:end - i]
        return base

    def _snd(self, a):
        np = self.np
        a = np.clip(a, -1, 1)
        pcm = (a * 32000).astype(np.int16)
        if self.ch > 1:
            pcm = np.ascontiguousarray(np.repeat(pcm[:, None], self.ch, axis=1))
        return self.pg.sndarray.make_sound(pcm)

    def _build(self):
        np = self.np
        T = self._tone
        S = self.sounds
        S["coin"] = self._snd(self._cat(T(1318, 0.07, vol=0.35, decay=20), T(1760, 0.35, vol=0.4, decay=9)))
        S["pickup"] = self._snd(T(660, 0.16, 990, vol=0.35, decay=18))
        S["splash"] = self._snd(self._add(self._noise(0.25, 0.45, 14, 12), T(320, 0.15, 180, vol=0.2, decay=20)))
        S["bubble"] = self._snd(T(220, 0.09, 560, vol=0.25, decay=25, harm=0))
        sp = np.zeros(int(self.rate * 0.4))
        for i, f in enumerate((1800, 2400, 2100, 2900, 3300)):
            sp = self._mix(sp, T(f, 0.12, vol=0.18, decay=30, harm=0), i * 0.05)
        S["sparkle"] = self._snd(sp)
        su = np.zeros(int(self.rate * 0.7))
        for i, f in enumerate((523, 659, 784, 1046)):
            su = self._mix(su, T(f, 0.35, vol=0.3, decay=9), i * 0.08)
        S["success"] = self._snd(su)
        S["fail"] = self._snd(self._add(T(320, 0.5, 110, vol=0.35, decay=4, wave="square"), self._noise(0.5, 0.1, 6)))
        S["deny"] = self._snd(self._cat(T(190, 0.09, vol=0.3, decay=12, wave="square"),
                                        T(150, 0.12, vol=0.3, decay=12, wave="square"), gap=0.03))
        bell = self._add(T(880, 1.3, vol=0.3, decay=3.5, harm=0), T(880 * 2.76, 1.0, vol=0.12, decay=5, harm=0),
                         T(1320, 1.1, vol=0.12, decay=4, harm=0))
        S["bell"] = self._snd(bell)
        S["angry"] = self._snd(T(160, 0.3, 95, vol=0.35, decay=6, wave="square"))
        for lvl in range(2, 6):
            c = np.zeros(int(self.rate * 0.5))
            base = 523 * (2 ** ((lvl - 2) * 2 / 12.0))
            for i, k in enumerate((1.0, 1.26, 1.5)):
                c = self._mix(c, T(base * k, 0.25, vol=0.25, decay=10), i * 0.06)
            S["combo%d" % lvl] = self._snd(c)
        caw = self._add(self._noise(0.22, 0.5, 6, 3) * np.sin(2 * np.pi * 620 * self._t(0.22)),
                        T(700, 0.22, 450, vol=0.2, decay=6, wave="square"))
        S["caw"] = self._snd(self._cat(caw, caw * 0.8, gap=0.08))
        boil = self._noise(0.9, 0.35, 2.5, 40)
        for i in range(7):
            boil = self._mix(boil, T(random.uniform(150, 300), 0.08, random.uniform(350, 600), vol=0.2, decay=25, harm=0), i * 0.11)
        S["boil"] = self._snd(boil)
        S["event"] = self._snd(self._cat(T(784, 0.25, vol=0.3, decay=6), T(1175, 0.6, vol=0.3, decay=4)))
        sc = np.zeros(int(self.rate * 0.3))
        for i in range(3):
            sc = self._mix(sc, self._noise(0.07, 0.35, 20, 2), i * 0.09)
        S["scrub"] = self._snd(sc)
        fan = np.zeros(int(self.rate * 1.4))
        for i, f in enumerate((523, 659, 784)):
            fan = self._mix(fan, T(f, 0.25, vol=0.28, decay=8, wave="tri"), i * 0.13)
        fan = self._mix(fan, self._add(T(1046, 0.9, vol=0.3, decay=3, wave="tri"), T(1318, 0.9, vol=0.18, decay=3, harm=0)), 0.42)
        S["fanfare"] = self._snd(fan)
        # rain: soft filtered noise loop
        rn = np.random.uniform(-1, 1, int(self.rate * 2.0))
        rn = np.convolve(rn, np.ones(9) / 9, mode="same") * 0.35
        rn[:200] *= np.linspace(0, 1, 200)
        rn[-200:] *= np.linspace(1, 0, 200)
        self.rain = self._snd(rn)
        self.music = self._snd(self._music())

    def _music(self):
        """A gentle 3/4 shop waltz: C - Am - F - G, bass + plucked chords + melody."""
        np = self.np
        beat = 60.0 / 112
        prog = [(261.6, (0, 4, 7)), (220.0, (0, 3, 7)), (174.6, (0, 4, 7)), (196.0, (0, 4, 7))]
        bars = []
        for root, tri in prog:
            bars += [(root, tri)] * 2
        total = len(bars) * 3 * beat
        buf = np.zeros(int(self.rate * total) + self.rate)
        rnd = random.Random(3)
        scale = [0, 2, 4, 7, 9, 12, 14, 16]
        T = self._tone
        for b, (root, tri) in enumerate(bars):
            t0 = b * 3 * beat
            buf = self._mix(buf, T(root / 2, beat * 2.5, vol=0.22, decay=1.6, wave="tri"), t0)
            for k in (1, 2):
                for semi in tri:
                    buf = self._mix(buf, T(root * 2 ** (semi / 12.0), beat * 0.9, vol=0.06, decay=5, harm=0.1), t0 + k * beat)
            for k in range(3):
                if rnd.random() < 0.75:
                    semi = rnd.choice(scale)
                    f = root * 2 * 2 ** (semi / 12.0)
                    buf = self._mix(buf, T(f, beat * 1.2, vol=0.11, decay=3.2, wave="tri"), t0 + k * beat)
        buf = buf[:int(self.rate * total)]
        fade = int(self.rate * 0.02)
        buf[:fade] *= np.linspace(0, 1, fade)
        buf[-fade:] *= np.linspace(1, 0, fade)
        return buf / max(1e-6, float(np.abs(buf).max())) * 0.7

    # ---- playback
    def play(self, name, level=None, quiet=False):
        if not self.ok or not self.sfx_on:
            return
        if name == "combo":
            name = "combo%d" % clamp(level or 2, 2, 5)
        snd = self.sounds.get(name)
        if snd is None:
            return
        now = time.perf_counter()
        if now - self.last.get(name, 0) < 0.06:
            return
        self.last[name] = now
        try:
            ch = self.pg.mixer.find_channel(True)
            if ch:
                ch.set_volume(0.35 if quiet else 0.9)
                ch.play(snd)
        except Exception:
            pass

    def set_music(self, on):
        self.music_on = on
        if not self.ok:
            return
        try:
            ch = self.pg.mixer.Channel(0)
            if on:
                if not ch.get_busy():
                    ch.set_volume(0.35)
                    ch.play(self.music, loops=-1)
            else:
                ch.stop()
        except Exception:
            pass

    def update(self, g):
        if not self.ok:
            return
        try:
            k = rain_strength(g) if self.sfx_on else 0.0
            ch = self.pg.mixer.Channel(1)
            if k > 0.01:
                if not ch.get_busy():
                    ch.play(self.rain, loops=-1)
                ch.set_volume(0.55 * k)
            elif ch.get_busy():
                ch.stop()
        except Exception:
            pass


AUDIO = Audio()


def sfx(name, level=None, quiet=False):
    AUDIO.play(name, level, quiet)


# =============================================================================
# GLUT CALLBACKS / MAIN LOOP
# =============================================================================
GAME = None
_last_t = None
_fps_acc = [0, 0.0]


def quit_game():
    os._exit(0)


def init_gl():
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glEnable(GL_LIGHT1)
    glEnable(GL_LIGHT2)
    glEnable(GL_COLOR_MATERIAL)
    glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
    glEnable(GL_NORMALIZE)
    glShadeModel(GL_SMOOTH)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, (0.15, 0.15, 0.15, 1))
    glMaterialf(GL_FRONT_AND_BACK, GL_SHININESS, 20.0)
    glLightModeli(GL_LIGHT_MODEL_TWO_SIDE, GL_TRUE)
    glEnable(GL_FOG)
    glFogi(GL_FOG_MODE, GL_LINEAR)
    glFogf(GL_FOG_START, 35.0)
    glFogf(GL_FOG_END, 120.0)
    glHint(GL_POINT_SMOOTH_HINT, GL_NICEST)
    glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
    glHint(GL_PERSPECTIVE_CORRECTION_HINT, GL_NICEST)
    try:
        glLightModeli(GL_LIGHT_MODEL_COLOR_CONTROL, GL_SEPARATE_SPECULAR_COLOR)
    except Exception:
        pass
    glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
    glTexEnvi(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_MODULATE)
    build_textures()
    try:
        glEnable(GL_MULTISAMPLE)
    except Exception:
        pass


def display():
    global _last_t
    now = time.perf_counter()
    dt = 0.016 if _last_t is None else min(0.05, now - _last_t)
    _last_t = now
    _fps_acc[0] += 1
    _fps_acc[1] += dt
    if _fps_acc[1] >= 0.5:
        GAME.fps = _fps_acc[0] / _fps_acc[1]
        _fps_acc[0], _fps_acc[1] = 0, 0.0
    GAME.update(dt)
    AUDIO.update(GAME)
    render_world(GAME)
    render_hud(GAME)
    glutSwapBuffers()


def idle():
    glutPostRedisplay()


def reshape(w, h):
    GAME.W, GAME.H = max(1, w), max(1, h)
    glViewport(0, 0, GAME.W, GAME.H)


def _key_str(key):
    if isinstance(key, bytes):
        return key.decode("latin-1").lower()
    return str(key).lower()


def keyboard(key, x, y):
    GAME.on_key(_key_str(key))


def keyboard_up(key, x, y):
    GAME.on_key_up(_key_str(key))


SPECIAL_MAP = {GLUT_KEY_LEFT: "left", GLUT_KEY_RIGHT: "right", GLUT_KEY_UP: "up", GLUT_KEY_DOWN: "down"}


def special(key, x, y):
    if key in SPECIAL_MAP:
        GAME.special.add(SPECIAL_MAP[key])


def special_up(key, x, y):
    if key in SPECIAL_MAP:
        GAME.special.discard(SPECIAL_MAP[key])


def mouse(button, state, x, y):
    g = GAME
    if button == 3 and state == GLUT_DOWN:
        g.cam_dist = clamp(g.cam_dist - 0.8, 5.0, 18.0)
        return
    if button == 4 and state == GLUT_DOWN:
        g.cam_dist = clamp(g.cam_dist + 0.8, 5.0, 18.0)
        return
    if button in (GLUT_LEFT_BUTTON, GLUT_RIGHT_BUTTON):
        if state == GLUT_DOWN:
            if button == GLUT_LEFT_BUTTON:
                for (rx, ry, rw, rh, fn) in reversed(g.click_rects):
                    if rx <= x <= rx + rw and ry <= y <= ry + rh:
                        fn()
                        return
            g.mouse_down = True
            g.mouse_last = (x, y)
        else:
            g.mouse_down = False


def passive_motion(x, y):
    GAME.mouse_pos = (x, y)


def motion(x, y):
    g = GAME
    g.mouse_pos = (x, y)
    if not g.mouse_down or g.state not in ("play",) or g.paused:
        g.mouse_last = (x, y)
        return
    dx = x - g.mouse_last[0]
    dy = y - g.mouse_last[1]
    g.mouse_last = (x, y)
    g.cam_yaw -= dx * g.mouse_sens * 0.02
    g.cam_pitch = clamp(g.cam_pitch + dy * g.mouse_sens * 0.02, 0.12, 1.35)


def main():
    global GAME
    glutInit(sys.argv)
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGBA | GLUT_DEPTH | GLUT_MULTISAMPLE)
    glutInitWindowSize(WIN_W, WIN_H)
    glutInitWindowPosition(60, 40)
    glutCreateWindow(TITLE)
    GAME = Game()
    init_gl()
    AUDIO.start()
    glutIgnoreKeyRepeat(1)
    glutDisplayFunc(display)
    glutIdleFunc(idle)
    glutReshapeFunc(reshape)
    glutKeyboardFunc(keyboard)
    glutKeyboardUpFunc(keyboard_up)
    glutSpecialFunc(special)
    glutSpecialUpFunc(special_up)
    glutMouseFunc(mouse)
    glutMotionFunc(motion)
    glutPassiveMotionFunc(passive_motion)
    glutMainLoop()


if __name__ == "__main__":
    main()