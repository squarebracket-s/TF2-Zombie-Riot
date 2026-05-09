# Parse all items, weapons and their paps.
import util, vdf, os, subprocess, json
import trimesh, pyrender, PIL
trimesh.util.attach_to_log()
import scipy
import numpy as np
#from modules.gamedata import items_game

# Patch pyassimp to prevent null pointer error
if os.path.isdir("venv/lib/python3.14/site-packages/pyassimp/"):
    util.write("venv/lib/python3.14/site-packages/pyassimp/core.py", util.read("venv/lib/python3.14/site-packages/pyassimp/core.py").replace("""else:
                        setattr(target, name, [obj[i] for i in range(length)])""","""elif obj:
                        setattr(target, name, [obj[i] for i in range(length)])"""))
    from pyassimp import load

CFG_WEAPONS = vdf.loads(util.read("./TF2-Zombie-Riot/addons/sourcemod/configs/zombie_riot/weapons.cfg"))["Weapons"]

"""
TODO
[ ] Weapon Attributes (Clip, reserve, firerate, etc.)
[ ] Tooltip CSS rework as to fit the attributes
[ ] Automatically generated weapon icons... someday.
[ ] Fix: When searching for weapon kit, its weapons may not be shown if the name differs from the kit name
"""

DECOMPILED=[]
class Weapon:
    def __init__(self, weapon_name, weapon_data):
        self._weapon_name,self.name=weapon_name,weapon_name
        self._weapon_data=weapon_data

        if "tags" in weapon_data:
            self.taglist = weapon_data["tags"].split(";")
            if "," in weapon_data["tags"]: self.taglist = weapon_data["tags"].split(",") # crystal shard uses commas instead of semicolons. blame artvin XXX: Source repo issue
            self.tags = " ".join(f"#{tag}" for tag in self.taglist if tag != "" and len(tag)>2)
        else: self.tags = ""; self.taglist=[]

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
            self.lvl = f"<div>Level: {weapon_data["level"]}</div>"
        else:
            self.lvl = ""

        # If weapon uses custom model, fetch source SMD file from bodygroup
        if "model_weapon_override" in weapon_data:
            if weapon_data["model_weapon_override"].startswith("models/zombie_riot/weapons/"):
                pure_filename = weapon_data["model_weapon_override"].split("/")[-1].split(".")[0]
                if (weapon_data["model_weapon_override"] not in DECOMPILED):
                    # Decompile model
                    self.model_path = f"TF2-Zombie-Riot\\{weapon_data["model_weapon_override"]}"
                    subprocess.run(["./CrowbarDecompiler(1.1).exe",self.model_path,"decompiled\\"])
                    DECOMPILED.append(weapon_data["model_weapon_override"])
                    
                    # Generate bodygroup mappings for model
                    qcdata = util.read(f"decompiled/{pure_filename}.qc")
                    bodygroup_idx = 1
                    bodygroup_map = {}
                    for line in qcdata.split("\n"):
                        if line.strip().startswith("studio"):
                            bodygroup_map[2**(bodygroup_idx-1)]=line.split(" ")[-1].strip('"')
                            bodygroup_idx += 1
                    util.write(f"decompiled/{pure_filename}.json", json.dumps(bodygroup_map,indent=2))
                """
                Issues:
                - Objects aren't in frame in the final image
                """
                # Get SMD file
                if "weapon_bodygroup" in weapon_data: self.mdl_bodygroup = weapon_data["weapon_bodygroup"]
                else: self.mdl_bodygroup = "1"
                self.smd_path = "decompiled/"+json.loads(util.read(f"decompiled/{pure_filename}.json"))[self.mdl_bodygroup] # TODO cache
                # load pyassimp & mesh
                with load(self.smd_path) as assimp_scene:
                    assert len(assimp_scene.meshes)
                    assimp_mesh = assimp_scene.meshes[0]
                    assert len(assimp_mesh.vertices)
                trimesh_mesh = trimesh.Trimesh(vertices=assimp_mesh.vertices,faces=assimp_mesh.faces)
                trimesh_mesh.apply_scale(0.1)
                
                # Bounds calculation
                # assimp: yxz?
                longest_side = 0
                max_vals = [0,0,0]
                for n,coordinate in enumerate(trimesh_mesh.bounds[0]):
                    val = abs(coordinate-trimesh_mesh.bounds[1][n])
                    if val > max(max_vals):
                        longest_side = n
                    max_vals[n]=max(max_vals[n],val)
                center = np.mean( np.array(trimesh_mesh.bounds), axis=0 )
                truecenter = np.mean( np.array(trimesh_mesh.vertices), axis=0 )
                if util.LOCAL:
                    print(weapon_name,"----------------------------")
                    print("bounds:",trimesh_mesh.bounds)
                    print("center:",center)
                    print("longest_side:",longest_side)
                    print("max_vals:",max_vals)
                    print("vertices:",len(trimesh_mesh.vertices))
                
                # Pyrender from trimesh
                pyrender_mesh = pyrender.Mesh.from_trimesh(trimesh_mesh)
                scene = pyrender.Scene(bg_color=[180/255, 184/255, 171/255])
                node = pyrender.Node(mesh=pyrender_mesh, matrix=np.eye(4))
                scene.add_node(node)

                # Center object & position camera
                vertical_angle = 35
                offset = np.array([
                    -max_vals[longest_side]*int(longest_side==2),
                    max_vals[longest_side]*(vertical_angle/45), # up/down
                    max_vals[longest_side]*int(longest_side<=1),
                ])
                angle = [
                    -vertical_angle,
                    -90*int(longest_side==2),
                    0,
                ]
                scene.set_pose(node, scipy.spatial.transform.RigidTransform.from_components(
                    translation = -center,
                    rotation = scipy.spatial.transform.Rotation.from_euler("xyz",[0,0,0],degrees=True)
                ).as_matrix())
                camera = pyrender.OrthographicCamera(xmag=1, ymag=1)
                camera_pose = scipy.spatial.transform.RigidTransform.from_components(
                    translation = offset,
                    rotation = scipy.spatial.transform.Rotation.from_euler("xyz",angle,degrees=True)
                )
                scene.add(camera, pose=camera_pose.as_matrix())
                # Render scene
                if longest_side == 2:
                    width,height = max_vals[2], max_vals[1]
                elif longest_side == 1:
                    width,height = max_vals[0], max_vals[1]
                else:
                    width,height = max_vals[0], max_vals[1]
                mult = 100
                r = pyrender.OffscreenRenderer(width*mult, height*mult)
                color, depth = r.render(scene)
                plw = PIL.Image.fromarray(color).convert('RGB')
                if not os.path.isdir("gh-pages/icons"): subprocess.run(["mkdir", "gh-pages/icons"])
                plw.save(f"gh-pages/icons/{self.name}.png")
                self.has_model = True
                #pyrender.Viewer(scene)
                    


    def to_html(self,wcfghidden=True,wtags=None):
        hidden_str = "<i>Hidden</i>\n" if "hidden" in self._weapon_data else ""
        # TODO defaultdict to clean up
        if "model_weapon_override" in self._weapon_data:
            if self._weapon_data["model_weapon_override"].startswith("models/zombie_riot/weapons/"):
                icon = f'<div class="secondary notice"><img src="static/info.svg">Experimental weapon preview</div><img class="weapon_preview" src="icons/{self.name}.png">'
            else:
                icon = ""
        else:
            icon = ""
        context = {
            "name": self.name,
            "data_item": util.fill_template(
                util.read("templates/items/item.html"), 
                {
                    "tags": self.tags,
                    "author": util.apply_morecolors(self.author),
                    "cost": self.cost,
                    "desc": f"{hidden_str}{self.lvl}{util.divfornewline(self.description)}{icon}",
                }    
            ),
            "wtags": wtags or self.tags,
            "wcfghidden": "weapon_cfghidden hidden" if ("hidden" in self._weapon_data) and wcfghidden else ""
        }
        return util.fill_template(util.read("templates/items/item_preview.html"), context)
    

    def paps_to_html(self,wcfghidden=True,wtags=None):
        context = {
            "wtags": wtags or self.tags,
            "wcfghidden": "weapon_cfghidden" if ("hidden" in self._weapon_data) and wcfghidden else "" # paps are hidden by default
        }
        return util.fill_template(self.get_paps_html(), context)
    

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
        for tag in self.taglist:
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
    
class GenericItem:
    def __init__(self, item_data):
        self.is_item_category="enhanceweapon_click" not in item_data and "cost" not in item_data
        self.is_weapon=(("desc" in item_data) or ("author" in item_data)) and not "weaponkit" in item_data
        self.is_weapon_kit="weaponkit" in item_data
        self.is_trophy="desc" in item_data and "visual_desc_only" in item_data
        self.is_category="author" not in item_data and "filter" in item_data and "whiteout" not in item_data
        self.is_text="whiteout" in item_data

def parse():
    util.log("Parsing Weapon List...")

    HTML_WEAPON = ""
    def item_block(key, data, depth, html, tags):
        if "hidden" not in data:
            depth += 1
            contents=""
            for item in data:
                item_data = data[item]
                itm = GenericItem(item_data)
                if itm.is_trophy:
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
                    contents += util.fill_template(util.read("templates/items/item_preview.html"), context)
                elif itm.is_weapon:
                    wep = Weapon(item,item_data)
                    tags=wep.add_global_tags(tags)
                    contents += wep.to_html()
                    contents += wep.paps_to_html()
                elif itm.is_weapon_kit:
                    kit = Weapon(item,item_data)
                    tags=kit.add_global_tags(tags)
                    contents += kit.to_html(wcfghidden=False)

                    # kit items (has pap)
                    def _kitweps():
                        h=""
                        for k,v in item_data.items():
                            if GenericItem(v).is_weapon:
                                kitwep = Weapon(k,v)
                                h += kitwep.to_html(wcfghidden=False, wtags=kit.tags)
                                h += kitwep.paps_to_html(wcfghidden=False, wtags=kit.tags)
                        return h
                    contents += f'<div style="margin-left: 10px;">\n{_kitweps()}</div>\n'
                elif item[0].isupper() and itm.is_category or "Perks" in item and not ("decompile" in util.DEBUG): # unneeded data is always lowercase...
                    contents, tags = item_block(item, item_data, depth, contents, tags)
                elif "Trophies" == item and not ("decompile" in util.DEBUG): # Item
                    contents, tags = item_block(item, item_data, depth, contents, tags)
                elif itm.is_text and not ("decompile" in util.DEBUG): # Text shown in menu
                    contents += f"{item}\n"
            html += f'<details>\n    <summary class="noselect">{key}</summary>{contents}</details>\n'
        return html, tags


    tags = []
    for item_category in CFG_WEAPONS:
        if GenericItem(CFG_WEAPONS[item_category]).is_item_category:
            HTML_WEAPON, tags = item_block(item_category,CFG_WEAPONS[item_category],0, HTML_WEAPON, tags)
    
    if not ("decompile" in util.DEBUG):
        tags_html = "".join([f"<div class=\"btn\" tabindex=\"0\" onclick=\"filter_set_tag('{tag}');\">#{tag}</div>" for tag in tags])
        context = {
            "gtags": tags_html,
            "itemdata": HTML_WEAPON
        }
        util.write("gh-pages/items.html", util.fill_template(util.read("templates/items/items.html"), context))