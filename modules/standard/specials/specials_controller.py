import math

from core.chat_blob import ChatBlob
from core.decorators import instance, command
from core.command_param_types import Int, Decimal

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

    def start(self):
        self.command_alias_service.add_alias("aimshot", "aimedshot")
        self.command_alias_service.add_alias("as", "aimedshot")
        self.command_alias_service.add_alias("inits", "weapon")
        self.command_alias_service.add_alias("specials", "weapon")
        self.command_alias_service.add_alias("fling", "flingshot")

    @command(command="aggdef", params=[Decimal("weapon_attack"), Decimal("weapon_recharge"), Int("init_skill")], access_level="all",
             description="Show agg/def information")
    def aggdef_cmd(self, request, weapon_attack, weapon_recharge, init_skill):
        init_result = self.get_init_result(weapon_attack, weapon_recharge, init_skill)
        bar_position = init_result * 8 / 100

        inits_full_agg = self.get_inits_needed(100, weapon_attack, weapon_recharge)
        inits_neutral = self.get_inits_needed(87.5, weapon_attack, weapon_recharge)
        inits_full_def = self.get_inits_needed(0, weapon_attack, weapon_recharge)

        blob = "Attack: <highlight>%.2f secs<end>\n" % weapon_attack
        blob += "Recharge: <highlight>%.2f secs<end>\n" % weapon_recharge
        blob += "Init Skill: <highlight>%d<end>\n\n" % init_skill

        blob += "You must set you AGG/DEF bar at <highlight>%d%% (%.2f)<end> to wield your weapon at 1/1.\n\n" % (int(init_result), bar_position)

        blob += "Init needed for max speed at Full Agg (100%%): <highlight>%d<end>\n" % inits_full_agg
        blob += "Init needed for max speed at Neutral (88%%): <highlight>%d<end>\n" % inits_neutral
        blob += "Init needed for max speed at Full Def (0%%): <highlight>%d<end>\n\n" % inits_full_def

        blob += "Note that at the neutral position (88%), your attack and recharge time will match that of the weapon you are using.\n\n\n"

        blob += "Based on the !aggdef command from Budabot, which was based upon a RINGBOT module made by NoGoal(RK2) and modified for Budabot by Healnjoo(RK2)"

        return ChatBlob("Agg/Def Results", blob)

    @command(command="aimedshot", params=[Decimal("weapon_attack"), Decimal("weapon_recharge"), Int("aimed_shot_skill")], access_level="all",
             description="Show aimed shot information")
    def aimedshot_cmd(self, request, weapon_attack, weapon_recharge, aimed_shot_skill):
        as_info = self.get_aimed_shot_info(weapon_attack, weapon_recharge, aimed_shot_skill)

        blob = "Attack: <highlight>%.2f secs<end>\n" % weapon_attack
        blob += "Recharge: <highlight>%.2f secs<end>\n" % weapon_recharge
        blob += "Aimed Shot Skill: <highlight>%d<end>\n\n" % aimed_shot_skill

        blob += "Aimed Shot Multiplier: <highlight>1 - %dx<end>\n" % as_info.multiplier
        blob += "Aimed Shot Recharge: <highlight>%d secs<end>\n\n" % as_info.recharge

        blob += "You need <highlight>%d<end> Aimed Shot Skill to cap your recharge at <highlight>%d<end> seconds." % (as_info.skill_cap, as_info.hard_cap)

        return ChatBlob("Aimed Shot Results", blob)

    @command(command="brawl", params=[Int("brawl_skill")], access_level="all",
             description="Show brawl information")
    def brawl_cmd(self, request, brawl_skill):
        brawl_info = self.get_brawl_info(brawl_skill)

        blob = "Brawl Skill: <highlight>%d<end>\n\n" % brawl_skill

        blob += "Brawl Recharge: <highlight>15 secs<end> (constant)\n"
        blob += "Brawl Damage: <highlight> %d - %d (%d)<end>\n" % (brawl_info.min_dmg, brawl_info.max_dmg, brawl_info.crit_dmg)
        blob += "Stun Change: <highlight>%d%%<end>\n" % brawl_info.stun_chance
        blob += "Stun Duration: <highlight>%d secs<end>\n\n" % brawl_info.stun_duration

        blob += "Stun chance is 10% for brawl skill less than 1000 and 20% for brawl skill 1000 or greater.\n"
        blob += "Stun duration is 3 seconds for brawl skill less than 2001 and 4 seconds for brawl skill 2001 or greater.\n\n\n"

        blob += "Based on the !brawl command from Budabot by Imoutochan (RK1)"

        return ChatBlob("Brawl Results", blob)

    @command(command="burst", params=[Decimal("weapon_attack"), Decimal("weapon_recharge"), Int("burst_recharge"), Int("burst_skill")], access_level="all",
             description="Show burst information")
    def burst_cmd(self, request, weapon_attack, weapon_recharge, burst_recharge, burst_skill):
        burst_info = self.get_burst_info(weapon_attack, weapon_recharge, burst_recharge, burst_skill)

        blob = "Attack: <highlight>%.2f secs<end>\n" % weapon_attack
        blob += "Recharge: <highlight>%.2f secs<end>\n" % weapon_recharge
        blob += "Burst Recharge: <highlight>%d<end>\n" % burst_recharge
        blob += "Burst Skill: <highlight>%d<end>\n\n" % burst_skill

        blob += "Burst Recharge: <highlight>%d secs<end>\n\n" % burst_info.recharge

        blob += "You need <highlight>%d<end> Burst Skill to cap your recharge at <highlight>%d secs<end>." % (burst_info.skill_cap, burst_info.hard_cap)

        return ChatBlob("Burst Results", blob)

    @command(command="dimach", params=[Int("dimach_skill")], access_level="all",
             description="Show dimach information")
    def dimach_cmd(self, request, dimach_skill):
        dimach_info = self.get_dimach_info(dimach_skill)

        blob = "Dimach Skill: <highlight>%d<end>\n\n" % dimach_skill

        blob += "<header2>Martial Artist<end>\n"
        blob += "Damage: <highlight>%d<end>\n" % dimach_info.ma_dmg
        blob += "Recharge: <highlight>%s<end>\n\n" % self.util.time_to_readable(dimach_info.ma_recharge)

        blob += "<header2>Keeper<end>\n"
        blob += "Self Heal: <highlight>%d<end>\n" % dimach_info.keeper_heal
        blob += "Recharge: <highlight>5 mins<end> (constant)\n\n"

        blob += "<header2>Shade<end>\n"
        blob += "Damage: <highlight>%d<end>\n" % dimach_info.shade_dmg
        blob += "Self Heal: <highlight>%d%%<end> * <highlight>%d<end> = <highlight>%d<end>\n" % \
                (dimach_info.shade_heal_percentage, dimach_info.shade_dmg, round(dimach_info.shade_heal_percentage * dimach_info.shade_dmg / 100))
        blob += "Recharge: <highlight>%s<end>\n\n" % self.util.time_to_readable(dimach_info.shade_recharge)

        blob += "<header2>All other professions<end>\n"
        blob += "Damage: <highlight>%d<end>\n" % dimach_info.general_dmg
        blob += "Recharge: <highlight>30 mins<end> (constant)\n\n\n"

        blob += "Based on the !dimach command from Budabot by Imoutochan (RK1)"

        return ChatBlob("Dimach Results", blob)

    @command(command="fastattack", params=[Decimal("weapon_attack"), Int("fast_attack_skill")], access_level="all",
             description="Show fast attack information")
    def fastattack_cmd(self, request, weapon_attack, fast_attack_skill):
        fast_attack_info = self.get_fast_attack_info(weapon_attack, fast_attack_skill)

        blob = "Attack: <highlight>%.2f secs<end>\n" % weapon_attack
        blob += "Fast Attack Skill: <highlight>%d<end>\n\n" % fast_attack_skill

        blob += "Fast Attack Recharge: <highlight>%.2f secs<end>\n\n" % fast_attack_info.recharge

        blob += "You need <highlight>%d<end> Fast Attack Skill to cap your recharge at <highlight>%.2f secs<end>." % (fast_attack_info.skill_cap, fast_attack_info.hard_cap)

        return ChatBlob("Fast Attack Results", blob)

    @command(command="flingshot", params=[Decimal("weapon_attack"), Int("fling_shot_skill")], access_level="all",
             description="Show fling shot information")
    def flingshot_cmd(self, request, weapon_attack, fling_shot_skill):
        fling_shot_info = self.get_fling_shot_info(weapon_attack, fling_shot_skill)

        blob = "Attack: <highlight>%.2f secs<end>\n" % weapon_attack
        blob += "Fling Shot Skill: <highlight>%d<end>\n\n" % fling_shot_skill

        blob += "Fling Shot Recharge: <highlight>%.2f secs<end>\n\n" % fling_shot_info.recharge

        blob += "You need <highlight>%d<end> Fling Shot Skill to cap your recharge at <highlight>%.2f secs<end>." % (fling_shot_info.skill_cap, fling_shot_info.hard_cap)

        return ChatBlob("Fling Shot Results", blob)

    @command(command="fullauto", params=[Decimal("weapon_attack"), Decimal("weapon_recharge"), Int("full_auto_recharge"), Int("full_auto_skill")], access_level="all",
             description="Show full auto information")
    def fullauto_cmd(self, request, weapon_attack, weapon_recharge, full_auto_recharge, full_auto_skill):
        full_auto_info = self.get_full_auto_info(weapon_attack, weapon_recharge, full_auto_recharge, full_auto_skill)

        blob = "Attack: <highlight>%.2f secs<end>\n" % weapon_attack
        blob += "Recharge: <highlight>%.2f secs<end>\n" % weapon_recharge
        blob += "Full Auto Recharge: <highlight>%d<end>\n" % full_auto_recharge
        blob += "Full Auto Skill: <highlight>%d<end>\n\n" % full_auto_skill

        blob += "Full Auto Recharge: <highlight>%d secs<end>\n" % full_auto_info.recharge
        blob += "Max Number of Bullets: <highlight>%d<end>\n\n" % full_auto_info.max_bullets

        blob += "You need <highlight>%d<end> Full Auto Skill to cap your recharge at <highlight>%d secs<end>.\n\n" % (full_auto_info.skill_cap, full_auto_info.hard_cap)

        blob += "From <highlight>0 to 10K<end> damage, the bullet damage is unchanged.\n"
        blob += "From <highlight>10K to 11.5K<end> damage, each bullet damage is halved.\n"
        blob += "From <highlight>11K to 15K<end> damage, each bullet damage is halved again.\n"
        blob += "<highlight>15K<end> is the damage cap."

        return ChatBlob("Full Auto Results", blob)

    @command(command="mafist", params=[Int("ma_skill")], access_level="all",
             description="Show martial arts information")
    def mafist_cmd(self, request, ma_skill):
        ma_info = self.get_martial_arts_info(ma_skill)

        blob = "Martial Arts Skill: <highlight>%d<end>\n\n" % ma_skill

        blob += "<header2>Martial Artist<end>\n"
        blob += "Speed: <highlight>%.2f / %.2f secs<end>\n" % (ma_info.ma_speed, ma_info.ma_speed)
        blob += "Damage: <highlight>%d - %d (%d)<end>\n\n" % (ma_info.ma_min_dmg, ma_info.ma_max_dmg, ma_info.ma_crit_dmg)

        blob += "<header2>Shade<end>\n"
        blob += "Speed: <highlight>%.2f / %.2f secs<end>\n" % (ma_info.shade_speed, ma_info.shade_speed)
        blob += "Damage: <highlight>%d - %d (%d)<end>\n\n" % (ma_info.shade_min_dmg, ma_info.shade_max_dmg, ma_info.shade_crit_dmg)

        blob += "<header2>All other professions<end>\n"
        blob += "Speed: <highlight>%.2f / %.2f secs<end>\n" % (ma_info.gen_speed, ma_info.gen_speed)
        blob += "Damage: <highlight>%d - %d (%d)<end>\n\n" % (ma_info.gen_min_dmg, ma_info.gen_max_dmg, ma_info.gen_crit_dmg)

        return ChatBlob("Martial Arts Results", blob)

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
            inits_recharge = ((((init_result - 87.5) * 0.02) + 1 - weapon_attack + 4) * -900) + 1200

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
        general_dmg = {1: 1, 1000: 2000, 1001: 2001, 2000: 2500, 2001: 2501, 3000: 2850}
        ma_recharge = {1: 1800, 1000: 1800, 1001: 1188, 2000: 600, 2001: 600, 3000: 300}
        ma_dmg = {1: 1, 1000: 2000, 1001: 2001, 2000: 2340, 2001: 2341, 3000: 2550}
        shade_recharge = {1: 300, 1000: 300, 1001: 300, 2000: 300, 2001: 240, 3000: 200}
        shade_dmg = {1: 1, 1000: 920, 1001: 921, 2000: 1872, 2001: 1873, 3000: 2750}
        shade_heal_percentage = {1: 70, 1000: 70, 1001: 70, 2000: 75, 2001: 75, 3000: 80}
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
