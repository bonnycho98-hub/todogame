from app.services.sprite import generate_sprite, SPRITE_COLORS


def test_sprite_has_five_lines():
    result = generate_sprite(seed=42)
    assert len(result["lines"]) == 5


def test_sprite_color_is_valid_hex():
    result = generate_sprite(seed=42)
    color = result["color"]
    assert color.startswith("#")
    assert len(color) == 7


def test_same_seed_produces_same_sprite():
    a = generate_sprite(seed=123)
    b = generate_sprite(seed=123)
    assert a == b


def test_different_seeds_likely_differ():
    results = [generate_sprite(seed=i) for i in range(20)]
    unique = {tuple(r["lines"]) for r in results}
    assert len(unique) > 5


def test_face_line_contains_parentheses():
    result = generate_sprite(seed=1)
    face_line = result["lines"][1]
    assert "(" in face_line and ")" in face_line
