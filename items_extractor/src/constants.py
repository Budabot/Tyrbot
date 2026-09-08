class Attribute:
    Flags = 0
    Life = 1
    Can = 30
    Level = 54
    ItemClass = 76
    Icon = 79
    RechargeDelay = 210
    ItemDelay = 294
    Placement = 298
    BurstRecharge = 374
    FullAutoRecharge = 375


class ItemType:
    MISC = 0
    WEAPON = 1
    ARMOR = 2
    IMPLANT = 3
    TEMPLATE = 4
    SPIRIT = 5

    NAMES = {
        0: "Misc",
        1: "Weapon",
        2: "Armor",
        3: "Implant",
        4: "Template",
        5: "Spirit"
    }

    @classmethod
    def get_name(cls, item_type_id: int):
        return cls.NAMES.get(item_type_id)


class CanFlag:
    Burst = 2048
    FlingShot = 4096
    FullAuto = 8192
    AimedShot = 16384
    FastAttack = 262144


class EventType:
    OnUse = 0
    ToUse = 3
    ToWear = 6
    OnWear = 14


class IndexRecordType:
    AODB_ITEM_TYPE = 1000020
    AODB_NANO_TYPE = 1040005


class ArmorSlot:
    NECK = 2
    HEAD = 4
    BACK = 8
    RIGHT_SHOULDER = 16
    CHEST = 32
    LEFT_SHOULDER = 64
    RIGHT_ARM = 128
    HANDS = 256
    LEFT_ARM = 512
    RIGHT_WRIST = 1024
    LEGS = 2048
    LEFT_WRIST = 4096
    RIGHT_FINGER = 8192
    FEET = 16384
    LEFT_FINGER = 32768


class WeaponSlot:
    HUD1 = 2
    HUD3 = 4
    UTIL1 = 8
    UTIL2 = 16
    UTIL3 = 32
    RIGHT_HAND = 64
    BELT = 128
    LEFT_HAND = 256
    DECK1 = 512
    DECK2 = 1024
    DECK3 = 2048
    DECK4 = 4096
    DECK5 = 8192
    DECK6 = 16384
    HUD2 = 32768


WEAPON_GROUPS = [
    ([WeaponSlot.UTIL1, WeaponSlot.UTIL2, WeaponSlot.UTIL3], "Util"),
    ([WeaponSlot.HUD1, WeaponSlot.HUD2, WeaponSlot.HUD3], "Hud"),
    ([WeaponSlot.BELT, WeaponSlot.DECK1, WeaponSlot.DECK2, WeaponSlot.DECK3,
      WeaponSlot.DECK4, WeaponSlot.DECK5, WeaponSlot.DECK6], "Deck"),
    ([WeaponSlot.LEFT_HAND, WeaponSlot.RIGHT_HAND], "Weapon")
]

ARMOR_GROUPS = [
    ([ArmorSlot.NECK], "Neck"),
    ([ArmorSlot.HEAD], "Head"),
    ([ArmorSlot.BACK], "Back"),
    ([ArmorSlot.CHEST], "Chest"),
    ([ArmorSlot.HANDS], "Hands"),
    ([ArmorSlot.LEGS], "Legs"),
    ([ArmorSlot.FEET], "Feet"),
    ([ArmorSlot.RIGHT_SHOULDER, ArmorSlot.LEFT_SHOULDER], "Shoulders"),
    ([ArmorSlot.RIGHT_ARM, ArmorSlot.LEFT_ARM], "Arms"),
    ([ArmorSlot.RIGHT_WRIST, ArmorSlot.LEFT_WRIST], "Wrists"),
    ([ArmorSlot.RIGHT_FINGER, ArmorSlot.LEFT_FINGER], "Fingers")
]
