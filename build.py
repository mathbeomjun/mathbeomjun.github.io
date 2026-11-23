#!/usr/bin/env python3
"""build.py — 홈페이지·공개 CV·비공개 전체 기록을 만드는 빌드 스크립트.

사용법
    python build.py             # _site/index.html, _site/cv.pdf  (GitHub Actions 가 실행하는 것과 동일)
    python build.py --no-pdf    # 홈페이지만 (LaTeX 없이 빠르게 확인)
    python build.py --record    # + private_out/record.pdf (private/private.yml 이 있으면 반영)
    python build.py --inline    # + _site/preview.html (CSS/JS 를 한 파일에 넣은 미리보기)

입력 (내용은 이 세 파일에서만 수정)
    data/papers.bib        모든 논문
    data/cv.yml            나머지 이력 + 출력 설정(outputs)
    private/private.yml    비공개 세부 기록 (GitHub 에 올리지 않음)

출력
    _site/                 GitHub Pages 로 배포되는 폴더 (index.html, cv.pdf, assets/, files/)
    private_out/record.pdf 비공개 전체 기록
    build/                 LaTeX 중간 파일 (무시해도 됨)

구조
    load()          cv.yml + papers.bib + private.yml 을 읽어 하나의 dict 로
    load_papers()   BibTeX → 논문 dict 목록. status 로 publications/preprints 분리, 연도 내림차순
    context()       출력(web/cv/record)별로 hide 필터(vis), 섹션 on/off(on), 링크 선택(link) 제공
    render_html()   templates/index.html.j2 → _site/index.html
    render_pdf()    templates/cv.tex.j2 → XeLaTeX(latexmk) → cv.pdf / record.pdf
    write_seo()     _site/sitemap.xml, robots.txt (검색엔진용, profile.site_url 기준)
의존성: pyyaml, jinja2, bibtexparser==1.4.2 (2.x 는 API 가 달라 동작하지 않음), XeLaTeX, Noto Serif CJK KR.
"""
import collections
import datetime as dt
import hashlib
import html
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import bibtexparser
import jinja2
import yaml

ROOT = Path(__file__).resolve().parent
OUT, BUILD, PRIVATE_OUT = ROOT / "_site", ROOT / "build", ROOT / "private_out"
SELF = "Beomjun"

# ── text helpers ─────────────────────────────────────────────────────────
GREEK = dict(zip(
    "alpha beta gamma delta epsilon varepsilon zeta eta theta kappa lambda mu nu xi pi rho sigma tau phi varphi chi psi omega "
    "Gamma Delta Theta Lambda Xi Pi Sigma Phi Psi Omega".split(),
    "αβγδϵεζηθκλμνξπρστϕφχψωΓΔΘΛΞΠΣΦΨΩ"))
BB = {"R": "ℝ", "C": "ℂ", "N": "ℕ", "Z": "ℤ", "Q": "ℚ", "H": "ℍ", "S": "𝕊", "T": "𝕋"}
SYM = {"infty": "∞", "partial": "∂", "nabla": "∇", "cdot": "·", "times": "×", "le": "≤", "leq": "≤",
       "ge": "≥", "geq": "≥", "to": "→", "in": "∈"}


def _math_html(m):
    m = re.sub(r"\\mathbb\{(\w)\}", lambda g: BB.get(g.group(1), g.group(1)), m)
    m = re.sub(r"\\([A-Za-z]+)", lambda g: GREEK.get(g.group(1), SYM.get(g.group(1), g.group(0))), m)
    m = html.escape(m, quote=False)
    m = re.sub(r"(?<![\w&;])([A-Za-z])(?![\w])", r"<i>\1</i>", m)
    m = re.sub(r"\^\{([^}]*)\}|\^(\S)", lambda g: f"<sup>{g.group(1) or g.group(2)}</sup>", m)
    m = re.sub(r"_\{([^}]*)\}|_(\S)", lambda g: f"<sub>{g.group(1) or g.group(2)}</sub>", m)
    return f'<span class="m">{m}</span>'


def _plain(s):
    return s.replace("---", "—").replace("--", "–").replace("``", "“").replace("''", "”").replace("{", "").replace("}", "")


def tex2html(s):
    if not s:
        return ""
    parts = re.split(r"(\$[^$]+\$)", str(s))
    return "".join(_math_html(p[1:-1]) if p.startswith("$") else html.escape(_plain(p), quote=False) for p in parts)


HANGUL = re.compile(r"([\u1100-\u11ff\u3000-\u303f\u3130-\u318f\uac00-\ud7a3][\u1100-\u11ff\u3000-\u303f\u3130-\u318f\uac00-\ud7a3\s]*[\u1100-\u11ff\u3000-\u303f\u3130-\u318f\uac00-\ud7a3]|[\u1100-\u11ff\u3000-\u303f\u3130-\u318f\uac00-\ud7a3])")


def tex_escape(s):
    """Escape LaTeX specials outside $...$; wrap Hangul runs in \\kr{}."""
    if s is None:
        return ""
    out = []
    for p in re.split(r"(\$[^$]+\$)", str(s)):
        if p.startswith("$"):
            out.append(p)
            continue
        p = (p.replace("\\", r"\textbackslash{}").replace("&", r"\&").replace("%", r"\%").replace("#", r"\#")
              .replace("_", r"\_").replace("~", r"\textasciitilde{}").replace("^", r"\textasciicircum{}"))
        p = HANGUL.sub(r"{\\kr \1}", p)
        out.append(p)
    return "".join(out)


def bib_tex(s):
    """BibTeX field → LaTeX body (braces kept, Hangul wrapped)."""
    return HANGUL.sub(r"{\\kr \1}", str(s or "")).replace("&", r"\&").replace("%", r"\%")


def url_escape(u):
    return str(u).replace("%", r"\%").replace("#", r"\#").replace("&", r"\&")


def with_list(names):
    names = list(names or [])
    if not names:
        return ""
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def flip(name):
    name = name.strip()
    if "," in name:
        last, first = [x.strip() for x in name.split(",", 1)]
        return f"{first} {last}"
    return name


def visible(items, out):
    if out == "record":
        return list(items or [])
    return [x for x in (items or []) if out not in (x.get("hide") or [])]


# ── data ─────────────────────────────────────────────────────────────────
def load_papers():
    parser = bibtexparser.bparser.BibTexParser(common_strings=True, ignore_nonstandard_types=False)
    db = bibtexparser.loads((ROOT / "data" / "papers.bib").read_text(encoding="utf-8"), parser)
    papers = []
    for order, e in enumerate(db.entries):
        authors = [a for a in re.split(r"\s+and\s+", e.get("author", "")) if a.strip()]
        co = [flip(a) for a in authors if SELF not in a]
        p = {
            "key": e["ID"], "order": order,
            "title": e.get("title", ""), "journal": e.get("journal", ""),
            "volume": e.get("volume"), "number": e.get("number"), "pages": e.get("pages"),
            "year": int(e.get("year", 0)), "doi": e.get("doi"), "url": e.get("url"),
            "arxiv": e.get("eprint"), "status": e.get("status", "published").strip().lower(),
            "note": e.get("note"), "hide": [h.strip() for h in e.get("hide", "").split(",") if h.strip()],
            "with": with_list(co),
        }
        p["arxiv_url"] = f"https://arxiv.org/abs/{p['arxiv']}" if p["arxiv"] else None
        p["journal_url"] = p["url"] or (f"https://doi.org/{p['doi']}" if p["doi"] else None)
        if p["arxiv"]:
            yy = int(p["arxiv"][:2])
            p["posted"] = 2000 + yy
        papers.append(p)
    key = lambda p: (-p["year"], p["order"])
    pubs = sorted([p for p in papers if p["status"] != "preprint"], key=key)
    pre = sorted([p for p in papers if p["status"] == "preprint"], key=key)
    return papers, pubs, pre


def load():
    data = yaml.safe_load((ROOT / "data" / "cv.yml").read_text(encoding="utf-8"))
    data["papers"], data["publications"], data["preprints"] = load_papers()
    for o in data.get("organized", []):
        o["with_str"] = with_list(o.get("with"))
    for t in data.get("talks", []):
        t["year"] = int(str(t["date"])[:4])
    now = dt.datetime.now(dt.timezone(dt.timedelta(hours=9)))
    data["updated"], data["updated_iso"] = now.strftime("%B %-d, %Y"), now.strftime("%Y-%m-%d")
    priv = ROOT / "private" / "private.yml"
    data["private"] = yaml.safe_load(priv.read_text(encoding="utf-8")) if priv.exists() else {}
    return data


def summary(data):
    rows = collections.defaultdict(lambda: {"published": 0, "posted": 0, "talks": 0})
    for p in data["papers"]:
        if p["status"] != "preprint":
            rows[p["year"]]["published"] += 1
        if p.get("posted"):
            rows[p["posted"]]["posted"] += 1
    for t in data.get("talks", []):
        rows[t["year"]]["talks"] += 1
    years = sorted(rows, reverse=True)
    return {
        "n_pub": sum(p["status"] == "published" for p in data["papers"]),
        "n_acc": sum(p["status"] == "accepted" for p in data["papers"]),
        "n_pre": sum(p["status"] == "preprint" for p in data["papers"]),
        "n_talks": len(data.get("talks", [])),
        "rows": [(y, rows[y]) for y in years if y >= 2015],
    }


# ── renderers ────────────────────────────────────────────────────────────
def make_link(data, out):
    base = (data["profile"].get("site_url") or "").rstrip("/")
    def link(item):
        item = item or {}
        f, u = item.get("file"), item.get("url")
        if out == "web":
            return f or u
        if f and base:
            return f"{base}/{f}"
        return u or (f"{base}/{f}" if f and base else None)
    return link


def context(data, out):
    c = dict(data)
    c["link"] = make_link(data, out)
    c["out"] = out
    c["on"] = lambda section: section in data["outputs"][out]
    c["vis"] = lambda items: visible(items, out)
    c["publications"] = visible(data["publications"], out)
    c["preprints"] = visible(data["preprints"], out)
    return c


def site_meta(data):
    """검색엔진용 구조화 정보(JSON-LD, schema.org ProfilePage/Person). 내용은 cv.yml 의 profile 에서만 가져옴."""
    p = data["profile"]
    base = (p.get("site_url") or p.get("url") or "").rstrip("/")
    person = {
        "@type": "Person",
        "name": p["name"],
        "alternateName": p.get("name_ko"),
        "jobTitle": p.get("position"),
        "worksFor": {"@type": "CollegeOrUniversity", "name": p.get("institution"),
                     "department": {"@type": "Organization", "name": p.get("department")}},
        "affiliation": {"@type": "CollegeOrUniversity", "name": p.get("institution")},
        "knowsAbout": [s.strip() for s in re.split(r",| and ", p.get("interests_web") or "") if s.strip()],
        "url": base + "/" if base else None,
    }
    page = {"@context": "https://schema.org", "@type": "ProfilePage", "mainEntity":
            {k: v for k, v in person.items() if v}}
    return json.dumps(page, ensure_ascii=False, indent=1).replace("</", "<\\/")


def write_seo(data):
    """_site/sitemap.xml, _site/robots.txt — profile.site_url 이 있을 때만."""
    base = (data["profile"].get("site_url") or "").rstrip("/")
    if not base:
        return
    today = dt.date.today().isoformat()
    paths = [""] + (["cv.pdf"] if (OUT / "cv.pdf").exists() else [])
    paths += sorted(f.relative_to(OUT).as_posix() for f in (OUT / "files").rglob("*.pdf")) if (OUT / "files").exists() else []
    urls = "".join(f"  <url><loc>{html.escape(base + '/' + p)}</loc><lastmod>{today}</lastmod></url>\n" for p in paths)
    (OUT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + urls + "</urlset>\n", encoding="utf-8")
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {base}/sitemap.xml\n", encoding="utf-8")


def render_html(data, inline=False):
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(ROOT / "templates"), autoescape=False,
                             trim_blocks=True, lstrip_blocks=True)
    env.filters["t"] = tex2html
    env.filters["e"] = lambda s: html.escape(str(s or ""))
    ctx = context(data, "web")
    ctx["jsonld"] = site_meta(data)
    css = (ROOT / "assets" / "style.css").read_bytes()
    ctx["style_version"] = hashlib.sha256(css).hexdigest()[:16]
    ctx["script_version"] = hashlib.sha256((ROOT / "assets" / "flow.js").read_bytes()).hexdigest()[:16]
    (OUT / "index.html").write_text(env.get_template("index.html.j2").render(**ctx, inline=False), encoding="utf-8")
    if inline:
        js = (ROOT / "assets" / "flow.js").read_text(encoding="utf-8")
        page = env.get_template("index.html.j2").render(**ctx, inline=True, inline_css=css.decode("utf-8"), inline_js=js)
        (OUT / "preview.html").write_text(page, encoding="utf-8")


def render_pdf(data, out, dest):
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(ROOT / "templates"),
        block_start_string="((*", block_end_string="*))", variable_start_string="(((",
        variable_end_string=")))", comment_start_string="((=", comment_end_string="=))",
        trim_blocks=True, lstrip_blocks=True, autoescape=False)
    env.filters["x"] = tex_escape
    env.filters["b"] = bib_tex
    env.filters["u"] = url_escape
    ctx = context(data, out)
    if out == "record":
        ctx["stats"] = summary(data)
    BUILD.mkdir(exist_ok=True)
    name = "cv" if out == "cv" else "record"
    tex = env.get_template("cv.tex.j2").render(**ctx, fontdir=str(ROOT / "fonts") + "/")
    (BUILD / f"{name}.tex").write_text(tex, encoding="utf-8")
    subprocess.run(["latexmk", "-xelatex", "-interaction=nonstopmode", "-halt-on-error", f"{name}.tex"],
                   cwd=BUILD, check=True, stdout=subprocess.DEVNULL)
    dest.parent.mkdir(exist_ok=True)
    shutil.copy(BUILD / f"{name}.pdf", dest)


def replace_tree(src, dst):
    """dst 를 src 의 새 복사본으로 교체 (지난 빌드에서 남은 파일도 정리됨).
    Dropbox 폴더에서는 기존 _site 파일을 덮어쓰거나 그 플래그를 바꾸는 것이 막힐 수 있어
    (Errno 1 Operation not permitted), 먼저 지우고 내용만 복사한다 (copy2 의 메타데이터·플래그 복사 생략)."""
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, copy_function=shutil.copy)


def main():
    data = load()
    OUT.mkdir(exist_ok=True)
    replace_tree(ROOT / "assets", OUT / "assets")
    if (ROOT / "files").exists():
        replace_tree(ROOT / "files", OUT / "files")
    (OUT / ".nojekyll").touch()
    render_html(data, inline="--inline" in sys.argv)
    if "--no-pdf" not in sys.argv:
        render_pdf(data, "cv", OUT / "cv.pdf")
    if "--record" in sys.argv:
        render_pdf(data, "record", PRIVATE_OUT / "record.pdf")
    write_seo(data)
    print(f"built: {len(data['publications'])} publications, {len(data['preprints'])} preprints, "
          f"{len(data.get('talks', []))} talks")


if __name__ == "__main__":
    main()
