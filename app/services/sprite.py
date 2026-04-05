import random
import json

SPRITE_COLORS = [
    "#ff9f43", "#67e5ff", "#a29bfe", "#fd79a8", "#0be881",
    "#ffd32a", "#00cec9", "#6c5ce7", "#fab1a0", "#74b9ff",
]

HEADS   = ["╭✿╮", "∧∧∧", "★─★", "♡♡♡", "◈✦◈", "∿∿∿", "≋≋≋", "~∇~"]
EYES    = ["◉", "⊙", "★", "♥", "─", "˘", "ω", "≧", "◕", "✦", "▲", "■"]
MOUTHS  = ["ω", "▽", "‿", "3", "▿", "ᵕ", "益", "ᴗ", "◡", "∇"]
UPPERS  = ["╰─╯", "─══─", "╔══╗", "╭──╮", "〔  〕", "【  】", "⌈  ⌉"]
LOWERS  = ["/||\\", "╱  ╲", "║  ║", "╰──╯", "│  │", "⎸  ⎹"]
FEET    = ["◡ ◡", "▔ ▔", "╚══╝", "∪ ∪", "⌣ ⌣", "﹂ ﹂"]


def generate_sprite(seed: int = None) -> dict:
    """5줄 특수문자 스프라이트를 랜덤 생성한다."""
    rng = random.Random(seed)
    eye = rng.choice(EYES)
    mouth = rng.choice(MOUTHS)
    lines = [
        rng.choice(HEADS),
        f"({eye}{mouth}{eye})",
        rng.choice(UPPERS),
        rng.choice(LOWERS),
        rng.choice(FEET),
    ]
    color = rng.choice(SPRITE_COLORS)
    return {"lines": lines, "color": color}


def sprite_to_text(sprite_data: dict) -> str:
    """스프라이트 dict를 줄바꿈 문자열로 변환한다."""
    return "\n".join(sprite_data["lines"])


def serialize_sprite(sprite_data: dict) -> str:
    return json.dumps(sprite_data, ensure_ascii=False)


def deserialize_sprite(sprite_json: str) -> dict:
    return json.loads(sprite_json)
