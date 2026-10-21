"""Qwen-Image 2.1 이미지 생성 (v11.23): ComfyUI 에서 '내보내기(API)' 로 저장한 워크플로 파일을 틀로 써서
프롬프트·시드·크기만 바꿔 실행한다. (모델·텍스트 인코더·VAE 이름과 로더 종류는 내 ComfyUI 에서 돌아간 설정 그대로 → 버전이 달라도 안전)

틀 파일: qwen_image_api.json  (SceneMaker 폴더, config.toml 옆 또는 그 아래 workflows 폴더)
틀이 없으면 기본 노드 구성을 시도하지만, 템플릿 버전이 다르면 실패할 수 있다.
"""

import json
from pathlib import Path

TEMPLATE_NAMES = ("qwen_image_api.json", "qwen_image_2_1_api.json")


def _roots():
    here = Path(__file__).resolve().parent
    return [Path.cwd(), here.parent, here.parent / "workflows", here]


def find_template(c):
    q = c.get("qwen", {}) or {}
    names = [q["workflow"]] if q.get("workflow") else list(TEMPLATE_NAMES)
    for root in _roots():
        for n in names:
            p = Path(n)
            p = p if p.is_absolute() else root / n
            if p.is_file():
                return p
    return None


def _links(wf):
    """KSampler 계열이 가리키는 positive/negative 노드 번호."""
    pos, neg = set(), set()
    for node in wf.values():
        inp = node.get("inputs", {})
        if isinstance(inp.get("positive"), list):
            pos.add(str(inp["positive"][0]))
        if isinstance(inp.get("negative"), list):
            neg.add(str(inp["negative"][0]))
    return pos, neg


def fill_template(wf, positive, negative, seed, width, height, prefix):
    """API 워크플로(dict)의 프롬프트·시드·크기·저장 이름을 바꿔 새 dict 로 돌려준다. 바꾼 항목 수를 함께 반환."""
    wf = json.loads(json.dumps(wf))
    pos_ids, neg_ids = _links(wf)
    done = {"positive": 0, "negative": 0, "seed": 0, "size": 0}
    for nid, node in wf.items():
        inp = node.get("inputs")
        if not isinstance(inp, dict):
            continue
        for k in list(inp):
            v = inp[k]
            if isinstance(v, list):                                   # 다른 노드에서 오는 값은 건드리지 않음
                continue
            if k == "positive_prompt":
                inp[k] = positive; done["positive"] += 1
            elif k == "negative_prompt":
                inp[k] = negative; done["negative"] += 1
            elif k in ("seed", "noise_seed") and isinstance(v, (int, float)):
                inp[k] = int(seed); done["seed"] += 1
            elif k == "width" and isinstance(v, (int, float)):
                inp[k] = int(width); done["size"] += 1
            elif k == "height" and isinstance(v, (int, float)):
                inp[k] = int(height); done["size"] += 1
            elif k == "filename_prefix" and isinstance(v, str):
                inp[k] = prefix
        if "Latent" in str(node.get("class_type", "")) and "width" in inp and "height" in inp:
            inp["width"], inp["height"] = int(width), int(height)       # 해상도 선택 노드에서 오는 값이어도 16:9 로 직접 지정
            done["size"] += 2
        if k_text(inp):
            if str(nid) in pos_ids:
                inp["text"] = positive; done["positive"] += 1
            elif str(nid) in neg_ids:
                inp["text"] = negative; done["negative"] += 1
    if not done["positive"]:                                          # 샘플러가 positive/negative 로 연결하지 않는 구성(가이더 사용 등): 글자 칸 중 가장 긴 것 = 긍정 프롬프트
        cands = []
        for nid, node in wf.items():
            inp = node.get("inputs") if isinstance(node, dict) else None
            if not isinstance(inp, dict):
                continue
            for k in ("text", "prompt", "positive", "positive_prompt", "negative", "negative_prompt"):
                v = inp.get(k)
                if isinstance(v, str):
                    cands.append((len(v), nid, k))
        if cands:
            cands.sort(reverse=True)
            _, nid, k = cands[0]
            wf[nid]["inputs"][k] = positive; done["positive"] += 1
            for _, nid2, k2 in cands[1:]:
                if "neg" in k2 or not wf[nid2]["inputs"][k2].strip() or wf[nid2]["inputs"][k2] == "":
                    wf[nid2]["inputs"][k2] = negative; done["negative"] += 1
    # v11.23: 템플릿의 '기본 예시 문장'이 다른 칸(링크로 연결된 문자열 노드·다른 이름의 칸)에 남아 있으면 그것이 그림을 결정해 버린다
    #         (비 오는 텐트를 골랐는데 템플릿 기본 문장의 거실·벽난로 그림이 나오던 문제). 긍정 문장 칸을 끝까지 따라가 모두 바꾼다.
    PROMPT_KEYS = ("text", "prompt", "value", "string", "positive_prompt", "positive", "user_prompt", "instruction", "caption")
    def follow(nid, key, depth=0):
        node = wf.get(str(nid))
        if not isinstance(node, dict) or depth > 6:
            return
        inp = node.get("inputs") or {}
        for k in PROMPT_KEYS:
            v = inp.get(k)
            if isinstance(v, list) and v:
                follow(v[0], key, depth + 1)
            elif isinstance(v, str) and (len(v) > 20 or v == ""):
                inp[k] = key
                done.setdefault("followed", []).append(f"{nid}:{node.get('class_type')}:{k}")
    for pid in pos_ids:
        follow(pid, positive)
    for nid in neg_ids:
        follow(nid, negative)
    foreign = []
    for nid, node in wf.items():
        inp = node.get("inputs") if isinstance(node, dict) else None
        if not isinstance(inp, dict) or "Save" in str(node.get("class_type", "")):
            continue
        for k, v in inp.items():
            if isinstance(v, str) and len(v) > 60 and v not in (positive, negative) and k not in ("unet_name", "clip_name", "vae_name", "filename_prefix"):
                foreign.append(f"{nid}:{node.get('class_type')}:{k}")
    done["foreign"] = foreign
    return wf, done


def describe(wf):
    """로그용: 노드 종류와 값이 글자인 입력 칸 이름 (프롬프트 칸을 못 찾았을 때 원인 확인용)."""
    out = []
    for nid, node in list(wf.items())[:60]:
        if isinstance(node, dict):
            keys = [k for k, v in (node.get("inputs") or {}).items() if isinstance(v, str)]
            out.append(f"{nid}:{node.get('class_type')}:{','.join(keys)}")
    return "; ".join(out)


def k_text(inp):
    return isinstance(inp.get("text"), str)


def default_graph(c, positive, negative, seed, width, height, prefix):
    """틀 파일이 없을 때: 표준 노드로 구성 (ComfyUI 버전에 따라 clip type 이름이 다를 수 있음)."""
    q = c.get("qwen", {}) or {}
    wf = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": q.get("unet", "qwen_image_2.1_int8_convrot.safetensors"),
                                                     "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": q.get("clip", "qwen3vl_8b_int8_convrot.safetensors"),
                                                     "type": q.get("clip_type", "qwen_image"), "device": "default"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": q.get("vae", "qwen_image_2.1_vae_bf16.safetensors")}},
        "4": {"class_type": "ModelSamplingAuraFlow", "inputs": {"model": ["1", 0], "shift": q.get("shift", 3.0)}},
        "5": {"class_type": "CLIPTextEncode", "inputs": {"text": positive, "clip": ["2", 0]}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": negative, "clip": ["2", 0]}},
        "7": {"class_type": "EmptySD3LatentImage", "inputs": {"width": int(width), "height": int(height), "batch_size": 1}},
        "8": {"class_type": "KSampler", "inputs": {
            "seed": int(seed), "steps": q.get("steps", 25), "cfg": q.get("cfg", 1.0),
            "sampler_name": q.get("sampler", "euler"), "scheduler": q.get("scheduler", "simple"),
            "denoise": 1.0, "model": ["4", 0], "positive": ["5", 0], "negative": ["6", 0],
            "latent_image": ["7", 0]}},
        "9d": {"class_type": "VAEDecode", "inputs": {"samples": ["8", 0], "vae": ["3", 0]}},
        "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": prefix, "images": ["9d", 0]}},
    }
    return wf


def build_qwen(c, positive, negative, seed, prefix="scenemaker/qwen", width=1536, height=864):
    """워크플로 dict 와 설명(어떤 틀을 썼는지)을 돌려준다."""
    p = find_template(c)
    if p is None:
        return default_graph(c, positive, negative, seed, width, height, prefix), "기본 구성(틀 파일 없음)"
    wf = json.loads(p.read_text(encoding="utf-8-sig"))
    if "nodes" in wf and "links" in wf:
        raise SystemExit(f"{p.name} 는 '저장'으로 만든 일반 파일입니다. ComfyUI 메뉴 ☰ → 내보내기 → 'API' 로 다시 저장하세요.")
    wf, done = fill_template(wf, positive, negative, seed, width, height, prefix)
    if not done["positive"]:
        raise SystemExit(f"{p.name} 에서 프롬프트 칸을 찾지 못했습니다. ComfyUI 에서 '내보내기(API)' 로 저장했는지 확인하세요.\n  (파일 구조: {describe(wf)[:900]})")
    extra = ""
    if done.get("followed"):
        extra += f" · 연결된 문장 칸 {len(done['followed'])}곳도 교체"
    if done.get("foreign"):
        extra += f" · ⚠ 교체하지 못한 긴 문장 칸: {', '.join(done['foreign'][:4])}"
    return wf, f"{p.name} (프롬프트 {done['positive']} · 시드 {done['seed']} · 크기 {done['size']}{extra}) → 문장 앞부분: {positive[:60]}"
