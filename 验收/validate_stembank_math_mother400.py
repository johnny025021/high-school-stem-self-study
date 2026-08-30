from __future__ import annotations

import io
import json
import sys
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

try:
    from PIL import Image
except ImportError:
    Image = None


HERE = Path(__file__).resolve().parent
APP_ROOT = HERE.parent
BANK_ROOT = APP_ROOT / "题库" / "数学" / "章节练习" / "母题400"
RESULT_JSON = HERE / "math-mother400-acceptance-results.json"
RESULT_MD = HERE / "math-mother400-acceptance-report.md"
EXPECTED_PACKAGES = 21
EXPECTED_QUESTIONS = 400
KNOWN_SOURCE_METADATA_MISMATCHES = {
    "B1_C01_第1章_集合与逻辑_核心母题_V1.0.zip": {
        "assets/subjects/math/Q_MATH_B1_C01_0007/answer_01.webp": {
            "recorded": [1095, 241],
            "actual": [1095, 251],
            "reason": "inherited source-package height metadata; image bytes decode correctly and are preserved unchanged",
        }
    }
}


def unsafe_entry(name: str) -> bool:
    path = PurePosixPath(name.replace("\\", "/"))
    return path.is_absolute() or ".." in path.parts or (path.parts and ":" in path.parts[0])


def find_entry(names: list[str], suffix: str) -> str | None:
    candidates = [name for name in names if name.lower().endswith(suffix)]
    return sorted(candidates, key=lambda value: (value.count("/"), len(value)))[0] if candidates else None


def resolve_asset(names: set[str], entry: str, asset_path: str) -> str | None:
    clean = asset_path.lstrip("./")
    root = entry[: -len("data/questions.json")] if entry.lower().endswith("data/questions.json") else entry[: -len("questions.json")]
    for candidate in (root + clean, clean):
        if candidate in names:
            return candidate
    matches = [name for name in names if name.endswith("/" + clean)]
    return matches[0] if len(matches) == 1 else None


def validate_package(path: Path) -> dict:
    row = {
        "file_name": path.name,
        "package_id": "",
        "chapter_id": "",
        "question_count": 0,
        "asset_count": 0,
        "decoded_asset_count": 0,
        "question_ids": [],
        "errors": [],
        "warnings": [],
    }
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

            manifest_entry = find_entry(names_list, "manifest.json")
            questions_entry = find_entry(names_list, "questions.json")
            if not manifest_entry or not questions_entry:
                row["errors"].append("manifest.json or questions.json is missing")
                return row

            manifest = json.loads(archive.read(manifest_entry).decode("utf-8-sig"))
            document = json.loads(archive.read(questions_entry).decode("utf-8-sig"))
            questions = document.get("questions") or []
            row["package_id"] = manifest.get("package_id", "")
            row["chapter_id"] = manifest.get("chapter_id", "")
            row["question_count"] = len(questions)

            if manifest.get("subject_id") != "math":
                row["errors"].append("subject_id is not math")
            if manifest.get("package_id") != document.get("package_id"):
                row["errors"].append("package_id differs between manifest and questions")
            if int(manifest.get("question_count") or 0) != len(questions):
                row["errors"].append("question_count differs from manifest")
            if int(manifest.get("mother_question_count") or 0) != len(questions):
                row["errors"].append("mother_question_count differs from questions")

            ids = [question.get("question_id") for question in questions]
            row["question_ids"] = ids
            if any(not value for value in ids) or len(ids) != len(set(ids)):
                row["errors"].append("question IDs are missing or duplicated within package")
            if any(question.get("subject_id") != "math" for question in questions):
                row["errors"].append("question subject_id is not math")
            if any(question.get("is_mother_question") is False for question in questions):
                row["errors"].append("package contains a non-mother question")

            referenced: list[tuple[dict, str]] = []
            for question in questions:
                for asset in question.get("assets") or []:
                    resolved = resolve_asset(names, questions_entry, str(asset.get("file_path") or ""))
                    if not resolved:
                        row["errors"].append(f"missing asset {asset.get('file_path')} for {question.get('question_id')}")
                    else:
                        referenced.append((asset, resolved))

            row["asset_count"] = len(referenced)
            if Image is None:
                row["warnings"].append("Pillow unavailable; image decoding skipped")
            else:
                for asset, entry_name in referenced:
                    try:
                        with Image.open(io.BytesIO(archive.read(entry_name))) as image:
                            image.load()
                            row["decoded_asset_count"] += 1
                            recorded = [int(asset.get("width") or image.width), int(asset.get("height") or image.height)]
                            actual = [image.width, image.height]
                            known = KNOWN_SOURCE_METADATA_MISMATCHES.get(path.name, {}).get(entry_name)
                            if recorded != actual:
                                if known and recorded == known["recorded"] and actual == known["actual"]:
                                    row["warnings"].append(f"known source metadata mismatch preserved unchanged: {entry_name} recorded={recorded} actual={actual}")
                                else:
                                    row["errors"].append(f"dimension mismatch: {entry_name} recorded={recorded} actual={actual}")
                    except Exception as exc:  # noqa: BLE001
                        row["errors"].append(f"image decode failed: {entry_name}: {exc}")
    except (zipfile.BadZipFile, json.JSONDecodeError, UnicodeDecodeError) as exc:
        row["errors"].append(f"archive/JSON parse failure: {exc}")
    return row


def main() -> int:
    paths = sorted(BANK_ROOT.glob("*.zip"))
    packages = [validate_package(path) for path in paths]
    ids = [question_id for package in packages for question_id in package["question_ids"]]
    errors = [f"{package['file_name']}: {error}" for package in packages for error in package["errors"]]
    warnings = [f"{package['file_name']}: {warning}" for package in packages for warning in package["warnings"]]
    if len(paths) != EXPECTED_PACKAGES:
        errors.append(f"package count expected {EXPECTED_PACKAGES}, got {len(paths)}")
    if len(ids) != EXPECTED_QUESTIONS:
        errors.append(f"question count expected {EXPECTED_QUESTIONS}, got {len(ids)}")
    if len(ids) != len(set(ids)):
        errors.append("question IDs are duplicated across packages")

    result = {
        "validation_profile": "stembank_math_mother400_acceptance_v1",
        "validated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "bank_root": str(BANK_ROOT),
        "status": "passed" if not errors else "failed",
        "pillow_available": Image is not None,
        "totals": {
            "packages": len(paths),
            "questions": len(ids),
            "assets": sum(package["asset_count"] for package in packages),
            "decoded_assets": sum(package["decoded_asset_count"] for package in packages),
        },
        "stable_question_ids_unique": len(ids) == len(set(ids)),
        "errors": errors,
        "warnings": warnings,
        "packages": [{key: value for key, value in package.items() if key != "question_ids"} for package in packages],
    }
    RESULT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# STEMBank 数学母题400验收报告",
        "",
        f"- 结果：`{result['status']}`",
        f"- 题库包：{result['totals']['packages']} / {EXPECTED_PACKAGES}",
        f"- 母题：{result['totals']['questions']} / {EXPECTED_QUESTIONS}",
        f"- 资源：{result['totals']['assets']}",
        f"- 成功解码：{result['totals']['decoded_assets']}",
        f"- 稳定题号全局唯一：{'是' if result['stable_question_ids_unique'] else '否'}",
        "",
        "## 边界",
        "",
        "本报告验证ZIP安全、包身份、母题标记、稳定题号、资源引用、图片解码和尺寸。可见界面仍需人工复核。",
        "",
    ]
    if errors:
        lines.extend(["## 错误", ""] + [f"- {item}" for item in errors] + [""])
    if warnings:
        lines.extend(["## 警告", ""] + [f"- {item}" for item in warnings] + [""])
    RESULT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"status": result["status"], "totals": result["totals"], "errors": len(errors), "warnings": len(warnings)}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
