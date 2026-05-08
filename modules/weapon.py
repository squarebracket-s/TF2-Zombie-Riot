# Parse all items, weapons and their paps.
import util
import vdf
#from modules.gamedata import items_game

CFG_WEAPONS = vdf.loads(util.read("./TF2-Zombie-Riot/addons/sourcemod/configs/zombie_riot/weapons.cfg"))["Weapons"]

class Weapon:
    def __init__(self, weapon_name, weapon_data, gtags):
        self._weapon_name=weapon_name
        self._weapon_data=weapon_data

        if "tags" in weapon_data:
            taglist = weapon_data["tags"].split(";")
            if "," in weapon_data["tags"]: taglist = weapon_data["tags"].split(",") # crystal shard uses commas instead of semicolons. blame artvin
            self.tags = " ".join(f"#{tag}" for tag in taglist if tag != "" and len(tag)>2)
        else: self.tags = ""

        if "author" in weapon_data: self.author = f"By {weapon_data["author"]}"
        else: self.author = ""

        self.cost = weapon_data["cost"]
        if self.cost=="0": self.cost="Free"

        if "desc" in weapon_data: 
            k = weapon_data["desc"]
            self.description = util.get_key(k)
            self.description = self.description.replace("\\n","\n").replace("\n-","\n - ")
            if self.description.startswith("-"): self.description=" - "+self.description[1:]
        else: self.description = ""

        if "level" in weapon_data:
            self.lvl = f"Level: {weapon_data["level"]}  \n"
        else:
            self.lvl = ""


    def tohtml(self,wcfghidden=True):
        hidden_str = "<i>Hidden</i>\n" if "hidden" in self._weapon_data else ""
        context = {
            "name": self.name,
            "data_item": util.fill_template(
                util.read("templates/items/item.html"), 
                {
                    "tags": self.tags,
                    "author": util.apply_morecolors(self.author),
                    "cost": self.cost,
                    "desc": f"{hidden_str}<div>{self.lvl}</div>{util.divfornewline(self.description)}",
                }    
            ),
            "wtags": self.tags,
            "wcfghidden": "weapon_cfghidden hidden" if ("hidden" in self._weapon_data) and wcfghidden else ""
        }
        return util.fill_template(util.read("templates/items/item_preview.html"), context)
    

    def papstohtml(self,wcfghidden=True):
        context = {
            "wtags": self.tags,
            "wcfghidden": "weapon_cfghidden" if ("hidden" in self._weapon_data) and wcfghidden else "" # paps are hidden by default
        }
        return util.fill_template(wep.get_paps_html(), context)
    

    def get_paps_html(self):
        """
        pap_#_pappaths define how many paps you can choose from below ("2" paths on "PaP 1" allows you to choose between "PaP 2" and "PaP 3")
        pap_#_papskip Skips a number of paps to choose ("1" skip on "PaP 1" allows you to choose "PaP 3" instead)
        """
        pap_idx = 0
        pap_html = ""
        def item_block(parent_pap,idx,html,depth):
            html += f"<div class=\"weapon_pap wcfghidden hidden\" weapon_tags=\"wtags\" style=\"margin-left: {(depth+1)*10}px;\">\n"
            for i in range(int(parent_pap.pappaths)):
                idx += 1
                if int(parent_pap.pappaths)>1:
                    html += f"<i>Path {i+1}</i>\n"
                pd = WeaponPap(self._weapon_name,self._weapon_data,idx,depth)
                if pd.valid:
                    html += pd.to_html()
                    if pd.pappaths!="0": html = item_block(pd, idx+int(pd.papskip), html, depth+1)
            html += "</div>\n"
            return html
        
        if "pappaths" in self._weapon_data: init_pap_paths = self._weapon_data["pappaths"]
        else: init_pap_paths = 1
        pap_html = item_block(WeaponPap_Dummy(init_pap_paths), pap_idx, pap_html, 0)
        if len(pap_html)>0:
            pap_html += "\n"
        return pap_html
    

    def add_global_tags(self, gtags):
        if "tags" in weapon_data:
            taglist = weapon_data["tags"].split(";")
            for tag in taglist:
                if tag.capitalize() not in gtags and tag not in gtags and len(tag)>2: gtags.append(tag)
        return gtags

class WeaponPap:
    def __init__(self, weapon_name, weapon_data, idx, depth):
        self.depth = depth
        pap_key = f"pap_{idx}_"
        key_desc = pap_key+"desc"
        util.debug(f"Parsing {weapon_name} {pap_key}","weaponpap")
        if key_desc in weapon_data:
            key_customname = pap_key + "custom_name"
            if key_customname in weapon_data: self.name = weapon_data[key_customname]
            else: self.name = weapon_name
            
            self.description = weapon_data[key_desc]

            self.cost = weapon_data[pap_key+"cost"]

            if pap_key+"tags" in weapon_data: self.tags = " ".join(f"#{tag}" for tag in weapon_data[pap_key+"tags"].split(";") if tag != "")
            else: self.tags = ""

            # There has got to a better way to do this
            key_papskip = pap_key+"papskip"
            if key_papskip in weapon_data: self.papskip = weapon_data[key_papskip]
            else: self.papskip = "0"

            key_pappaths = pap_key+"pappaths"
            if key_pappaths in weapon_data: self.pappaths = weapon_data[key_pappaths]
            else: self.pappaths = "1"

            key_extra_desc = pap_key+"extra_desc"
            if key_extra_desc in weapon_data: self.extra_desc = weapon_data[key_extra_desc]
            else: self.extra_desc = ""

        self.valid = key_desc in weapon_data

    def to_link(self):
        return f"{" "*self.depth}{self.name}  \n"
    
    def to_html_preview(self):
        if len(self.tags)>0: tags = f"{self.tags}"
        else: tags = ""
        extra_desc = self.extra_desc.replace("\\n","\n") if len(self.extra_desc) > 0 else ""
        desc = util.get_key(self.description).replace("\\n","\n")

        context = {
            "name": self.name,
            "tags": tags,
            "author": "",
            "cost": f"{self.cost}",
            "desc": f"{util.divfornewline(desc)}{util.divfornewline(extra_desc)}",
        }
        return util.fill_template(util.read("templates/items/item.html"), context)
    
    def to_html(self):
        context = { # wtags left out intentionally, it is replaced later
            "name": self.name,
            "data_item": self.to_html_preview()
        }
        return util.fill_template(util.read("templates/items/item_preview.html"), context)

class WeaponPap_Dummy:
    def __init__(self, init_pap_paths):
        self.papskip = "0"
        self.pappaths = init_pap_paths


def parse():
    util.log("Parsing Weapon List...")

    HTML_WEAPON = ""
    
    def is_item_category(c):
        return "enhanceweapon_click" not in c and "cost" not in c


    def is_weapon(c):
        return (("desc" in c) or ("author" in c)) and not "weaponkit" in c


    def is_trophy(c):
        return "desc" in c and "visual_desc_only" in c


    def is_category(c):
        return "author" not in c and "filter" in c and "whiteout" not in c


    def item_block(key,data,depth,html, tags):
        if "hidden" not in data:
            depth += 1
            html += util.fill_template(util.read("templates/items/item_block_start.html"),{"key":key})
            for item in data:
                item_data = data[item]
                if is_trophy(item_data):
                    """
                    "Magia Wings [???]"
                        {
                            "desc"		"Oh how the Stars shine upon those who rule Ruina..." (can be a desc key!)
                            "cost"		"0"
                            "textstore"	"Magia Wings [???]"
                            "visual_desc_only"	"0"
                            "attributes"	"2 ; 1.0"
                            "index"		"2" //0 = primary, 1 = secondary, 2 = melee, 3 = Body, 4 = mage?
                            "slot"		"11" // 11 is cosmetics
                        }
                    """
                    context = {
                        "name": util.get_key(item, silent=True),
                        "data_item": util.divfornewline(util.get_key(item_data["desc"], silent=True)),
                        "wtags": "",
                        "wcfghidden": ""
                    }
                    html += util.fill_template(util.read("templates/items/item_preview.html"), context)
                elif is_weapon(item_data):
                    wep = Weapon(item,item_data)
                    tags=wep.add_global_tags()
                    html += wep.tohtml()
                    html += wep.papstohtml()
                elif "weaponkit" in item_data:
                    kit = Weapon(item,item_data)
                    tags=kit.add_global_tags()
                    html += kit.tohtml(wcfghidden=False)

                    # kit items (has pap)
                    def _kitweps():
                        h=""
                        for k,v in item_data.items():
                            if is_weapon(v):
                                kitwep = Weapon(k,v)
                                h += kitwep.tohtml(wcfghidden=False)
                                h += kitwep.papstohtml(wcfghidden=False)
                        return h
                    html += f'<div style="margin-left: 10px;">\n>{_kitweps()}</div>\n'
                elif item[0].isupper() and is_category(item_data) or "Perks" in item: # unneeded data is always lowercase...
                    html, tags = item_block(item, item_data, depth, html, tags)
                elif "Trophies" == item: # Item
                    html, tags = item_block(item, item_data, depth, html, tags)
                elif "whiteout" in item_data: # Text shown in menu
                    html += item + "\n"
            html += "</details>\n"
        return html, tags


    tags = []
    for item_category in CFG_WEAPONS:
        if is_item_category(CFG_WEAPONS[item_category]):
            HTML_WEAPON, tags = item_block(item_category,CFG_WEAPONS[item_category],0, HTML_WEAPON, tags)
    
    tags_html = "".join([f"<div class=\"btn\" tabindex=\"0\" onclick=\"filter_set_tag('{tag}');\">#{tag}</div>" for tag in tags])
    context = {
        "gtags": tags_html,
        "itemdata": HTML_WEAPON
    }
    util.write("gh-pages/items.html", util.fill_template(util.read("templates/items/items.html"), context))