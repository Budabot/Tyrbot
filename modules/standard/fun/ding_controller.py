import random

from core.command_param_types import SignedInt
from core.decorators import command, instance


@instance()
class DingController:
    """
        Port of Budabot fun module
    """

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
                text_options = ["Reclaim sure is doing a number on you if you're going backwards...",
                                "Wtb negative exp kite teams!",
                                f"That leaves you with... {levels_to_go} more levels until 220, I don't see the problem?",
                                f"How the hell did you get to {current_level}?"]
            elif current_level == 1:
                text_options = ["You didn't even start yet...",
                                "Did you somehow start from level 0?",
                                "Dinged from 1 to 1? Congratz"]
            elif current_level == 15:
                text_options = ["You're <yellow>TL 2</yellow> already? Nice.",
                                "Title level 2, Congratulations! Go spend your well earned IP!"]
            elif current_level == 25:
                text_options = ["Congratulations! Make sure to finish up in subway before moving on!",
                                f"<red>*Abmouth Supremus sweating profusely*</red> Congratz on your 25th, {character_name}!"]
            elif current_level == 50:
                text_options = [f"Yay, <yellow>TL 3</yellow> Congratulations, {character_name}!",
                                "Title level 3, Congratulations! Go spend your well earned IP!"]
            elif current_level == 60:
                text_options = ["Congratulations! Make sure to finish up in ToTW before moving on!",
                                f"Nice! Time to test out Aztur's immortality? Congratz on your 60th level, {character_name}!"]
            elif current_level == 100:
                text_options = [f"Congratz! <red>Level 100</red> - {character_name} you rock!",
                                "Congratulations! Time to twink up for T.I.M!",
                                "Gratz, you're half way to 200. More missions, MORE!",
                                "Woot! Congrats, don't forget to put on your 1k token board."]
            elif current_level == 150:
                text_options = ["S10 time!!!",
                                "Time to ungimp yourself! Horray!. Congrats =)",
                                "What starts with A, and ends with Z? <green>ALIUMZ!</green>",
                                "Wow, is it that time already? TL 5 really? You sure are moving along! Gratz"]
            elif current_level == 180:
                text_options = ["Congratz! Now go kill some <green>aliumz</green> at S13/28/35!!",
                                "Only 20 more froob levels to go! HOORAH!",
                                "Yay, only 10 more levels until TL 6! Way to go!"]
            elif current_level == 190:
                text_options = ["Wow holy shiznits! You're TL 6 already? Congrats!",
                                "Just a few more steps and you're there buddy, keep it up!",
                                f"Almost party time! just a bit more to go {character_name}. We'll be sure to bring you a cookie!"]
            elif current_level == 200:
                text_options = [f"Congratz! The big Two Zero Zero!!! Party at {character_name}'s place",
                                "Best of the best in froob terms, congratulations!",
                                "What a day indeed. Finally done with froob levels. Way to go!"]
            elif 200 < current_level < 220:
                text_options = ["Congratz! Just a few more levels to go!",
                                "Enough with the dingin you are making the fr00bs feel bad!",
                                "Come on save some dings for the rest!"]
            elif current_level == 220:
                text_options = ["Congratz! You have reached the end of the line! NO MORE FUN FOR YOU! :P",
                                f"Holy shit, you finally made it! What an accomplishment... Congratulations {character_name}, for reaching a level reserved for the greatest!",
                                f"I'm going to miss you a great deal, because after this, we no longer can be together {character_name}. We must part so you can continue getting your research and AI levels done! Farewell!",
                                "How was the inferno grind? I'm glad to see you made it through, and congratulations for finally getting the level you well deserved!",
                                f"Our congratulations, to our newest level 220 member, {character_name}, for his dedication. We present him with his new honorary rank, Chuck Norris!",
                                f"Holy crap, you actually did it! Dear {character_name}, I salute you for your determination and sheer awesomeness. Congratulations, to our newest level 220 member!"]
            elif current_level > 220:
                text_options = ["Umm...no.",
                                "You must be high, because that number is too high...",
                                "Ha, ha, ha...",
                                "You must be a GM or one hell of an exploiter, that number it too high!",
                                "Yeah, and I'm Chuck Norris...",
                                "Not now, not later, not ever... find a more reasonable level!"]
            else:
                text_options = ["Ding ding ding... now ding some more!",
                                "Keep em coming!",
                                "Don't stop now, you're getting there!",
                                f"Come on, COME ON! Only {levels_to_go} more levels to go until 220!"]
        return random.choice(text_options)
