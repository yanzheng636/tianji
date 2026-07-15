"""古籍知识图谱的人工策划目录。

这里只放稳定、可解释的领域定义，不调用任何 LLM。书中未命中的概念不会输出，
避免生成没有原典证据的空知识页。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DomainSpec:
    slug: str
    name: str
    description: str


@dataclass(frozen=True)
class IntentSpec:
    slug: str
    name: str
    description: str
    keywords: tuple[str, ...]
    preferred_domains: tuple[str, ...]


@dataclass(frozen=True)
class ConceptSpec:
    slug: str
    name: str
    domain: str
    definition: str
    keywords: tuple[str, ...]
    aliases: tuple[str, ...] = ()
    intents: tuple[str, ...] = ()
    relations: tuple[tuple[str, str], ...] = ()

    @property
    def node_id(self) -> str:
        return f"concept:{self.domain}:{self.slug}"


DOMAINS: tuple[DomainSpec, ...] = (
    DomainSpec("qian", "签筒灵签", "签诗、签级、签解、占验及具体所问事项的解释体系。"),
    DomainSpec("bazi", "八字命理", "以干支、五行、十神、格局、旺衰和运限解释命局的传统体系。"),
    DomainSpec("physiognomy", "相法", "以形貌、骨格、五官、气色及掌纹等观察人的传统相法体系。"),
    DomainSpec("divination", "易占", "以卦象、爻变、体用和六爻取用等方法进行占断的传统体系。"),
    DomainSpec("cultivation", "修身劝善", "以改过、积善、谦德、因果和处世格言提供行动劝勉。"),
)


INTENTS: tuple[IntentSpec, ...] = (
    IntentSpec("exam", "升学考试", "文殊殿入口：考试、学业、智慧与功名。", ("考试", "科甲", "功名", "文昌", "登科", "学业", "读书", "聪明"), ("bazi", "qian", "cultivation")),
    IntentSpec("love", "姻缘感情", "月老祠入口：姻缘、婚姻、夫妻和感情关系。", ("姻缘", "婚姻", "夫妻", "桃花", "感情", "配偶", "妻", "夫"), ("bazi", "qian", "divination")),
    IntentSpec("wealth", "财运财帛", "财神殿入口：求财、正偏财、财帛和田宅。", ("财", "財", "富", "田宅", "求财", "求財", "财帛", "財帛", "金银", "金銀"), ("bazi", "qian", "divination")),
    IntentSpec("career", "事业官禄", "财神殿入口：事业、官禄、职位、谋事和贵人。", ("事业", "事業", "官禄", "官祿", "仕", "升迁", "升遷", "职位", "職位", "贵人", "貴人", "谋事", "謀事"), ("bazi", "qian", "divination")),
    IntentSpec("health", "健康寿命", "健康、疾病、气色、精神和寿夭相关内容。", ("健康", "疾病", "病", "寿", "壽", "气色", "氣色", "精神", "夭"), ("bazi", "qian", "physiognomy", "cultivation")),
    IntentSpec("natal", "本命命理", "天机殿入口：本命、八字、相貌和个人禀赋。", ("本命", "命局", "八字", "日主", "格局", "面相", "手相", "骨格"), ("bazi", "physiognomy")),
    IntentSpec("divination", "问卦占断", "问卦入口：卦象、爻变、取用和吉凶判断。", ("问卦", "問卦", "占", "卦", "爻", "吉凶", "用神"), ("divination", "qian")),
    IntentSpec("cultivation", "修身劝勉", "许愿池及无精确命中时的行动建议与劝勉。", ("修身", "劝善", "勸善", "积德", "積德", "改过", "改過", "行善", "谦", "謙"), ("cultivation",)),
    IntentSpec("general", "通用", "不属于单一殿堂的通用古籍知识。", (), tuple(d.slug for d in DOMAINS)),
)


CONCEPTS: tuple[ConceptSpec, ...] = (
    # 八字命理
    ConceptSpec("yin-yang", "阴阳", "bazi", "古代用相对、互根与消长关系说明事物性质的基本范畴。", ("阴阳", "陰陽"), intents=("natal",)),
    ConceptSpec("five-elements", "五行", "bazi", "木、火、土、金、水五类性质及其生克关系。", ("五行", "金木水火土"), intents=("natal",)),
    ConceptSpec("generation-restraint", "生克制化", "bazi", "五行之间相生、相克以及因组合产生制约和转化的关系。", ("生克", "相生", "相克", "制化"), intents=("natal",), relations=(("depends_on", "five-elements"),)),
    ConceptSpec("heavenly-stems", "天干", "bazi", "甲乙丙丁戊己庚辛壬癸十个干符号及其阴阳五行属性。", ("天干", "十干", "甲乙丙丁戊己庚辛壬癸"), intents=("natal",)),
    ConceptSpec("earthly-branches", "地支", "bazi", "子丑寅卯辰巳午未申酉戌亥十二个支符号及其五行、时序关系。", ("地支", "十二支", "子丑寅卯辰巳午未申酉戌亥"), intents=("natal",)),
    ConceptSpec("ganzhi", "干支", "bazi", "天干与地支配合形成的纪时和命理表达系统。", ("干支",), intents=("natal",), relations=(("part_of", "heavenly-stems"), ("part_of", "earthly-branches"))),
    ConceptSpec("day-master", "日主", "bazi", "八字日柱天干，传统命理以此作为分析命局关系的中心。", ("日主", "日元", "日干"), aliases=("日元", "日干"), intents=("natal",)),
    ConceptSpec("month-command", "月令", "bazi", "出生月份地支所代表的季节气势，常用于判断五行旺衰。", ("月令", "月建"), aliases=("月建",), intents=("natal",), relations=(("depends_on", "earthly-branches"),)),
    ConceptSpec("strength", "旺衰强弱", "bazi", "依据月令、根气、生扶克泄等判断日主及五行力量状态。", ("旺衰", "强弱", "強弱", "身旺", "身弱", "衰旺"), intents=("natal",), relations=(("depends_on", "day-master"), ("depends_on", "month-command"))),
    ConceptSpec("useful-god", "八字用神", "bazi", "命理分析中为调节命局偏颇、成就格局而选取的关键五行或十神。", ("用神",), intents=("natal",), relations=(("depends_on", "strength"), ("depends_on", "pattern"))),
    ConceptSpec("favorable-god", "喜神", "bazi", "对命局有辅助或增益作用、通常配合用神发挥作用的五行或十神。", ("喜神", "喜用"), intents=("natal",), relations=(("depends_on", "useful-god"),)),
    ConceptSpec("taboo-god", "忌神", "bazi", "在特定命局中加重偏颇或破坏格局、需要避免增助的五行或十神。", ("忌神",), intents=("natal",), relations=(("contrasts_with", "useful-god"),)),
    ConceptSpec("pattern", "格局", "bazi", "依据月令、十神配置与气势对命局结构所作的类型化归纳。", ("格局", "成格", "破格"), intents=("natal",), relations=(("depends_on", "month-command"),)),
    ConceptSpec("ten-gods", "十神", "bazi", "以日主为中心，按其他干支与日主的生克及阴阳关系建立的十类关系。", ("十神", "十星"), aliases=("十星",), intents=("natal",)),
    ConceptSpec("peer", "比肩", "bazi", "与日主五行、阴阳相同的十神。", ("比肩",), intents=("career", "wealth", "natal"), relations=(("is_a", "ten-gods"),)),
    ConceptSpec("rob-wealth", "劫财", "bazi", "与日主五行相同而阴阳相异的十神。", ("劫财", "劫財"), intents=("wealth", "natal"), relations=(("is_a", "ten-gods"),)),
    ConceptSpec("eating-god", "食神", "bazi", "日主所生且阴阳相同的十神。", ("食神",), intents=("career", "health", "natal"), relations=(("is_a", "ten-gods"),)),
    ConceptSpec("hurting-officer", "伤官", "bazi", "日主所生且阴阳相异的十神。", ("伤官", "傷官"), intents=("career", "natal"), relations=(("is_a", "ten-gods"),)),
    ConceptSpec("indirect-wealth", "偏财", "bazi", "日主所克且阴阳相同的十神。", ("偏财", "偏財"), intents=("wealth", "love", "natal"), relations=(("is_a", "ten-gods"),)),
    ConceptSpec("direct-wealth", "正财", "bazi", "日主所克且阴阳相异的十神。", ("正财", "正財"), intents=("wealth", "love", "natal"), relations=(("is_a", "ten-gods"),)),
    ConceptSpec("seven-killings", "七杀", "bazi", "克日主且阴阳相同的十神，又称偏官。", ("七杀", "七殺", "偏官"), aliases=("偏官",), intents=("career", "health", "natal"), relations=(("is_a", "ten-gods"),)),
    ConceptSpec("direct-officer", "正官", "bazi", "克日主且阴阳相异的十神。", ("正官", "官星"), intents=("career", "love", "natal"), relations=(("is_a", "ten-gods"),)),
    ConceptSpec("indirect-resource", "偏印", "bazi", "生日主且阴阳相同的十神，又称枭神。", ("偏印", "枭神", "梟神"), aliases=("枭神",), intents=("exam", "natal"), relations=(("is_a", "ten-gods"),)),
    ConceptSpec("direct-resource", "正印", "bazi", "生日主且阴阳相异的十神，也常称印绶。", ("正印", "印绶", "印綬"), aliases=("印绶",), intents=("exam", "career", "natal"), relations=(("is_a", "ten-gods"),)),
    ConceptSpec("six-relatives", "六亲", "bazi", "以十神和宫位映射父母、兄弟、配偶、子女等亲属关系。", ("六亲", "六親"), intents=("love", "natal"), relations=(("depends_on", "ten-gods"),)),
    ConceptSpec("luck-cycle", "大运", "bazi", "按出生信息排出的阶段性运程序列。", ("大运", "大運"), intents=("career", "wealth", "love", "health", "natal"), relations=(("depends_on", "ganzhi"),)),
    ConceptSpec("annual-luck", "流年", "bazi", "以某一年的干支与原命局、运程发生作用来讨论年度变化。", ("流年", "太岁"), intents=("career", "wealth", "love", "health", "natal"), relations=(("depends_on", "ganzhi"), ("depends_on", "luck-cycle"))),
    ConceptSpec("hidden-stems", "藏干", "bazi", "地支内部所含天干的传统命理表达，用于补充地支五行与十神关系。", ("藏干", "人元"), intents=("natal",), relations=(("part_of", "earthly-branches"), ("depends_on", "heavenly-stems"))),
    ConceptSpec("nayin", "纳音", "bazi", "六十甲子各组对应的传统五行名目，属于干支系统的附加分类。", ("纳音", "納音", "六十花甲纳音", "六十花甲納音"), intents=("natal",), relations=(("depends_on", "ganzhi"),)),
    ConceptSpec("seasonal-adjustment", "调候", "bazi", "结合出生季节寒暖燥湿讨论命局所需五行的取用路径。", ("调候", "調候", "寒暖燥湿", "寒暖燥濕"), intents=("health", "natal"), relations=(("depends_on", "month-command"), ("depends_on", "useful-god"))),
    ConceptSpec("auxiliary-stars", "神煞", "bazi", "由干支组合推得的辅助性传统标记，须与命局主体结构合看。", ("神煞", "贵人", "貴人", "禄马", "祿馬"), intents=("career", "love", "health", "natal"), relations=(("depends_on", "ganzhi"),)),
    ConceptSpec("peach-blossom", "桃花", "bazi", "传统命理中与人缘、情感或风流倾向相关的一类神煞称谓。", ("桃花", "咸池"), aliases=("咸池",), intents=("love", "natal")),
    ConceptSpec("wenchang", "文昌", "bazi", "传统命理中与文才、学习和科名相关的神煞称谓。", ("文昌", "文曲"), intents=("exam", "natal")),

    # 易占
    ConceptSpec("trigrams", "八卦", "divination", "乾、兑、离、震、巽、坎、艮、坤八个基本卦象。", ("八卦", "乾兑离震巽坎艮坤"), intents=("divination",)),
    ConceptSpec("hexagram", "六十四卦", "divination", "由上下两个三爻卦组合形成的六十四种卦象。", ("六十四卦", "重卦"), intents=("divination",), relations=(("depends_on", "trigrams"),)),
    ConceptSpec("images-numbers", "象数", "divination", "以卦象所取的形象和数理关系进行推演的易学路径。", ("象数", "象數"), intents=("divination",), relations=(("depends_on", "trigrams"),)),
    ConceptSpec("body-function", "体用", "divination", "梅花易数中区分主体与所问对象，并据生克判断关系的方法。", ("体用", "體用", "体卦", "體卦", "用卦"), intents=("divination",), relations=(("depends_on", "generation-restraint"),)),
    ConceptSpec("mutual-hexagram", "互卦", "divination", "从本卦中间爻位重新组合得到、用于观察过程的卦象。", ("互卦",), intents=("divination",), relations=(("part_of", "hexagram"),)),
    ConceptSpec("changed-hexagram", "变卦", "divination", "动爻阴阳变化后形成、用于观察变化结果的卦象。", ("变卦", "變卦", "之卦"), intents=("divination",), relations=(("depends_on", "moving-line"),)),
    ConceptSpec("moving-line", "动爻", "divination", "占得卦中发生阴阳变化的爻位。", ("动爻", "動爻", "变爻", "變爻"), intents=("divination",), relations=(("part_of", "hexagram"),)),
    ConceptSpec("innate-trigrams", "先天八卦", "divination", "传统上归于伏羲次序、常用于象数关系的八卦排列。", ("先天八卦", "伏羲八卦"), intents=("divination",), relations=(("is_a", "trigrams"),)),
    ConceptSpec("later-trigrams", "后天八卦", "divination", "传统上归于文王次序、常用于方位与时序的八卦排列。", ("后天八卦", "後天八卦", "文王八卦"), intents=("divination",), relations=(("is_a", "trigrams"),)),
    ConceptSpec("six-lines", "六爻", "divination", "以六个爻位、干支、六亲等要素进行判断的占卜体系。", ("六爻", "六畫"), intents=("divination",), relations=(("depends_on", "hexagram"),)),
    ConceptSpec("divination-useful-god", "六爻用神", "divination", "六爻占断中依据所问事项选定的核心爻或六亲类别。", ("用神", "取用神"), intents=("divination",), relations=(("depends_on", "six-lines"),)),
    ConceptSpec("original-spirit", "原神", "divination", "六爻体系中生助用神的五行或爻。", ("原神",), intents=("divination",), relations=(("depends_on", "divination-useful-god"),)),
    ConceptSpec("avoid-spirit", "忌神", "divination", "六爻体系中克制用神的五行或爻。", ("忌神",), intents=("divination",), relations=(("contrasts_with", "original-spirit"), ("depends_on", "divination-useful-god"))),
    ConceptSpec("enemy-spirit", "仇神", "divination", "六爻体系中生助忌神或克制原神、间接不利用神的五行或爻。", ("仇神",), intents=("divination",), relations=(("depends_on", "avoid-spirit"),)),
    ConceptSpec("world-response", "世应", "divination", "六爻卦中用世爻与应爻表示主客、自他或双方关系的框架。", ("世应", "世爻", "应爻", "應爻"), intents=("divination",), relations=(("part_of", "six-lines"),)),
    ConceptSpec("six-relatives-lines", "六亲取象", "divination", "以父母、兄弟、官鬼、妻财、子孙五类六亲映射所问对象。", ("六亲", "六親", "父母爻", "兄弟爻", "官鬼", "妻财", "妻財", "子孙", "子孫"), intents=("divination",), relations=(("used_by", "divination-useful-god"),)),
    ConceptSpec("flying-spirit", "飞神", "divination", "伏神之上或内外动静关系中显露并作用于伏神、本爻的爻。", ("飞神", "飛神"), intents=("divination",), relations=(("part_of", "six-lines"),)),
    ConceptSpec("hidden-spirit", "伏神", "divination", "所需六亲未在本卦显现时，依本宫首卦定位的隐藏用爻。", ("伏神", "伏藏", "伏而不现", "伏而不現"), intents=("divination",), relations=(("contrasts_with", "flying-spirit"), ("depends_on", "divination-useful-god"))),
    ConceptSpec("month-break", "月破", "divination", "卦爻与月建相冲所形成的状态，须结合动静、生克和填合讨论。", ("月破", "破爻", "出破", "填实", "填實"), intents=("divination",), relations=(("part_of", "six-lines"),)),
    ConceptSpec("void-in-decade", "旬空", "divination", "六十甲子每旬所缺两支对应的空亡状态，传统占断结合出旬、冲实等条件判断。", ("旬空", "空亡", "出空", "填空"), intents=("divination",), relations=(("part_of", "six-lines"),)),
    ConceptSpec("advance-retreat", "进退神", "divination", "动爻变为同五行相邻地支时，用进神、退神描述力量趋进或趋退。", ("进神", "進神", "退神", "进退神", "進退神"), intents=("divination",), relations=(("depends_on", "moving-line"),)),
    ConceptSpec("reverse-repeat", "反吟伏吟", "divination", "卦爻变化中以冲反复或原位重复表示反复、迟滞等过程的传统术语。", ("反吟", "伏吟"), intents=("divination",), relations=(("depends_on", "changed-hexagram"),)),
    ConceptSpec("three-harmony", "三合成局", "divination", "三个地支会合成五行局势，用于讨论多爻共同作用。", ("三合", "三合局", "会局", "會局"), intents=("divination",), relations=(("depends_on", "six-lines"),)),
    ConceptSpec("six-clash-harmony", "六冲六合", "divination", "卦与爻的六冲、六合关系，用于观察离合、快慢与反复。", ("六冲", "六沖", "六合", "六冲卦", "六合卦"), intents=("divination",), relations=(("depends_on", "hexagram"),)),
    ConceptSpec("six-beasts", "六兽", "divination", "青龙、朱雀、勾陈、螣蛇、白虎、玄武六类辅助取象。", ("六兽", "六獸", "青龙", "青龍", "朱雀", "勾陈", "勾陳", "螣蛇", "白虎", "玄武"), intents=("divination",), relations=(("part_of", "six-lines"),)),

    # 相法
    ConceptSpec("physiognomy", "相法", "physiognomy", "通过形貌、骨格、神气和气色等作传统观察与判断的方法体系。", ("相法", "相人", "观相", "觀相"), intents=("natal",)),
    ConceptSpec("face", "面相", "physiognomy", "以面部形态、部位和气色为主要对象的相法分支。", ("面相", "面部"), intents=("natal",), relations=(("is_a", "physiognomy"),)),
    ConceptSpec("palm", "手相", "physiognomy", "以手形、掌丘和掌纹为主要对象的相法分支。", ("手相", "掌相", "相掌"), aliases=("掌相",), intents=("natal",), relations=(("is_a", "physiognomy"),)),
    ConceptSpec("palm-lines", "掌纹", "physiognomy", "手掌上的纹理及其位置、形态，是传统手相观察要素。", ("掌纹", "掌中纹", "手纹"), intents=("natal",), relations=(("part_of", "palm"),)),
    ConceptSpec("five-officials", "五官", "physiognomy", "相法中对耳、眉、眼、鼻、口等面部要素的合称。", ("五官",), intents=("natal",), relations=(("part_of", "face"),)),
    ConceptSpec("three-regions", "三停", "physiognomy", "将面部或身体分为上、中、下三段观察比例与阶段的相法框架。", ("三停", "三庭"), aliases=("三庭",), intents=("natal",), relations=(("part_of", "face"),)),
    ConceptSpec("five-mountains", "五岳", "physiognomy", "相法把额、鼻、颏及两颧比作五岳，用于观察面部骨势。", ("五岳", "五嶽"), intents=("natal",), relations=(("part_of", "face"),)),
    ConceptSpec("twelve-palaces", "十二宫", "physiognomy", "相法按人生事项划分的十二个面部观察区域。", ("十二宫", "十二宮"), intents=("career", "wealth", "love", "health", "natal"), relations=(("part_of", "face"),)),
    ConceptSpec("complexion", "气色", "physiognomy", "相法中观察面部色泽、明暗、润枯及其变化的要素。", ("气色", "氣色", "色气", "色氣"), intents=("health", "natal"), relations=(("part_of", "face"),)),
    ConceptSpec("yintang", "印堂", "physiognomy", "两眉之间的面部区域，相法常结合形态和气色观察。", ("印堂", "命宫", "命宮"), intents=("career", "health", "natal"), relations=(("part_of", "twelve-palaces"),)),
    ConceptSpec("mingtang", "明堂", "physiognomy", "相法中对面部或掌中特定开阔区域的称谓，具体所指依体系而异。", ("明堂",), intents=("wealth", "natal")),
    ConceptSpec("bone-structure", "骨格", "physiognomy", "相法对头面及身体骨势、形局和支撑感的整体观察。", ("骨格", "骨法", "骨相"), intents=("health", "natal"), relations=(("part_of", "physiognomy"),)),
    ConceptSpec("spirit-vitality", "神气", "physiognomy", "相法对人的精神状态、眼神、举止和整体生命感的观察。", ("神气", "神氣", "精神"), intents=("health", "natal"), relations=(("part_of", "physiognomy"),)),
    ConceptSpec("wealth-palace", "财帛宫", "physiognomy", "相法十二宫中与财帛事项相关的观察区域。", ("财帛宫", "財帛宮", "财帛", "財帛"), intents=("wealth", "natal"), relations=(("is_a", "twelve-palaces"),)),
    ConceptSpec("career-palace", "官禄宫", "physiognomy", "相法十二宫中与事业、职位相关的观察区域。", ("官禄宫", "官祿宮", "官禄", "官祿"), intents=("career", "natal"), relations=(("is_a", "twelve-palaces"),)),
    ConceptSpec("marriage-palace", "夫妻宫", "physiognomy", "相法十二宫中与婚姻、配偶关系相关的观察区域。", ("夫妻宫", "夫妻宮", "妻妾宫", "妻妾宮"), intents=("love", "natal"), relations=(("is_a", "twelve-palaces"),)),
    ConceptSpec("six-departments-three-talents", "六府三才", "physiognomy", "以两辅骨、两颧骨、两颐骨为六府，并结合额、鼻、颏三才观察面部配合。", ("六府", "三才", "六府三才"), intents=("career", "wealth", "natal"), relations=(("part_of", "face"), ("depends_on", "bone-structure"))),
    ConceptSpec("five-stars-six-luminaries", "五星六曜", "physiognomy", "以五官及眉、月孛等部位配名五星六曜的传统面部分类。", ("五星", "六曜", "五星六曜", "五星六矅"), intents=("natal",), relations=(("part_of", "face"),)),
    ConceptSpec("physiognomy-annual-limit", "流年运限", "physiognomy", "按面部年龄部位讨论不同岁数阶段变化的相法框架。", ("流年运限", "流年運限", "流年部位", "运限", "運限"), intents=("career", "wealth", "love", "health", "natal"), relations=(("used_by", "face"),)),
    ConceptSpec("moles", "痣相", "physiognomy", "观察痣的位置、色泽和形态的传统相法分支。", ("痣相", "痣", "黑痣", "面痣"), intents=("health", "natal"), relations=(("part_of", "physiognomy"),)),
    ConceptSpec("occipital-bone", "玉枕骨", "physiognomy", "相法对后脑枕骨形态的传统称谓与分类。", ("玉枕", "枕骨", "玉枕骨"), intents=("career", "health", "natal"), relations=(("part_of", "bone-structure"),)),

    # 灵签
    ConceptSpec("qian-poem", "签诗", "qian", "签条上的韵文正文，是解签时首先引用的文本。", ("签诗", "籤詩", "诗曰", "詩曰"), intents=("divination",)),
    ConceptSpec("qian-level", "签级", "qian", "大吉、上吉、中平、下下等对签意总体倾向的等级标记。", ("大吉", "上吉", "中吉", "中平", "下下"), intents=("divination",)),
    ConceptSpec(
        "sacred-meaning", "圣意", "qian",
        "灵签文本中按功名、婚姻、疾病、诉讼等事项给出的简要断语。",
        (
            "圣意", "聖意", "功名", "求财", "求財", "财运", "財運", "婚姻", "姻缘", "姻緣",
            "疾病", "健康", "事业", "事業", "考试", "學業", "学业", "上岸",
        ),
        intents=("exam", "career", "wealth", "love", "health", "divination"),
    ),
    ConceptSpec("qian-explanation", "解曰", "qian", "对签诗含义、适用事项和吉凶条件所作的解释。", ("解曰", "签解", "籤解"), intents=("divination",)),
    ConceptSpec("qian-interpretation", "释义", "qian", "对签诗用典、语义和占断边界所作的进一步阐释。", ("释义", "釋義"), intents=("divination",)),
    ConceptSpec("qian-verification", "占验", "qian", "记录抽得某签后的实际经历，用来说明传统解签如何对应事件。", ("占验", "占驗"), intents=("divination",)),

    # 修身劝善
    ConceptSpec("establish-destiny", "立命", "cultivation", "强调通过反省、选择和持续行动建立人生方向，而非消极等待命数。", ("立命", "造命", "命自我立", "命由我作"), intents=("cultivation", "natal")),
    ConceptSpec("reform", "改过", "cultivation", "发现自身过失后，从认知、行为和习惯上持续修正。", ("改过", "改過", "改恶", "改惡"), intents=("cultivation",)),
    ConceptSpec("accumulate-good", "积善", "cultivation", "通过持续行善、利人和减少伤害积累德行。", ("积善", "積善", "行善", "善行", "积德", "積德"), intents=("cultivation",)),
    ConceptSpec("cause-effect", "因果感应", "cultivation", "善恶行为与其后果相联系的传统伦理解释框架。", ("因果", "感应", "感應", "报应", "報應", "福报", "福報"), intents=("cultivation",)),
    ConceptSpec("humility", "谦德", "cultivation", "以谦逊、不自满和尊重他人为核心的修身原则。", ("谦", "謙", "谦德", "謙德", "谦虚", "謙虛"), intents=("exam", "career", "cultivation")),
    ConceptSpec("self-reflection", "自省", "cultivation", "经常检点自己的念头和行为，并据此修正过失。", ("自省", "反省", "省察", "检点", "檢點"), intents=("cultivation",), relations=(("used_by", "reform"),)),
    ConceptSpec("filial-piety", "孝悌", "cultivation", "敬爱父母、友爱兄弟的传统家庭伦理原则。", ("孝悌", "孝顺", "孝順", "父母"), intents=("love", "cultivation")),
    ConceptSpec("speech-conduct", "谨言慎行", "cultivation", "约束言语和行为，减少轻率、欺骗与伤害。", ("慎言", "谨言", "謹言", "慎行", "妄语", "妄語"), intents=("career", "love", "cultivation")),
    ConceptSpec("benevolence", "仁善", "cultivation", "体恤他人、减少伤害并主动利人的道德取向。", ("仁慈", "仁爱", "仁愛", "慈悲", "利人"), intents=("love", "cultivation")),
)


DOMAIN_BY_SLUG = {item.slug: item for item in DOMAINS}
INTENT_BY_SLUG = {item.slug: item for item in INTENTS}
CONCEPT_BY_ID = {item.node_id: item for item in CONCEPTS}
