"""Render the requested Top 30 explanation table as one white PNG."""
import json
import re
import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'output' / 'current'
OUT = DEST / 'HLTV_TOP30预测_2025依据版_2026-11-17_白底黑字.png'

# Text preserves the table delivered in the conversation. Scores and names are
# loaded from the frozen, Hong Kong-updated model output to prevent retyping drift.
TEXT = {
1: ('6 MVP＋6 EVP构成最厚的个人荣誉履历，包括克拉科夫、EPL S24等高质量MVP。Major Rating 1.45、超级精英1.63，最高舞台表现突出；Top5 1.26、Top10 1.32，强队表现和样本兼备。14项主赛中13项至少1.00；香港0.91是明显低谷。', '领先donk 6.084分，其中荣誉贡献领先3.186分、分档表现领先0.888分。年度均值略低于donk，并未抵消其更完整的赛事履历优势。'),
2: ('3 MVP＋6 EVP，包括波尔图、EWC及阿斯塔纳MVP，香港新增第二EVP。精英赛事Rating 1.43、Top5 1.27，个人输出极强。主赛151图、Elite以上82图；EPL S23的0.81属于明显低谷，但仅2图，按小样本处理。', '落后ZywOo主要在荣誉质量与整体分档表现；领先m0NESY 4.904分，主要来自荣誉和强队对抗优势，稳居第二。'),
3: ('科隆Major MVP＋8 EVP，最高等级荣誉突出，香港新增第四EVP。Top5 1.24、Top10 1.25；14项主赛全部至少1.00，兼有高峰和稳定下限。限制是其他最高级赛事输出、全年荣誉累积仍不及前二。', '领先KSCERATO 6.444分，荣誉贡献领先3.301分、强队对抗领先1.999分。Major MVP与多站高质量EVP，使他与第四名拉开明显距离。'),
4: ('2 MVP＋4 EVP，香港及Thunderpick MVP、克拉科夫第二EVP是主要支撑。主赛209图、Elite以上84图，样本充分；精英赛事1.22、Big赛事1.21。限制在Major仅1.12、Top5为1.13，最高舞台与最强对手输出尚不足以追赶前三。', '仅领先ropz 0.418分。两人荣誉模块几乎持平，KSCERATO主要靠更好的分档表现领先；第四、第五属于接近的位置。'),
5: ('1 MVP＋6 EVP，鹿特丹精英赛事MVP、EPL S24第二EVP及香港第三EVP提供支撑。Top5 1.17，主赛172图、Elite以上78图，13/14项主赛至少1.00。Major和超级精英均为1.11，最高档峰值不够突出。', '领先flameZ 1.257分，主要依靠荣誉贡献领先1.860分；低于KSCERATO则主要因为分档赛事表现稍弱。'),
6: ('5 EVP，其中EPL S24第一EVP、鹿特丹第二EVP、克拉科夫第三EVP质量较高。超级精英1.24、精英赛事1.23，Top5 1.15；13/14项主赛至少1.00。缺少MVP，Major仅1.08，波尔图0.96限制进一步上升。', '领先molodoy 2.688分，主要靠强队对抗和个人贡献调节后的团队成绩。虽然没有MVP，多个高质量EVP与充分样本仍支撑第六。'),
7: ('6 EVP，包含Major第五EVP、香港及PGL Masters第一EVP。主赛209图，16/17项主赛至少1.00，下限和参赛覆盖良好。主要短板是Top5仅1.02、精英赛事1.13，最强对抗输出不足。', '香港第一EVP使其由第八升至第七。目前领先sh1ro 1.699分，荣誉贡献优势2.456分足以抵消强队对抗劣势。'),
8: ('5 EVP，包括波尔图第一EVP，以及Major和克拉科夫荣誉。Major 1.24、超级精英1.30，最高档表现可靠；Top5 1.14。限制在Big赛事均值仅1.08，荣誉总量与顺位不及更前面的选手。', '领先w0nderful 1.820分，主要来自强队对抗和分档表现。对molodoy的强队优势未能抵消荣誉差距，因而排第八。'),
9: ('亚特兰大MVP＋3 EVP，EPL S23、北京第一EVP构成持续的Big赛事高峰，Big档均值1.25。主赛159图、Top10对抗101图，样本充足。Major仅1.05、克拉科夫0.82，最高赛事表现是主要短板。', '领先Spinx 2.275分，强队对抗贡献领先1.481分、荣誉领先0.627分；但最高等级赛事不足以支持追上sh1ro。'),
10: ('1 MVP＋4 EVP，Bounty S2 MVP、克拉科夫及两站精英赛事EVP提供基础。主赛186图、Elite以上68图，覆盖广。限制在Top5 1.01、Major 0.99，且16项主赛有3项低于1.00。', '领先kyousuke 1.155分，主要靠更厚的荣誉累积和样本覆盖；个人对强队的输出逊于后者，但综合履历暂时守住前十。'),
11: ('Major第一EVP＋另外2 EVP，最高等级个人高峰有分量；超级精英1.26，Top5、Top10均1.11。限制是精英与Big档均值仅1.11、1.13，里约及Thunderpick出现低谷，全年履历厚度不及前十。', '领先xertioN 0.404分，强队对抗贡献领先1.425分、分档表现领先0.464分，抵消了样本与稳定性劣势。'),
12: ('北京MVP＋3 EVP，Big档均值1.17；15/16项主赛至少1.00，主赛186图，稳定性和覆盖良好。短板是Top5仅1.00、超级精英1.00、精英1.08，面对最高难度时的输出下降。', '落后kyousuke主要在强队表现；领先NiKo 0.447分，主要靠更充分的样本和略高的荣誉贡献。第11—13名差距较小。'),
13: ('1 MVP＋2 EVP，科隆Major第二EVP、Major Rating 1.25是核心支撑。13/14项主赛至少1.00，下限较好。Bounty S1 MVP按既定规则乘0.60；Top5仅1.03、精英赛事1.09，限制总分。', '领先makazze 1.245分，主要来自分档表现与荣誉优势；未能超过xertioN，是因为样本和荣誉综合贡献稍低。'),
14: ('EPL S23 MVP＋2 EVP，包含鹿特丹精英赛事第三EVP。主赛159图，13/14项至少1.00，参赛覆盖与下限较好。Major 0.96、Top5 0.99，最重要赛事和最强对抗的表现限制上限。', '领先Wicadia 0.386分，主要靠样本质量和团队贡献；尽管荣誉模块低于Wicadia，完整履历仍使他略微领先。'),
15: ('4 EVP分布于Major、两站精英赛事及EPL S23，荣誉质量较好；Major 1.26是突出高峰。限制在克拉科夫0.92、北京0.88，Top10仅1.02，跨赛事起伏和强队输出仍有不足。', '领先latto仅0.239分。主要依靠更完整的高级赛事覆盖和略高荣誉分，抵消对方更好的强队表现；位置并不稳固。'),
16: ('2 MVP＋2 EVP，CAC和FPG3夺得MVP，Top5、Top10均1.15，13/14项主赛至少1.00，个人表现强。限制是两个MVP均属模型Medium档，Major仅8图，缺少超级精英样本，Elite以上总计40图。', '领先YEKINDAR 0.654分，主要靠强队对抗和个人荣誉。未能超过Wicadia，主要因为高等级赛事覆盖明显不足。'),
17: ('PGL Masters MVP＋Major第六EVP，Major 1.18；主赛209图、Elite以上84图，16/17项至少1.00，履历完整且下限稳定。主要短板为Top5仅0.95，精英及Big档均值均为1.08。', '仅领先b1t 0.078分。荣誉与团队贡献优势刚好抵消强队对抗和分档表现劣势，两人可视作非常接近。'),
18: ('亚特兰大第一EVP、北京第四EVP；Major与Big档均值均1.18，Top10 1.13，13/14项主赛至少1.00。限制是没有MVP、仅两项EVP，荣誉累积明显弱于前方部分选手。', '领先torzsi 1.987分，主要靠更好的强队对抗与分档赛事表现。与YEKINDAR几乎并列，差异主要来自荣誉与实际输出的取舍。'),
19: ('3 EVP，包括北京第二、Bounty S2第一及克卢日第三EVP。主赛186图、Top10对抗103图，样本充分。限制在Top5 1.00、Top10 1.04，且16项主赛仅11项至少1.00，里约0.84、鹿特丹0.85等低谷拉低分数。', '领先HeavyGod 1.953分，荣誉和样本优势足以抵消个人表现、强队对抗与稳定性劣势；当前比第20名拥有更明确的分数缓冲。'),
20: ('Major第七EVP＋FPG3第四EVP，Major 1.27，Top5 1.08、Top10 1.10；12/13项主赛至少1.00，个人表现和下限是支撑。短板是没有大赛MVP，主赛142图、Elite以上57图，荣誉与高级样本厚度有限。', '仅领先tN1R 0.014分。强队对抗和分档表现优势，刚好抵消荣誉、团队成绩和覆盖劣势。属于几乎并列的入榜边缘，不能视作稳进。'),
21: ('3 EVP，来自里约、波尔图和阿斯塔纳；主赛151图、Elite以上82图，荣誉和高级经历足够。限制在Major 0.96、Top10 1.01，13项主赛仅8项至少1.00，个人输出与稳定性弱于HeavyGod。', '距第20名仅0.014分，是第一候补；同时领先第22名3.118分，与HeavyGod构成相对独立的榜尾竞争组。'),
22: ('波尔图第二EVP＋北京第七EVP，有一项较高质量精英赛事荣誉；9/11项主赛至少1.00。限制在Major 0.91、没有超级精英主赛样本，精英档仅1.05。全年305图中，模型主赛事仅139图，总图数不能直接代表高级履历。', '领先PR仅0.061分，主要靠荣誉和稳定性；距第20名仍有3.131分，需要新增高质量表现才能实质接近入榜线。'),
23: ('PGL Masters第三EVP＋北京第六EVP；Top5 1.07、Top10 1.10，强队表现有支撑。限制是缺少Major及超级精英主赛样本，Elite以上仅38图；Bounty S1为0.78、EWC为0.86，下限存在缺口。', '个人输出与强队表现优于xelex，但荣誉和稳定性不足，略居其后；领先Magnojez 0.134分，主要靠覆盖与团队贡献。'),
24: ('Thunderpick第一EVP＋广州第五EVP；Big档1.16、Top5和Top10均1.10，个人输出有竞争力。限制在主赛仅96图、Elite以上25图，精英档只有12图且Rating 0.95，高级验证不足。', '距PR仅0.134分，强队表现和荣誉优势未能抵消样本与团队贡献劣势。领先yuurih 0.560分，主要凭更好的个人输出和稳定性。'),
25: ('Major第九EVP＋里约第四EVP，主赛209图、Elite以上84图，履历和覆盖充分。限制非常明确：Top5 0.95、Top10 0.97，精英档0.97、Big档0.99；17项主赛仅7项至少1.00，全年输出不足。', '样本和荣誉使他领先dem0n 0.404分；但较多比赛经历无法抵消实际表现偏低，因而仍低于样本更少、输出更强的Magnojez。'),
26: ('EWC第五EVP＋PGL Bucharest第三EVP，精英档均值1.22，有值得认可的高档赛事表现。限制在Major 0.98、Top10 1.02，11项主赛有4项低于1.00；荣誉总分较低，高峰尚未形成持续履历。', '领先910 0.868分，主要来自荣誉及团队贡献；低于yuurih则主要因为高级样本和荣誉累积不足。'),
27: ('克卢日第七EVP＋CAC第五EVP；11/13项主赛至少1.00，跨赛事下限较好，Major 1.06。限制是奖项顺位靠后，Top5 1.00、Top10 1.02，Elite以上仅36图，缺少足够强的高等级峰值。', '领先dziugss 0.688分，主要靠荣誉与分档表现；无法超过dem0n，是因为高质量个人荣誉和团队贡献仍有差距。'),
28: ('PGL Bucharest第一EVP，该站Rating 1.28；Major 1.12，提供了一定最高赛事表现支撑。限制是唯一荣誉来自Medium档，精英与Big档均值仅1.06、1.05，Top5与Top10均1.04，全年高质量高峰偏少。', '领先Jimpphat 0.370分，主要靠更好的强队对抗与样本质量；距第20名5.846分，现有荣誉厚度不足以形成直接竞争。'),
29: ('StarSeries第二EVP，精英和Big档均值均1.08，主赛122图、Elite以上53图，有一定履历基础。限制是只有一项EVP，缺少Major主赛样本，Top5 0.97，鹿特丹0.88、北京0.94等低谷也拉低评价。', '领先try仅0.253分，主要靠更完整的样本覆盖；个人荣誉和对强队的输出反而落后，当前排名对参数较敏感。'),
30: ('EWC第一EVP是高质量单站支撑；Top5、Top10均1.10，强队表现不差。主要限制是主赛仅80图、Elite以上32图、Top10对抗35图，缺少Major和超级精英主赛样本；一项高质量EVP尚不足以补齐全年履历。', '与Jimpphat相比，荣誉贡献领先1.525分、强队对抗领先1.433分，但样本质量落后3.121分，最终排第三十。距第20名6.468分。'),
}


def font(size, bold=False):
    return ImageFont.truetype(str(Path(os.environ['WINDIR']) / 'Fonts' / ('msyhbd.ttc' if bold else 'msyh.ttc')), size)


def wrap(text, face, width):
    lines = []
    for paragraph in text.split('\n'):
        line = ''
        for char in re.findall(r'[A-Za-z0-9]+(?:[./_-][A-Za-z0-9]+)*|.', paragraph):
            if line and face.getlength(line + char) > width:
                # Keep closing punctuation away from the beginning of a line.
                if char in '，。；：、？！）】》”':
                    line += char
                    lines.append(line)
                    line = ''
                else:
                    lines.append(line)
                    line = char
            else:
                line += char
        if line:
            lines.append(line)
    return lines


def main():
    rows = sorted((p for p in json.loads((ROOT/'output/current/evaluation.json').read_text(encoding='utf-8'))['players'] if p.get('rank') and p['rank'] <= 30), key=lambda p:p['rank'])
    assert len(rows) == len(TEXT) == 30
    width, margin, pad, line_height = 3600, 70, 30, 60
    col_widths = [140, 295, 225, 1640, 1160]
    assert sum(col_widths) == width - 2 * margin
    faces = [font(44, True), font(42, True), font(42, True), font(40), font(40)]
    row_layouts = []
    for row in rows:
        values = [str(row['rank']), row['name'], format(row['score'], '.3f'), *TEXT[row['rank']]]
        lines = [wrap(value, face, cell_width - 2*pad - (50 if i >= 3 else 8)) for i, (value, face, cell_width) in enumerate(zip(values, faces, col_widths))]
        height = max(180, max(map(len, lines)) * line_height + 2*pad)
        row_layouts.append((values, lines, height))
    table_top, header_height = 475, 118
    footnotes = [
        '模型：2025依据版 HTPM 3.5；预测对象：2026年；快照日期：2026年11月17日；香港荣誉已补齐。',
        '综合分 S＝0.30A＋0.27E＋0.23O＋0.05T＋0.05C＋0.10N。A荣誉，E分档表现，O强队对抗，T团队贡献，C稳定性，N样本质量。',
        'Rating为原始统计，实际计分经过样本收缩；稳定性指跨赛事下限。第21—30名是候补顺序，积分不是入榜概率。',
        '相邻名次贡献差是同一模型内的算术解释。特别接近的位置：4—5、11—13、14—18、20—21、22—24；HeavyGod与tN1R仅差约0.014分。',
        '当前结果未模拟剩余赛程；缺少全池同口径的关键阶段数据，未单独加入淘汰赛评分。模型为研究假设，并非HLTV官方公式。',
        '数据与逐人完整计算：工作区 output/current/evaluation.json 与 scores.json。',
    ]
    footfont = font(34)
    foot_lines = [wrap(t, footfont, width - 2*margin) for t in footnotes]
    table_bottom = table_top + header_height + sum(r[2] for r in row_layouts)
    height = table_bottom + 72 + sum(len(lines)*51 + 18 for lines in foot_lines) + 65
    canvas = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(canvas)
    draw.text((margin, 58), '2026 HLTV TOP30 预测及详细理由', font=font(88, True), fill='black')
    draw.text((margin, 190), '2025依据版 HTPM 3.5  ｜  截至2026年11月17日  ｜  香港荣誉更新后', font=font(45, True), fill='black')
    intro = '满分100，积分保留三位小数。综合考虑个人荣誉、分档赛事表现、强队对抗、团队贡献、跨赛事稳定性与样本质量。'
    for i, line in enumerate(wrap(intro, font(38), width-2*margin)):
        draw.text((margin, 285+i*57), line, font=font(38), fill='black')
    headers = ['排名', '选手', '积分', '主要支撑与限制因素', '为什么处在这个位置']
    edges = [margin]
    for w in col_widths:
        edges.append(edges[-1] + w)
    for i, label in enumerate(headers):
        f = font(42, True)
        draw.text(((edges[i]+edges[i+1]-f.getlength(label))/2, table_top+29), label, font=f, fill='black')
    y = table_top + header_height
    draw.line((margin, table_top, width-margin, table_top), fill='black', width=3)
    draw.line((margin, y, width-margin, y), fill='black', width=3)
    for row, (_, lines, row_height) in zip(rows, row_layouts):
        for i, (cell_lines, face) in enumerate(zip(lines, faces)):
            text_y = y + (row_height - len(cell_lines)*line_height)/2
            for line in cell_lines:
                text_x = ((edges[i]+edges[i+1]-face.getlength(line))/2) if i < 3 else edges[i]+pad
                assert text_x >= edges[i]
                assert text_x + face.getlength(line) <= edges[i+1]-12
                draw.text((text_x, text_y), line, font=face, fill='black')
                text_y += line_height
        y += row_height
        draw.line((margin, y, width-margin, y), fill='black', width=5 if row['rank'] == 20 else 2)
    for x in edges:
        draw.line((x, table_top, x, table_bottom), fill='black', width=2)
    y = table_bottom + 60
    for lines in foot_lines:
        for line in lines:
            draw.text((margin, y), line, font=footfont, fill='black')
            y += 51
        y += 18
    DEST.mkdir(parents=True, exist_ok=True)
    canvas.save(OUT, dpi=(220, 220), optimize=True)
    qa = ROOT/'output/qa_top30_image'
    qa.mkdir(parents=True, exist_ok=True)
    # Review-only contact sheet plus original-resolution slices.
    thumb = canvas.copy()
    thumb.thumbnail((1400, 5500))
    thumb.save(qa/'overview.png')
    for i, top in enumerate(range(0, height, 1800), 1):
        canvas.crop((0, top, width, min(top+1800, height))).save(qa/f'slice-{i}.png')
    print(json.dumps({'path':str(OUT), 'width':width, 'height':height, 'bytes':OUT.stat().st_size, 'qa_slices':(height+1799)//1800},ensure_ascii=False))


if __name__ == '__main__':
    main()
