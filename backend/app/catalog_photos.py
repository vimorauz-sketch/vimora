"""Stock photos that update-4 attached to services automatically.

They did not match the services well, so services now show hand-drawn illustrations instead.
`seed-catalog` removes exactly these automatic photos; anything an admin uploaded or chose is kept.
"""

from __future__ import annotations


def _img(photo_id: str) -> str:
    return f"https://images.unsplash.com/photo-{photo_id}?auto=format&fit=crop&w=900&q=70"


def _dl(short_id: str) -> str:
    # public Unsplash photo page id -> redirect to the image CDN
    return f"https://unsplash.com/photos/{short_id}/download?w=900"


P = {
    "laptop_typing": (_img("1486312338219-ce68d2c6f44d"), "Glenn Carstens-Peters"),
    "laptop_phone": (_img("1517430816045-df4b7de11d1d"), "freestocks"),
    "classroom": (_img("1569653402334-2e98fbaa80ee"), "sunrise University"),
    "repair_1": (_img("1629904853716-f0bc54eea481"), "Compagnons"),
    "code_screen": (_img("1504639725590-34d0984388bd"), "Kevin Ku"),
    "hardware": (_img("1610563166150-b34df4f3bcd6"), "Radowan Nakif Rehan"),
    "code_dark": (_img("1577375729152-4c8b5fcda381"), "Pakata Goh"),
    "repair_2": (_img("1629904853893-c2c8981a1dc5"), "Compagnons"),
    "devices": (_img("1619462572322-a28a773cbed5"), "Szabo Viktor"),
    "design_ui": (_img("1575089976121-8ed7b2a54265"), "Procreator"),
    "server": (_img("1640163561331-1b68a6474957"), "RUT MIIT"),
    "workspace_1": (_img("1556636530-6b7482d80e3d"), "Patrick Amoy"),
    "workspace_2": (_img("1603969409447-ba86143a03f6"), "Firosnv. Photography"),
    "desk": (_img("1467232004584-a241de8bcf5d"), "Lee Campbell"),
    "workspace_3": (_img("1723987135977-ae935608939e"), "Anastassia Anufrieva"),
    "paper_board": (_dl("N52kuG_koFo"), "Lauren Sauder"),
    "notebook": (_dl("AVWmtS-qK3Y"), "Unsplash"),
    "printer": (_dl("oPyAcpkQch0"), "Unsplash"),
    "printer_art": (_dl("BBJiJZgArZs"), "Unsplash"),
    "hands_typing": (_dl("c_TURbyrRic"), "Brett Wharton"),
    "keyboard": (_dl("A6QgqHWq2eQ"), "Michael Marais"),
    "mini_keyboard": (_dl("pfQaePVnga0"), "Unsplash"),
    "typewriter": (_dl("Pll7AP6NFpY"), "camilo jimenez"),
    "tablet_edit": (_dl("3ccTizXilxQ"), "Detail"),
    "video_edit": (_dl("2qu4YY3p-V4"), "dlxmedia.hu"),
    "web_code": (_dl("V4WcgOwOPY0"), "Peaky Frames"),
    "php_code": (_dl("ytZ2SJvNAxs"), "Unsplash"),
    "website": (_dl("mW-XyiuJPcs"), "Memento Media"),
    "phone_social": (_dl("2f_zK0ruzJE"), "Swello"),
    "phone_table": (_dl("Lddf7sR5jbk"), "Shutter Speed"),
    "phone_stats": (_dl("f0ySPhgyCWc"), "Unsplash"),
    "phone_data": (_dl("YRKUwWH_zL8"), "Unsplash"),
}

LEGACY_DEFAULT_URLS: frozenset[str] = frozenset(url for url, _ in P.values())
