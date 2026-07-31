import json
import math
import time

from core.chat_blob import ChatBlob
from core.command_param_types import Any, Const, Int, Options
from core.decorators import instance, command
from core.dict_object import DictObject


def to_dict_object(obj):
    if isinstance(obj, dict):
        return DictObject({k: to_dict_object(v) for k, v in obj.items()})
    elif isinstance(obj, list):
        return [to_dict_object(v) for v in obj]
    else:
        return obj


@instance()
class ImplantDesignerController:
    SLOTS = ["head", "eye", "ear", "rarm", "chest", "larm", "rwrist", "waist", "lwrist", "rhand", "legs", "lhand", "feet"]
    GRADES = ["shiny", "bright", "faded"]

    def inject(self, registry):
        self.db = registry.get_instance("db")
        self.text = registry.get_instance("text")
        self.util = registry.get_instance("util")
        self.command_alias_service = registry.get_instance("command_alias_service")
        self.implant_controller = registry.get_instance("implant_controller")

    def start(self):
        self.db.exec("CREATE TABLE IF NOT EXISTS implant_design (name VARCHAR(255) NOT NULL, owner VARCHAR(255) NOT NULL, dt INT NOT NULL, design TEXT NOT NULL)")
        self.command_alias_service.add_alias("impdesign", "implantdesigner")

    @command(command="implantdesigner", params=[], access_level="all",
             description="Show current implant design build")
    def implantdesigner_cmd(self, request):
        blob = self.get_implant_designer_build(request.sender.name)
        return ChatBlob("Implant Designer", blob)

    @command(command="implantdesigner", params=[Const("clear")], access_level="all",
             description="Clear all slots in current implant design build")
    def implantdesigner_clear_cmd(self, request, clear):
        self.save_design(request.sender.name, "@", DictObject({}))
        reply_text = "Implant Designer has been cleared.\n\n" + self.get_implant_designer_build(request.sender.name)
        return ChatBlob("Implant Designer", reply_text)

    @command(command="implantdesigner", params=[Const("results")], access_level="all",
             description="Show summary results of current implant design build")
    def implantdesigner_results_cmd(self, request, results):
        blob = self.get_implant_designer_results(request.sender.name)
        return ChatBlob("Implant Designer Results", blob)

    @command(command="implantdesigner", params=[Options(SLOTS)], access_level="all",
             description="Show or manage a specific implant slot", extended_description="Slot can be head, eye, ear, rarm, chest, larm, rwrist, waist, lwrist, rhand, legs, lhand, or feet.")
    def implantdesigner_slot_cmd(self, request, slot):
        slot = slot.lower()

        blob = self.text.make_tellcmd("See Build", "implantdesigner")
        blob += " <tab> "
        blob += self.text.make_tellcmd("Clear this slot", f"implantdesigner {slot} clear")
        blob += " <tab> "
        blob += self.text.make_tellcmd("Require Ability", f"implantdesigner {slot} require")
        blob += "\n-------------------------\n"
        blob += "<header2>Implants</header2>  "
        for ql in [25, 50, 75, 100, 125, 150, 175, 200, 225, 250, 275, 300]:
            blob += self.text.make_tellcmd(str(ql), f"implantdesigner {slot} {ql}") + " "
        blob += "\n\n" + self.get_symbiants_links(slot)
        blob += "\n-------------------------\n\n"

        design = self.get_design(request.sender.name, "@")
        slot_obj = design.get(slot)

        if slot_obj and slot_obj.get("symb"):
            symb = slot_obj.get("symb")
            symb_name = symb.get("name") if isinstance(symb, dict) else getattr(symb, "name", "")
            blob += f"<highlight>{symb_name}</highlight>\n\n"
            blob += "<header2>Requirements</header2>\n"
            treatment = symb.get("Treatment") if isinstance(symb, dict) else getattr(symb, "Treatment", 0)
            level = symb.get("Level") if isinstance(symb, dict) else getattr(symb, "Level", 0)
            blob += f"Treatment: {treatment}\n"
            blob += f"Level: {level}\n"
            reqs = symb.get("reqs", []) if isinstance(symb, dict) else getattr(symb, "reqs", [])
            for req in reqs:
                req_name = req.get("Name") if isinstance(req, dict) else getattr(req, "Name", "")
                req_amount = req.get("Amount") if isinstance(req, dict) else getattr(req, "Amount", 0)
                blob += f"{req_name}: {req_amount}\n"
            blob += "\n<header2>Modifications</header2>\n"
            mods = symb.get("mods", []) if isinstance(symb, dict) else getattr(symb, "mods", [])
            for mod in mods:
                mod_name = mod.get("Name") if isinstance(mod, dict) else getattr(mod, "Name", "")
                mod_amount = mod.get("Amount") if isinstance(mod, dict) else getattr(mod, "Amount", 0)
                blob += f"{mod_name}: {mod_amount}\n"
            blob += "\n\n"
        else:
            ql = slot_obj.get("ql", 300) if slot_obj else 300
            blob += f"<header2>QL</header2> {ql}"
            shiny = slot_obj.get("shiny", "") if slot_obj else ""
            bright = slot_obj.get("bright", "") if slot_obj else ""
            faded = slot_obj.get("faded", "") if slot_obj else ""
            implant = self.get_implant_info(ql, shiny, bright, faded)
            if implant:
                blob += f" - Treatment: {implant.Treatment} {implant.AbilityName}: {implant.Ability}"
            blob += "\n\n"

            blob += "<header2>Shiny</header2>\n"
            blob += self.show_cluster_choices(design, slot, "shiny")

            blob += "<header2>Bright</header2>\n"
            blob += self.show_cluster_choices(design, slot, "bright")

            blob += "<header2>Faded</header2>\n"
            blob += self.show_cluster_choices(design, slot, "faded")

        return ChatBlob(f"Implant Designer ({slot})", blob)

    @command(command="implantdesigner", params=[Options(SLOTS), Options(GRADES + ["symb"]), Any("value")], access_level="all",
             description="Set cluster or symbiant for a slot")
    def implantdesigner_slot_cluster_cmd(self, request, slot, type_name, value):
        return self.handle_add_cluster_or_symb(request.sender.name, slot.lower(), type_name.lower(), value.strip())

    @command(command="implantdesigner", params=[Options(SLOTS), Int("ql")], access_level="all",
             description="Set quality level for an implant slot")
    def implantdesigner_slot_ql_cmd(self, request, slot, ql):
        return self.handle_set_ql(request.sender.name, slot.lower(), ql)

    @command(command="implantdesigner", params=[Options(SLOTS), Const("clear")], access_level="all",
             description="Clear a specific implant slot")
    def implantdesigner_slot_clear_cmd(self, request, slot, clear):
        return self.handle_clear_slot(request.sender.name, slot.lower())

    @command(command="implantdesigner", params=[Options(SLOTS), Const("require")], access_level="all",
             description="Show available abilities to require for an implant slot")
    def implantdesigner_slot_require_cmd(self, request, slot_param, require):
        slot = slot_param.lower()

        design = self.get_design(request.sender.name, "@")
        slot_obj = design.get(slot)

        if not slot_obj:
            return "You must have at least one cluster filled to require an ability."
        if slot_obj.get("symb"):
            return "You cannot require an ability for a symbiant."
        if not slot_obj.get("shiny") and not slot_obj.get("bright") and not slot_obj.get("faded"):
            return "You must have at least one cluster filled to require an ability."
        if slot_obj.get("shiny") and slot_obj.get("bright") and slot_obj.get("faded"):
            return "You must have at least one empty cluster to require an ability."

        blob = self.text.make_tellcmd("See Build", "implantdesigner")
        blob += " <tab> "
        blob += self.text.make_tellcmd("Clear this slot", f"implantdesigner {slot} clear")
        blob += "\n-------------------------\n\n"
        blob += self.text.make_tellcmd(slot, f"implantdesigner {slot}") + " "
        blob += self.get_implant_summary(slot_obj) + "\n"
        blob += f"Which ability do you want to require for {slot}?\n\n"

        abilities = self.db.query("SELECT Name FROM Ability")
        for row in abilities:
            blob += self.text.make_tellcmd(row.Name, f"implantdesigner {slot} require {row.Name}") + "\n"

        return ChatBlob(f"Implant Designer Require Ability ({slot})", blob)

    @command(command="implantdesigner", params=[Options(SLOTS), Const("require"), Any("ability")], access_level="all",
             description="Require a specific ability for an implant slot")
    def implantdesigner_slot_require_ability_cmd(self, request, slot_param, require, ability):
        return self.handle_require_ability(request.sender.name, slot_param.lower(), ability)

    def handle_set_ql(self, sender_name, slot, ql):
        design = self.get_design(sender_name, "@")
        if slot not in design:
            design[slot] = DictObject({})
        slot_obj = design[slot]
        if "symb" in slot_obj:
            del slot_obj["symb"]
        slot_obj["ql"] = ql
        self.save_design(sender_name, "@", design)

        blob = f"<highlight>{slot}</highlight> has been set to QL <highlight>{ql}</highlight>.\n\n"
        blob += self.get_implant_designer_build(sender_name)
        return ChatBlob("Implant Designer", blob)

    def handle_clear_slot(self, sender_name, slot):
        design = self.get_design(sender_name, "@")
        if slot in design:
            del design[slot]
            self.save_design(sender_name, "@", design)

        blob = f"<highlight>{slot}</highlight> has been cleared.\n\n"
        blob += self.get_implant_designer_build(sender_name)
        return ChatBlob("Implant Designer", blob)

    def handle_add_cluster_or_symb(self, sender_name, slot, type_name, item):
        design = self.get_design(sender_name, "@")
        if slot not in design:
            design[slot] = DictObject({})
        slot_obj = design[slot]

        if type_name == "symb":
            sql = """SELECT s.ID, s.Name, s.TreatmentReq, s.LevelReq
                     FROM Symbiant s
                     JOIN ImplantType i ON s.SlotID = i.ImplantTypeID
                     WHERE i.ShortName = ? AND s.Name = ?"""
            symb_row = self.db.query_single(sql, [slot, item])
            if not symb_row:
                return f"Could not find symbiant <highlight>{item}</highlight>."

            # convert slot to symb
            for g in self.GRADES:
                if g in slot_obj:
                    del slot_obj[g]
            if "ql" in slot_obj:
                del slot_obj["ql"]

            symb = DictObject({
                "name": symb_row.Name,
                "Treatment": symb_row.TreatmentReq,
                "Level": symb_row.LevelReq,
                "reqs": self.db.query("SELECT a.Name, s.Amount FROM SymbiantAbilityMatrix s JOIN Ability a ON s.AbilityID = a.AbilityID WHERE SymbiantID = ?", [symb_row.ID]),
                "mods": self.db.query("SELECT c.LongName AS Name, s.Amount FROM SymbiantClusterMatrix s JOIN Cluster c ON s.ClusterID = c.ClusterID WHERE SymbiantID = ?", [symb_row.ID])
            })
            slot_obj["symb"] = symb
            msg_header = f"<highlight>{slot}(symb)</highlight> has been set to <highlight>{symb.name}</highlight>.\n\n"
        else:
            if item.lower() == "clear":
                if type_name in slot_obj:
                    del slot_obj[type_name]
                    msg_header = f"<highlight>{slot}({type_name})</highlight> has been cleared.\n\n"
                else:
                    msg_header = f"There is no cluster in <highlight>{slot}({type_name})</highlight>.\n\n"
            else:
                slot_obj[type_name] = item
                msg_header = f"<highlight>{slot}({type_name})</highlight> has been set to <highlight>{item}</highlight>.\n\n"

        self.save_design(sender_name, "@", design)

        blob = msg_header + self.get_implant_designer_build(sender_name)
        return ChatBlob("Implant Designer", blob)

    def handle_require_ability(self, sender_name, slot, ability_input):
        ability = self.util.get_ability(ability_input)
        if not ability:
            return f"Unknown ability <highlight>{ability_input}</highlight>."

        design = self.get_design(sender_name, "@")
        slot_obj = design.get(slot)
        if not slot_obj:
            return "You must have at least one cluster filled to require an ability."
        if slot_obj.get("symb"):
            return "You cannot require an ability for a symbiant."
        if not slot_obj.get("shiny") and not slot_obj.get("bright") and not slot_obj.get("faded"):
            return "You must have at least one cluster filled to require an ability."
        if slot_obj.get("shiny") and slot_obj.get("bright") and slot_obj.get("faded"):
            return "You must have at least one empty cluster to require an ability."

        blob = self.text.make_tellcmd("See Build", "implantdesigner")
        blob += " <tab> "
        blob += self.text.make_tellcmd("Clear this slot", f"implantdesigner {slot} clear")
        blob += "\n-------------------------\n\n"
        blob += self.text.make_tellcmd(slot, f"implantdesigner {slot}") + " "
        blob += self.get_implant_summary(slot_obj) + "\n"
        blob += f"Combinations for <highlight>{slot}</highlight> that will require {ability}:\n"

        params = [ability]
        sql = """SELECT
                    i.AbilityQL1, i.AbilityQL200, i.AbilityQL201, i.AbilityQL300,
                    i.TreatQL1, i.TreatQL200, i.TreatQL201, i.TreatQL300,
                    c1.LongName as ShinyEffect,
                    c2.LongName as BrightEffect,
                    c3.LongName as FadedEffect
                FROM ImplantMatrix i
                JOIN Cluster c1 ON i.ShiningID = c1.ClusterID
                JOIN Cluster c2 ON i.BrightID = c2.ClusterID
                JOIN Cluster c3 ON i.FadedID = c3.ClusterID
                JOIN Ability a ON i.AbilityID = a.AbilityID
                WHERE a.Name = ?"""

        if slot_obj.get("shiny"):
            sql += " AND c1.LongName = ?"
            params.append(slot_obj.get("shiny"))
        if slot_obj.get("bright"):
            sql += " AND c2.LongName = ?"
            params.append(slot_obj.get("bright"))
        if slot_obj.get("faded"):
            sql += " AND c3.LongName = ?"
            params.append(slot_obj.get("faded"))

        sql += " ORDER BY c1.LongName, c2.LongName, c3.LongName"

        data = self.db.query(sql, params)
        primary = None
        for row in data:
            results = []
            if not slot_obj.get("shiny"):
                results.append(("shiny", row.ShinyEffect))
            if not slot_obj.get("bright"):
                results.append(("bright", row.BrightEffect))
            if not slot_obj.get("faded"):
                results.append(("faded", row.FadedEffect))

            formatted_results = [
                ("-Empty-" if not item[1] else self.text.make_tellcmd(item[1], f"implantdesigner {slot} {item[0]} {item[1]}"))
                for item in results
            ]

            if formatted_results and formatted_results[0] != primary:
                blob += "\n" + formatted_results[0] + "\n"
                primary = formatted_results[0]
            if len(formatted_results) > 1:
                blob += "<tab>" + formatted_results[1] + "\n"

        return ChatBlob(f"Implant Designer Require {ability} ({slot}) ({len(data)})", blob)

    def get_implant_designer_build(self, sender_name):
        design = self.get_design(sender_name, "@")
        blob = self.text.make_tellcmd("Results", "implantdesigner results")
        blob += " <tab> "
        blob += self.text.make_tellcmd("Clear All", "implantdesigner clear")
        blob += "\n-----------------\n\n"

        for slot in self.SLOTS:
            blob += self.text.make_tellcmd(slot, f"implantdesigner {slot}")
            slot_obj = design.get(slot)
            if slot_obj:
                blob += self.get_implant_summary(slot_obj)
            else:
                blob += "\n"
            blob += "\n"

        return blob

    def get_implant_summary(self, slot_obj):
        if not slot_obj:
            return "\n"

        symb = slot_obj.get("symb")
        if symb:
            symb_name = symb.get("name") if isinstance(symb, dict) else getattr(symb, "name", "")
            return f" {symb_name}\n"

        ql = slot_obj.get("ql", 300)
        shiny = slot_obj.get("shiny", "")
        bright = slot_obj.get("bright", "")
        faded = slot_obj.get("faded", "")

        implant = self.get_implant_info(ql, shiny, bright, faded)
        msg = f" QL{ql}"
        if implant:
            msg += f" - Treatment: {implant.Treatment} {implant.AbilityName}: {implant.Ability}"
        msg += "\n"

        for grade in self.GRADES:
            val = slot_obj.get(grade)
            if not val:
                msg += "  <highlight>-Empty-</highlight>\n"
            else:
                effect_field = f"{grade.capitalize()}EffectTypeID"
                effect_id = getattr(implant, effect_field, None) if implant else None
                mod_amount = self.get_cluster_mod_amount(ql, grade, effect_id) if effect_id else 0
                msg += f"  <highlight>{val}</highlight> ({mod_amount})\n"

        return msg

    def get_cluster_mod_amount(self, ql, grade, effect_id):
        sql = "SELECT ID, Name, MinValLow, MaxValLow, MinValHigh, MaxValHigh FROM EffectTypeMatrix WHERE ID = ?"
        row = self.db.query_single(sql, [effect_id])
        if not row:
            return 0

        if ql < 201:
            min_val, max_val, min_ql, max_ql = row.MinValLow, row.MaxValLow, 1, 200
        else:
            min_val, max_val, min_ql, max_ql = row.MinValHigh, row.MaxValHigh, 201, 300

        mod_amount = self.util.interpolate_value(ql, {min_ql: min_val, max_ql: max_val})
        if mod_amount is None:
            mod_amount = 0

        if grade == "bright":
            mod_amount = round(mod_amount * 0.6)
        elif grade == "faded":
            mod_amount = round(mod_amount * 0.4)

        return int(mod_amount)

    def get_symbiants_links(self, slot):
        artillery = self.text.make_tellcmd("Artillery", f"symb {slot} artillery")
        control = self.text.make_tellcmd("Control", f"symb {slot} control")
        extermination = self.text.make_tellcmd("Extermination", f"symb {slot} extermination")
        infantry = self.text.make_tellcmd("Infantry", f"symb {slot} infantry")
        support = self.text.make_tellcmd("Support", f"symb {slot} support")
        return f"<header2>Symbiants</header2>  {artillery}  {control}  {extermination}  {infantry}  {support}"

    def show_cluster_choices(self, design, slot, grade):
        msg = ""
        slot_obj = design.get(slot)
        if slot_obj and slot_obj.get(grade):
            msg += f" - {slot_obj.get(grade)}"
        msg += "\n"
        msg += self.text.make_tellcmd("-Empty-", f"implantdesigner {slot} {grade} clear") + "\n"

        clusters = self.get_clusters_for_slot(slot, grade)
        for row in clusters:
            msg += self.text.make_tellcmd(row.skill, f"implantdesigner {slot} {grade} {row.skill}") + "\n"
        msg += "\n\n"
        return msg

    def get_implant_designer_results(self, name):
        design = self.get_design(name, "@")

        mods = {}
        reqs = {"Treatment": 0, "Level": 1}
        implants = []
        clusters = []
        symbiants = []

        for slot in self.SLOTS:
            slot_obj = design.get(slot)
            if not slot_obj:
                continue

            if slot_obj.get("symb"):
                symb = slot_obj.get("symb")
                symb_name = symb.get("name") if isinstance(symb, dict) else getattr(symb, "name", "")
                symbiants.append(DictObject({"slot": slot, "name": symb_name}))

                treatment = symb.get("Treatment") if isinstance(symb, dict) else getattr(symb, "Treatment", 0)
                level = symb.get("Level") if isinstance(symb, dict) else getattr(symb, "Level", 0)
                if treatment > reqs["Treatment"]:
                    reqs["Treatment"] = treatment
                if level > reqs["Level"]:
                    reqs["Level"] = level

                reqs_list = symb.get("reqs", []) if isinstance(symb, dict) else getattr(symb, "reqs", [])
                for req in reqs_list:
                    req_name = req.get("Name") if isinstance(req, dict) else getattr(req, "Name", "")
                    req_amount = req.get("Amount") if isinstance(req, dict) else getattr(req, "Amount", 0)
                    current_req = reqs.get(req_name, 0)
                    if req_amount > current_req:
                        reqs[req_name] = req_amount

                mods_list = symb.get("mods", []) if isinstance(symb, dict) else getattr(symb, "mods", [])
                for mod in mods_list:
                    mod_name = mod.get("Name") if isinstance(mod, dict) else getattr(mod, "Name", "")
                    mod_amount = mod.get("Amount") if isinstance(mod, dict) else getattr(mod, "Amount", 0)
                    mods[mod_name] = mods.get(mod_name, 0) + mod_amount
            else:
                ql = slot_obj.get("ql", 300)
                shiny = slot_obj.get("shiny", "")
                bright = slot_obj.get("bright", "")
                faded = slot_obj.get("faded", "")

                implant = self.get_implant_info(ql, shiny, bright, faded)
                if implant:
                    if implant.Treatment > reqs["Treatment"]:
                        reqs["Treatment"] = implant.Treatment
                    ability_req = reqs.get(implant.AbilityName, 0)
                    if implant.Ability > ability_req:
                        reqs[implant.AbilityName] = implant.Ability

                implants.append(DictObject({"ql": ql, "slot": slot}))

                for grade in self.GRADES:
                    cluster_name = slot_obj.get(grade)
                    if cluster_name:
                        effect_field = f"{grade.capitalize()}EffectTypeID"
                        effect_id = getattr(implant, effect_field, None) if implant else None
                        mod_amount = self.get_cluster_mod_amount(ql, grade, effect_id) if effect_id else 0
                        mods[cluster_name] = mods.get(cluster_name, 0) + mod_amount

                        min_ql = self.get_cluster_min_ql(ql, grade)
                        clusters.append(DictObject({"ql": min_ql, "slot": slot, "grade": grade, "name": cluster_name}))

        sorted_mods = sorted(mods.items())
        sorted_clusters = sorted(clusters, key=lambda c: (c.name, self.GRADES.index(c.grade)))

        blob = self.text.make_tellcmd("See Build", "implantdesigner")
        blob += "\n---------\n\n"

        blob += "<header2>Requirements to Equip</header2>\n"
        for req_name, req_amount in reqs.items():
            blob += f"{req_name}: <highlight>{req_amount}</highlight>\n"
        blob += "\n"

        blob += "<header2>Skills Gained</header2>\n"
        for skill_name, skill_amount in sorted_mods:
            blob += f"{skill_name}: <highlight>{skill_amount}</highlight>\n"
        blob += "\n"

        if symbiants:
            blob += "<header2>Symbiants Needed</header2>\n"
            for s in symbiants:
                symb_link = self.text.make_tellcmd(s.name, f"symb {s.name}")
                blob += f"<highlight>{s.slot}</highlight>: {symb_link}\n"
            blob += "\n"

        if implants:
            blob += "<header2>Basic Implants Needed</header2>\n"
            for imp in implants:
                blob += f"<highlight>{imp.slot}</highlight> ({imp.ql})\n"
            blob += "\n"

        if clusters:
            blob += "<header2>Clusters Needed</header2>\n"
            for cl in sorted_clusters:
                blob += f"<highlight>{cl.name}</highlight>, {cl.grade} ({cl.ql}+)\n"

        return blob

    def get_cluster_min_ql(self, ql, grade):
        if ql >= 201:
            if grade == "shiny":
                return max(201, math.floor(ql * 0.86))
            elif grade == "bright":
                return max(201, math.floor(ql * 0.84))
            else:
                return max(201, math.floor(ql * 0.82))
        else:
            if grade == "shiny":
                return math.floor(ql * 0.86)
            elif grade == "bright":
                return math.floor(ql * 0.84)
            else:
                return math.floor(ql * 0.82)

    def get_implant_info(self, ql, shiny, bright, faded):
        sql = """SELECT
                    i.AbilityQL1, i.AbilityQL200, i.AbilityQL201, i.AbilityQL300,
                    i.TreatQL1, i.TreatQL200, i.TreatQL201, i.TreatQL300,
                    c1.EffectTypeID as ShinyEffectTypeID,
                    c2.EffectTypeID as BrightEffectTypeID,
                    c3.EffectTypeID as FadedEffectTypeID,
                    a.Name AS AbilityName
                FROM ImplantMatrix i
                JOIN Cluster c1 ON i.ShiningID = c1.ClusterID
                JOIN Cluster c2 ON i.BrightID = c2.ClusterID
                JOIN Cluster c3 ON i.FadedID = c3.ClusterID
                JOIN Ability a ON i.AbilityID = a.AbilityID
                WHERE c1.LongName = ? AND c2.LongName = ? AND c3.LongName = ?"""

        row = self.db.query_single(sql, [shiny, bright, faded])
        if not row:
            return None

        if ql < 201:
            min_ability, max_ability = row.AbilityQL1, row.AbilityQL200
            min_treat, max_treat = row.TreatQL1, row.TreatQL200
            min_ql, max_ql = 1, 200
        else:
            min_ability, max_ability = row.AbilityQL201, row.AbilityQL300
            min_treat, max_treat = row.TreatQL201, row.TreatQL300
            min_ql, max_ql = 201, 300

        row.Ability = self.util.interpolate_value(ql, {min_ql: min_ability, max_ql: max_ability})
        row.Treatment = self.util.interpolate_value(ql, {min_ql: min_treat, max_ql: max_treat})
        return row

    def get_clusters_for_slot(self, implant_type, cluster_type):
        sql = """SELECT c1.LongName AS skill
                 FROM Cluster c1
                 JOIN ClusterImplantMap c2 ON c1.ClusterID = c2.ClusterID
                 JOIN ClusterType c3 ON c2.ClusterTypeID = c3.ClusterTypeID
                 JOIN ImplantType i ON c2.ImplantTypeID = i.ImplantTypeID
                 WHERE i.ShortName = ? AND c3.Name = ?"""
        return self.db.query(sql, [implant_type.lower(), cluster_type.lower()])

    def get_design(self, sender, name):
        row = self.db.query_single("SELECT design FROM implant_design WHERE owner = ? AND name = ?", [sender, name])
        if not row:
            return DictObject({})
        try:
            return to_dict_object(json.loads(row.design))
        except Exception:
            return DictObject({})

    def save_design(self, sender, name, design):
        json_data = json.dumps(design)
        num_rows = self.db.exec("UPDATE implant_design SET design = ?, dt = ? WHERE owner = ? AND name = ?", [json_data, int(time.time()), sender, name])
        if num_rows == 0:
            self.db.exec("INSERT INTO implant_design (name, owner, dt, design) VALUES (?, ?, ?, ?)", [name, sender, int(time.time()), json_data])
