from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data" / "catalog.json"
PAGE = ROOT / "学科" / "化学" / "index.html"
PACKAGE_ROOT = ROOT / "题库" / "化学" / "章节练习" / "金典导学案" / "必修第一册"
EXPECTED = {
    "PKG_CHEM_JINDIAN_GUIDE_SH_B1_C01": (166, 9, 39, "2c26ce50be75cabe19a2e68f522725ddeeb09212f3d7885debad341f560cc906"),
    "PKG_CHEM_JINDIAN_GUIDE_SH_B1_C02": (176, 9, 40, "7c405787101fcc69aad280918a2dae1038db5ab6e8b8ea7c5b1a3adafcee0786"),
    "PKG_CHEM_JINDIAN_GUIDE_SH_B1_C03": (105, 6, 26, "98cfc81adf3f87048d642a20b48cca3303bcd62d81cad97bd0eb57866a6bf9ec"),
    "PKG_CHEM_JINDIAN_GUIDE_SH_B1_C04": (160, 9, 41, "e973d02b980af204fb213fdbfa82e987f237d833fcaacac3889207bfca83bcb3"),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def unsafe(name: str) -> bool:
    path = PurePosixPath(name.replace("\\", "/"))
    return path.is_absolute() or ".." in path.parts or (path.parts and ":" in path.parts[0])


def main() -> None:
    errors: list[str] = []
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    entries = [item for item in catalog.get("packages", []) if item.get("subject_id") == "chemistry"]
    if len(entries) != 4 or {item.get("package_id") for item in entries} != set(EXPECTED):
        errors.append("catalog must expose exactly four Chemistry chapters")
    if len({item.get("library_id") for item in entries}) != 1 or len({item.get("book_id") for item in entries}) != 1:
        errors.append("catalog Chemistry library/book grouping is inconsistent")
    if [item.get("chapter_order") for item in sorted(entries, key=lambda x: x.get("chapter_order", 0))] != [1, 2, 3, 4]:
        errors.append("catalog Chemistry chapter order is invalid")

    package_results = []
    for entry in entries:
        package_id = entry["package_id"]
        questions, sections, segments, expected_hash = EXPECTED[package_id]
        path = ROOT / entry["path"]
        if not path.is_file():
            errors.append(f"missing ZIP: {entry['path']}")
            continue
        actual_hash = sha256(path)
        if actual_hash != expected_hash or path.stat().st_size != entry.get("file_size"):
            errors.append(f"ZIP hash or size mismatch: {package_id}")
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            if any(unsafe(name) for name in names):
                errors.append(f"unsafe ZIP entry: {package_id}")
            if not {"manifest.json", "questions.json", "learning-content.json", "README.md"} <= set(names):
                errors.append(f"required entry missing: {package_id}")
                continue
            manifest = json.loads(archive.read("manifest.json"))
            question_doc = json.loads(archive.read("questions.json"))
            learning = json.loads(archive.read("learning-content.json"))
        if manifest.get("schema_version") != "1.1" or manifest.get("package_status") != "frozen":
            errors.append(f"not a frozen Schema 1.1 package: {package_id}")
        if manifest.get("package_id") != package_id or len(question_doc.get("questions", [])) != questions:
            errors.append(f"question identity/count mismatch: {package_id}")
        if manifest.get("section_count") != sections or len(learning.get("lessons", [])) != sections:
            errors.append(f"lesson count mismatch: {package_id}")
        if len(learning.get("segments", [])) != segments:
            errors.append(f"knowledge segment count mismatch: {package_id}")
        if entry.get("question_count") != questions or entry.get("section_count") != sections or entry.get("published") is not True:
            errors.append(f"catalog metadata mismatch: {package_id}")
        package_results.append({"package_id": package_id, "questions": questions, "sections": sections, "knowledge_segments": segments, "sha256": actual_hash})

    html = PAGE.read_text(encoding="utf-8")
    required_text = ["V3.4.0 正式版", "chemistryLibrarySelect", "chemistryBookSelect", "chemistryLessonSelect", "openCourseKnowledge", "查看原书前题材料", "已显示最多前五题"]
    for text in required_text:
        if text not in html:
            errors.append(f"Chemistry page capability marker missing: {text}")
    forbidden = ["V3.3.0 本地验收版", "请先把第一章加入学习范围"]
    for text in forbidden:
        if text in html:
            errors.append(f"stale local-review marker remains: {text}")

    result = {
        "status": "passed" if not errors else "failed",
        "chemistry_packages": len(package_results),
        "questions": sum(item["questions"] for item in package_results),
        "sections": sum(item["sections"] for item in package_results),
        "knowledge_segments": sum(item["knowledge_segments"] for item in package_results),
        "packages": package_results,
        "errors": errors,
    }
    output = ROOT / "验收" / "chemistry-whole-book-local-validation.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
