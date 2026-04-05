def test_create_and_list_npc(client):
    res = client.post("/api/npcs", json={"name": "엄마", "relation_type": "가족"})
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "엄마"
    assert data["sprite"]  # 자동 생성됨

    res2 = client.get("/api/npcs")
    assert res2.status_code == 200
    assert any(n["name"] == "엄마" for n in res2.json())


def test_create_quest_with_subtask_and_complete(client):
    npc = client.post("/api/npcs", json={"name": "친구", "relation_type": "친구"}).json()
    need = client.post("/api/needs", json={"npc_id": npc["id"], "title": "연락받고싶어함"}).json()
    quest = client.post("/api/quests", json={
        "need_id": need["id"], "title": "주 1회 전화",
        "quest_type": "daily", "routine": {"type": "daily"}, "intimacy_reward": 20
    }).json()
    st = client.post("/api/subtasks", json={
        "quest_id": quest["id"], "title": "안부 묻기", "order": 0
    }).json()

    res = client.post(f"/api/subtasks/{st['id']}/complete")
    assert res.status_code == 200
    result = res.json()
    assert result["subtask_done"] is True
    assert result["quest_done"] is True


def test_dashboard_returns_data(client):
    res = client.get("/api/dashboard")
    assert res.status_code == 200
    data = res.json()
    assert "happiness" in data
    assert data["happiness"]["level"] >= 1
    assert "routine_quests" in data
    assert "self_section" in data
    assert "npc_section" in data


def test_level_reward_create_and_claim(client):
    res = client.post("/api/rewards", json={"level": 99, "message": "케이크 사먹기"})
    assert res.status_code == 201
    reward_id = res.json()["id"]

    res2 = client.post(f"/api/rewards/{reward_id}/claim")
    assert res2.status_code == 200
    assert res2.json()["is_claimed"] is True

    res3 = client.post(f"/api/rewards/{reward_id}/claim")
    assert res3.status_code == 400


def test_need_is_not_archived_by_default(client):
    npc = client.post("/api/npcs", json={"name": "테스트NPC", "relation_type": "기타"}).json()
    need = client.post("/api/needs", json={"npc_id": npc["id"], "title": "테스트 니즈"}).json()
    assert need["is_archived"] is False


def test_complete_need_archives_it(client):
    npc = client.post("/api/npcs", json={"name": "니즈완료테스트NPC", "relation_type": "기타"}).json()
    need = client.post("/api/needs", json={"npc_id": npc["id"], "title": "완료할 니즈"}).json()

    res = client.post(f"/api/needs/{need['id']}/complete")
    assert res.status_code == 200
    assert res.json()["done"] is True

    # 목록에서 제외됐는지 확인
    needs_list = client.get(f"/api/needs?npc_id={npc['id']}").json()
    assert not any(n["id"] == need["id"] for n in needs_list)


def test_dashboard_npc_section_includes_needs(client):
    npc = client.post("/api/npcs", json={"name": "대시보드섹션테스트NPC", "relation_type": "기타"}).json()
    client.post("/api/needs", json={"npc_id": npc["id"], "title": "대시보드용 니즈2"})

    res = client.get("/api/dashboard")
    assert res.status_code == 200
    dashboard = res.json()

    npc_item = next(
        (item for item in dashboard["npc_section"] if item["npc"]["name"] == "대시보드섹션테스트NPC"),
        None,
    )
    assert npc_item is not None
    assert any(
        nwq["need"]["title"] == "대시보드용 니즈2"
        for nwq in npc_item["needs"]
    )


def test_double_complete_need_returns_409(client):
    npc = client.post("/api/npcs", json={"name": "409테스트NPC", "relation_type": "기타"}).json()
    need = client.post("/api/needs", json={"npc_id": npc["id"], "title": "중복완료 니즈"}).json()
    client.post(f"/api/needs/{need['id']}/complete")
    res = client.post(f"/api/needs/{need['id']}/complete")
    assert res.status_code == 409


def test_routine_quests_section_contains_daily_quest(client):
    quest = client.post("/api/quests", json={
        "title": "매일 물 마시기",
        "quest_type": "daily",
        "routine": {"type": "daily"},
        "intimacy_reward": 5,
    }).json()

    res = client.get("/api/dashboard")
    assert res.status_code == 200
    routine_quests = res.json()["routine_quests"]
    assert any(q["id"] == quest["id"] for q in routine_quests)


def test_routine_quest_is_all_done_today_false_before_complete(client):
    quest = client.post("/api/quests", json={
        "title": "루틴미완료테스트",
        "quest_type": "daily",
        "routine": {"type": "daily"},
        "intimacy_reward": 5,
    }).json()
    st = client.post("/api/subtasks", json={
        "quest_id": quest["id"], "title": "서브태스크", "order": 0
    }).json()

    res = client.get("/api/dashboard")
    routine_quests = res.json()["routine_quests"]
    target = next(q for q in routine_quests if q["id"] == quest["id"])
    assert target["is_all_done_today"] is False


def test_routine_quest_is_all_done_today_true_after_complete(client):
    quest = client.post("/api/quests", json={
        "title": "루틴완료테스트",
        "quest_type": "daily",
        "routine": {"type": "daily"},
        "intimacy_reward": 5,
    }).json()
    st = client.post("/api/subtasks", json={
        "quest_id": quest["id"], "title": "서브태스크", "order": 0
    }).json()

    client.post(f"/api/subtasks/{st['id']}/complete")

    res = client.get("/api/dashboard")
    routine_quests = res.json()["routine_quests"]
    target = next(q for q in routine_quests if q["id"] == quest["id"])
    assert target["is_all_done_today"] is True


def test_self_section_contains_self_needs_and_quests(client):
    # npc_id 없는 need = self need
    need = client.post("/api/needs", json={"title": "나를위한니즈"}).json()
    quest = client.post("/api/quests", json={
        "need_id": need["id"],
        "title": "나를위한퀘스트",
        "quest_type": "one_time",
        "intimacy_reward": 10,
    }).json()

    res = client.get("/api/dashboard")
    assert res.status_code == 200
    self_section = res.json()["self_section"]

    need_entry = next(
        (nwq for nwq in self_section["needs"] if nwq["need"]["id"] == need["id"]),
        None,
    )
    assert need_entry is not None
    assert any(q["id"] == quest["id"] for q in need_entry["quests"])


def test_completed_routine_quests_sorted_to_bottom(client):
    # 미완료 퀘스트 생성
    q_undone = client.post("/api/quests", json={
        "title": "미완료루틴",
        "quest_type": "daily",
        "routine": {"type": "daily"},
        "intimacy_reward": 5,
    }).json()

    # 완료 퀘스트 생성 + 완료 처리
    q_done = client.post("/api/quests", json={
        "title": "완료루틴",
        "quest_type": "daily",
        "routine": {"type": "daily"},
        "intimacy_reward": 5,
    }).json()
    st = client.post("/api/subtasks", json={
        "quest_id": q_done["id"], "title": "서브태스크", "order": 0
    }).json()
    client.post(f"/api/subtasks/{st['id']}/complete")

    res = client.get("/api/dashboard")
    routine_quests = res.json()["routine_quests"]

    idx_undone = next((i for i, q in enumerate(routine_quests) if q["id"] == q_undone["id"]), None)
    idx_done = next((i for i, q in enumerate(routine_quests) if q["id"] == q_done["id"]), None)

    assert idx_undone is not None
    assert idx_done is not None
    assert idx_undone < idx_done  # 미완료가 완료보다 앞에 와야 함
