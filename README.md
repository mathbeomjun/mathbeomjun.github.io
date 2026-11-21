# 최범준 학술 홈페이지 · CV · 전체 기록

이 저장소는 **데이터 파일 세 개**로 홈페이지, 공개 CV, 비공개 전체 기록을 자동으로 만듭니다.
사람이든 AI든, 내용을 바꿀 때는 아래 "무엇을 어디에" 표만 보면 됩니다.

## 1. 구조

```
data/papers.bib          ← 논문 전부 (BibTeX)
data/cv.yml              ← 논문 외 모든 이력 + 어떤 섹션을 어디에 보일지(outputs)
private/private.yml      ← 비공개 세부 기록 (GitHub에 올라가지 않음, .gitignore)
private/private.example.yml   비공개 기록 양식
files/                   ← 홈페이지에 올릴 PDF (프로그램북, 강의노트 등)
templates/index.html.j2  홈페이지 구조
templates/cv.tex.j2      CV·전체 기록 조판 (XeLaTeX)
assets/style.css         홈페이지 디자인 (색·서체·여백)
assets/flow.js           상단 곡선단축흐름 그림
fonts/                   CV용 Source Serif 4 (SIL OFL)
build.py                 빌드 스크립트
.github/workflows/       push 하면 자동 빌드·배포
```

결과물

| 결과물 | 공개 | 만드는 방법 |
|---|---|---|
| 홈페이지 `index.html` | 공개 | push 하면 자동 / `python build.py --no-pdf` |
| 공개 CV `cv.pdf` | 공개 | push 하면 자동 / `python build.py` |
| 전체 기록 `record.pdf` | 비공개 | 로컬에서 `python build.py --record` 만 |
| `sitemap.xml`, `robots.txt` | 공개 | 빌드할 때 자동 (홈페이지·cv.pdf·files/ PDF 목록, `profile.site_url` 기준) |

홈페이지 `<head>`의 검색·링크 미리보기 정보(Open Graph, JSON-LD)는 `data/cv.yml` 의 `profile` 에서 자동으로 채워집니다.

## 2. 무엇을 어디에 (자주 하는 작업)

| 하고 싶은 일 | 파일 | 방법 |
|---|---|---|
| 새 프리프린트 | `data/papers.bib` | Preprints 구역 맨 위에 항목 추가, `status = {preprint}` (파일 머리말에 템플릿) |
| 논문 게재 승인 | `data/papers.bib` | 해당 항목에 `status = {accepted}`, `journal` 추가, Accepted 구역으로 이동 |
| 논문 출판 | `data/papers.bib` | `status` 줄 삭제, `doi`·`volume`·`pages` 추가, Published 구역 맨 위로 |
| 새 강연 | `data/cv.yml` → `talks` | 맨 위에 `date`, `title`, `event`, `place` |
| 새 연구비·수상 | `data/cv.yml` → `grants` | 맨 위에 추가. 과제번호는 `number`, 사사 문구는 `ack` |
| 연구비 금액·역할 | `private/private.yml` | "Research grants (details)" 섹션 |
| 새 학기 강의 | `data/cv.yml` → `teaching.instructor` | 맨 위에 한 줄 |
| 학회·워크숍 조직 | `data/cv.yml` → `organized` | 맨 위에 추가. 행사 전이면 `status: upcoming` |
| 편집·학회 위원 | `data/cv.yml` → `service` | 맨 위에 추가 |
| 논문 심사·평가위원·학위심사 | `private/private.yml` | 해당 섹션 맨 위에 추가 |
| PDF 자료 공개 | `files/` + `data/cv.yml` | PDF를 `files/`에 넣고, 항목에 `file: files/이름.pdf` |
| 홈페이지에서만 숨기기 | `data/cv.yml` | 항목에 `hide: [web]` (CV에서만 숨기려면 `[cv]`) |
| 섹션 자체를 빼거나 순서 변경 | `data/cv.yml` → `outputs` | 목록에서 이름을 빼거나 순서 변경 |
| 직위 변경 | `data/cv.yml` → `profile.position` 과 `positions` | 새 직위 맨 위에, 이전 직위는 `group: previous` 와 종료 시점 |
| 색·서체·여백 | `assets/style.css` | 맨 위 `:root` 변수 |

각 데이터 파일의 맨 위와 섹션마다 필드 설명과 예시가 주석으로 달려 있습니다.

## 3. 반드시 지킬 것

- **`private/private.yml` 은 절대 GitHub에 올리지 않습니다.** GitHub Desktop이나 git으로 올리면 `.gitignore`가 자동으로 막아 주지만, GitHub 웹페이지에 끌어다 올리면 막지 못합니다.
- **사실이 확인되지 않은 내용을 추가하지 않습니다.** 특히 AI가 수정할 때 이메일·문서로 확인되지 않은 강연·직위·수상은 넣지 말고, 불확실하면 `private.yml` 에 "(확인 필요)"로만 남깁니다.
- **인용 키(`@article{...}`의 이름)는 바꾸지 않습니다.** `private.yml`의 `paper_notes`가 이 키로 연결됩니다.
- **YAML 들여쓰기는 스페이스 2칸**, 날짜·기간은 따옴표로 감쌉니다.
- 새 항목은 각 목록의 **맨 위**에 추가합니다 (적힌 순서대로 출력됨).
- 수정 후에는 `python build.py --no-pdf` 로 빌드가 성공하는지 확인합니다.

## 4. 처음 한 번 설정 (GitHub Pages)

1. 이 폴더를 Dropbox 등 원하는 곳에 두고, `private.yml`을 `private/` 안에 넣습니다.
2. GitHub Desktop: File → Add Local Repository → 이 폴더 → create a repository.
3. 변경 목록에 `private.yml`이 없는지 확인하고 Commit.
4. Publish repository: 이름 `아이디.github.io`, "Keep this code private" 해제.
5. GitHub 저장소 Settings → Pages → Source 를 **GitHub Actions** 로.
6. Actions 탭에서 초록색 체크 확인 후 `https://아이디.github.io` 접속.
7. `data/cv.yml` 의 `profile.site_url` 에 그 주소를 적고 다시 Commit·Push (CV 안 링크가 새 주소를 쓰게 됨).

## 5. 로컬 빌드

```
pip install pyyaml jinja2 bibtexparser==1.4.2
python build.py --no-pdf   # 홈페이지만
python build.py            # + cv.pdf  (XeLaTeX, latexmk, Noto Serif CJK KR 필요)
python build.py --record   # + private_out/record.pdf
cd _site && python -m http.server   # http://localhost:8000 에서 미리보기
```
