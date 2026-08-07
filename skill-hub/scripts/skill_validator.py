#!/usr/bin/env python3
"""skill_validator.py — Skill 校验层，参考 DataFlow-Harness 的 Validation Engine
每次 skill_manage 操作前先跑校验，不通过则拒绝提交。
用法：
  python3.11 skill_validator.py check <skill_path>         # 校验单个 Skill
  python3.11 skill_validator.py check-all                  # 校验所有已安装 Skill
  python3.11 skill_validator.py preflight <action> <name>  # 操作前校验（create/patch/delete）
"""

import sys, os, re, json, yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, List

SKILLS_DIR = Path.home() / ".hermes" / "skills"
REQUIRED_FIELDS = ["name", "description"]
OPTIONAL_FIELDS = ["category", "version", "label", "disable-model-invocation", "metadata"]


@dataclass
class ValidationError:
    """校验失败记录"""
    path: str
    field: str
    message: str
    severity: str = "error"  # error | warning


@dataclass
class ValidationResult:
    """校验结果"""
    skill_path: str
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return len(self.errors) == 0

    @property
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0


def parse_frontmatter(filepath: Path) -> tuple[dict, str]:
    """解析 SKILL.md 的 YAML frontmatter"""
    content = filepath.read_text()
    # 匹配 YAML frontmatter (--- ... ---)
    match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if not match:
        return {}, content
    try:
        frontmatter = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError as e:
        return {"_yaml_error": str(e)}, content
    return frontmatter, content


def list_all_skills() -> dict[str, Path]:
    """扫描所有已安装 Skill，返回 {name: path}"""
    skills = {}
    for md in SKILLS_DIR.rglob("**/SKILL.md"):
        fm, _ = parse_frontmatter(md)
        name = fm.get("name", "")
        if name:
            skills[name] = md.parent
    return skills


def validate_skill(skill_path: Path, all_skills: dict) -> ValidationResult:
    """校验单个 Skill"""
    result = ValidationResult(skill_path=str(skill_path))

    if not (skill_path / "SKILL.md").exists():
        result.errors.append(ValidationError(str(skill_path), "file", "SKILL.md 不存在"))
        return result

    fm, content = parse_frontmatter(skill_path / "SKILL.md")

    # 0. YAML 语法错误（最优先）
    if "_yaml_error" in fm:
        result.errors.append(ValidationError(str(skill_path), "YAML", f"语法错误: {fm['_yaml_error']}"))
        return result

    # 1. 必填字段
    for field in REQUIRED_FIELDS:
        if field not in fm or not fm[field]:
            result.errors.append(ValidationError(str(skill_path), field, f"缺少必填字段 '{field}'"))

    # 2. name 是否合法（小写 + 连字符）
    name = fm.get("name", "")
    if name and not re.match(r'^[a-z][a-z0-9_-]{0,63}$', name):
        result.errors.append(ValidationError(
            str(skill_path), "name",
            f"'{name}' 不合法: 必须小写字母开头，仅含 [a-z0-9_-]，最长 64 字符"
        ))

    # 3. category 是否已存在同名字段
    category = fm.get("category", "")
    if category and category not in {"feishu", "development", "data-science", "devops",
                                       "research", "productivity", "automation", "personal",
                                       "TWS", "feishu-ai", "", "mlops", "creative",
                                       "design-taste-frontend", "gaming", "media", "email",
                                       "weread", "social-media", "smart-home", "leisure",
                                       "gifs", "apple", "pipeline", "domain", "yuanbao",
                                       "computer-use", "finance", "note-taking", "diagramming",
                                       "mcp", "stackpilot", "inference-sh", "dogfood",
                                       "baoyu-design", "emil-design-eng", "apple-design",
                                       "hermes-desktop-plugins", "skill-hub",
                                       "animation-vocabulary", "improve-animations",
                                       "find-animation-opportunities", "review-animations",
                                       "interest-driven-onboarding", "knowledge-capture",
                                       "feishu-card-send"}:
        result.warnings.append(ValidationError(
            str(skill_path), "category",
            f"'{category}' 不是已注册的 category，建议检查是否拼写错误",
            severity="warning"
        ))

    # 4. description 长度
    desc = fm.get("description", "")
    if desc and len(desc) < 20:
        result.warnings.append(ValidationError(
            str(skill_path), "description",
            f"描述过短 ({len(desc)} 字符)，建议 ≥20 字说明 Skill 用途",
            severity="warning"
        ))

    # 5. 引用的 Skill 是否存在（从 frontmatter 和内容中提取）
    refs = set()
    for line in content.split("\n"):
        for m in re.finditer(r'`([a-z][a-z0-9_-]+)`\s*(?:skill|Skill)', line):
            refs.add(m.group(1))
        # Also check "See also: xxx, yyy" patterns
        if "see" in line.lower() and "skill" in line.lower():
            for m in re.finditer(r'(?:skill|Skill)[:\s]+`([a-z0-9_-]+)`', line):
                refs.add(m.group(1))

    for ref in refs:
        if ref != name and ref not in all_skills:
            result.warnings.append(ValidationError(
                str(skill_path), "reference",
                f"引用的 Skill '{ref}' 不存在",
                severity="warning"
            ))

    # 6. 文件完整性检查
    references_dir = skill_path / "references"
    templates_dir = skill_path / "templates"
    scripts_dir = skill_path / "scripts"
    if references_dir.exists() and not any(references_dir.iterdir()):
        result.warnings.append(ValidationError(str(skill_path), "file", "references/ 目录为空"))

    return result


def validate_all() -> dict[str, ValidationResult]:
    """校验所有 Skill"""
    all_skills = list_all_skills()
    results = {}
    for name, path in sorted(all_skills.items()):
        results[name] = validate_skill(path, all_skills)
    return results


def preflight_check(action: str, skill_name: str) -> ValidationResult:
    """操作前校验"""
    skill_path = SKILLS_DIR / skill_name
    all_skills = list_all_skills()

    result = ValidationResult(skill_path=str(skill_path))

    if action in ("create",):
        # 创建前检查：是否已存在
        if skill_name in all_skills:
            result.errors.append(ValidationError(
                str(all_skills[skill_name]), "name",
                f"Skill '{skill_name}' 已存在: {all_skills[skill_name]}",
            ))
        # 检查 name 格式
        if not re.match(r'^[a-z][a-z0-9_-]{0,63}$', skill_name):
            result.errors.append(ValidationError(
                str(skill_path), "name",
                f"'{skill_name}' 不合法: 必须小写字母开头，仅含 [a-z0-9_-]"
            ))

    if action in ("patch", "edit"):
        if not (skill_path / "SKILL.md").exists():
            result.errors.append(ValidationError(
                str(skill_path), "file",
                f"Skill '{skill_name}' 不存在，无法修改"
            ))

    if action in ("delete",):
        if not (skill_path / "SKILL.md").exists():
            result.errors.append(ValidationError(
                str(skill_path), "file",
                f"Skill '{skill_name}' 不存在，无法删除"
            ))
        else:
            # 删除前检查：是否有其他 Skill 引用它
            all_skills = list_all_skills()
            for other_name, other_path in all_skills.items():
                if other_name == skill_name:
                    continue
                _, content = parse_frontmatter(other_path / "SKILL.md")
                if skill_name in content:
                    result.warnings.append(ValidationError(
                        str(other_path), "reference",
                        f"'{other_name}' 引用了 '{skill_name}'，删除后引用会断裂",
                        severity="warning"
                    ))

    return result


def format_result(result: ValidationResult) -> str:
    """格式化输出校验结果"""
    lines = []
    name = os.path.basename(result.skill_path)
    status = "✅" if result.passed else "❌"
    lines.append(f"\n{status} {name}")

    for e in result.errors:
        lines.append(f"  ❌ [{e.field}] {e.message}")
    for w in result.warnings:
        lines.append(f"  ⚠️  [{w.field}] {w.message}")

    if result.passed and not result.has_warnings:
        lines.append(f"  ✅ 全部通过")
    return "\n".join(lines)


# CLI
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Skill Validator — DataFlow-Harness 风格校验层")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("check-all", help="校验所有 Skill")

    check = sub.add_parser("check", help="校验单个 Skill")
    check.add_argument("skill_path", help="Skill 路径或名称")

    pf = sub.add_parser("preflight", help="操作前校验")
    pf.add_argument("action", choices=["create", "patch", "edit", "delete"])
    pf.add_argument("skill_name")

    args = parser.parse_args()

    if args.command == "check-all":
        results = validate_all()
        error_count = sum(1 for r in results.values() if not r.passed)
        warn_count = sum(1 for r in results.values() if r.has_warnings)
        for r in results.values():
            if not r.passed or r.has_warnings:
                print(format_result(r))
        print(f"\n{'='*50}")
        print(f"总计: {len(results)} Skills | ❌ {error_count} 个错误 | ⚠️ {warn_count} 个警告")

    elif args.command == "check":
        path = SKILLS_DIR / args.skill_path
        if not path.exists():
            print(f"❌ Skill '{args.skill_path}' 不存在")
            sys.exit(1)
        all_skills = list_all_skills()
        result = validate_skill(path, all_skills)
        print(format_result(result))
        sys.exit(0 if result.passed else 1)

    elif args.command == "preflight":
        result = preflight_check(args.action, args.skill_name)
        print(format_result(result))
        sys.exit(0 if result.passed else 1)
