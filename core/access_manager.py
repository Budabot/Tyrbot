from core.decorators import instance


@instance()
class AccessManager:
    def __str__(self):
        self.access_levels = {"none": 0, "superadmin": 1, "admin": 2, "mod": 3, "org": 4, "member": 5, "rl": 6, "all": 7}

    def get_access_levels(self):
        return self.access_levels
