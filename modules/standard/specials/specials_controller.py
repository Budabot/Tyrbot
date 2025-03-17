import math

from core.chat_blob import ChatBlob
from core.decorators import instance, command
from core.command_param_types import Int, Decimal, Item

from core.dict_object import DictObject


@instance()
class SpecialsController:
    def __init__(self):
        pass

    def inject(self, registry):
        self.db = registry.get_instance("db")
        self.text = registry.get_instance("text")
        self.util = registry.get_instance("util")
        self.items_controller = registry.get_instance("items_controller")
        self.command_alias_service = registry.get_instance("command_alias_service")

    def pre_start(self):
        self.db.load_sql_file(self.module_dir + "/" + "weapon_attributes.sql")

    def start(self):
        self.command_alias_service.add_alias("aimshot", "aimedshot")
        self.command_alias_service.add_alias("as", "aimedshot")
        self.command_alias_service.add_alias("inits", "weapon")
        self.command_alias_service.add_alias("init", "weapon")
        self.command_alias_service.add_alias("specials", "weapon")
        self.command_alias_service.add_alias("fling", "flingshot")

    @command(command="aggdef", params=[Decimal("weapon_attack"), Decimal("weapon_recharge"), Int("init_skill")], access_level="all",
             description="Show agg/def information")
    def aggdef_cmd(self, request, weapon_attack, weapon_recharge, init_skill):
        init_result = self.get_init_result(weapon_attack, weapon_recharge, init_skill)

        inits_full_agg = self.get_inits_needed(100, weapon_attack, weapon_recharge)
        inits_neutral = self.get_inits_needed(87.5, weapon_attack, weapon_recharge)
        inits_full_def = self.get_inits_needed(0, weapon_attack, weapon_recharge)

        blob = "Attack: <highlight>%.2f secs</highlight>\n" % weapon_attack
        blob += "Recharge: <highlight>%.2f secs</highlight>\n" % weapon_recharge
        blob += "Init Skill: <highlight>%d</highlight>\n\n" % init_skill

        blob += "You must set your AGG/DEF bar at <highlight>%d%%</highlight> to wield your weapon at 1/1.\n\n" % int(init_result)

        blob += "Init needed for max speed at Full Agg (100%%): <highlight>%d</highlight>\n" % inits_full_agg
        blob += "Init needed for max speed at Neutral (87.5%%): <highlight>%d</highlight>\n" % inits_neutral
        blob += "Init needed for max speed at Full Def (0%%): <highlight>%d</highlight>\n\n" % inits_full_def

        blob += self.get_inits_display(weapon_attack, weapon_recharge) + "\n\n"

        blob += "Note that at the neutral position (87.5%), your attack and recharge time will match that of the weapon you are using.\n\n\n"

        blob += "Based on the !aggdef command from Budabot, which was based upon a RINGBOT module made by NoGoal(RK2) and modified for Budabot by Healnjoo(RK2)"

        return ChatBlob("Agg/Def Results", blob)

    @command(command="aimedshot", params=[Decimal("weapon_attack"), Decimal("weapon_recharge"), Int("aimed_shot_skill")], access_level="all",
             description="Show aimed shot information")
    def aimedshot_cmd(self, request, weapon_attack, weapon_recharge, aimed_shot_skill):
        as_info = self.get_aimed_shot_info(weapon_attack, weapon_recharge, aimed_shot_skill)

        blob = "Attack: <highlight>%.2f secs</highlight>\n" % weapon_attack
        blob += "Recharge: <highlight>%.2f secs</highlight>\n" % weapon_recharge
        blob += "Aimed Shot Skill: <highlight>%d</highlight>\n\n" % aimed_shot_skill

        blob += "Aimed Shot Multiplier: <highlight>1 - %dx</highlight>\n" % as_info.multiplier
        blob += "Aimed Shot Recharge: <highlight>%d secs</highlight>\n\n" % as_info.recharge

        blob += "You need <highlight>%d</highlight> Aimed Shot Skill to cap your recharge at <highlight>%d</highlight> seconds." % (as_info.skill_cap, as_info.hard_cap)

        return ChatBlob("Aimed Shot Results", blob)

    @command(command="brawl", params=[Int("brawl_skill")], access_level="all",
             description="Show brawl information")
    def brawl_cmd(self, request, brawl_skill):
        brawl_info = self.get_brawl_info(brawl_skill)

        blob = "Brawl Skill: <highlight>%d</highlight>\n\n" % brawl_skill

        blob += "Brawl Recharge: <highlight>15 secs</highlight> (constant)\n"
        blob += "Brawl Damage: <highlight> %d - %d (%d)</highlight>\n" % (brawl_info.min_dmg, brawl_info.max_dmg, brawl_info.crit_dmg)
        blob += "Stun Change: <highlight>%d%%</highlight>\n" % brawl_info.stun_chance
        blob += "Stun Duration: <highlight>%d secs</highlight>\n\n" % brawl_info.stun_duration

        blob += "Stun chance is 10% for brawl skill less than 1000 and 20% for brawl skill 1000 or greater.\n"
        blob += "Stun duration is 3 seconds for brawl skill less than 2001 and 4 seconds for brawl skill 2001 or greater.\n\n\n"

        blob += "Based on the !brawl command from Budabot by Imoutochan (RK1)"

        return ChatBlob("Brawl Results", blob)

    @command(command="burst", params=[Decimal("weapon_attack"), Decimal("weapon_recharge"), Int("burst_recharge"), Int("burst_skill")], access_level="all",
             description="Show burst information")
    def burst_cmd(self, request, weapon_attack, weapon_recharge, burst_recharge, burst_skill):
        burst_info = self.get_burst_info(weapon_attack, weapon_recharge, burst_recharge, burst_skill)

        blob = "Attack: <highlight>%.2f secs</highlight>\n" % weapon_attack
        blob += "Recharge: <highlight>%.2f secs</highlight>\n" % weapon_recharge
        blob += "Burst Recharge: <highlight>%d</highlight>\n" % burst_recharge
        blob += "Burst Skill: <highlight>%d</highlight>\n\n" % burst_skill

        blob += "Burst Recharge: <highlight>%d secs</highlight>\n\n" % burst_info.recharge

        blob += "You need <highlight>%d</highlight> Burst Skill to cap your recharge at <highlight>%d secs</highlight>." % (burst_info.skill_cap, burst_info.hard_cap)

        return ChatBlob("Burst Results", blob)

    @command(command="dimach", params=[Int("dimach_skill")], access_level="all",
             description="Show dimach information")
    def dimach_cmd(self, request, dimach_skill):
        dimach_info = self.get_dimach_info(dimach_skill)

        blob = "Dimach Skill: <highlight>%d</highlight>\n\n" % dimach_skill

        blob += "<header2>Martial Artist</header2>\n"
        blob += "Damage: <highlight>%d</highlight>\n" % dimach_info.ma_dmg
        blob += "Recharge: <highlight>%s</highlight>\n\n" % self.util.time_to_readable(dimach_info.ma_recharge)

        blob += "<header2>Keeper</header2>\n"
        blob += "Self Heal: <highlight>%d</highlight>\n" % dimach_info.keeper_heal
        blob += "Recharge: <highlight>5 mins</highlight> (constant)\n\n"

        blob += "<header2>Shade</header2>\n"
        blob += "Damage: <highlight>%d</highlight>\n" % dimach_info.shade_dmg
        blob += "Self Heal: <highlight>%d%%</highlight> * <highlight>%d</highlight> = <highlight>%d</highlight>\n" % \
                (dimach_info.shade_heal_percentage, dimach_info.shade_dmg, round(dimach_info.shade_heal_percentage * dimach_info.shade_dmg / 100))
        blob += "Recharge: <highlight>%s</highlight>\n\n" % self.util.time_to_readable(dimach_info.shade_recharge)

        blob += "<header2>All other professions</header2>\n"
        blob += "Damage: <highlight>%d</highlight>\n" % dimach_info.general_dmg
        blob += "Recharge: <highlight>30 mins</highlight> (constant)\n\n\n"

        blob += "Based on the !dimach command from Budabot by Imoutochan (RK1)"

        return ChatBlob("Dimach Results", blob)

    @command(command="fastattack", params=[Decimal("weapon_attack"), Int("fast_attack_skill")], access_level="all",
             description="Show fast attack information")
    def fastattack_cmd(self, request, weapon_attack, fast_attack_skill):
        fast_attack_info = self.get_fast_attack_info(weapon_attack, fast_attack_skill)

        blob = "Attack: <highlight>%.2f secs</highlight>\n" % weapon_attack
        blob += "Fast Attack Skill: <highlight>%d</highlight>\n\n" % fast_attack_skill

        blob += "Fast Attack Recharge: <highlight>%.2f secs</highlight>\n\n" % fast_attack_info.recharge

        blob += "You need <highlight>%d</highlight> Fast Attack Skill to cap your recharge at <highlight>%.2f secs</highlight>." % (fast_attack_info.skill_cap, fast_attack_info.hard_cap)

        return ChatBlob("Fast Attack Results", blob)

    @command(command="flingshot", params=[Decimal("weapon_attack"), Int("fling_shot_skill")], access_level="all",
             description="Show fling shot information")
    def flingshot_cmd(self, request, weapon_attack, fling_shot_skill):
        fling_shot_info = self.get_fling_shot_info(weapon_attack, fling_shot_skill)

        blob = "Attack: <highlight>%.2f secs</highlight>\n" % weapon_attack
        blob += "Fling Shot Skill: <highlight>%d</highlight>\n\n" % fling_shot_skill

        blob += "Fling Shot Recharge: <highlight>%.2f secs</highlight>\n\n" % fling_shot_info.recharge

        blob += "You need <highlight>%d</highlight> Fling Shot Skill to cap your recharge at <highlight>%.2f secs</highlight>." % (fling_shot_info.skill_cap, fling_shot_info.hard_cap)

        return ChatBlob("Fling Shot Results", blob)

    @command(command="fullauto", params=[Decimal("weapon_attack"), Decimal("weapon_recharge"), Int("full_auto_recharge"), Int("full_auto_skill")], access_level="all",
             description="Show full auto information")
    def fullauto_cmd(self, request, weapon_attack, weapon_recharge, full_auto_recharge, full_auto_skill):
        full_auto_info = self.get_full_auto_info(weapon_attack, weapon_recharge, full_auto_recharge, full_auto_skill)

        blob = "Attack: <highlight>%.2f secs</highlight>\n" % weapon_attack
        blob += "Recharge: <highlight>%.2f secs</highlight>\n" % weapon_recharge
        blob += "Full Auto Recharge: <highlight>%d</highlight>\n" % full_auto_recharge
        blob += "Full Auto Skill: <highlight>%d</highlight>\n\n" % full_auto_skill

        blob += "Full Auto Recharge: <highlight>%d secs</highlight>\n" % full_auto_info.recharge
        blob += "Max Number of Bullets: <highlight>%d</highlight>\n\n" % full_auto_info.max_bullets

        blob += "You need <highlight>%d</highlight> Full Auto Skill to cap your recharge at <highlight>%d secs</highlight>.\n\n" % (full_auto_info.skill_cap, full_auto_info.hard_cap)

        blob += "From <highlight>0 to 10K</highlight> damage, the bullet damage is unchanged.\n"
        blob += "From <highlight>10K to 11.5K</highlight> damage, each bullet damage is halved.\n"
        blob += "From <highlight>11.5K to 15K</highlight> damage, each bullet damage is halved again.\n"
        blob += "<highlight>15K</highlight> is the damage cap."

        return ChatBlob("Full Auto Results", blob)

    @command(command="mafist", params=[Int("ma_skill")], access_level="all",
             description="Show martial arts information")
    def mafist_cmd(self, request, ma_skill):
        ma_info = self.get_martial_arts_info(ma_skill)

        blob = "Martial Arts Skill: <highlight>%d</highlight>\n\n" % ma_skill

        blob += "<header2>Martial Artist</header2>\n"
        blob += "Speed: <highlight>%.2f / %.2f secs</highlight>\n" % (ma_info.ma_speed, ma_info.ma_speed)
        blob += "Damage: <highlight>%d - %d (%d)</highlight>\n\n" % (ma_info.ma_min_dmg, ma_info.ma_max_dmg, ma_info.ma_crit_dmg)

        blob += "<header2>Shade</header2>\n"
        blob += "Speed: <highlight>%.2f / %.2f secs</highlight>\n" % (ma_info.shade_speed, ma_info.shade_speed)
        blob += "Damage: <highlight>%d - %d (%d)</highlight>\n\n" % (ma_info.shade_min_dmg, ma_info.shade_max_dmg, ma_info.shade_crit_dmg)

        blob += "<header2>All other professions</header2>\n"
        blob += "Speed: <highlight>%.2f / %.2f secs</highlight>\n" % (ma_info.gen_speed, ma_info.gen_speed)
        blob += "Damage: <highlight>%d - %d (%d)</highlight>\n\n" % (ma_info.gen_min_dmg, ma_info.gen_max_dmg, ma_info.gen_crit_dmg)

        return ChatBlob("Martial Arts Results", blob)

    @command(command="nanoinit", params=[Decimal("nano_attack_time"), Int("nano_cast_init")], access_level="all",
             description="Show nano cast init information")
    def nanoinit_cmd(self, request, nano_attack_time, nano_cast_init):
        nano_cast_info = self.get_nano_cast_info(nano_cast_init, nano_attack_time)

        blob = "Attack: <highlight>%.2f secs</highlight>\n" % nano_attack_time
        blob += "Nano Cast Init: <highlight>%d</highlight>\n\n" % nano_cast_init

        blob += "Cast Time Reduction: <highlight>%.2f</highlight>\n" % nano_cast_info.cast_time_reduction
        blob += "Effective Cast Time: <highlight>%.2f</highlight>\n\n" % nano_cast_info.effective_cast_time

        if nano_cast_info.bar_setting > 100:
            blob += "You cannot instacast this nano at any AGG/DEF setting.\n\n"
        else:
            blob += "You must set your AGG/DEF bar to <highlight>%d%%</highlight> to instacast this nano.\n\n" % nano_cast_info.bar_setting

        blob += "NanoC. Init needed to instacast at Full Agg (100%%): <highlight>%d</highlight>\n" % nano_cast_info.instacast_full_agg
        blob += "NanoC. Init needed to instacast at Neutral (87.5%%): <highlight>%d</highlight>\n" % nano_cast_info.instacast_neutral
        blob += "NanoC. Init needed to instacast at Half (50%%): <highlight>%d</highlight>\n" % nano_cast_info.instacast_half
        blob += "NanoC. Init needed to instacast at Full Def (0%%): <highlight>%d</highlight>\n\n" % nano_cast_info.instacast_full_def

        blob += "Cast time at Full Agg (100%%): <highlight>%.2f</highlight>\n" % nano_cast_info.cast_time_full_agg
        blob += "Cast time at Neutral (87.5%%): <highlight>%.2f</highlight>\n" % nano_cast_info.cast_time_neutral
        blob += "Cast time at Half (50%%): <highlight>%.2f</highlight>\n" % nano_cast_info.cast_time_half
        blob += "Cast time at Full Def (0%%): <highlight>%.2f</highlight>" % nano_cast_info.cast_time_full_def

        return ChatBlob("Nano Cast Init Results", blob)

    @command(command="weapon", params=[Int("item_id"), Int("ql", is_optional=True)], access_level="all",
             description="Show weapon information")
    def weapon_cmd(self, request, item_id, ql):
        return self.get_weapon_info(item_id, ql)

    @command(command="weapon", params=[Item("weapon_link")], access_level="all",
             description="Show weapon information")
    def weapon_cmd(self, request, item):
        return self.get_weapon_info(item.high_id, item.ql)

    @command(command="weapon", params=[Int("item_id"), Int("ql", is_optional=True)], access_level="all",
             description="Show weapon information")
    def weapon_manual_cmd(self, request, item_id, ql):
        if not ql:
            item = self.items_controller.get_by_item_id(item_id)
            if item:
                ql = item.highql
            else:
                return "Could not find item with id <highlight>%d</highlight>." % item_id

        return self.get_weapon_info(item_id, ql)

    def get_weapon_info(self, item_id, ql):
        if ql:
            item = self.db.query_single(
                "SELECT * FROM aodb WHERE highid = ? AND lowql <= ? AND highql >= ? "
                "UNION "
                "SELECT * FROM aodb WHERE lowid = ? AND lowql <= ? AND highql >= ? "
                "LIMIT 1", [item_id, ql, ql, item_id, ql, ql])
        else:
            item = self.db.query_single("SELECT * FROM aodb WHERE highid = ? UNION SELECT * FROM aodb WHERE lowid = ? LIMIT 1", [item_id, item_id])

        if not item:
            return "Could not find item with ID <highlight>%d</highlight>." % item_id

        ql = ql or item.highql

        low_attributes = self.db.query_single("SELECT * FROM weapon_attributes WHERE id = ?", [item.lowid])
        high_attributes = self.db.query_single("SELECT * FROM weapon_attributes WHERE id = ?", [item.highid])

        if not low_attributes or not high_attributes:
            return "Could not find weapon information or item is not a weapon for ID <highlight>%d</highlight>." % item_id

        weapon_attack = self.util.interpolate_value(ql, {item.lowql: low_attributes.attack_time, item.highql: high_attributes.attack_time}) / 100
        weapon_recharge = self.util.interpolate_value(ql, {item.lowql: low_attributes.recharge_time, item.highql: high_attributes.recharge_time}) / 100

        blob = "%s (QL %d)\n\n" % (self.text.make_item(item.lowid, item.highid, ql, item.name), ql)
        blob += "Attack: <highlight>%.2f</highlight>\n" % weapon_attack
        blob += "Recharge: <highlight>%.2f</highlight>\n\n" % weapon_recharge

        blob += self.get_inits_display(weapon_attack, weapon_recharge) + "\n"

        if high_attributes.aimed_shot:
            as_info = self.get_aimed_shot_info(weapon_attack, weapon_recharge, 1)
            blob += "<header2>Aimed Shot</header2>\n<highlight>%d</highlight> skill needed to cap Aimed Shot recharge at <highlight>%d secs</highlight>\n\n" % \
                    (as_info.skill_cap, as_info.hard_cap)

        if high_attributes.burst:
            burst_recharge = self.util.interpolate_value(ql, {item.lowql: low_attributes.burst, item.highql: high_attributes.burst})
            burst_info = self.get_burst_info(weapon_attack, weapon_recharge, burst_recharge, 1)
            blob += "<header2>Burst</header2> Recharge: <highlight>%d</highlight>\n<highlight>%d</highlight> skill needed to cap Burst recharge at <highlight>%d secs</highlight>\n\n" % \
                    (burst_recharge, burst_info.skill_cap, burst_info.hard_cap)

        if high_attributes.fast_attack:
            fast_attack_info = self.get_fast_attack_info(weapon_attack, 1)
            blob += "<header2>Fast Attack</header2>\n<highlight>%d</highlight> skill needed to cap Fast Attack recharge at <highlight>%.2f secs</highlight>\n\n" % \
                    (fast_attack_info.skill_cap, fast_attack_info.hard_cap)

        if high_attributes.fling_shot:
            fling_shot_info = self.get_fling_shot_info(weapon_attack, 1)
            blob += "<header2>Fling Shot</header2>\n<highlight>%d</highlight> skill needed to cap Fling Shot recharge at <highlight>%.2f secs</highlight>\n\n" % \
                    (fling_shot_info.skill_cap, fling_shot_info.hard_cap)

        if high_attributes.full_auto:
            full_auto_recharge = self.util.interpolate_value(ql, {item.lowql: low_attributes.full_auto, item.highql: high_attributes.full_auto})
            full_auto_info = self.get_full_auto_info(weapon_attack, weapon_recharge, full_auto_recharge, 1)
            blob += "<header2>Full Auto</header2> Recharge: <highlight>%d</highlight>\n<highlight>%d</highlight> skill needed to cap Full Auto recharge at <highlight>%d secs</highlight>\n\n" % \
                    (full_auto_recharge, full_auto_info.skill_cap, full_auto_info.hard_cap)

        return ChatBlob("Weapon Info for %s (QL %d)" % (item.name, ql), blob)

    def get_init_result(self, weapon_attack, weapon_recharge, init_skill):
        if init_skill < 1200:
            attack_calc = (((weapon_attack - (init_skill / 600)) - 1) / 0.02) + 87.5
            recharge_calc = (((weapon_recharge - (init_skill / 300)) - 1) / 0.02) + 87.5
        else:
            attack_calc = (((weapon_attack - (1200 / 600) - ((init_skill - 1200) / 600 / 3)) - 1) / 0.02) + 87.5
            recharge_calc = (((weapon_recharge - (1200 / 300) - ((init_skill - 1200) / 300 / 3)) - 1) / 0.02) + 87.5

        if attack_calc < recharge_calc:
            init_result = recharge_calc
        else:
            init_result = attack_calc

        init_result = min(init_result, 100)  # max of 100
        init_result = max(init_result, 0)  # min of 0

        return init_result

    def get_inits_needed(self, init_result, weapon_attack, weapon_recharge):
        inits_attack = (((init_result - 87.5) * 0.02) + 1 - weapon_attack) * -600
        inits_recharge = (((init_result - 87.5) * 0.02) + 1 - weapon_recharge) * -300

        if inits_attack > 1200:
            inits_attack = ((((init_result - 87.5) * 0.02) + 1 - weapon_attack + 2) * -1800) + 1200

        if inits_recharge > 1200:
            inits_recharge = ((((init_result - 87.5) * 0.02) + 1 - weapon_recharge + 4) * -900) + 1200

        if inits_attack < inits_recharge:
            return inits_recharge
        else:
            return inits_attack

    def get_aimed_shot_info(self, weapon_attack, weapon_recharge, aimed_shot_skill):
        result = DictObject()
        result.multiplier = round(aimed_shot_skill / 95)
        result.hard_cap = math.floor(weapon_attack + 10)
        result.skill_cap = math.ceil((4000 * weapon_recharge - 1100) / 3)

        as_recharge = math.ceil((weapon_recharge * 40) - (aimed_shot_skill * 3 / 100) + weapon_attack - 1)
        if as_recharge < result.hard_cap:
            as_recharge = result.hard_cap

        result.recharge = as_recharge

        return result

    def get_brawl_info(self, brawl_skill):
        min_values = {1: 1, 1000: 100, 1001: 101, 2000: 170, 2001: 171, 3000: 235}
        max_values = {1: 2, 1000: 500, 1001: 501, 2000: 850, 2001: 851, 3000: 1145}
        crit_values = {1: 3, 1000: 500, 1001: 501, 2000: 600, 2001: 601, 3000: 725}

        brawl_info = DictObject()
        brawl_info.min_dmg = self.util.interpolate_value(brawl_skill, min_values)
        brawl_info.max_dmg = self.util.interpolate_value(brawl_skill, max_values)
        brawl_info.crit_dmg = self.util.interpolate_value(brawl_skill, crit_values)
        brawl_info.stun_chance = 10 if brawl_skill < 1000 else 20
        brawl_info.stun_duration = 3 if brawl_skill < 2001 else 4

        return brawl_info

    def get_burst_info(self, weapon_attack, weapon_recharge, burst_recharge, burst_skill):
        result = DictObject()
        result.hard_cap = round(weapon_attack + 8)
        result.skill_cap = math.floor(((weapon_recharge * 20) + (burst_recharge / 100) - 8) * 25)

        recharge = math.floor((weapon_recharge * 20) + (burst_recharge / 100) - (burst_skill / 25) + weapon_attack)
        if recharge < result.hard_cap:
            recharge = result.hard_cap

        result.recharge = recharge

        return result

    def get_dimach_info(self, dimach_skill):
        # item ids: 42033, 42032, 213260, 213261, 213262, 213263
        general_dmg = {1: 1, 1000: 2000, 1001: 2001, 2000: 2500, 2001: 2501, 3000: 2850}

        # item ids: 42033, 42032, 213264, 213265, 213266, 213267
        ma_recharge = {1: 1800, 1000: 1800, 1001: 1188, 2000: 600, 2001: 600, 3000: 300}
        ma_dmg = {1: 1, 1000: 2000, 1001: 2001, 2000: 2340, 2001: 2341, 3000: 2550}

        # item ids: 213269, 213270, 213271, 213272, 213273, 213274
        shade_recharge = {1: 300, 1000: 300, 1001: 300, 2000: 300, 2001: 240, 3000: 200}
        shade_dmg = {1: 1, 1000: 920, 1001: 921, 2000: 1872, 2001: 1873, 3000: 2750}
        shade_heal_percentage = {1: 70, 1000: 70, 1001: 70, 2000: 75, 2001: 75, 3000: 80}

        # item ids: 211399, 211400, 213275, 213276, 213277, 213278
        keeper_heal = {1: 1, 1000: 3000, 1001: 3001, 2000: 10500, 2001: 10501, 3000: 15000}

        result = DictObject()
        result.general_dmg = self.util.interpolate_value(dimach_skill, general_dmg)
        result.ma_recharge = self.util.interpolate_value(dimach_skill, ma_recharge)
        result.ma_dmg = self.util.interpolate_value(dimach_skill, ma_dmg)
        result.shade_recharge = self.util.interpolate_value(dimach_skill, shade_recharge)
        result.shade_dmg = self.util.interpolate_value(dimach_skill, shade_dmg)
        result.shade_heal_percentage = self.util.interpolate_value(dimach_skill, shade_heal_percentage)
        result.keeper_heal = self.util.interpolate_value(dimach_skill, keeper_heal)

        return result

    def get_fast_attack_info(self, weapon_attack, fast_attack_skill):
        result = DictObject()
        result.hard_cap = weapon_attack + 5
        result.skill_cap = ((weapon_attack * 16) - result.hard_cap) * 100

        recharge = (weapon_attack * 16) - (fast_attack_skill / 100)
        if recharge < result.hard_cap:
            recharge = result.hard_cap

        result.recharge = recharge

        return result

    def get_fling_shot_info(self, weapon_attack, fling_shot_skill):
        result = DictObject()
        result.hard_cap = weapon_attack + 5
        result.skill_cap = ((weapon_attack * 16) - result.hard_cap) * 100

        recharge = (weapon_attack * 16) - (fling_shot_skill / 100)
        if recharge < result.hard_cap:
            recharge = result.hard_cap

        result.recharge = recharge

        return result

    def get_full_auto_info(self, weapon_attack, weapon_recharge, full_auto_recharge, full_auto_skill):
        result = DictObject()
        result.hard_cap = math.floor(weapon_attack + 10)
        result.skill_cap = ((weapon_recharge * 40) + (full_auto_recharge / 100) - 11) * 25
        result.max_bullets = 5 + math.floor(full_auto_skill / 100)

        recharge = round((weapon_recharge * 40) + (full_auto_recharge / 100) - (full_auto_skill / 25) + round(weapon_attack - 1))
        if recharge < result.hard_cap:
            recharge = result.hard_cap

        result.recharge = recharge

        return result

    def get_martial_arts_info(self, ma_skill):
        result = DictObject()

        # ma items: http://budabot.com/forum/viewtopic.php?f=7&t=1264&p=5739#p5739
        #  QL    1       100     500     1      500      1      500
        #     211349, 211350, 211351, 211359, 211360, 211365, 211366    // Shade
        #     211352, 211353, 211354, 211357, 211358, 211363, 211364    // MA
        #      43712, 144745,  43713, 211355, 211356, 211361, 211362    // Gen/other

        ma_min_dmg = {1: 4, 200: 45, 1000: 125, 1001: 130, 2000: 220, 2001: 225, 3000: 450}
        ma_max_dmg = {1: 8, 200: 75, 1000: 400, 1001: 405, 2000: 830, 2001: 831, 3000: 1300}
        ma_crit_dmg = {1: 3, 200: 50, 1000: 500, 1001: 501, 2000: 560, 2001: 561, 3000: 800}
        ma_speed = {1: 1.15, 200: 1.20, 1000: 1.25, 1001: 1.30, 2000: 1.35, 2001: 1.45, 3000: 1.50}

        shade_min_dmg = {1: 3, 200: 25, 1000: 55, 1001: 56, 2000: 130, 2001: 131, 3000: 280}
        shade_max_dmg = {1: 5, 200: 60, 1000: 258, 1001: 259, 2000: 682, 2001: 683, 3000: 890}
        shade_crit_dmg = {1: 3, 200: 50, 1000: 250, 1001: 251, 2000: 275, 2001: 276, 3000: 300}
        shade_speed = {1: 1.25, 200: 1.25, 1000: 1.45, 1001: 1.45, 2000: 1.65, 2001: 1.65, 3000: 1.85}

        gen_min_dmg = {1: 3, 200: 25, 1000: 65, 1001: 66, 2000: 140, 2001: 204, 3000: 300}
        gen_max_dmg = {1: 5, 200: 60, 1000: 280, 1001: 281, 2000: 715, 2001: 831, 3000: 990}
        gen_crit_dmg = {1: 3, 200: 50, 1000: 500, 1001: 501, 2000: 605, 2001: 605, 3000: 630}
        gen_speed = {1: 1.25, 200: 1.25, 1000: 1.45, 1001: 1.45, 2000: 1.65, 2001: 1.65, 3000: 1.85}

        result.ma_min_dmg = self.util.interpolate_value(ma_skill, ma_min_dmg)
        result.ma_max_dmg = self.util.interpolate_value(ma_skill, ma_max_dmg)
        result.ma_crit_dmg = self.util.interpolate_value(ma_skill, ma_crit_dmg)
        result.ma_speed = self.util.interpolate_value(ma_skill, ma_speed, 2)

        result.shade_min_dmg = self.util.interpolate_value(ma_skill, shade_min_dmg)
        result.shade_max_dmg = self.util.interpolate_value(ma_skill, shade_max_dmg)
        result.shade_crit_dmg = self.util.interpolate_value(ma_skill, shade_crit_dmg)
        result.shade_speed = self.util.interpolate_value(ma_skill, shade_speed, 2)

        result.gen_min_dmg = self.util.interpolate_value(ma_skill, gen_min_dmg)
        result.gen_max_dmg = self.util.interpolate_value(ma_skill, gen_max_dmg)
        result.gen_crit_dmg = self.util.interpolate_value(ma_skill, gen_crit_dmg)
        result.gen_speed = self.util.interpolate_value(ma_skill, gen_speed, 2)

        return result

    def get_nano_cast_info(self, nano_cast_init, nano_attack_time):
        if nano_cast_init > 1200:
            nano_cast_reduction = (nano_cast_init - 1200) / 600 + 6
        else:
            nano_cast_reduction = nano_cast_init / 200

        result = DictObject()
        result.cast_time_reduction = nano_cast_reduction
        result.effective_cast_time = nano_attack_time - nano_cast_reduction
        result.instacast_full_agg = self.get_nano_init_for_instacast(nano_attack_time - 1)
        result.instacast_neutral = self.get_nano_init_for_instacast(nano_attack_time - 0.75)
        result.instacast_half = self.get_nano_init_for_instacast(nano_attack_time)
        result.instacast_full_def = self.get_nano_init_for_instacast(nano_attack_time + 1)
        result.cast_time_full_agg = result.effective_cast_time - 1
        result.cast_time_neutral = result.effective_cast_time - 0.75
        result.cast_time_half = result.effective_cast_time
        result.cast_time_full_def = result.effective_cast_time + 1

        bar_setting = round(result.effective_cast_time / 0.02 + 50)
        if bar_setting < 0:
            bar_setting = 0
        result.bar_setting = bar_setting

        return result

    def get_nano_init_for_instacast(self, nano_attack_time):
        if nano_attack_time < 6:
            return nano_attack_time * 200
        else:
            return 1200 + (nano_attack_time - 6) * 600

    def get_inits_display(self, weapon_attack, weapon_recharge):
        num_steps = 9
        step_size = 100 / (num_steps - 1)
        blob = ""
        for i in reversed(range(0, num_steps)):
            inits_needed = self.get_inits_needed(i * step_size, weapon_attack, weapon_recharge)
            blob += "DEF >%s%s%s< AGG %d%% %d init \n" % ("=" * i, "][", "=" * (num_steps - 1 - i), i * step_size, inits_needed)

        return blob
