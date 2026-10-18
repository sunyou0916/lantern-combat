# Lantern Combat v0.37

랜턴이 멈춘 세 탑에 빛을 나누면 식물과 물고기가 돌아오고 공기가 맑아집니다.
중앙의 먹구름을 없앤 뒤에는 유령이 되어 달라진 풍경을 둘러봅니다.
v0.37은 **v0.36과 게임 내용이 완전히 같고, 코드 구조만 정리한 버전**입니다. 이전 버전은 그대로 보존했습니다.

## 실행

`lantern_combat.v0.37` 폴더에서:

```powershell
python -m pip install -r requirements.txt
python main.py
```

Python과 Pygame이 필요합니다(v0.36과 같은 Python 3.11에서 사용 가능). 코드와 `assets/`, `map.json`을 함께 유지하세요.
한국어 폰트는 `assets/fonts/`에 라이선스와 함께 동봉되어 있습니다.

## 진행과 조작

랜덤 맵 탐험 → 땅·물·공기 레이드 → 열린 탑에 접촉 → 세 탑 점등 → 먹구름 보스 → 엔딩 → 유령 자유 탐험.
지역 첫 입장과 레이드 완료 안내 중에는 조작이 계속됩니다.
도입 6초, 탑 점등 2.8초, 보스 등장 4.8초, 엔딩 9.5초 동안만 조작을 멈춥니다.

| 입력 | 동작 |
| --- | --- |
| WASD / 방향키 | 이동 |
| 마우스로 조준 + Space / 왼쪽 버튼 | 불꽃 공격 |
| E | 전투방 탈출 확인. 탑은 접촉으로 활성화 |
| Enter | 현재 컷신 건너뛰기 |
| Esc | 일시정지·재개. 탈출 확인창에서는 취소 |
| R | 스토리와 방문 기록까지 초기화하고 새 게임 |
| M | 일반 플레이 중 음악 켜기·끄기 |
| 마우스 휠 / 오른쪽 드래그 / F | 유령 탐험 중 확대·축소 / 카메라 이동 / 따라가기 |

컷신이 끝나면 누르고 있던 이동·공격·E 키를 놓아 주세요.
컷신을 넘겨도 점등·능력치 변경·보스 생성·유령 전환은 정상 적용됩니다.

보스 HP **480**, 공격 피해 **30**, 타워의 보스 피해 초당 **0.6**과 기존 네 패턴을 유지합니다.
세 번째 탑에서도 플레이어는 HP **40**, 공격력 **6**으로 살아서 싸웁니다.

## 코드 구조

v0.36까지는 `game.py` 한 파일(1,586줄)의 `Game` 클래스가 맵 생성부터 보스 패턴, 그리기, 메인 루프까지
모두 맡았습니다. v0.37에서는 역할별 클래스로 나눴습니다.

```
main.py                     실행 진입점
lantern/
  config.py                 모든 밸런스·화면·파일 경로 설정값
  game.py                   Game: 상태를 묶고 매 프레임 시스템을 순서대로 실행
  game_state.py             Phase(진행 단계), GameState, Notice(안내 문구), EndingSequence
  app.py · input.py         창·메인 루프 / 키보드·마우스 → 게임 명령
  audio.py                  배경 음악, 효과음
  world/                    맵
    map_generator.py          MapGenerator: 미로·전투방·적·함정 배치 생성
    world_map.py              WorldMap: 생성된 맵과 좌표·충돌·검색
    room.py · trap.py         Room(전투방, RoomStatus) · Trap
    pathfinding.py            GridNavigator: 적의 길찾기
  entities/                 게임 속 대상 (데이터 클래스)
    player.py · enemy.py      Player · Enemy
    boss.py                   Boss, BossDash(돌진), Hazard(번개 표식)
    projectiles.py            Flame(불꽃), HealItem
  systems/                  규칙
    movement.py               PlayerMovement: 이동·벽 충돌·방 입장
    raid.py                   RaidSystem: 레이드 진행·적 생성·탈출 확인
    combat.py                 CombatSystem: 공격·피해·탑 빛·회복·함정
    enemy_ai.py               EnemyAI: 감지·추격·근접 공격
    boss_fight.py             BossFight: 보스 이동과 네 가지 패턴
    progression.py            Progression: 탑 점등 → 보스 → 엔딩 → 유령
    camera.py                 Camera
  story/
    script.py                 이야기 문구와 장면 길이
    director.py               StoryDirector: 시간 기반 컷신 재생
  render/                   그리기
    renderer.py               GameRenderer: 월드 → HUD → 오버레이
    world_renderer.py         바닥·정화 효과·탑·적·보스·플레이어
    lighting.py · hud.py      안개·조명 / 화면 고정 UI
    story_renderer.py         컷신 연출·자막
    sprites.py · themes.py    애니메이션·테마 이미지 불러오기
    fonts.py · layers.py      한국어 글꼴 / 레이어 캐시
```

| 고치고 싶은 것 | 파일 |
| --- | --- |
| HP·공격력·속도·보스 수치 같은 밸런스 | `lantern/config.py` |
| 이야기 문구, 컷신 길이 | `lantern/story/script.py` (`INTRO`, `REGIONS`, `TOWERS`, `BOSS_LINES`, `ENDING`, `DURATIONS`) |
| 보스 패턴 | `lantern/systems/boss_fight.py` |
| 적의 움직임 | `lantern/systems/enemy_ai.py` |
| 레이드 규칙 | `lantern/systems/raid.py` |
| 탑을 켰을 때 일어나는 일 | `lantern/systems/progression.py` |
| 맵 생성 | `lantern/world/map_generator.py` |
| 화면 모습 | `lantern/render/` |
