from core.chat_blob import ChatBlob
from core.decorators import instance, command


@instance()
class ImplantDesignerController:
    def inject(self, registry):
        self.text = registry.get_instance("text")
        self.command_alias_service = registry.get_instance("command_alias_service")

    def start(self):
        self.command_alias_service.add_alias("impdesign", "implantdesigner")

    @command(command="implantdesigner", params=[], access_level="all",
             description="Shows links to several web-based implant designers")
    def implant_designer_cmd(self, request):
        blob = "Tinker Plants\n"
        blob += self.text.make_chatcmd("https://ao.tinkeringidiot.com/tinkerplants/", "/start https://ao.tinkeringidiot.com/tinkerplants/")
        blob += "\n\n"
        blob += "Bitnyk's Implant Tool\n"
        blob += self.text.make_chatcmd("http://hexmusic.free.fr/forum/implants.php", "/start http://hexmusic.free.fr/forum/implants.php")

        return ChatBlob(f"Implant Designer Links", blob)
