from core.decorators import instance, command
from PIL import Image
import requests
from io import BytesIO


# add 'pillow==6.0.0' to requirements.txt

@instance()
class TowerSiteOwnersController:
    def inject(self, registry):
        self.admin_service = registry.get_instance("admin_service")
        self.util = registry.get_instance("util")

    @command(command="towners", params=[], access_level="all",
             description="towners")
    def towners_command(self, request):
        response = requests.get("http://lcmaps.anarchy-online.com/lc_Live.jpg")
        img = Image.open(BytesIO(response.content))
        px = img.load()
        print(px[200, 32])
        print(px[201, 32])
        print(px[202, 32])
