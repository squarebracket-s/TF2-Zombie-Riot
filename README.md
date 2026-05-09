# tf2_zr_wikigen
*https://artvin01.github.io/TF2-Zombie-Riot/*
Automatic encyclopedia generator for https://github.com/artvin01/TF2-Zombie-Riot.
Icon source: https://github.com/feathericons/feather


# Running locally (Linux)
[Open Asset Import Library (assimp)](https://github.com/assimp/assimp/)
```bash
# Installation
git clone https://github.com/artvin01/TF2-Zombie-Riot -b wiki_gen; cd TF2-Zombie-Riot
python -m venv venv
./venv/bin/pip install -r requirements.txt

git clone https://github.com/artvin01/TF2-Zombie-Riot
# (optional) Decompile weapon models to generate icons
# Dependencies: wine, unzip, assimp (linked above)
wget https://github.com/mrglaster/Source-models-decompiler-cmd/releases/download/Update/CrowbarDecompiler.1.1.zip
unzip CrowbarDecompiler.1.1.zip
SCOPE=items DEBUG=decompile ./venv/bin/python main.py

# Generate wiki
./venv/bin/python main.py
```
All generated files will be put in `gh-pages/`.
Decompiled model files are located in `decompiled/`.

# TODO
- [x] Waveset data
  - [ ] Special wavesets
    - [x] ZR: Survival
    - [x] ZR: Raidrush
    - [x] ZR: Rogue
    - [ ] ZR: Construction
        - [x] Construction 1
        - [ ] Construction 2 (partial support)
    - [x] ZR: Special Maps
- [x] NPC data
  - [ ] Better NPC data parsing
- [x] Item data
  - [x] Items
  - [x] Weapon Paps
  - [x] Trophies
  - [ ] Weapon Attributes (Clip, reserve, firerate, etc.)
- [x] Skilltree data

