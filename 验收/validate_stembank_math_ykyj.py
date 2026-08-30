from __future__ import annotations

import hashlib
import io
import json
import sys
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

try:
    from PIL import Image
except ImportError:  # pragma: no cover - reported in output
    Image = None


APP_SCHEMA_MAJOR = 1
EXPECTED_BOOK_ID = "MATH_YKYL2026_U1"
EXPECTED_DELIVERY_ID = "MATH_YKYL2026_U1_REVIEWED_FROZEN_V1.0"
EXPECTED_TOTALS = {"chapters": 9, "lessons": 106, "questions": 1378, "assets": 2822}

HERE = Path(__file__).resolve().parent
APP_ROOT = HERE.parent
DELIVERY_ROOT = APP_ROOT / "题库" / "数学" / "章节练习" / "一课一练" / "2026上册"
RESULT_JSON = HERE / "math-ykyj-import-acceptance-results.json"
RESULT_MD = HERE / "math-ykyj-import-acceptance-report.md"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def json_entry(names: list[str], pattern: str) -> str | None:
    candidates = [name for name in names if name.lower().endswith(pattern)]
    if not candidates:
        return None
    return sorted(candidates, key=lambda value: (value.count("/"), len(value)))[0]


def unsafe_entry(name: str) -> bool:
    path = PurePosixPath(name.replace("\\", "/"))
    return path.is_absolute() or ".." in path.parts or ":" in path.parts[0]


def resolve_asset(names: set[str], questions_entry: str, asset_path: str) -> str | None:
    clean = asset_path.lstrip("./")
    root = questions_entry[: -len("data/questions.json")] if questions_entry.lower().endswith("data/questions.json") else questions_entry[: -len("questions.json")]
    for candidate in (root + clean, clean):
        if candidate in names:
            return candidate
    suffix = "/" + clean
    matches = [name for name in names if name.endswith(suffix)]
    return matches[0] if len(matches) == 1 else None


def validate_zip(path: Path, expected: dict) -> dict:
    row = {
        "chapter": expected["chapter"],
        "file_name": path.name,
        "sha256": sha256_file(path),
        "errors": [],
        "warnings": [],
        "question_count": 0,
        "lesson_count": 0,
        "asset_count": 0,
        "decoded_asset_count": 0,
        "question_ids": [],
        "section_ids": [],
        "package_id": "",
        "chapter_id": "",
    }
    if row["sha256"] != str(expected["sha256"]).upper():
        row["errors"].append("SHA-256 differs from delivery manifest")
    if path.stat().st_size != int(expected["bytes"]):
        row["errors"].append("file size differs from delivery manifest")

    try:
        with zipfile.ZipFile(path) as archive:
            names_list = archive.namelist()
            names = set(names_list)
            duplicates = [name for name, count in Counter(names_list).items() if count > 1]
            if duplicates:
                row["errors"].append(f"duplicate ZIP entries: {duplicates[:3]}")
            bad_paths = [name for name in names_list if unsafe_entry(name)]
            if bad_paths:
                row["errors"].append(f"unsafe ZIP paths: {bad_paths[:3]}")

            manifest_entry = json_entry(names_list, "manifest.json")
            questions_entry = json_entry(names_list, "questions.json")
            if not manifest_entry or not questions_entry:
                row["errors"].append("manifest.json or questions.json is missing")
                return row

            manifest = json.loads(archive.read(manifest_entry).decode("utf-8-sig"))
            questions_doc = json.loads(archive.read(questions_entry).decode("utf-8-sig"))
            questions = questions_doc.get("questions") or []
            row["package_id"] = manifest.get("package_id", "")
            row["chapter_id"] = manifest.get("chapter_id", "")

            schema = str(manifest.get("schema_version") or questions_doc.get("schema_version") or "1")
            try:
                if int(schema.split(".")[0]) > APP_SCHEMA_MAJOR:
                    row["errors"].append(f"unsupported schema {schema}")
            except ValueError:
                row["errors"].append(f"invalid schema {schema}")
            if manifest.get("subject_id") != "math":
                row["errors"].append("subject_id is not math")
            if manifest.get("book_id") != EXPECTED_BOOK_ID:
                row["errors"].append("book_id mismatch")
            if manifest.get("package_id") != questions_doc.get("package_id"):
                row["errors"].append("package_id differs between manifest and questions")
            if len(questions) != int(expected["question_count"]):
                row["errors"].append("question count differs from delivery manifest")

            active_questions = [q for q in questions if q.get("is_active") is not False and q.get("content_status") in {"verified", "image_verified", "needs_review"}]
            if len(active_questions) != len(questions):
                row["errors"].append("some questions would be rejected by the V3 loader status gate")

            question_ids = [q.get("question_id") for q in questions]
            if any(not value for value in question_ids) or len(question_ids) != len(set(question_ids)):
                row["errors"].append("question IDs are missing or duplicated within the package")
            section_ids = {q.get("section_id") for q in questions if q.get("section_id")}
            if not section_ids or any(not q.get("section_name") for q in questions):
                row["errors"].append("section_id/section_name required for V3 lesson navigation is missing")

            referenced_assets: list[tuple[dict, str]] = []
            for question in questions:
                for asset in question.get("assets") or []:
                    resolved = resolve_asset(names, questions_entry, str(asset.get("file_path") or ""))
                    if not resolved:
                        row["errors"].append(f"missing asset {asset.get('file_path')} for {question.get('question_id')}")
                        continue
                    referenced_assets.append((asset, resolved))

            for asset, entry_name in referenced_assets:
                if Image is None:
                    continue
                try:
                    with Image.open(io.BytesIO(archive.read(entry_name))) as image:
                        image.load()
                        row["decoded_asset_count"] += 1
                        if asset.get("width") and int(asset["width"]) != image.width:
                            row["errors"].append(f"width mismatch: {entry_name}")
                        if asset.get("height") and int(asset["height"]) != image.height:
                            row["errors"].append(f"height mismatch: {entry_name}")
                except Exception as exc:  # noqa: BLE001
                    row["errors"].append(f"image decode failed: {entry_name}: {exc}")

            row["question_count"] = len(questions)
            row["lesson_count"] = len(section_ids)
            row["asset_count"] = len(referenced_assets)
            row["question_ids"] = question_ids
            row["section_ids"] = sorted(section_ids)
            if Image is None:
                row["warnings"].append("Pillow unavailable; image decode and dimension checks skipped")
    except (zipfile.BadZipFile, json.JSONDecodeError, UnicodeDecodeError) as exc:
        row["errors"].append(f"archive/JSON parse failure: {exc}")
    return row


def main() -> int:
    manifest_path = DELIVERY_ROOT / "delivery-manifest.json"
    if not manifest_path.exists():
        raise SystemExit(f"Missing delivery manifest: {manifest_path}")
    delivery = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    if delivery.get("delivery_id") != EXPECTED_DELIVERY_ID or delivery.get("book_id") != EXPECTED_BOOK_ID:
        raise SystemExit("Unexpected delivery identity")

    chapters = []
    for expected in delivery.get("chapters") or []:
        path = DELIVERY_ROOT / expected["file_name"]
        if path.exists():
            chapters.append(validate_zip(path, expected))
        else:
            chapters.append({"chapter": expected["chapter"], "file_name": expected["file_name"], "errors": ["file missing"], "warnings": [], "question_count": 0, "lesson_count": 0, "asset_count": 0, "decoded_asset_count": 0, "question_ids": [], "section_ids": [], "package_id": "", "chapter_id": "", "sha256": ""})

    all_question_ids = [item for chapter in chapters for item in chapter["question_ids"]]
    all_section_ids = [item for chapter in chapters for item in chapter["section_ids"]]
    totals = {
        "chapters": len(chapters),
        "lessons": len(set(all_section_ids)),
        "questions": sum(chapter["question_count"] for chapter in chapters),
        "assets": sum(chapter["asset_count"] for chapter in chapters),
        "decoded_assets": sum(chapter["decoded_asset_count"] for chapter in chapters),
    }
    errors = [f"{chapter['file_name']}: {error}" for chapter in chapters for error in chapter["errors"]]
    warnings = [f"{chapter['file_name']}: {warning}" for chapter in chapters for warning in chapter["warnings"]]
    if len(all_question_ids) != len(set(all_question_ids)):
        errors.append("question IDs are duplicated across chapter packages")
    for key, expected in EXPECTED_TOTALS.items():
        if totals[key] != expected:
            errors.append(f"total {key} expected {expected}, got {totals[key]}")

    result = {
        "validation_profile": "mathbank_v3_real_frozen_package_acceptance_v1",
        "validated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "app_version": "3.1.0",
        "question_schema_version": "1.1",
        "delivery_id": delivery["delivery_id"],
        "delivery_root": str(DELIVERY_ROOT),
        "status": "passed" if not errors else "failed",
        "pillow_available": Image is not None,
        "totals": totals,
        "expected_totals": EXPECTED_TOTALS,
        "stable_question_ids_unique": len(all_question_ids) == len(set(all_question_ids)),
        "errors": errors,
        "warnings": warnings,
        "chapters": [{key: value for key, value in chapter.items() if key not in {"question_ids", "section_ids"}} for chapter in chapters],
    }
    RESULT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# STEMBank 数学 V3.1.0 一课一练导入验收报告",
        "",
        f"- 结果：`{result['status']}`",
        f"- 应用版本：`{result['app_version']}`",
        f"- 题库结构：`{result['question_schema_version']}`",
        f"- 交付 ID：`{result['delivery_id']}`",
        f"- 验收时间：`{result['validated_at']}`",
        "",
        "## 总量",
        "",
        f"- 章节：{totals['chapters']} / {EXPECTED_TOTALS['chapters']}",
        f"- 课次：{totals['lessons']} / {EXPECTED_TOTALS['lessons']}",
        f"- 题目：{totals['questions']} / {EXPECTED_TOTALS['questions']}",
        f"- 资源引用：{totals['assets']} / {EXPECTED_TOTALS['assets']}",
        f"- 成功解码图片：{totals['decoded_assets']}",
        f"- 全书稳定题目 ID 唯一：{'是' if result['stable_question_ids_unique'] else '否'}",
        "",
        "## 逐章结果",
        "",
        "| 章 | 题目 | 课次 | 资源 | 解码 | 结果 |",
        "| ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for chapter in chapters:
        lines.append(f"| {chapter['chapter']} | {chapter['question_count']} | {chapter['lesson_count']} | {chapter['asset_count']} | {chapter['decoded_asset_count']} | {'通过' if not chapter['errors'] else '失败'} |")
    lines.extend(["", "## 验收边界", "", "本报告验证了 V3 加载合同、Schema 1.1、交付哈希、ZIP 安全、题目与课次稳定 ID、全部资源引用、图片解码和尺寸。由于应用内浏览器安全策略不允许打开本地 `file://` 页面，本轮未自动执行可见浏览器点击测试；学生首次使用时仍应按 README 完成一次人工界面确认。", ""])
    if errors:
        lines.extend(["## 错误", ""] + [f"- {item}" for item in errors] + [""])
    if warnings:
        lines.extend(["## 警告", ""] + [f"- {item}" for item in warnings] + [""])
    RESULT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"status": result["status"], "totals": totals, "errors": len(errors), "warnings": len(warnings)}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
