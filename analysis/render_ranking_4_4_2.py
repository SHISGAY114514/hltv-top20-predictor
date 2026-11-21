"""Render a verified 4.4 snapshot to a single Chinese ranking poster (Windows / Pillow)."""
import argparse
import json
import os
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOTS = {"4.4.2": "463b1b66c3749110", "4.4.3": "36985ce4e8239e62"}


# These short captions describe the named player's results in this specific frozen snapshot.
CAPTIONS = {
    "ZywOo": "6 次 MVP、6 次 EVP。克拉科夫夺得 MVP，也是他的年度最高峰。",
    "donk": "3 次 MVP、6 次 EVP。电竞世界杯夺得 MVP，科隆 Major 打出 1.36 Rating。",
    "m0NESY": "科隆 Major 20 图打出 1.27 Rating 并获 MVP，另有 8 次 EVP。",
    "KSCERATO": "香港 Rivals 与雷电杯两夺 MVP，克拉科夫获第二 EVP。",
    "ropz": "鹿特丹 MVP 加上 6 次 EVP。鹿特丹三位队友的峰值按年终评语计入。",
    "flameZ": "5 次 EVP 中有 3 次第一 EVP，分别来自克卢日、Fort Worth 和 EPL S24。",
    "sh1ro": "共获 5 次 EVP。科隆 Major 14 图打出 1.24 Rating，录得个人年度最高峰。",
    "molodoy": "共获 6 次 EVP，科隆 Major 第五 EVP、电竞世界杯第三 EVP 都计入履历。",
    "w0nderful": "在亚特兰大夺得 MVP，又在 EPL S23 和北京两站获得第一 EVP。",
    "kyousuke": "科隆 Major 打满 20 图，获第一 EVP。CS 亚洲锦标赛也获第一 EVP。",
    "Wicadia": "科隆 Major 13 图打出 1.26 Rating，是他全年 4 次 EVP 中峰值最高的一站。",
    "Spinx": "BLAST Bounty S2 获 MVP，另有 4 次 EVP，其中 EPL S24 排第三。",
    "NiKo": "BLAST Bounty S1 获 MVP，科隆 Major 20 图打出 1.25 Rating，获第二 EVP。",
    "xertioN": "北京站夺得 MVP，阿斯塔纳获第二 EVP，全年另有两站 EVP。",
    "latto": "在 CS 亚洲锦标赛和 FISSURE Playground 3 两夺 MVP，另获 2 次 EVP。",
    "YEKINDAR": "在 PGL Masters 布加勒斯特站夺得 MVP，科隆 Major 获第六 EVP。",
    "makazze": "EPL S23 总决赛夺得 MVP，并在鹿特丹和 Fort Worth 两获 EVP。",
    "b1t": "亚特兰大获第一 EVP。科隆 Major 13 图打出 1.18 Rating，贡献年度最高峰。",
    "torzsi": "3 次 EVP 分别来自 BLAST Bounty S2、北京和克卢日，北京站峰值最高。",
    "HeavyGod": "科隆 Major 16 图打出 1.27 Rating，获第七 EVP，守住前 20 入围线。",
    "try": "电竞世界杯获第一 EVP。仅收录 72 张主赛事地图，样本覆盖落后于 HeavyGod。",
    "tN1R": "3 次 EVP 分别来自里约、波尔图和阿斯塔纳，里约站为第二 EVP。",
    "dem0n": "在电竞世界杯和 PGL 布加勒斯特站获 EVP，模型中的最高峰来自波尔图。",
    "xelex": "波尔图第二 EVP 和北京站 EVP 支撑了履历，也是他仅有的两站 EVP。",
    "PR": "两次 EVP 来自 PGL Masters 布加勒斯特站和北京站，前者是他的年度最高峰。",
    "yuurih": "科隆 Major 和里约各获一次 EVP，累计有 191 张主赛事地图进入模型。",
    "Magnojez": "雷电杯获第一 EVP，广州站获第五 EVP。两个奖项是本次履历的主要来源。",
    "910": "在克卢日与 CS 亚洲锦标赛两获 EVP，主赛事样本共 119 图。",
    "xfl0ud": "电竞世界杯获第六 EVP，主赛事样本共 53 图，领先下一名不足 0.1 分。",
    "dgt": "广州站获第一 EVP，阿斯塔纳站也是 EVP，以微弱优势守住第 30 名。",
}

PARTS = {"A": "荣誉", "E": "分档赛事表现", "O": "对强队表现", "K": "关键阶段",
         "P": "峰值", "C": "稳定性", "N": "样本覆盖", "H": "年度校正"}
INK, MUTED, PAPER = "#172c39", "#425a64", "#f9f8f2"
NAVY, ACCENT, TEAL = "#112f40", "#c26027", "#096c65"
WIDTH = 1080


@lru_cache(None)
def font(face, size):
    return ImageFont.truetype(str(Path(os.environ["WINDIR"]) / "Fonts" / face), size)


def render(version="4.4.2"):
    folder = ROOT / "output" / ("forecast_" + version.replace(".", "_"))
    source = folder / "snapshot" / SNAPSHOTS[version] / "scores.json"
    output = ROOT / "output/model_cards" / f"HTPM-{version}-ranking.png"
    data = json.loads(source.read_text(encoding="utf-8"))
    players = [p for p in data["players"] if p["eligible"]]
    assert data["version"] == f"HTPM-{version}" and data["cutoff"] == "2026-11-17"
    assert len(data["scope"]) == 23 and [p["rank"] for p in players] == list(range(1, 178))
    assert set(CAPTIONS) == {p["name"] for p in players[:30]}
    row_height, short_height, header_height, band_height, footer = 129, 52, 270, 68, 67
    height = header_height + 3*band_height + 30*row_height + 74*short_height + footer
    image = Image.new("RGB", (WIDTH, height), PAPER)
    draw = ImageDraw.Draw(image)
    cn, bold, latin, digits = "msyh.ttc", "msyhbd.ttc", "arialbd.ttf", "consola.ttf"

    def label(x, y, value, face, size, color, *, right=False, width=None):
        f = font(face, size)
        anchor = "rt" if right else "lt"
        bounds = draw.textbbox((x, y), value, font=f, anchor=anchor)
        assert bounds[0] >= 0 and bounds[2] < WIDTH and bounds[1] >= 0 and bounds[3] < height, value
        if width:
            assert bounds[2] - bounds[0] <= width, (value, bounds, width)
        draw.text((x, y), value, font=f, fill=color, anchor=anchor)

    def band(y, title, detail):
        draw.rectangle((0, y, WIDTH-1, y+band_height-1), fill=NAVY)
        draw.rectangle((0, y, 9, y+band_height-1), fill="#ed9e68")
        label(37, y+20, title, bold, 27, "white")
        label(1042, y+24, detail, cn, 20, "#c7dcdb", right=True)
        return y + band_height

    draw.rectangle((0, 0, WIDTH-1, header_height-1), fill="#e7eee7")
    draw.rectangle((38, 37, 46, 63), fill=TEAL)
    label(62, 38, f"HTPM   /   {version}", latin, 30, TEAL)
    label(1042, 41, "截至 2026.11.17", bold, 24, INK, right=True)
    label(34, 89, "2026 年度选手预测榜", bold, 65, NAVY)
    label(39, 188, "Counter-Strike 2", latin, 26, INK)
    label(302, 188, "23 项赛事   /   177 位选手", cn, 24, MUTED)
    label(1042, 192, "新加坡 Major 赛前预测", cn, 22, MUTED, right=True)
    label(39, 232, "前 30 名列出赛事依据、领先下一名的总分差，以及优势最大的两项分差。", cn, 19, MUTED)

    y = header_height
    drawn = []
    for i, p in enumerate(players[:30]):
        if i == 0:
            y = band(y, "第 1–20 名", "选手  /  顺位依据  /  模型分数")
        elif i == 20:
            y = band(y, "第 21–30 名", "选手  /  顺位依据  /  模型分数")
        following = players[i+1]
        if i % 2:
            draw.rectangle((0, y, WIDTH-1, y+row_height-1), fill="#f0f2ed")
        label(36, y+17, f"{p['rank']:02}", digits, 38, ACCENT if i < 3 else TEAL)
        label(118, y+15, p["name"], latin, 40, NAVY)
        label(1042, y+17, f"{p['score']:.3f}", digits, 37, NAVY, right=True)
        label(119, y+64, CAPTIONS[p["name"]], cn, 22, INK, width=923)
        differences = {k: p["contributions"][k] - following["contributions"][k] for k in PARTS}
        first, second = sorted(differences, key=differences.get, reverse=True)[:2]
        assert differences[second] > 0
        gap = p["score"] - following["score"]
        note = (f"领先 {following['name']} {gap:.3f} 分"
                f"　·　{PARTS[first]} +{differences[first]:.2f}　{PARTS[second]} +{differences[second]:.2f}")
        label(119, y+96, note, cn, 20, MUTED, width=923)
        drawn.append(p["rank"])
        y += row_height

    y = band(y, "第 31–177 名", "每行从左至右依次排列")
    start = y
    for i, p in enumerate(players[30:]):
        col, line = i % 2, i // 2
        x, y = col*540, start + line*short_height
        if line % 2 == 0 and col == 0:
            draw.rectangle((0, y, WIDTH-1, y+short_height-1), fill="#eaf0eb")
        label(x+37, y+13, f"{p['rank']:02}", digits, 26, TEAL)
        label(x+112, y+12, p["name"], latin, 28, INK, width=248)
        label(x+501, y+13, f"{p['score']:.3f}", digits, 26, INK, right=True)
        drawn.append(p["rank"])
    y += short_height
    draw.line((540, start, 540, y-1), fill="#cedad3", width=2)
    assert drawn == list(range(1, 178)) and y + footer == height
    draw.rectangle((0, y, WIDTH-1, height-1), fill=NAVY)
    label(37, y+21, f"HTPM {version}   /   独立模型预测", cn, 22, "#f8f7ee")
    label(1042, y+23, "总分保留三位小数，排序使用完整精度", cn, 20, "#d1dfdd", right=True)
    image.save(output, optimize=True)
    print(output, image.size)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", choices=SNAPSHOTS, default="4.4.2")
    render(parser.parse_args().model)
