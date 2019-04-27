import math

from core.chat_blob import ChatBlob
from core.decorators import instance, command
from core.command_param_types import Any, Const, Int
from core.dict_object import DictObject


@instance()
class LadderController:
    def __init__(self):
        self.grades = ["shiny", "bright", "faded"]

    def inject(self, registry):
        self.db = registry.get_instance("db")
        self.util = registry.get_instance("util")
        self.text = registry.get_instance("text")

    @command(command="ladder", params=[Const("treatment"), Int("starting_amount")], access_level="all",
             description="Show sequence of laddering implants for treatment",
             extended_description="The starting amount should be the treatment or ability you have with all nano buffs, perks, and items-buffing equipment equipped, "
                                  "but minus any buffs from implants that you have equipped.")
    def ladder_treatment_cmd(self, request, _, treatment):
        if treatment < 11:
            return "Base treatment must be at least <highlight>11<end>."

        prefix = "skill_"
        result = self.optimized_steps(prefix, treatment, self.get_implant_by_max_treatment)

        blob = self.format_steps("treatment", result.steps, treatment, (treatment + self.calculate_total(result.slots, prefix)))

        return ChatBlob("Laddering Treatment", blob)

    @command(command="ladder", params=[Const("ability"), Int("starting_amount")], access_level="all",
             description="Show sequence of laddering implants for ability",
             extended_description="The starting amount should be the treatment or ability you have with all nano buffs, perks, and items-buffing equipment equipped, "
                                  "but minus any buffs from implants you have equipped.")
    def ladder_ability_cmd(self, request, _, ability):
        if ability < 6:
            return "Base ability must be at least <highlight>6<end>."

        prefix = "ability_"
        result = self.optimized_steps(prefix, ability, self.get_implant_by_max_ability)

        blob = self.format_steps("ability", result.steps, ability, (ability + self.calculate_total(result.slots, prefix)))

        return ChatBlob("Laddering Ability", blob)

    def format_steps(self, label, steps, starting, ending):
        blob = "Starting %s: <highlight>%s<end>\n\n" % (label, starting)
        blob += "-------------------\n\n"
        for (action, grade, implant) in steps:
            blob += "%s %s QL <highlight>%d<end>\n\n" % (action.capitalize(), grade, implant.ql)

        blob += "-------------------\n\n"
        blob += "Ending %s: <highlight>%s<end>\n\n" % (label, ending)
        blob += "\nInspired by a command written by Lucier of the same name"

        return blob

    def optimized_steps(self, prefix, base_value, get_max_implant):
        grade_combinations = [self.grades,
                              ["shiny", "faded", "bright"],
                              ["bright", "shiny", "faded"],
                              ["bright", "faded", "shiny"],
                              ["faded", "shiny", "bright"],
                              ["faded", "bright", "shiny"]]

        best = None
        for grade_combo in grade_combinations:
            result = self.get_steps(prefix, base_value, get_max_implant, lambda current_grade: self.get_next_grade(current_grade, grade_combo))
            if not best:
                best = result
            else:
                result_value = self.calculate_total(result.slots, prefix)
                best_value = self.calculate_total(best.slots, prefix)
                if result_value > best_value:
                    # this is here as a sanity check, but it appears that the result is always the same no matter which order you insert the implants
                    best = result
                elif best_value == result_value and len(result.steps) < len(best.steps):
                    # this optimizes for the least amount of steps/implants
                    best = result

        return best

    def get_steps(self, prefix, base_value, get_max_implant, get_next_grade):
        slots = DictObject({"shiny": None,
                            "bright": None,
                            "faded": None})

        steps = []

        num_skipped = 0
        current_grade = None
        while num_skipped < 3:
            current_grade = get_next_grade(current_grade)

            # find next highest possible implant
            new_implant = get_max_implant(self.calculate_total(slots, prefix, current_grade) + base_value)

            if not slots.get(current_grade):
                steps.append(["add", current_grade, new_implant])
                slots[current_grade] = new_implant
            elif new_implant.get(prefix + current_grade) > slots.get(current_grade).get(prefix + current_grade):
                steps.append(["remove", current_grade, slots.get(current_grade)])
                steps.append(["add", current_grade, new_implant])
                slots[current_grade] = new_implant
            else:
                num_skipped += 1

        return DictObject({"slots": slots,
                           "steps": steps})

    def get_next_grade(self, current_grade, grades):
        if not current_grade:
            next_index = 0
        else:
            next_index = grades.index(current_grade) + 1
            if next_index >= len(grades):
                next_index = 0

        return grades[next_index]

    def get_implant_by_max_treatment(self, treatment):
        return self.db.query_single("SELECT * from implant_requirement WHERE treatment <= ? ORDER BY ql DESC LIMIT 1", [treatment])

    def get_implant_by_max_ability(self, ability):
        return self.db.query_single("SELECT * from implant_requirement WHERE ability <= ? ORDER BY ql DESC LIMIT 1", [ability])

    def get_cluser_min_ql(self, ql, grade):
        if grade == "shiny":
            result = math.floor(ql * 0.86)
        elif grade == "bright":
            result = math.floor(ql * 0.84)
        elif grade == "faded":
            result = math.floor(ql * 0.82)
        else:
            raise Exception("Unknown grade: '%s'" % grade)

        if ql >= 201:
            return max(201, result)
        else:
            return result

    def calculate_total(self, slots, prefix, skip_grade=None):
        value = 0
        for grade in self.grades:
            if grade != skip_grade:
                implant = slots.get(grade)
                if implant:
                    value += implant.get(prefix + grade)

        return value
