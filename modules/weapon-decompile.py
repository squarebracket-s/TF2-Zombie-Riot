# Parse all items, weapons and their paps.
import vdf, os, subprocess, json
def read(filename):
    try:
        # Windows-specific fix to: https://stackoverflow.com/questions/9233027/unicodedecodeerror-charmap-codec-cant-decode-byte-x-in-position-y-character
        # no idea if applying encoding="utf-8" everywhere changes anything, better be safe
        if os.name == 'nt':
            with open(filename, 'r', encoding="utf-8") as f:
                return f.read()
        else:
            with open(filename, 'r') as f:
                return f.read()
    except FileNotFoundError:
        return None

def write(filename, val):
    with open(filename, 'w+') as f:
        f.write(str(val))
    return True

CFG_WEAPONS = vdf.loads(read("./TF2-Zombie-Riot/addons/sourcemod/configs/zombie_riot/weapons.cfg"))["Weapons"]

DECOMPILED_MDLS=[]
def decompile_model(path):
    if path.startswith("models/zombie_riot/weapons/"):
        pure_filename = path.split("/")[-1].split(".")[0]
        if (path not in DECOMPILED_MDLS):
            # Decompile model
            model_path = f"TF2-Zombie-Riot/{path}"
            subprocess.run(["./CrowbarDecompiler(1.1).exe",model_path,"decompiled/"])
            DECOMPILED_MDLS.append(path)
            
            # Generate bodygroup mappings for model
            qcdata = read(f"decompiled/{pure_filename}.qc")
            bodygroup_idx = 1
            bodygroup_map = {}
            for line in qcdata.split("\n"):
                if line.strip().startswith("studio"):
                    bodygroup_map[2**(bodygroup_idx-1)]=line.split(" ")[-1].strip('"')
                    bodygroup_idx += 1
            write(f"decompiled/{pure_filename}.json", json.dumps(bodygroup_map,indent=2))

class Weapon:
    def __init__(self, weapon_name, weapon_data):
        self._weapon_name,self.name=weapon_name,weapon_name
        self._weapon_data=weapon_data
        if "model_weapon_override" in weapon_data:
            decompile_model(weapon_data["model_weapon_override"])
        self.get_paps_html()
                    
    def get_paps_html(self):
        """
        pap_#_pappaths define how many paps you can choose from below ("2" paths on "PaP 1" allows you to choose between "PaP 2" and "PaP 3")
        pap_#_papskip Skips a number of paps to choose ("1" skip on "PaP 1" allows you to choose "PaP 3" instead)
        """
        pap_idx = 0
        pap_html = ""
        def item_block(parent_pap,idx):
            for i in range(int(parent_pap.pappaths)):
                idx += 1
                pd = WeaponPap(self._weapon_name,self._weapon_data,idx)
        
        if "pappaths" in self._weapon_data: init_pap_paths = self._weapon_data["pappaths"]
        else: init_pap_paths = 1
        pap_html = item_block(WeaponPap_Dummy(init_pap_paths), pap_idx)

class WeaponPap:
    def __init__(self, weapon_name, weapon_data, idx):
        pap_key = f"pap_{idx}_"
        print(f"Parsing {weapon_name} {pap_key}","weaponpap")
        if f"{pap_key}model_weapon_override" in weapon_data:
            decompile_model(weapon_data[f"{pap_key}model_weapon_override"])

class WeaponPap_Dummy:
    def __init__(self, init_pap_paths):
        self.papskip = "0"
        self.pappaths = init_pap_paths
    
class GenericItem:
    def __init__(self, item_data):
        self.is_item_category="enhanceweapon_click" not in item_data and "cost" not in item_data
        self.is_weapon=(("desc" in item_data) or ("author" in item_data)) and not "weaponkit" in item_data
        self.is_weapon_kit="weaponkit" in item_data
        self.is_category="author" not in item_data and "filter" in item_data and "whiteout" not in item_data

print("Parsing Weapon List...")

def item_block(key, data):
    if "hidden" not in data:
        contents=""
        for item in data:
            item_data = data[item]
            itm = GenericItem(item_data)
            if itm.is_weapon:
                wep = Weapon(item,item_data)
            elif itm.is_weapon_kit:
                kit = Weapon(item,item_data)
                for k,v in item_data.items():
                    if GenericItem(v).is_weapon:
                        kitwep = Weapon(k,v)
            elif item[0].isupper() and itm.is_category: # unneeded data is always lowercase...
                item_block(item, item_data)

for item_category in CFG_WEAPONS:
    if GenericItem(CFG_WEAPONS[item_category]).is_item_category:
        item_block(item_category,CFG_WEAPONS[item_category])