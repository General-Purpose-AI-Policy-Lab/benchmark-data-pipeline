"""Draft lineage alias-map builder. Auto-proposes raw model_version → (vendor,
chain, release_node, variant, in_chain) from the decisions in LINEAGE_PLAN.md.
Output is reviewed, not trusted blindly (regex leaks: mini∈minimal, 3.7/37/3-7,
nemo∈Nemotron). Cross-checks node obs-counts against the validated plan numbers."""
import pandas as pd, re
from pathlib import Path

# Anchor I/O to the repo root (parent of diagnostics/) so the script works from
# any working directory, not just the repo root.
ROOT = Path(__file__).resolve().parent.parent
df = pd.read_csv(ROOT / 'data/processed/benchmarks_merged.csv')
base = df[['model_version', 'organization']].drop_duplicates('model_version').copy()
base['n_obs'] = base.model_version.map(df.groupby('model_version').size())

HOST = re.compile(r'^(chutes|fireworks|deepinfra|parasail|zai-org|qwen|moonshotai|openai|deepseek)[/-]', re.I)

def norm(s):
    t = s.strip().rstrip('*†').strip()
    t = HOST.sub('', t)
    return t

def variant(t):
    """variant tag from a (tier-stripped) string"""
    tl = t.lower()
    if 'non-thinking' in tl or 'non thinking' in tl: return 'non-thinking'
    if 'deep-think' in tl or 'deep think' in tl or 'deepthink' in tl: return 'deepthink'
    if 'thinking' in tl or '(think' in tl: return 'thinking'
    # reasoning-mode flag (e.g. grok-4-1-fast-reasoning vs -non-reasoning): a
    # materially different mode, so tag it as a distinct variant of the node.
    if 'non-reasoning' in tl or 'non reasoning' in tl: return 'non-reasoning'
    if 'reasoning' in tl: return 'reasoning'
    # Effort is delimited by '_' (e.g. _high) or '(' (e.g. (xHigh)), NOT a bare
    # space — a space+word is a tier NAME ('Mistral Medium 3'), not an effort level.
    # The optional 'pro' prefix keeps GPT-5.6 Sol's pro mode ('_promax',
    # '_prounknown' — upstream Name reads "GPT-5.6 Sol (pro, max)") as its own
    # variant of Sol instead of folding it into plain '_max'.
    mo = re.search(r'[_(]\(?(pro)?(xhigh|minimal|low|medium|high|max|none|unknown)\b', tl)
    if mo: return 'effort:' + (mo.group(1) or '') + mo.group(2)
    mo = re.search(r'[_ ]\(?(\d+)k\b', tl)
    if mo: return 'token:%sk' % mo.group(1)
    if 'vision' in tl: return 'vision'
    if 'beta' in tl: return 'beta'
    return 'bare'

# OpenAI codename releases (5.6: sol / terra / luna). Reviewed by hand: these are
# PEER MODEL TYPES shipped in one generation, not a flagship/pro/mini capability
# ladder, so none is folded into a tier chain. The scores rule out the ladder
# reading: terra sits 0.095 BELOW sol at matched effort (0/40 benchmarks) whereas
# a real pro tier sits ABOVE its flagship (5.4-pro +0.051 on 9/10, 5.2-pro +0.090
# on 7/7), and luna outscores the mini line it was previously filed on (+0.129
# over 5.4-mini, 11/11). sol continues the flagship spine (+0.027 over 5.5, above
# on 20/28 effort-matched cells). terra and luna BRANCH off the 5.5 node as
# parented off-spine siblings: all three types share the 5.5 base, so each
# codename takes one Brownian delta from 5.5 and its effort variants (including
# the effort:unknown leaderboard rows) tie to the node through the variant
# offsets. Founding them as their own chains instead loses both: a single-node
# chain is dropped by `build_lineage_structure`, leaving every variant a free
# test-taker. The cost of the branch is prior-vs-data tension: the delta mean is
# positive but both sit BELOW 5.5 (above on 3/27 and 0/27), so the data pays the
# soft prior to place them under their parent. A 5.7-terra would parent onto
# `terra 5.6`, continuing the branch.
CODENAME_CHAIN = {'sol': 'gpt', 'terra': 'gpt', 'luna': 'gpt'}
CODENAME_PARENT = {'terra': '5.5', 'luna': '5.5'}

# `_pro<effort>` is the effort parser swallowing a Pro-MODE tag: upstream names it
# "GPT 5.6 Sol (Max + Pro)", i.e. Sol run under an advanced harness, not a separate
# release. Scored as the model's own ability it would inflate the node. Anchored to
# `_pro` + an effort word at the end so real `-pro-` models (gpt-5.4-pro,
# deepseek-v4-pro) are untouched.
OUT_HARNESS = re.compile(r'cowork|web-?app|heavy|chatgpt agent| agent$'
                         r'|_pro(max|unknown|high|low|medium|xhigh|none|minimal)$', re.I)
OUT_MODALITY = re.compile(r'audio|-live|live-preview|robotics|video|llava|omni|realtime|voxtral', re.I)

def classify(mv, org):
    t = norm(mv); tl = t.lower(); ol = (str(org) if isinstance(org, str) else '').lower()
    # ---- harness / modality (any vendor) ----
    if OUT_HARNESS.search(mv): return dict(vendor='', chain='', node='', variant='harness', in_chain='no')
    if OUT_MODALITY.search(tl) and 'deep' not in tl: return dict(vendor='', chain='', node='', variant='modality', in_chain='no')

    # ================= ANTHROPIC =================
    if 'anthropic' in ol or 'claude' in tl or 'fable' in tl or 'mythos' in tl:
        v = variant(t)
        if 'mythos' in tl: return dict(vendor='Anthropic', chain='opus', node='Fable 5', variant='preview', in_chain='yes')
        if 'fable' in tl:  return dict(vendor='Anthropic', chain='opus', node='Fable 5', variant=v, in_chain='yes')
        for tier in ['opus', 'sonnet', 'haiku']:
            if tier in tl:
                # version
                ver = None
                if tier == 'sonnet' and '0620' in tl: ver = '3.5-Jun'
                elif tier == 'sonnet' and '1022' in tl: ver = '3.5-Oct'
                else:
                    # Order matters: every 4-x / 3-x pattern is checked before the
                    # bare '-5', which would otherwise swallow the '-5' inside
                    # '4-5' and the release dates ('claude-opus-4-5-2025...').
                    # A future 5.1 needs its own '5-1'/'5.1' entry ahead of '-5'.
                    for vv in ['4-8','4.8','4-7','4.7','4-6','4.6','4-5','4.5','4-1','4.1','3-7','3.7','37','3-5','3.5','-4-','-4 ','opus 4','sonnet 4','haiku 4','sonnet-4','opus-4','haiku-4','4-sonnet','4-opus','3-opus','3-sonnet','3-haiku','-3-','-5']:
                        if vv in tl: ver = vv; break
                vmap = {'4-8':'4.8','4-7':'4.7','4-6':'4.6','4-5':'4.5','4-1':'4.1','3-7':'3.7','37':'3.7',
                        '3-5':'3.5','-4-':'4','-4 ':'4','opus 4':'4','sonnet 4':'4','haiku 4':'4','sonnet-4':'4','opus-4':'4','haiku-4':'4','4-sonnet':'4','4-opus':'4',
                        '3-opus':'3','3-sonnet':'3','3-haiku':'3','-3-':'3','-5':'5'}
                ver = vmap.get(ver, ver)
                node = f'{tier.capitalize()} {ver}' if ver else f'{tier.capitalize()} ?'
                return dict(vendor='Anthropic', chain=tier, node=node, variant=v, in_chain='yes')
        # legacy Claude (1.x / 2.x / instant) — no tier → independent
        return dict(vendor='Anthropic', chain='', node='claude-legacy', variant='', in_chain='no')

    # ================= OPENAI =================
    if 'openai' in ol or re.match(r'(gpt|o[1345]|chatgpt|codex|davinci|babbage|ada|curie|text-)', tl):
        v = variant(t)
        if re.search(r'\boss\b', tl):
            # open-weights pair; each size is a single-node chain kept for its
            # variant offsets (bare/high/medium/unknown tie to one ability)
            size = '120b' if '120' in tl else '20b'
            return dict(vendor='OpenAI', chain=f'gpt-oss-{size}', node=f'oss-{size}', variant=v, in_chain='yes')
        if any(x in tl for x in ['gpt2','gpt-j','gpt-neo','cerebras','davinci','babbage','ada','curie','text-']):
            return dict(vendor='OpenAI', chain='', node='GPT-3-era', variant='', in_chain='no')
        if 'codex' in tl:
            # Version-BOUNDARY regex, not a hand-maintained substring list: the old
            # list ['5.3','5.2','5.1','5'] let a bare '5' match '5.5-codex' and
            # collapse it onto the '5-codex' founder node (found 2026-07-06). Capture
            # the full minor version so new codex releases route to their own node.
            mo = re.search(r'gpt-(\d+(?:\.\d+)?)-codex', tl)
            if mo:
                ver = mo.group(1)
                # mini codex is a separate product tier -> keep OUT of the flagship
                # codex chain (no cross-tier mixing); too few nodes to chain, so
                # route independent (matches the standalone codex-mini handling).
                if 'mini' in tl:
                    return dict(vendor='OpenAI', chain='', node=f'{ver}-codex-mini', variant=v, in_chain='no')
                # '-max' is a higher-effort variant of the same codex release, not a
                # new node: tag it (variant() only catches '_max'/'(max', not the
                # hyphen form) so it shares the base node's psi instead of posing as
                # a 'bare' base release.
                vv = 'effort:max' if re.search(r'-max\b', tl) else v
                return dict(vendor='OpenAI', chain='codex', node=f'{ver}-codex', variant=vv, in_chain='yes')
            # standalone codex without a gpt-<ver> prefix (e.g. codex-mini-2025-05-16):
            # OpenAI, but independent (no version to chain on).
            return dict(vendor='OpenAI', chain='', node=('codex-mini' if 'mini' in tl else 'codex'), variant=v, in_chain='no')
        if re.match(r'o[1345]\b', tl) or re.match(r'o[1345][- ]', tl):
            sub = 'o-mini' if 'mini' in tl else ('o-pro' if 'pro' in tl else 'o-flagship')
            gen = re.match(r'o([1345])', tl).group(1)
            suf = '-mini' if sub=='o-mini' else '-pro' if sub=='o-pro' else ''
            node = f'o{gen}{suf}'
            if sub=='o-flagship' and 'preview' in tl: node = 'o1-preview'
            return dict(vendor='OpenAI', chain=sub, node=node, variant=v, in_chain='yes')
        # gpt tiers — nano/mini before flagship; minimal is effort not mini.
        # anchor version to 'gpt-<ver>' so years (2025) and 3.5's '5' don't leak.
        def gptver(s):
            m = re.search(r'gpt-(\d(?:\.\d+)?)(o)?', s)
            if not m: return '?'
            base = m.group(1)
            if m.group(2): return '4o'
            if base == '4' and 'turbo' in s: return '4-turbo'
            if base == '3.5': return '3.5-turbo'
            return base
        # Codename releases carry no tier word, so the substring tests below see
        # nothing and would collapse every tier onto the flagship node. Runs
        # BEFORE the 'pro' test so Sol's pro-mode rows stay Sol variants rather
        # than being pulled onto the pro chain by the bare 'pro' substring.
        mo = re.search(r'gpt-\d(?:\.\d+)?[- (]+(' + '|'.join(CODENAME_CHAIN) + r')', tl)
        if mo:
            cn = mo.group(1); ch = CODENAME_CHAIN[cn]
            node = gptver(tl) if cn == 'sol' else f'{cn} {gptver(tl)}'
            d = dict(vendor='OpenAI', chain=ch, node=node, variant=v, in_chain='yes')
            if cn in CODENAME_PARENT:
                d['parent'] = CODENAME_PARENT[cn]
            return d
        if 'nano' in tl:  return dict(vendor='OpenAI', chain='nano',  node='nano '+gptver(tl), variant=v, in_chain='yes')
        if re.search(r'gpt-5-mini|4o-mini|4\.1-mini|5\.4-mini', tl): return dict(vendor='OpenAI', chain='mini', node='mini '+gptver(tl), variant=v, in_chain='yes')
        if 'pro' in tl and 'gpt-5' in tl: return dict(vendor='OpenAI', chain='pro', node='pro '+gptver(tl), variant=v, in_chain='yes')
        if 'chatgpt' in tl: return dict(vendor='OpenAI', chain='gpt', node='4o', variant='chatgpt', in_chain='yes')
        ver = gptver(tl)
        if ver == '4.5': return dict(vendor='OpenAI', chain='', node='gpt-4.5-preview', variant=v, in_chain='no')
        return dict(vendor='OpenAI', chain='gpt', node=ver, variant=v, in_chain='yes')

    # ================= GOOGLE =================
    if 'google' in ol or 'deepmind' in ol or 'gemini' in tl or 'gemma' in tl:
        if 'gemma' in tl:
            # sizes are separate products, so each model id founds its own
            # single-node chain: gemma-4-31b-it ties its bare/minimal/none
            # rungs, lone releases drop at fit time as before
            base = re.sub(r'_(?:low|medium|high|minimal|max|xhigh|none|unknown|\d+k)$',
                          '', tl)
            return dict(vendor='Google', chain=base, node=base, variant=variant(t), in_chain='yes')
        if any(x in tl for x in ['palm','bard','gopher','chinchilla','t5-','glam','mathematician']):
            return dict(vendor='Google', chain='', node='legacy', variant='', in_chain='no')
        if 'exp-1206' in tl: return dict(vendor='Google', chain='', node='gemini-exp-1206', variant='', in_chain='no')
        if 'gemini' in tl:
            v = variant(t)
            tier = 'flash-lite' if ('flash-lite' in tl or 'flash lite' in tl) else ('flash' if 'flash' in tl else 'pro')
            # anchor version to 'gemini-<ver>' so dates (03-25) and token sizes (32k) don't leak
            mo = re.search(r'gemini[- ](\d(?:\.\d)?)', tl)
            ver = mo.group(1) if mo else '?'
            return dict(vendor='Google', chain=f'gemini-{tier}', node=f'{tier} {ver}', variant=v, in_chain='yes')

    # ================= xAI GROK =================
    if 'xai' in ol or 'grok' in tl:
        v = variant(t)
        if 'mini' in tl:
            # beta (2025-04-09) -> GA (2025-06-24) is a real release step, so the
            # mini line is a two-node chain and each node's effort rungs tie
            # through the variant offsets.
            node = '3-mini-beta' if 'beta' in tl else '3-mini'
            return dict(vendor='xAI', chain='grok-mini', node=node, variant=v, in_chain='yes')
        if 'code' in tl: return dict(vendor='xAI', chain='', node='grok-code-fast-1', variant=v, in_chain='no')
        if 'fast' in tl:
            ver = '4.1' if '4-1' in tl else '4'
            return dict(vendor='xAI', chain='grok-fast', node=f'{ver}-fast', variant=v, in_chain='yes')
        # Both spellings of every minor version must be listed BEFORE the bare
        # 'grok-<gen>' fallbacks, which are prefix matches: an unlisted 'grok-4.5'
        # falls through to 'grok-4' and silently shares the grok-4 node instead of
        # getting its own, which costs the chain a step.
        # ponytail: hand list, so each new minor version needs its entry here; a
        # version-boundary regex would generalize, but the date-suffixed ids
        # ('grok-4-0709') make that a rewrite, not a one-liner.
        for vv,lab in [('4-3','4.3'),('4.3','4.3'),('4-20','4.20'),('4.20','4.20'),('4-5','4.5'),('4.5','4.5'),('4-1','4.1'),('grok-4','4'),('grok-3','3'),('grok-2','2')]:
            if vv in tl: return dict(vendor='xAI', chain='grok', node=lab, variant=v, in_chain='yes')
        # A grok model with an unrecognized version (e.g. a future grok-5): flag
        # it UNROUTED so the coverage report surfaces it for review, rather than
        # silently dropping it into the generic independent bucket below.
        return dict(vendor='xAI', chain='', node='UNROUTED', variant=v, in_chain='no')

    # ================= DEEPSEEK =================
    if 'deepseek' in ol or 'deepseek' in tl:
        v = variant(t)
        if 'distill' in tl: return dict(vendor='DeepSeek', chain='', node='R1-distill', variant='', in_chain='no')
        if 'coder' in tl:   return dict(vendor='DeepSeek', chain='', node='coder', variant='', in_chain='no')
        if 'v4-flash' in tl:
            node = 'V4-flash-0731' if '0731' in tl else 'V4-flash'
            return dict(vendor='DeepSeek', chain='deepseek-flash', node=node, variant=v, in_chain='yes')
        if 'v4' in tl:      return dict(vendor='DeepSeek', chain='deepseek-v', node='V4-pro', variant=v, in_chain='yes')
        if 'reasoner' in tl: return dict(vendor='DeepSeek', chain='deepseek-v', node='V3.2', variant='thinking', in_chain='yes')
        if 'march 2025' in tl: return dict(vendor='DeepSeek', chain='deepseek-v', node='V3-0324', variant='bare', in_chain='yes')  # manual: "V3 (March 2025)" = 0324
        # r1[-_]: HOST strips the 'deepseek-' vendor prefix, so an effort row
        # arrives as 'r1_high', where \br1\b fails ('_' is a word char) — that
        # miss sent DeepSeek-R1_high to the independent bucket (found 2026-08-07
        # by the name audit's 6c ladder-split check).
        if re.search(r'\br1\b|r1[-_]|-r1', tl):
            return dict(vendor='DeepSeek', chain='deepseek-r', node=('R1-0528' if '0528' in tl else 'R1'), variant=v, in_chain='yes')
        # V3.2-Exp (experimental, 2025-09-29) is a distinct earlier release from the
        # December V3.2 line (Speciale + the deepseek-chat/reasoner endpoints, all
        # 2025-12-01). Without this split all six collapse onto one node dated to the
        # Sept Exp snapshot (found 2026-07-06), backdating the December model.
        if ('v3.2' in tl or 'v3p2' in tl) and 'exp' in tl:
            return dict(vendor='DeepSeek', chain='deepseek-v', node='V3.2-Exp', variant=v, in_chain='yes')
        # 'llm' before 'chat': deepseek-llm-67b-chat is the LLM-67b founder, not a
        # deepseek-chat (V3.2) alias — 'chat' as a bare substring would steal it.
        for vv,lab in [('v3.2','V3.2'),('v3p2','V3.2'),('v3-0324','V3-0324'),('v3.1','V3.1'),('v3p1','V3.1'),
                       ('v3','V3'),('v2.5','V2.5'),('v2','V2'),('llm','LLM-67b'),('chat','V3.2')]:
            if vv in tl: return dict(vendor='DeepSeek', chain='deepseek-v', node=lab, variant=v, in_chain='yes')

    # ================= ALIBABA QWEN =================
    if 'alibaba' in ol or 'qwen' in tl or 'qwq' in tl:
        v = variant(t)
        if 'qwen3-coder' in tl or 'coder-next' in tl:
            node = 'Coder-next' if 'next' in tl else 'Coder-480B'
            return dict(vendor='Alibaba', chain='qwen-coder', node=node, variant=v, in_chain='yes')
        if 'coder' in tl: return dict(vendor='Alibaba', chain='', node='qwen-coder', variant='', in_chain='no')
        if re.search(r'\bvl\b|omni|video|llava|vilamp', tl): return dict(vendor='Alibaba', chain='', node='qwen-mm', variant='', in_chain='no')
        if 'qwq' in tl:
            node = 'QwQ-Preview' if 'preview' in tl else 'QwQ-32B'
            return dict(vendor='Alibaba', chain='qwq', node=node, variant=v, in_chain='yes')
        if 'thinking-2507' in tl: return dict(vendor='Alibaba', chain='', node='qwq', variant='', in_chain='no')
        def qver(s):
            # gen is the number right after 'qwen'; dash-then-size (qwen-7b) = gen 1
            m = re.search(r'qwen(\d\.?\d?)', s)
            return m.group(1) if m else '1'
        if 'turbo' in tl: return dict(vendor='Alibaba', chain='', node='qwen-turbo', variant=v, in_chain='no')
        if 'max' in tl:   return dict(vendor='Alibaba', chain='qwen-max', node='max '+('2.5' if 'max-2025-01' in tl else qver(tl)), variant=v, in_chain='yes')
        # NB: dated qwen-plus snapshots within a generation (e.g. plus-2025-01-25 and
        # plus-2025-04-28) intentionally share one 'plus 2.5' node — kept pooled by
        # decision (ordering vs neighbouring nodes is unaffected either way).
        if 'plus' in tl:  return dict(vendor='Alibaba', chain='qwen-plus', node='plus '+('2.5' if 'plus-2025' in tl else qver(tl)), variant=v, in_chain='yes')
        if 'flash' in tl: return dict(vendor='Alibaba', chain='qwen-flash', node='flash '+qver(tl), variant=v, in_chain='yes')
        # open-weight: chain only fixed sizes 72/32/14/7B
        mo = re.search(r'(\d+)b', tl)
        sz = mo.group(1) if mo else '?'
        if sz in ['110','72','32','14','7'] and '235' not in tl:
            return dict(vendor='Alibaba', chain=f'qwen-open-{sz}b', node=f'{qver(tl)}-{sz}B', variant=v, in_chain='yes')
        return dict(vendor='Alibaba', chain='', node=f'qwen-open-{sz}b', variant=v, in_chain='no')

    # ================= MOONSHOT KIMI =================
    if 'moonshot' in ol or 'kimi' in tl:
        v = variant(t)
        if 'audio' in tl: return dict(vendor='Moonshot', chain='', node='kimi-audio', variant='', in_chain='no')
        # Ahead of the 'thinking' test: a thinking run of a NEW generation is a
        # variant of that generation, not a node of the previous one. Without a
        # branch here a new K<n> falls to the K2 default and shares K2's node.
        if 'k3' in tl: node='K3'
        elif 'k2.7' in tl or 'k2-7' in tl: node='K2.7'
        elif 'k2.6' in tl or 'k2-6' in tl: node='K2.6'
        elif 'k2.5' in tl or 'k2-5' in tl or 'k2p5' in tl: node='K2.5'
        elif 'thinking' in tl: node='K2-Thinking'
        elif '0905' in tl: node='K2-0905'
        else: node='K2'
        return dict(vendor='Moonshot', chain='kimi', node=node, variant=v, in_chain='yes')

    # ================= ZHIPU GLM =================
    if 'zhipu' in ol or 'z.ai' in ol or 'glm' in tl or 'chatglm' in tl:
        v = variant(t)
        if 'chatglm' in tl: return dict(vendor='Zhipu', chain='', node='chatglm2', variant='', in_chain='no')
        if 'air' in tl: return dict(vendor='Zhipu', chain='', node='GLM-4.5-Air', variant='', in_chain='no')
        # Some feeds spell the minor version with 'p' ('glm-5p2' = 5.2).
        # Unnormalized it misses '5.2' and falls through to the bare '5' node,
        # splitting one release across two. The alias map normally renames these
        # away upstream, but it is hand-maintained and lags a new release.
        tlv = re.sub(r'(\d)p(\d)', r'\1.\2', tl)
        for vv in ['5.2','5.1','4.7','4.6','4.5','5']:
            if vv in tlv: return dict(vendor='Zhipu', chain='glm', node=vv, variant=v, in_chain='yes')
        return dict(vendor='Zhipu', chain='', node='UNROUTED', variant=v, in_chain='no')  # unknown GLM version → flag for review

    # ================= META LLAMA =================
    if 'meta' in ol or 'llama' in tl or 'muse-spark' in tl:
        # muse-spark 1 (2026-04-08) -> 1.1 (2026-07-09): a real two-node chain,
        # and 1.1's high/xhigh rungs tie to its node
        if 'muse-spark' in tl:
            node = 'spark 1.1' if '1.1' in tl else 'spark 1'
            return dict(vendor='Meta AI', chain='muse-spark', node=node,
                        variant=variant(t), in_chain='yes')
        # 3rd-party derivatives / multimodal / MoE / base → independent
        if any(x in tl for x in ['tulu','hermes','dracarys','distill','open_llama','llava','vision','slime','vilamp','chutes/','-4-maverick','-4-scout','4-maverick','4-scout','17b']):
            return dict(vendor='Meta', chain='', node='llama-other', variant='', in_chain='no')
        if 'llama' in tl and ('instruct' in tl or 'chat' in tl):
            mo = re.search(r'(\d+)b', tl); sz = mo.group(1) if mo else '?'
            if 'llama-2' in tl or 'llama 2' in tl: gen = '2'
            elif '3.3' in tl: gen = '3.3'
            elif '3.1' in tl: gen = '3.1'
            elif 'llama-3' in tl or 'llama 3' in tl: gen = '3'
            else: gen = '?'
            if sz == '70': return dict(vendor='Meta', chain='llama-70b', node=f'{gen}-70B', variant='instruct', in_chain='yes')
            if sz == '8':  return dict(vendor='Meta', chain='llama-8b',  node=f'{gen}-8B',  variant='instruct', in_chain='yes')
        return dict(vendor='Meta', chain='', node='llama-other', variant='', in_chain='no')

    # ================= MINIMAX =================
    if 'minimax' in ol or 'minimax' in tl:
        # Minor versions first: the bare-generation entries are prefix matches.
        for vv in ['2.7','2.5','2.1','3','2','1']:
            if vv in tl: return dict(vendor='MiniMax', chain='minimax', node='M'+vv, variant='bare', in_chain='yes')
        return dict(vendor='MiniMax', chain='', node='UNROUTED', variant='bare', in_chain='no')  # unknown MiniMax version → flag

    # ================= MISTRAL =================
    if 'mistral' in ol or re.search(r'mistral|mixtral|codestral|magistral|ministral|pixtral', tl):
        if 'nemotron' in tl: return dict(vendor='NVIDIA', chain='', node='nemotron', variant='', in_chain='no')
        v = variant(t)
        if 'pixtral' in tl: return dict(vendor='Mistral', chain='', node='pixtral', variant='', in_chain='no')
        if 'magistral' in tl: return dict(vendor='Mistral', chain='', node='magistral', variant='', in_chain='no')
        if 'ministral' in tl: return dict(vendor='Mistral', chain='', node='ministral', variant='', in_chain='no')
        if 'mixtral' in tl: return dict(vendor='Mistral', chain='', node='mixtral', variant='', in_chain='no')
        if 'nemo' in tl: return dict(vendor='Mistral', chain='', node='mistral-nemo', variant='', in_chain='no')
        if 'codestral' in tl:
            return dict(vendor='Mistral', chain='codestral', node=('2501' if '2501' in tl else '2405'), variant=v, in_chain='yes')
        for line in ['large','small','medium']:
            if line in tl:
                mo = re.search(r'(2402|2407|2411|2501|2503|2505|2508)', tl)
                node = f'{line}-{mo.group(1)}' if mo else (f'{line}-2505' if 'medium 3' in tl else f'{line}-?')
                return dict(vendor='Mistral', chain=f'mistral-{line}', node=node, variant=v, in_chain='yes')
        if 'mistral-7b' in tl or re.search(r'mistral.*7b|7b.*mistral', tl):
            ver = 'v0.3' if 'v0.3' in tl else 'v0.2' if 'v0.2' in tl else 'v0.1'
            return dict(vendor='Mistral', chain='mistral-open-7b', node=ver, variant=v, in_chain='yes')

    # ================= XIAOMI MIMO =================
    if 'xiaomi' in ol or re.match(r'mimo-v', tl):
        v = variant(t)
        # pro and flash are separate product lines, so each gets its own chain.
        # A release with neither tag has no line to continue → independent.
        mo = re.search(r'mimo-v(\d+(?:\.\d+)?)-(pro|flash)', tl)
        if mo:
            return dict(vendor='Xiaomi', chain=f'mimo-{mo.group(2)}',
                        node=f'v{mo.group(1)}-{mo.group(2)}', variant=v, in_chain='yes')
        return dict(vendor='Xiaomi', chain='', node='(independent)', variant='', in_chain='no')

    # ================= AMAZON =================
    # nova-2.0-pro-preview: one release, three effort rungs (low/medium/none) —
    # a single-node chain kept for the variant offsets
    if 'nova-2.0-pro' in tl:
        return dict(vendor='Amazon', chain='nova-2-pro', node='2.0-pro-preview',
                    variant=variant(t), in_chain='yes')

    # ================= THINKING MACHINES =================
    # One release generation, no predecessor: each model is a single-node chain
    # kept for its VARIANT OFFSETS only (zero Brownian deltas — nothing to
    # order). That is what lets the xhigh/high/unknown panels inform the base
    # taker. Inkling and Inkling Small are distinct models (base beats Small on
    # both ARC sets), so two chains, never one ladder.
    if 'thinking machines' in ol or 'thinkingmachines' in ol or 'inkling' in tl:
        v = variant(t)
        if 'inkling' not in tl:
            # other TML releases (tml-interaction-small, ...) are NOT Inkling
            # configs; a vendor gate alone would splice them onto the node.
            return dict(vendor='Thinking Machines', chain='',
                        node='(independent)', variant='', in_chain='no')
        small = 'small' in tl
        return dict(vendor='Thinking Machines',
                    chain='inkling-small' if small else 'inkling',
                    node='Inkling Small' if small else 'Inkling',
                    variant=v, in_chain='yes')

    # long tail of minor vendors not among the chained majors → independent
    v0 = org.split(',')[0] if isinstance(org, str) else 'other'
    return dict(vendor=v0, chain='', node='(independent)', variant='', in_chain='no')

rows = [dict(raw_string=r.model_version, n_obs=r.n_obs, **classify(r.model_version, r.organization)) for r in base.itertuples()]
out = pd.DataFrame(rows)

# ---- node_date: min release date over a node's aliases; manual backfill for undated nodes ----
mdate = df.assign(d=pd.to_datetime(df.release_date, errors='coerce')).groupby('model_version').d.min()
out['model_date'] = out.raw_string.map(mdate)
nd = out[out.in_chain == 'yes'].groupby(['vendor', 'chain', 'node']).model_date.min()
BACKFILL = {('Anthropic','opus','Opus 3'): '2024-02-29', ('Anthropic','haiku','Haiku 3'): '2024-03-07',
            # pro 3 / flash-lite 3.1 are dated in the current data (2025-11-18 /
            # 2026-03-03); kept only as a safety net if a future refresh drops the
            # date, updated to match data so they can't re-introduce a mis-order.
            ('Google','gemini-pro','pro 3'): '2025-11-18', ('Google','gemini-flash-lite','flash-lite 3.1'): '2026-03-03',
            # Nodes whose rows carry NO release_date in the data at all, so the
            # min-over-aliases is NaT and only this map can date them. Without an
            # entry the node is undated and lineage.py drops its whole chain.
            # Dates are the vendors' own announcements, checked against external
            # sources on 2026-07-27 (Mistral's Codestral post; Xiaomi's MiMo
            # release log, which stamps v2.5-pro 04-23 Beijing = 04-22 UTC).
            ('Mistral','codestral','2405'): '2024-05-29',
            ('Xiaomi','mimo-pro','v2-pro'): '2026-03-18',
            ('Xiaomi','mimo-pro','v2.5-pro'): '2026-04-22',
            ('Xiaomi','mimo-flash','v2-flash'): '2026-03-18',
            # gpt-5.5-codex carries no release_date in the data (SEAL Remote Labor
            # Index only); use the gpt-5.5 flagship date as a proxy so it orders
            # after gpt-5.3-codex (2026-02-05). Only within-chain order matters here.
            ('OpenAI','codex','5.5-codex'): '2026-04-23'}
def node_date(r):
    if r.in_chain != 'yes': return r.model_date
    key = (r.vendor, r.chain, r.node)
    val = nd.get(key)
    if pd.isna(val): val = pd.to_datetime(BACKFILL.get(key))
    return val
out['node_date'] = out.apply(node_date, axis=1).dt.strftime('%Y-%m-%d')
out['parent'] = out['parent'].fillna('') if 'parent' in out.columns else ''

# ---- reviewed per-model overrides ----
# The rules above assign one node per (tier, version), which pools every dated
# snapshot of a release: the whole 4o line lands on one node, so its releases
# cannot move apart and share one theta. Splitting a pooled node, re-filing a
# model onto a different tier, and naming a `parent` are all judgements about
# what a release IS, which no regex over the name can recover. They live in this
# tracked overlay so a rebuild keeps them, applied AFTER node_date so the rows
# left behind on a pooled node keep the min-over-aliases date, which is the
# earliest release still on it.
OVERRIDES = ROOT / 'data/curated/lineage_node_overrides.csv'
ov = pd.read_csv(OVERRIDES, keep_default_na=False, dtype=str).set_index('raw_string')
hit = out.raw_string.isin(ov.index)
for col in ['chain', 'node', 'parent', 'node_date']:
    out.loc[hit, col] = out.loc[hit, 'raw_string'].map(ov[col])
stale = sorted(set(ov.index) - set(out.raw_string))
print(f'\noverrides applied: {hit.sum()}/{len(ov)} from {OVERRIDES.name}')
if stale:
    print(f'  STALE (no such model in the data, drop the row): {stale}')

# ---- demote chains the fit would drop anyway ----
# Per-row rules can't see siblings, so generic rules (every gemma id founds a
# chain) file lone releases as chains that build_lineage_structure then drops
# (single node, single variant group: nothing to tie). Demote them here, where
# the whole family is visible, so `in_chain=yes` means exactly "carries the
# lineage prior" and the map's chain count equals the live count. Runs AFTER
# the overrides, which can re-file rows either way. Mirror of lineage.py's
# keep rule: survive on >=2 nodes OR >=2 (node, variant) groups.
_yes = out.in_chain == 'yes'
_alive = {c for c, g in out[_yes].groupby('chain')
          if g['node'].nunique() >= 2
          or g[['node', 'variant']].drop_duplicates().shape[0] >= 2}
_demote = _yes & ~out.chain.isin(_alive)
if int(_demote.sum()):
    print(f"demoted {int(_demote.sum())} row(s) in "
          f"{out.loc[_demote, 'chain'].nunique()} lone single-variant chain(s) "
          f"to in_chain=no: {sorted(out.loc[_demote, 'chain'].unique())}")
    out.loc[_demote, 'in_chain'] = 'no'
    out.loc[_demote, 'chain'] = ''

out = out[['raw_string','vendor','chain','node','parent','node_date','variant','in_chain','n_obs']].sort_values(['in_chain','vendor','chain','node_date','node'])
out_path = ROOT / 'data/curated/lineage_map.csv'
out.to_csv(out_path, index=False)
print('WROTE', out_path)

# ---- coverage report ----
print('TOTAL models:', len(out), '| obs:', out.n_obs.sum())
print('in_chain:', out.in_chain.value_counts().to_dict())
un = out[out.node == 'UNROUTED']
print('\nUNROUTED (%d models, %d obs):' % (len(un), un.n_obs.sum()))
for r in un.itertuples(): print('   ', repr(r.raw_string), '|', r.vendor)
print('\nchained obs by vendor:', out[out.in_chain=='yes'].groupby('vendor').n_obs.sum().to_dict())
# cross-check key chains vs LINEAGE_PLAN validated node obs
print('\n=== node-obs cross-check (vs plan) ===')
for ch in ['opus','sonnet','haiku','llama-70b','llama-8b','gpt','grok','minimax']:
    sub = out[out.chain==ch]
    if not len(sub): continue
    nodes = sub.groupby('node').n_obs.sum().to_dict()
    print(f'  {ch}: {nodes}')
