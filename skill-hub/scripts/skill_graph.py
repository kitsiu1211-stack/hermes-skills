#!/usr/bin/env python3
"""skill_graph.py — Skill 依赖图，参考 DataFlow-Harness 的 Pipeline DAG。
每次 Skill 操作后自动更新图，删除/修改时检测引用断裂。

用法：
  python3.11 skill_graph.py build                 # 全量重构图
  python3.11 skill_graph.py deps <skill_name>     # 我依赖谁
  python3.11 skill_graph.py used_by <skill_name>  # 谁依赖我
  python3.11 skill_graph.py impact <skill_name>   # 删除我会断裂哪些引用
  python3.11 skill_graph.py suggest <skill_name>  # 基于标签推荐关联
  python3.11 skill_graph.py orphans              # 孤立 Skill（无入度也无人引用）
  python3.11 skill_graph.py stats                # 图统计

图结构（存储为 JSON）：
{
  "nodes": {
    "deep-grill": {
      "name": "deep-grill",
      "path": ".hermes/skills/deep-grill",
      "tags": ["cognitive", "analysis"],
      "description": "...",
      "outgoing": ["grill-me"],       # 我引用的 Skill
      "incoming": ["customer-research"] # 引用我的 Skill
    }
  }
}
"""

import sys, os, re, json
from pathlib import Path
from collections import defaultdict
import yaml

SKILLS_DIR = Path.home() / ".hermes" / "skills"
GRAPH_FILE = Path.home() / ".hermes" / "skills" / "skill-hub" / "data" / "skill_graph.json"


def parse_skill(skill_dir: Path) -> dict | None:
    """解析单个 Skill 的元数据"""
    md = skill_dir / "SKILL.md"
    if not md.exists():
        return None

    content = md.read_text()
    m = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if not m:
        return None

    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return None

    name = fm.get("name", "")
    if not name:
        return None

    tags = fm.get("tags", [])
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",")]

    return {
        "name": name,
        "path": str(skill_dir.relative_to(Path.home())),
        "tags": tags,
        "category": fm.get("category", ""),
        "description": fm.get("description", "")[:80],
        "outgoing": [],   # 我引用了哪些 Skill
        "incoming": [],   # 哪些 Skill 引用了我
    }


def extract_references(skill_dir: Path, all_names: set) -> list[str]:
    """从 SKILL.md 内容中提取引用的其他 Skill 名称"""
    md = skill_dir / "SKILL.md"
    content = md.read_text()

    refs = set()

    # 1. YAML frontmatter 里的 related_skills
    m = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if m:
        try:
            fm = yaml.safe_load(m.group(1)) or {}
            related = fm.get("related_skills", [])
            if isinstance(related, list):
                for r in related:
                    if isinstance(r, dict) and "skill" in r:
                        refs.add(r["skill"])
        except yaml.YAMLError:
            pass

    # 2. 正文里的 `skill-name` 模式
    for line in content.split("\n"):
        # 匹配反引号包裹的潜在 skill 名
        for match in re.finditer(r'`([a-z][a-z0-9_-]+)`', line):
            candidate = match.group(1)
            if candidate in all_names:
                refs.add(candidate)

    # 3. 正文里的 see also / 关联 Skill 段落
    body = content[m.end():] if m else content
    if "see also" in body.lower() or "关联" in body or "related" in body.lower():
        for match in re.finditer(r'`([a-z][a-z0-9_-]+)`', body):
            candidate = match.group(1)
            if candidate in all_names:
                refs.add(candidate)

    return list(refs)


def build_graph() -> dict:
    """全量重构依赖图"""
    nodes = {}

    # 第一遍：收集所有 Skill 名称
    all_dirs = list(SKILLS_DIR.rglob("SKILL.md"))
    for md in all_dirs:
        node = parse_skill(md.parent)
        if node:
            nodes[node["name"]] = node

    all_names = set(nodes.keys())

    # 第二遍：解析引用关系
    for name, node in nodes.items():
        skill_dir = Path.home() / node["path"]
        refs = extract_references(skill_dir, all_names)
        node["outgoing"] = sorted(refs)

    # 第三遍：构建 reverse index (incoming)
    for name, node in nodes.items():
        for ref in node["outgoing"]:
            if ref in nodes:
                if name not in nodes[ref]["incoming"]:
                    nodes[ref]["incoming"].append(name)

    return {"nodes": nodes, "total": len(nodes)}


def save_graph(graph: dict):
    GRAPH_FILE.parent.mkdir(parents=True, exist_ok=True)
    GRAPH_FILE.write_text(json.dumps(graph, indent=2, ensure_ascii=False))


def load_graph() -> dict:
    if GRAPH_FILE.exists():
        return json.loads(GRAPH_FILE.read_text()) or {"nodes": {}}
    return {"nodes": {}}


def show_deps(name: str, graph: dict):
    node = graph["nodes"].get(name)
    if not node:
        print(f"❌ Skill '{name}' 不在图中")
        return

    print(f"\n📦 {name}")
    print(f"   📂 {node['path']}")
    print(f"   🏷  {', '.join(node['tags']) if node['tags'] else '无'}")

    if node["outgoing"]:
        print(f"\n   → 我依赖 ({len(node['outgoing'])}):")
        for ref in node["outgoing"]:
            ref_node = graph["nodes"].get(ref, {})
            status = "✅" if ref_node else "❌"
            print(f"      {status} {ref}")
    else:
        print(f"\n   → 我不依赖其他 Skill")

    if node["incoming"]:
        print(f"\n   ← 依赖我 ({len(node['incoming'])}):")
        for ref in node["incoming"]:
            ref_tags = graph["nodes"].get(ref, {}).get("tags", [])
            tag_str = f" [{', '.join(ref_tags)}]" if ref_tags else ""
            print(f"      🔗 {ref}{tag_str}")
    else:
        print(f"\n   ← 没有 Skill 依赖我")


def show_impact(name: str, graph: dict):
    """删除这个 Skill 会断裂哪些引用"""
    node = graph["nodes"].get(name)
    if not node:
        print(f"❌ Skill '{name}' 不在图中")
        return

    if not node["incoming"]:
        print(f"✅ 删除 {name} 无影响——无 Skill 引用它")
        return

    print(f"\n⚠️ 删除 {name} 会断裂以下引用:")
    for ref in node["incoming"]:
        ref_node = graph["nodes"].get(ref, {})
        print(f"   🔗 {ref}: {ref_node.get('description', '?')}")

    # 检查是否还有 outgoing 到别处
    if node["outgoing"]:
        print(f"\n💡 {name} 同时依赖了:")
        for o in node["outgoing"]:
            print(f"   → {o}")
        print("   这些引用也会一起丢失。")


def show_orphans(graph: dict):
    """孤立 Skill：无入度且无出度"""
    orphans = []
    for name, node in graph["nodes"].items():
        if not node["outgoing"] and not node["incoming"]:
            orphans.append(name)

    print(f"\n🏝 孤立 Skill ({len(orphans)} 个):")
    for o in sorted(orphans)[:30]:
        node = graph["nodes"][o]
        print(f"   · {o}")
    if len(orphans) > 30:
        print(f"   ... 还有 {len(orphans) - 30} 个")


def suggest_related(name: str, graph: dict):
    """基于标签推荐可能相关的 Skill"""
    node = graph["nodes"].get(name)
    if not node:
        print(f"❌ Skill '{name}' 不在图中")
        return

    my_tags = set(node.get("tags", []))
    if not my_tags:
        print(f"⚠️  {name} 无标签，无法推荐")
        return

    # 找相同标签的其他 Skill
    candidates = defaultdict(int)
    for other_name, other_node in graph["nodes"].items():
        if other_name == name:
            continue
        if other_name in node["outgoing"]:  # 已关联的跳过
            continue
        common = my_tags & set(other_node.get("tags", []))
        if common:
            candidates[other_name] = len(common)

    top = sorted(candidates.items(), key=lambda x: -x[1])[:10]
    if not top:
        print(f"📭 没有标签匹配的推荐")
        return

    print(f"\n🎯 {name} 的可能关联:")
    for other, score in top:
        other_node = graph["nodes"].get(other, {})
        print(f"   🔗 {other} ({score} 个共同标签)")
        print(f"      {other_node.get('description', '?')}")


def show_stats(graph: dict):
    nodes = graph["nodes"]
    total = len(nodes)
    with_refs = sum(1 for n in nodes.values() if n["outgoing"])
    referenced = sum(1 for n in nodes.values() if n["incoming"])
    orphans = sum(1 for n in nodes.values() if not n["outgoing"] and not n["incoming"])
    most_refed = max(nodes.values(), key=lambda n: len(n["incoming"]), default=None)

    print(f"\n📊 依赖图统计:")
    print(f"   总 Skill: {total}")
    print(f"   有出度（引用他人）: {with_refs}")
    print(f"   有入度（被引用）: {referenced}")
    print(f"   孤立 Skill: {orphans}")
    if most_refed:
        print(f"   最高被引: {most_refed['name']} ({len(most_refed['incoming'])} 次)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "build":
        print("🔨 全量重构依赖图...")
        graph = build_graph()
        save_graph(graph)
        show_stats(graph)

    else:
        graph = load_graph()
        if not graph.get("nodes"):
            print("⚠️  图为空，先运行 build")
            sys.exit(1)

        if cmd == "deps" and len(sys.argv) > 2:
            show_deps(sys.argv[2], graph)
        elif cmd == "used_by" and len(sys.argv) > 2:
            show_deps(sys.argv[2], graph)
        elif cmd == "impact" and len(sys.argv) > 2:
            show_impact(sys.argv[2], graph)
        elif cmd == "suggest" and len(sys.argv) > 2:
            suggest_related(sys.argv[2], graph)
        elif cmd == "orphans":
            show_orphans(graph)
        elif cmd == "stats":
            show_stats(graph)
        else:
            print(f"❌ 未知命令: '{cmd}'")
            print(f"   可选: build, deps, used_by, impact, suggest, orphans, stats")
