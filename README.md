# 🧙‍♀️ Witch Liri's Magical Potion Shop

*One little shop. A thousand magical possibilities. And a cauldron that doesn't always cooperate.*

A 3D potion-crafting and time-management game written in **Python + PyOpenGL**. You play as Liri, a young witch who inherits her grandmother's nearly bankrupt potion shop. Gather magical ingredients, brew potions in the right order, serve impatient customers before they storm out, and rebuild the shop until the kingdom names you its **Official Royal Potion Maker**.

Every model in the game (characters, furniture, cauldrons, plants and crystals) is built from geometric primitives. Characters are animated with hierarchical transformations, and all textures, sound effects and music are generated in code. The whole game is a **single Python file** with no asset files.

📄 **[Read the full game description with screenshots](Liris_Potion_Shop.pdf)**

---

## ✨ Features

- **Brew potions:** gather flowers, herbs, mushrooms and crystals, then add them to the cauldron in the correct order. Tap SPACE in the gold zone while stirring for a **Perfect brew**.
- **Customers with personalities:** Village Wizards, Fairies, Adventurers, Impatient Witches and the Royal Magician, each with their own patience meter.
- **Returning regulars:** Sir Bram, Old Fennick, Pip and Madame Hazel come back across the days and continue their own little stories.
- **Combos:** serve customers quickly in a row to multiply your gold (×1.5 → ×2 → ×3).
- **Special orders:** "PERFECT" orders need a perfect brew, and "2×" orders want two potions.
- **Random events:** a crow that steals ingredients, a cauldron that boils over, rush hour, rain that speeds up the garden, and magic surges that double your gold.
- **Secret recipes:** five hidden potions to discover by experimenting, with rumours in the recipe book as clues.
- **Shop upgrades:** bigger shelves, a faster cauldron, a magical garden, more customer space, enchanted decorations and a **second cauldron**.
- **Potion freshness:** potions lose quality if they sit on the rack too long, so you can't just stockpile.
- **Five stages** leading to a royal commission and a fireworks ending.
- **Friendly for new players:** a gold guide arrow and a "NEXT" banner (which can be turned off) always show what to do next.

## 🎨 Graphics & sound

- Low-poly 3D shop with procedurally generated wood, plaster and grass textures
- Day-to-night cycle with a moving sun, moon, stars, drifting clouds and sunbeams through the windows
- Cartoon outlines, soft shadows and glowing particle effects
- Rounded, animated interface with a combo meter, event banners and speech bubbles
- Procedurally generated sound effects and a looping waltz soundtrack (via pygame)

## 🚀 Getting started

**Requirements:** Python 3.8+

```bash
pip install PyOpenGL PyOpenGL_accelerate numpy pygame
python witch_liri_potion_shop.py
```

> `pygame` is only used for sound. Without it the game still runs, just silently.
>
> **Windows:** if you see `NullFunctionError: glutInit`, your PyOpenGL install is missing freeglut. Install a PyOpenGL wheel that includes freeglut, or place `freeglut.dll` next to the script.
> **Linux:** `sudo apt install freeglut3-dev`

## 🎮 Controls

| Key | Action |
|---|---|
| **W A S D** / **Arrow keys** | Move Liri |
| **Mouse drag** / **Z C** | Rotate the camera (mouse wheel zooms) |
| **E** | Interact: collect (hold to keep picking), serve, shoo the crow, scrub, open upgrades |
| **1 – 8** | Add an ingredient to the cauldron |
| **Space** | Stir / start brewing, then tap again in the gold zone for a Perfect brew |
| **Enter** | Brew at the cauldron / serve at the counter |
| **X** | Empty the cauldron |
| **R** / **I** / **H** | Recipe book / inventory / help |
| **Esc** | Pause menu (settings, restart day, music & sound) |

## 🧪 How to play

1. **Gather:** collect ingredients from the herb garden and the ingredient shelf.
2. **Brew:** add ingredients in the recipe's order, then stir.
3. **Serve:** hand the right potion to the customer at the counter before their patience runs out.
4. **Earn:** gold and reputation unlock new recipes, customers and stages.
5. **Upgrade:** spend gold at the upgrade desk to grow the shop.

Your progress is saved automatically at the start of each day.

## 🛠️ Built with

- **Python**: game logic and systems
- **PyOpenGL** (GL, GLU, GLUT): 3D rendering, window and input
- **NumPy**: sound synthesis
- **pygame**: audio playback

**Techniques used:** hierarchical modelling and animation, fixed-function lighting with several light sources, display lists, procedural textures, billboarded particle sprites, a back-face outline pass for the cartoon look, clip planes, an orthographic 2D interface layer, circle/box collision, and a state-machine-driven game loop.

## 👩‍💻 Author

**Fariha Tasnim Alam** ([@fariha34](https://github.com/fariha34))
