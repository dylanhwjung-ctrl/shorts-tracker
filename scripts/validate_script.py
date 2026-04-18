"""
대본 자동 검증 도구 (규칙 기반 lint)

사용법:
  python scripts/validate_script.py <script_path>
  python scripts/validate_script.py <script_path> --category engineering
  python scripts/validate_script.py <script_path> --strict   # 경고도 exit 1

검사 항목:
  1. 문장 단위 줄바꿈 — 한 줄에 종결부호 2+개
  2. 글자 수 — 600~650자 가이드 (공백 포함)
  3. 톤 교차 검출 — 공학(~입니다체) vs 게임(~함체)
  4. TTS 발음 가이드 — 영문 단어 목록 (수동 대조용)
  5. 금지 단어 — 노란딱지 방지 (살인/자살/시신/학살 등)
  6. 시각·청각 지시문 — [화면·효과음·BGM·컷 등]

연동: feedback_script_line_break / _length / _engineering_tone, script_prompt.md
"""

import sys
import io
import re
import argparse
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")


# 종결부호 (한/영 양쪽)
SENTENCE_END = "[.!?]"

# 톤 감지 — 종결부호 직전의 한글 어미만 추출하여 판정
# "어미." / "어미!" / "어미?" / "어미'." / "어미다." 등
ENG_ENDINGS = ["입니다", "습니다", "하죠", "입니다만"]
GAME_ENDINGS = ["함", "음", "거임", "다고 함", "다고", "는데", "라고 함"]

# 라인별 어미 추출 정규식 — 종결부호 직전 한글 3자 이내
ENDING_EXTRACTOR = re.compile(r"([가-힣]{1,5})(?:['\"」』)]?[.!?])")

# 금지 단어 (노란딱지 방지) — 오탐 방지 위해 보수적 패턴
FORBIDDEN_PATTERNS = [
    (re.compile(r"살인"), "살인", "세상을 떠났다·최후를 맞이했다·제거당했다"),
    (re.compile(r"살해"), "살해", "세상을 떠났다·최후를 맞이했다·제거당했다"),
    (re.compile(r"자살"), "자살", "극단적 선택"),
    (re.compile(r"학살"), "학살", "희생시켰다·비극으로 몰아넣었다"),
    (re.compile(r"출혈"), "출혈", "붉은 흔적·붉은 액체"),
    (re.compile(r"시신"), "시신", "쓰러진 모습·남겨진 자취"),
    (re.compile(r"시체"), "시체", "쓰러진 모습·남겨진 자취"),
    (re.compile(r"제물로 바치"), "제물로 바치다", "희생시켰다"),
    # '피'는 구체 문구만 (오탐 방지: 피자/피해/피부/피의자 등 제외)
    (re.compile(r"피가 [튀흐쏟]|피를 [흘쏟]|흘린 피|피투성이|피범벅"), "피(유혈 표현)", "붉은 흔적·붉은 액체"),
]

# 시각·청각 지시문 (좁은 키워드)
STAGE_DIRECTION_PATTERNS = [
    re.compile(r"\[화면"),
    re.compile(r"\[자막"),
    re.compile(r"\[컷"),
    re.compile(r"\[카메라"),
    re.compile(r"\[효과음"),
    re.compile(r"효과음\]"),
    re.compile(r"BGM[:：\s]"),
    re.compile(r"\(효과음\)"),
    re.compile(r"\(배경음\)"),
    re.compile(r"\(지문\)"),
]

# 영문 단어 (TTS 가이드 검사용) — 3자 이상 알파벳
ENGLISH_WORD_PATTERN = re.compile(r"\b[A-Za-z][A-Za-z\-]{2,}\b")

# 카테고리 자동 추론 — 경로 패턴
CATEGORY_HINTS = [
    (re.compile(r"07_기술"), "engineering"),
    (re.compile(r"05_게임"), "gaming"),
    (re.compile(r"06_야구|baseball"), "baseball"),
]


class Issue:
    def __init__(self, level, code, line, message):
        self.level = level  # 'error' | 'warning' | 'info'
        self.code = code
        self.line = line  # None for whole-file issues
        self.message = message

    def format(self):
        icon = {"error": "❌", "warning": "⚠️ ", "info": "ℹ️ "}[self.level]
        loc = f"L{self.line}" if self.line else "—"
        return f"{icon} [{self.level.capitalize():<7}] {loc}  [{self.code}]  {self.message}"


def infer_category(path):
    p_str = str(path).replace("\\", "/")
    for pat, cat in CATEGORY_HINTS:
        if pat.search(p_str):
            return cat
    return None


def extract_body_preserve_lines(text):
    """대본 파일에서 본문만 남기고 메타 헤더는 빈 줄로 치환 (라인 번호 유지).

    우선순위:
      1) <script>...</script> 블록 (공학 대본 패턴)
      2) 마지막 `---` 구분자 이후 (게임 대본 패턴)
      3) 둘 다 없으면 전체 반환
    """
    lines = text.splitlines()
    body_lines = [""] * len(lines)

    in_script = False
    script_found = False
    for i, line in enumerate(lines):
        if re.match(r"\s*<script>\s*$", line):
            in_script = True
            script_found = True
            continue
        if re.match(r"\s*</script>\s*$", line):
            in_script = False
            continue
        if in_script:
            body_lines[i] = line

    if script_found:
        return "\n".join(body_lines)

    last_hr = -1
    for i, line in enumerate(lines):
        if re.match(r"^---+\s*$", line):
            last_hr = i
    if last_hr >= 0:
        for i in range(last_hr + 1, len(lines)):
            body_lines[i] = lines[i]
        return "\n".join(body_lines)

    return text


def check_line_breaks(lines):
    issues = []
    end_re = re.compile(SENTENCE_END)
    for i, line in enumerate(lines, 1):
        # 빈 줄이나 단락 구분은 skip
        stripped = line.strip()
        if not stripped:
            continue
        # 종결부호 개수 세기 (따옴표 뒤 포함)
        count = len(end_re.findall(stripped))
        # 문장 끝이 종결부호로 끝나면 정상 1개. 2개 이상이면 한 줄 안에 여러 문장.
        if count >= 2:
            # 맨 끝 종결부호는 정상이므로 내부에 1개 이상 있으면 경고
            # 정확히는 끝에서 제외하고 세기
            without_tail = re.sub(rf"{SENTENCE_END}+$", "", stripped)
            inner = len(end_re.findall(without_tail))
            if inner >= 1:
                issues.append(Issue(
                    "warning", "LINE_BREAK", i,
                    f"한 줄에 문장 {inner + 1}개 — 문장마다 줄바꿈 필요: \"{stripped[:60]}{'...' if len(stripped) > 60 else ''}\""
                ))
    return issues


def check_length(text):
    # 공백 포함 글자수 (줄바꿈 제외)
    count = len(text.replace("\n", "").replace("\r", ""))
    issues = []
    if count < 600:
        issues.append(Issue(
            "info", "LENGTH_SHORT", None,
            f"총 {count}자 — 가이드 600~650자 미만 (부족해도 억지로 늘리지 말 것)"
        ))
    elif count > 700:
        issues.append(Issue(
            "warning", "LENGTH_LONG", None,
            f"총 {count}자 — 700자 초과 (가이드 650 초과 심화)"
        ))
    elif count > 650:
        issues.append(Issue(
            "warning", "LENGTH_LONG", None,
            f"총 {count}자 — 650자 초과 (가이드 600~650)"
        ))
    else:
        issues.append(Issue(
            "info", "LENGTH_OK", None,
            f"총 {count}자 — 가이드 범위 (600~650)"
        ))
    return issues


def classify_ending(ending):
    """어미 문자열을 받아 'engineering' / 'gaming' / None 반환"""
    # 완전 일치 또는 끝부분 일치
    for e in ENG_ENDINGS:
        if ending.endswith(e):
            return "engineering"
    for e in GAME_ENDINGS:
        if ending.endswith(e):
            return "gaming"
    return None


def check_tone(lines, category):
    issues = []
    if not category:
        return issues
    # 서술 카테고리: engineering 계열은 '~입니다체', gaming은 '~함체'
    expected = "engineering" if category in ("engineering", "baseball") else "gaming"
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped:
            continue
        for m in ENDING_EXTRACTOR.finditer(stripped):
            ending = m.group(1)
            tone = classify_ending(ending)
            if tone and tone != expected:
                label_expected = "공식체(~입니다)" if expected == "engineering" else "커뮤니티체(~함)"
                label_found = "커뮤니티체(~함)" if tone == "gaming" else "공식체(~입니다)"
                issues.append(Issue(
                    "error", "TONE_MIX", i,
                    f"{label_expected} 기대 카테고리인데 {label_found} 어미 '{ending}' 사용"
                ))
                break  # 한 줄에 하나만 보고
    return issues


def check_tts_hints(text):
    words = ENGLISH_WORD_PATTERN.findall(text)
    # 중복 제거, 순서 유지
    seen = set()
    unique = []
    for w in words:
        if w not in seen:
            seen.add(w)
            unique.append(w)
    if not unique:
        return []
    return [Issue(
        "warning", "TTS_ENGLISH", None,
        f"영문 단어 {len(unique)}개 — 한글 발음 병기 수동 확인 필요: {', '.join(unique[:10])}{'...' if len(unique) > 10 else ''}"
    )]


def check_forbidden_words(lines):
    issues = []
    for i, line in enumerate(lines, 1):
        for pat, label, replacement in FORBIDDEN_PATTERNS:
            if pat.search(line):
                issues.append(Issue(
                    "error", "FORBIDDEN", i,
                    f"금지 단어 '{label}' 감지 → 순화 권장: {replacement}"
                ))
    return issues


def check_stage_directions(lines):
    issues = []
    for i, line in enumerate(lines, 1):
        for pat in STAGE_DIRECTION_PATTERNS:
            m = pat.search(line)
            if m:
                issues.append(Issue(
                    "error", "STAGE_DIR", i,
                    f"시각·청각 지시문 감지 '{m.group()}' — 대본엔 내레이션만"
                ))
                break
    return issues


def main():
    ap = argparse.ArgumentParser(
        description="대본 자동 검증",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("script_path", help="대본 파일 경로 (상대/절대 모두 허용)")
    ap.add_argument("--category", choices=["engineering", "gaming", "baseball"],
                    help="카테고리 강제 지정 (미지정 시 경로 기반 자동 추론)")
    ap.add_argument("--strict", action="store_true", help="경고도 exit 1로 처리")
    args = ap.parse_args()

    path = Path(args.script_path)
    if not path.exists():
        print(f"❌ 파일을 찾을 수 없음: {path}", file=sys.stderr)
        sys.exit(2)

    raw_text = path.read_text(encoding="utf-8")
    text = extract_body_preserve_lines(raw_text)
    lines = text.splitlines()

    category = args.category or infer_category(path)
    cat_label = {
        "engineering": "공학/과학 (~입니다체)",
        "gaming": "게임 (~함체)",
        "baseball": "야구 (~입니다체 추정)",
    }.get(category, "미지정 — 톤 검사 skip")

    print(f"📄 {path.name}")
    print(f"   카테고리: {cat_label}{' (자동 추론)' if category and not args.category else ''}")
    print()

    all_issues = []
    all_issues += check_line_breaks(lines)
    all_issues += check_length(text)
    all_issues += check_tone(lines, category)
    all_issues += check_tts_hints(text)
    all_issues += check_forbidden_words(lines)
    all_issues += check_stage_directions(lines)

    # 라인 순 정렬
    all_issues.sort(key=lambda x: (x.line or 10**9))

    for it in all_issues:
        print(it.format())

    err = sum(1 for x in all_issues if x.level == "error")
    warn = sum(1 for x in all_issues if x.level == "warning")
    info = sum(1 for x in all_issues if x.level == "info")

    print()
    print(f"📊 요약: Error {err}건, Warning {warn}건, Info {info}건")

    if err > 0:
        sys.exit(1)
    if args.strict and warn > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
