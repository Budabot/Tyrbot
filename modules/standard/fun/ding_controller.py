import random

from core.command_param_types import SignedInt
from core.decorators import command, instance
from core.registry import Registry


@instance()
class DingController:
    """
        Port of Budabot fun module
    """

    def inject(self, registry: Registry):
        self.command_alias_service = registry.get_instance(
            "command_alias_service")

    def start(self):
        self.command_alias_service.add_alias("levelup", "ding")

    @command(command="ding", params=[SignedInt("level", is_optional=True)], access_level="all",
             description="Show a random ding message, congratz!")
    def ding_command(self, request, level):
        if level is None:
            text_options = [
                "Yeah yeah gratz, I would give you a better response but you didn't say what level you dinged.",
                "Hmmm, I really want to know what level you dinged, but gratz anyways nub.",
                "When are you people going to start using me right! Gratz for your level though.",
                "Gratz! But what are we looking at? I need a level next time."]
        else:
            current_level = level
            levels_to_go = 220 - current_level
            character_name = request.sender.name
            if current_level <= 0:
                text_options = [("Reclaim sure is doing a number on you if you're going backwards..."),
                                ("Wtb negative exp kite teams!"),
                                ("That leaves you with... %d more levels until 220, I don't see the problem?" % (
                                    levels_to_go)),
                                ("How the hell did you get to %d?" % (current_level))]
            elif current_level == 1:
                text_options = [("You didn't even start yet..."),
                                ("Did you somehow start from level 0?"),
                                ("Dinged from 1 to 1? Congratz")]
            elif current_level == 15:
                text_options = [("You're <yellow>TL 2<end> already? Nice."),
                                ("Title level 2, Congratulations! Go spend your well earned IP!")]
            elif current_level == 25:
                text_options = [("Congratulations! Make sure to finish up in subway before moving on!"),
                                ("<red>*Abmouth Supremus sweating profusely*<end> Congratz on your 25th, %s!") % (
                                    character_name)]
            elif current_level == 50:
                text_options = [("Yay, <yellow>TL 3<end> Congratulations, %s!" % (character_name)),
                                ("Title level 3, Congratulations! Go spend your well earned IP!")]
            elif current_level == 60:
                text_options = [("Congratulations! Make sure to finish up in ToTW before moving on!"),
                                ("Nice! Time to test out Aztur's immortality? Congratz on your 60th level, %s!") % (
                                    character_name)]
            elif current_level == 100:
                text_options = [("Congratz! <red>Level 100<end> - %s you rock!" % (character_name)),
                                ("Congratulations! Time to twink up for T.I.M!"),
                                ("Gratz, you're half way to 200. More missions, MORE!"),
                                ("Woot! Congrats, don't forget to put on your 1k token board.")]
            elif current_level == 150:
                text_options = [("S10 time!!!"),
                                ("Time to ungimp yourself! Horray!. Congrats =)"),
                                ("What starts with A, and ends with Z? <green>ALIUMZ!<end>"),
                                ("Wow, is it that time already? TL 5 really? You sure are moving along! Gratz")]
            elif current_level == 180:
                text_options = [("Congratz! Now go kill some <green>aliumz<end> at S13/28/35!!"),
                                ("Only 20 more froob levels to go! HOORAH!"),
                                ("Yay, only 10 more levels until TL 6! Way to go!")]
            elif current_level == 190:
                text_options = [("Wow holy shiznits! You're TL 6 already? Congrats!"),
                                ("Just a few more steps and you're there buddy, keep it up!"),
                                ("Almost party time! just a bit more to go %s. We'll be sure to bring you a cookie!" % (
                                    character_name))]
            elif current_level == 200:
                text_options = [("Congratz! The big Two Zero Zero!!! Party at %s's place" % (character_name)),
                                ("Best of the best in froob terms, congratulations!"),
                                ("What a day indeed. Finally done with froob levels. Way to go!")]
            elif current_level > 200 and current_level < 220:
                text_options = [("Congratz! Just a few more levels to go!"),
                                ("Enough with the dingin you are making the fr00bs feel bad!"),
                                ("Come on save some dings for the rest!")]
            elif current_level == 220:
                text_options = [("Congratz! You have reached the end of the line! NO MORE FUN FOR YOU! :P"),
                                ("Holy shit, you finally made it! What an accomplishment... Congratulations %s, for reaching a level reserved for the greatest!" % (
                                    character_name)),
                                ("I'm going to miss you a great deal, because after this, we no longer can be together %s. We must part so you can continue getting your research and AI levels done! Farewell!" % (
                                    character_name)),
                                ("How was the inferno grind? I'm glad to see you made it through, and congratulations for finally getting the level you well deserved!"),
                                ("Our congratulations, to our newest level 220 member, %s, for his dedication. We present him with his new honorary rank, Chuck Norris!" % (
                                    character_name)),
                                ("Holy crap, you actually did it! Dear %s, I salute you for your determination and sheer awesomeness. Congratulations, to our newest level 220 member!" % (
                                    character_name))]
            elif current_level > 220:
                text_options = [("Umm...no."),
                                ("You must be high, because that number is too high..."),
                                ("Ha, ha, ha..."),
                                ("You must be a GM or one hell of an exploiter, that number it too high!"),
                                ("Yeah, and I'm Chuck Norris..."),
                                ("Not now, not later, not ever... find a more reasonable level!")]
            else:
                text_options = [("Ding ding ding... now ding some more!"),
                                ("Keep em coming!"),
                                ("Don't stop now, you're getting there!"),
                                ("Come on, COME ON! Only %d more levels to go until 220!") % (levels_to_go)]
        return random.choice(text_options)