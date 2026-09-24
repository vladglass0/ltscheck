"""Правила из manual.md (мл. сотрудник) + mods.holyworld.me."""
from __future__ import annotations

RESIDUE_DAYS = 14

# manual.md, "Правильные веса версий" (КБ размера .jar)
VERSION_WEIGHTS_EXACT_KB: dict[str, int] = {
    "1.16": 17083, "1.16.1": 17083, "1.16.2": 17096, "1.16.3": 17096,
    "1.16.4": 17136, "1.16.5": 17136,
    "1.17": 19079, "1.17.1": 19089,
    "1.18": 19569, "1.18.1": 19573, "1.18.2": 19785,
    "1.19": 20960, "1.19.1": 21137, "1.19.2": 21138,
    "1.19.3": 22173, "1.19.4": 22927,
    "1.20": 22489, "1.20.1": 22490, "1.20.2": 22643,
}
VERSION_OVERWEIGHT_TOLERANCE = 1.03
VERSION_WEIGHT_EXEMPT_SUBSTR = ("labymod", "laby-mod", "prostocraft", "prosto", "blclient", "lc", "lunar", "badlion")

# manual.md, Everything: ключевые слова остатков/хранения
EVERYTHING_KEYWORDS: tuple[str, ...] = tuple(
    "shellbag impact wurst bleachhack aristois huzuni skillclient nodus inertia ares sigma "
    "meteor atomic zamorozka liquidbounce nurik nursultan celestial calestial celka expensive "
    "neverhook excellent wexside wildclient minced deadcode akrien jigsaw future jessica dreampool "
    "vape infinity squad norules konas zeusclient richclient ghost_client rusherhack thunderhack "
    "moonhack winner nova exire doomsday nightware ricardo extazyy troxill antileak arbuz .akr .wex "
    "dauntiblyat rename_me_please editme takker fuzeclient wisefolder netlimiter flauncher clean-main "
    "vec.dll usboblivion.exe feather delta eclipse venus jex hakari hush hach rogalik catlavan haruka "
    "wissend fluger sperma vortex newcode astra britva "
    "bariton xray x-ray spambot cleancut spam_bot player_highlighter aimbot freecam bedrock_breaker_mode "
    "double_hotbar elytra_swap armor_hotswap smart_moving chest savesearcher worlddownloader gumballoff "
    "tweakeroo librarian_trade_finder sacurachorusfind entity_outliner clickcrystals crystal_optimizer "
    "crystal optimizer entity_xray invmove viabackwards viaforge viaproxy vialoader viamcp hitbox chunkcopy "
    "elytrahack seedcracker diamondsim forgehax stepup clientcommands xaero control-tweaks swingthroughgrass "
    "through camerautils mobhealthbar auto place showinginvisible health universalmod cheatutils inventory tweaks".split()
)

# manual.md, "Моды": запрещённые
BANNED_MODS: tuple[str, ...] = (
    "baritone", "xray", "spambot", "spam_bot", "inventory walk", "invmove",
    "player_highlighter", "aimbot", "freecam", "bedrock_breaker", "double_hotbar",
    "elytra_swap", "armor_hotswap", "smart_moving", "chest_stealer", "cheststealer",
    "chest_locator", "chestlocator", "savesearcher", "worlddownloader", "topkaautobuy",
    "gumballoff", "tweakeroo", "mob_hitbox", "mobhitbox", "hitbox",
    "librarian_trade_finder", "sacurachorusfind", "auto_attack", "autoattack",
    "entity_outliner", "seedcracker", "crystaloptimizer", "crystal_optimizer",
    "clickcrystals", "killaura", "triggerbot",
    "nursultan", "celestial", "akrien", "aristois", "impact", "meteor",
    "wurst", "bleachhack", "liquidbounce", "sigma", "vape",
)
VIA_BANNED = ("viabackwards", "viaforge", "viaproxy")
VIA_ALLOWED = ("viaversion", "viafabric", "viarewind", "vialoader")
VIA_SUSPICIOUS = ("vialoader", "viamcp")

LIBRARY_LEFTOVERS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("libraries", "cabaletta"), "cabaletta в корне libraries"),
    (("libraries", "com", "github", "impactdevelopment"), "ImpactDevelopment"),
    (("libraries", "net", "minecraftxray"), "minecraftxray"),
    (("libraries", "net", "impactclient"), "impactclient"),
)

# manual.md, SystemInformer: запрет. веса .dll (МБ)
DLL_FORBIDDEN_MB: dict[float, str] = {
    8.95: "инжект хитбоксы",
    8.90: "автобай",
    1.54: "инжект хитбоксы",
    1.43: "dauntiblyat.dll",
    1.42: "инжект хитбоксы",
}
DLL_WEIGHT_TOLERANCE_MB = 0.06

VEC_DLL_SIZE = 30 * 1024
VEC_DLL_SIZE_TOL = 4 * 1024
VEC_CONTENT_MARKER = b"net/minecraft/util/math/axisalignedbb"
MP3_HITS_SIZE = 9400174
MP3_HITS_TOL = 4096
EXE_SUSPICIOUS_SIZES: frozenset[int] = frozenset({
    1566208, 22285824, 1010176, 22433280, 348672, 352256, 782848,
    6887424, 763392, 6111, 743424, 1767424, 823808, 18126848,
})
EXE_FML_SIZE_RANGE = (700 * 1024, 5 * 1024 * 1024)
EXE_FML_MARKERS = (b"net/minecraftforge/fml/loading/FMLLoader", b"glowEsp")
EXE_D3D_SIZE_RANGE = (14 * 1024 * 1024, 17 * 1024 * 1024)
EXE_D3D_MARKERS = (b"D3D11CreateDeviceAndSwapChain", b"LoadLibraryA")
JAR_DUMIK_SIZE_RANGE = (21 * 1024, 10 * 1024 * 1024)
JAR_DUMIK_MARKERS = ("net/java/s.class", "net/java/f.class")

LOG_CHEAT_KEYWORDS = ("xray", "x-ray", "impact", "baritone", "celestial", "nursultan", "akrien")
LOG_CONNECT_MARKER = "connecting to"
LOG_USER_MARKER = "setting user:"

SHELLBAG_CLEANER_MARKERS = ("shellbag_analyzer_cleaner.ini", "shellbag backups")

JAR_CHEAT_CLASS_MARKERS = (
    "killaura", "autoattack", "auto_attack", "freecam", "free_cam",
    "triggerbot", "crystaloptimizer", "crystal_optimizer",
)
JAR_HITBOX_MARKERS = (
    "setboundingbox", "method_5857", "func_174826_a",
    "axisalignedbb", "hitresult", "class_239",
    "entityraytraceresult", "raytraceresult",
    "itemstack", "class_1799",
)

VM_MARKERS = (
    "vmware", "virtual", "vbox", "hyper-v", "hyperv", "qemu",
    "xen", "kvm", "virtio", "virtualbox", "vmci", "svga", "vmbus",
)
MONITORED_SERVICES = ("PcaSvc", "DPS", "SysMain", "EventLog", "bam")

# mods.holyworld.me (Scrapling stealthy-fetch 2026-09-24)
ALLOWED_VISUALS: tuple[str, ...] = (
    "fadingvisual", "stark helper", "pulsevisuals", "luminar visuals",
    "prizrak visuals", "astrixvisuals", "adaptive visuals", "soup visual",
)
BANNED_VISUALS: tuple[str, ...] = (
    "plintusvisuals", "phantom visual", "shiny visuals", "pvp essentials refined",
    "zero visuals", "more visuals", "pvputils", "visual+", "k3d visuals",
    "enough visuals", "soup visual (pvp visual)",
)
MINIMAP_BANS: tuple[dict[str, str], ...] = (
    {"mod": "xaero's minimap", "rule": "версии >= 25.3.0 запрещены (инвиз на карте)"},
    {"mod": "labymod 4 minimap", "rule": "запрещён (инвиз на карте)"},
    {"mod": "voxelmap", "rule": "новые версии запрещены (инвиз на карте)"},
)

STORAGE_EXTS = (".jar", ".exe", ".zip", ".rar", ".dll")

# тулзы уровня мл. сотрудник (имена кнопок с mods.holyworld.me/applications)
ML_TOOLS: tuple[dict[str, str], ...] = (
    {"name": "Everything", "use": "поиск файлов по имени/весу/контенту"},
    {"name": "ShellBag", "use": "удаленные/открытые папки"},
    {"name": "RegScanner", "use": "дата последнего инжекта .dll (RecentDocs/.dll, OpenSavePidlMRU)"},
    {"name": "RecentFilesView", "use": "недавно открытые файлы, Execute Time"},
    {"name": "BrowserDownloadsView", "use": "загрузки браузеров, End Time"},
    {"name": "USBDriveLog", "use": "история флешек, Unplug Time после вызова = бан"},
    {"name": "LastActivityView", "use": "подозрительные .exe/.jar рядом с javaw"},
    {"name": "ExecutedProgramsList", "use": "история запусков .exe"},
    {"name": "System Informer", "use": "Network javaw 192.168.x.x, Unloaded modules DLL-веса, Modules, Strings javaw/DPS"},
    {"name": "JournalTrace", "use": "NTFS-журнал: чистка .minecraft/Downloads/Desktop/prefetch"},
    {"name": "Ocean", "use": "автопроверка системы (доп. к ручным)"},
    {"name": "VersionChecker", "use": "проверка версий майнкрафта"},
    {"name": "HolyCheck", "use": "скачивание всего набора разом"},
)
