#!/usr/bin/env python3
"""skill_mutate.py — 类型化增量突变，不动全文，只改 YAML 里的一个字段。
参考 DataFlow-Harness 的 Mediated Mutation：每次操作原子化，不可分割。

用法：
  python3.11 skill_mutate.py <skill_name> update_field <key> <value>
  python3.11 skill_mutate.py <skill_name> add_tag <tag>
  python3.11 skill_mutate.py <skill_name> remove_tag <tag>
  python3.11 skill_mutate.py <skill_name> add_related <other_skill> <relationship>
  python3.11 skill_mutate.py <skill_name> remove_related <other_skill>

示例：
  skill_mutate.py deep-grill update_field status published
  skill_mutate.py deep-grill add_tag TWS
  skill_mutate.py deep-grill add_related grill-me suggested_after
"""

import sys, re, os
from pathlib import Path
import yaml

SKILLS_DIR = Path.home() / ".hermes" / "skills"
ALLOWED_TOP_KEYS = {"name", "description", "category", "version", "label",
                     "disable-model-invocation", "metadata", "status", "priority"}
ALLOWED_RELATIONSHIPS = {"suggested_after", "related_to", "precedes", "depends_on", "use_with"}


class SkillMutator:
    def __init__(self, skill_name: str):
        self.skill_name = skill_name
        self.skill_dir = SKILLS_DIR / skill_name
        self.md_path = self.skill_dir / "SKILL.md"

        if not self.md_path.exists():
            print(f"❌ Skill '{skill_name}' 不存在: {self.md_path}")
            sys.exit(1)

        self.raw = self.md_path.read_text()
        self._parse()

    def _parse(self):
        """解析 YAML frontmatter + body"""
        m = re.match(r'^---\s*\n(.*?)\n---\s*\n?(.*)', self.raw, re.DOTALL)
        if not m:
            print(f"❌ SKILL.md 无 YAML frontmatter")
            sys.exit(1)
        try:
            self.frontmatter = yaml.safe_load(m.group(1)) or {}
        except yaml.YAMLError as e:
            print(f"❌ YAML 语法错误: {e}")
            sys.exit(1)
        self.body = m.group(2)

    def _save(self):
        """YAML 序列化 → 写回 SKILL.md"""
        new_yaml = yaml.dump(self.frontmatter, allow_unicode=True,
                             sort_keys=False, default_flow_style=False).strip()
        new_content = f"---\n{new_yaml}\n---\n{self.body}"
        self.md_path.write_text(new_content)

    # ─── 字段操作 ──────────────────────────────────

    def update_field(self, key: str, value: str):
        """修改或新增 YAML 顶层字段"""
        key = key.strip()

        # 自动类型转换
        if value.lower() == "true":
            value = True
        elif value.lower() == "false":
            value = False
        elif value.isdigit():
            value = int(value)

        old = self.frontmatter.get(key)
        self.frontmatter[key] = value
        self._save()
        print(f"✅ [{self.skill_name}] {key}: {old} → {value}")

    # ─── 标签操作 ──────────────────────────────────

    def add_tag(self, tag: str):
        tag = tag.strip()
        tags = self.frontmatter.get("tags", [])
        if not isinstance(tags, list):
            tags = []
        if tag in tags:
            print(f"⚠️  [{self.skill_name}] tag '{tag}' 已存在，跳过")
            return
        tags.append(tag)
        self.frontmatter["tags"] = tags
        self._save()
        print(f"✅ [{self.skill_name}] +tag: {tag}")

    def remove_tag(self, tag: str):
        tag = tag.strip()
        tags = self.frontmatter.get("tags", [])
        if tag not in tags:
            print(f"⚠️  [{self.skill_name}] tag '{tag}' 不存在，跳过")
            return
        tags.remove(tag)
        self.frontmatter["tags"] = tags
        self._save()
        print(f"✅ [{self.skill_name}] -tag: {tag}")

    # ─── 关联 Skill 操作 ───────────────────────────

    def add_related(self, other: str, relationship: str = "related_to"):
        other = other.strip()
        relationship = relationship.strip()
        if relationship not in ALLOWED_RELATIONSHIPS:
            print(f"❌ 不支持的 relationship: '{relationship}'")
            print(f"   可选: {', '.join(ALLOWED_RELATIONSHIPS)}")
            sys.exit(1)

        # 检查对方 Skill 是否存在
        other_path = SKILLS_DIR / other / "SKILL.md"
        if not other_path.exists():
            print(f"⚠️  Skill '{other}' 不存在，但允许关联（可能是外部 Skill）")

        related = self.frontmatter.get("related_skills", [])
        if not isinstance(related, list):
            related = []

        new_entry = {"skill": other, "relationship": relationship}
        if new_entry in related:
            print(f"⚠️  [{self.skill_name}] → {other} 已关联，跳过")
            return

        related.append(new_entry)
        self.frontmatter["related_skills"] = related
        self._save()
        print(f"✅ [{self.skill_name}] → {other} ({relationship})")

    def remove_related(self, other: str):
        other = other.strip()
        related = self.frontmatter.get("related_skills", [])
        before = len(related)
        self.frontmatter["related_skills"] = [r for r in related
                                               if r.get("skill") != other]
        if len(self.frontmatter["related_skills"]) == before:
            print(f"⚠️  [{self.skill_name}] → {other} 未关联，跳过")
            return
        self._save()
        print(f"✅ [{self.skill_name}] ✕ {other}")

    # ─── 列出现状 ──────────────────────────────────

    def show(self):
        """打印当前 YAML frontmatter"""
        print(f"\n[{self.skill_name}]")
        for k, v in self.frontmatter.items():
            if k == "metadata":
                print(f"  {k}: <{len(v)} keys>")
            elif isinstance(v, list):
                print(f"  {k}: [{', '.join(map(str, v))}]")
            else:
                print(f"  {k}: {v}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    skill_name = sys.argv[1]

    # show 不需要操作参数
    if len(sys.argv) == 2:
        SkillMutator(skill_name).show()
        sys.exit(0)

    action = sys.argv[2]
    mutator = SkillMutator(skill_name)

    actions = {
        "show":          lambda: (None, mutator.show())[0],
        "update_field":  lambda: mutator.update_field(sys.argv[3], sys.argv[4]),
        "add_tag":       lambda: mutator.add_tag(sys.argv[3]),
        "remove_tag":    lambda: mutator.remove_tag(sys.argv[3]),
        "add_related":   lambda: mutator.add_related(sys.argv[3],
                                                      sys.argv[4] if len(sys.argv) > 4 else "related_to"),
        "remove_related":lambda: mutator.remove_related(sys.argv[3]),
    }

    if action not in actions:
        print(f"❌ 未知操作: '{action}'")
        print(f"   可选: {', '.join(actions.keys())}")
        sys.exit(1)

    actions[action]()
