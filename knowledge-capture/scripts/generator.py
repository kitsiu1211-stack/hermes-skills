#!/usr/bin/env python3
"""
Knowledge Capture - Generator
生成知识捕获内容：路由判断 → 提取核心洞察 → 生成格式化输出
"""

import argparse
import json
import re
import sys
from datetime import datetime
from typing import Dict, Any, List, Tuple


def classify_content(user_input: str) -> Dict[str, str]:
    """自动识别内容类型并路由"""
    input_lower = user_input.lower()

    # 外部学习输入特征（knowledge_graph）
    external_signals = [
        "http", "https", "www.",
        "文章", "播客", "书", "会议", "读了", "读完", "刚读", "听了", "看完", "看了", "在读",
        "分享", "推荐", "笔记", "摘录", "转发", "来源", "引用",
        "斯坦福", "论文", "报告", "白皮书",
    ]

    # 原创思考特征（growth_graph）
    internal_signals = [
        "我觉得", "感悟", "复盘", "思考", "想法", "灵感", "洞察",
        "今天", "最近", "刚才", "突然想到", "反思", "体会到",
        "理解了", "明白了", "发现",
    ]

    external_score = sum(1 for s in external_signals if s in input_lower)
    internal_score = sum(1 for s in internal_signals if s in input_lower)

    if external_score > internal_score:
        return {
            "type": "external",
            "target": "knowledge_graph",
            "target_name": "AI思考知识图谱",
        }
    elif internal_score > external_score:
        return {
            "type": "internal",
            "target": "growth_graph",
            "target_name": "成长图谱",
        }
    else:
        return {
            "type": "uncertain",
            "target": "ask_user",
            "target_name": "需要用户确认",
        }


def extract_core_insight(content: str, content_type: str) -> Dict[str, Any]:
    """提取核心洞察：Compiled Truth + 关键要点 + 可行动项"""
    lines = [l.strip() for l in content.strip().split("\n") if l.strip()]

    # Compiled Truth: 找最长且最有信息量的句子
    # 去掉纯标题行（过短）和纯链接
    candidates = [
        l for l in lines
        if len(l) > 20 and not l.startswith("http") and not l.startswith("- ")
    ]
    if candidates:
        core = max(candidates, key=len)
        # 截断不超过 200 字符
        if len(core) > 200:
            core = core[:197] + "..."
    else:
        core = lines[0][:200] if lines else content[:200]

    # 关键要点：提取 bullet points
    key_points = []
    for line in lines:
        stripped = line.lstrip("- *•").strip()
        if (line.startswith("-") or line.startswith("*") or line.startswith("•")) \
           and len(stripped) > 5:
            key_points.append(stripped)
        elif re.match(r"^\d+[\.\)、]", line):
            key_points.append(re.sub(r"^\d+[\.\)、]\s*", "", line))

    # 可行动项：解析多行结构
    # 先找 "可行动项" / "行动" 节标题 → 取后续 bullet lines
    action_items = []
    in_action_section = False
    action_section_markers = ["可行动项", "行动项", "action item", "TODO", "待办"]
    for line in lines:
        stripped = line.strip("- *•").strip()
        # 检测节标题（以"可行动项"、"行动"结尾或开头）
        is_section_header = any(
            stripped.startswith(m) or stripped.rstrip("：:") == m
            for m in action_section_markers
        ) and len(stripped) < 20
        if is_section_header:
            in_action_section = True
            continue
        # 在 action section 内，取 bullet 行
        if in_action_section:
            if line.startswith("-") or line.startswith("*") or line.startswith("•"):
                item = line.lstrip("- *•").strip()
                if len(item) > 3:
                    action_items.append(item)
            elif stripped and len(stripped) > 3:
                # 非 bullet 但有内容 → 退出 action section
                in_action_section = False
        # 兼容旧逻辑：含行动关键词的独立行（不在 bullet 列表中）
        if not in_action_section and not is_section_header:
            action_kw = ["行动", "建议", "TODO", "待办", "下一步"]
            if any(kw in stripped for kw in action_kw) and len(stripped) > 5:
                # 不是 section header 且含关键词 → 可能是 inline action
                if not any(stripped.startswith(m) for m in action_section_markers):
                    action_items.append(stripped)

    return {
        "compiled_truth": core,
        "key_points": key_points[:5],
        "action_items": action_items[:3],
    }


def auto_tag(content: str, content_type: str) -> List[str]:
    """自动打标签"""
    tags = []
    content_lower = content.lower()

    tag_mappings = {
        "#AI": ["ai", "大模型", "agent", "chatgpt", "claude", "机器学习", "深度学习"],
        "#Agent": ["agent", "智能体", "多agent", "multi-agent", "工具调用"],
        "#管理": ["团队", "管理", "组织", "领导力", "企业文化"],
        "#销售": ["客户", "销售", "bd", "谈判", "成交"],
        "#认知": ["思维", "认知", "学习", "成长", "元认知"],
        "#效率": ["效率", "工具", "流程", "自动化", "生产力"],
        "#商业": ["产品", "战略", "市场", "商业模式", "企业经营"],
        "#组织变革": ["组织变革", "数字化转型", "变革管理"],
        "#客户成功": ["客户成功", "客户体验", "customer success"],
    }

    for tag, keywords in tag_mappings.items():
        if any(kw in content_lower for kw in keywords):
            tags.append(tag)

    return tags[:5]


def get_weekday() -> str:
    """获取中文星期"""
    weekdays = ["一", "二", "三", "四", "五", "六", "日"]
    return weekdays[datetime.now().weekday()]


def generate_knowledge_graph_format(
    title: str,
    source: str,
    url: str,
    insight: Dict[str, Any],
    tags: List[str],
) -> str:
    """生成知识图谱格式内容"""
    today = datetime.now().strftime("%Y.%m.%d")

    content = f"""##### {today} | {title}

**来源**：{source}{' ' + url if url else ''}
**标签**：{' '.join(tags) if tags else '无'}

**Compiled Truth**：
> {insight['compiled_truth']}

**关键要点**：
"""
    for point in insight['key_points']:
        content += f"- {point}\n"

    if not insight['key_points']:
        content += "（未提取到关键要点）\n"

    if insight['action_items']:
        content += "\n**可行动项**：\n"
        for item in insight['action_items']:
            content += f"- [ ] {item}\n"

    return content


def generate_growth_graph_format(
    theme: str,
    content_text: str,
    insight: Dict[str, Any],
) -> str:
    """生成成长图谱格式内容"""
    today = datetime.now()
    date_str = today.strftime("%Y.%m.%d")
    weekday = get_weekday()

    # 一句话引入：取 compiled_truth 的前半部分
    intro = insight['compiled_truth'][:100]
    if len(insight['compiled_truth']) > 100:
        intro += "..."

    # 体系篇：核心洞察
    system_view = insight['compiled_truth']

    # 功能篇：关键要点
    function_points = insight['key_points']
    function_view = "\n".join(f"- {p}" for p in function_points) if function_points else "（待补充）"

    # 一句话总结
    summary = insight['compiled_truth'][:50]
    if len(insight['compiled_truth']) > 50:
        summary += "..."

    formatted = f"""## {date_str}（星期{weekday}）
主题：{theme}

### 一句话引入
> {intro}

### 体系篇
{system_view}

### 功能篇
{function_view}

### 一句话总结
> {summary}
"""
    return formatted


def generate_capture_output(
    user_input: str,
    route_override: str = "",
    source_url: str = "",
    title_override: str = "",
    source_override: str = "",
    manual_tags: List[str] = None,
) -> Dict[str, Any]:
    """
    生成知识捕获完整输出
    """
    if manual_tags is None:
        manual_tags = []

    # Step 1: 路由判断（可用 --route 覆盖）
    if route_override in ("growth_graph", "knowledge_graph"):
        route = {
            "type": "internal" if route_override == "growth_graph" else "external",
            "target": route_override,
            "target_name": "成长图谱" if route_override == "growth_graph" else "AI思考知识图谱",
        }
    else:
        route = classify_content(user_input)

    if route["target"] == "ask_user":
        return {
            "route": route,
            "extracted": {},
            "formatted_output": "",
            "target_doc": "ask_user",
            "status": "needs_classification",
        }

    # Step 2: 提取核心信息
    insight = extract_core_insight(user_input, route["type"])

    # Step 3: 自动标签
    auto_tags = auto_tag(user_input, route["type"])
    all_tags = list(dict.fromkeys(auto_tags + manual_tags))  # 去重保序

    # Step 4: 生成格式化输出
    if route["target"] == "knowledge_graph":
        title = title_override if title_override else (user_input[:30] + "..." if len(user_input) > 30 else user_input)
        source = source_override if source_override else (user_input[:50] + "..." if len(user_input) > 50 else user_input)
        formatted_output = generate_knowledge_graph_format(
            title=title,
            source=source,
            url=source_url,
            insight=insight,
            tags=all_tags,
        )
    elif route["target"] == "growth_graph":
        theme = user_input[:20] + "..." if len(user_input) > 20 else user_input
        formatted_output = generate_growth_graph_format(
            theme=theme,
            content_text=user_input,
            insight=insight,
        )
    else:
        formatted_output = ""

    return {
        "route": route,
        "extracted": {
            "compiled_truth": insight["compiled_truth"],
            "key_points": insight["key_points"],
            "action_items": insight["action_items"],
            "tags": all_tags,
        },
        "formatted_output": formatted_output,
        "target_doc": route["target"],
        "status": "success",
    }


def main():
    parser = argparse.ArgumentParser(description="Knowledge Capture Generator")
    parser.add_argument("--input", required=True, help="User input text")
    parser.add_argument("--route", default="", choices=["", "growth_graph", "knowledge_graph"],
                        help="Override route classification")
    parser.add_argument("--url", default="", help="Source URL")
    parser.add_argument("--title", default="", help="Manual title (overrides auto-extraction)")
    parser.add_argument("--source", default="", help="Source name (overrides auto-extraction)")
    parser.add_argument("--tags", default="", help="Manual tags (comma-separated)")
    parser.add_argument("--output", default="generator_output.json", help="Output file path")
    args = parser.parse_args()

    manual_tags = [t.strip() for t in args.tags.split(",") if t.strip()]

    result = generate_capture_output(
        user_input=args.input,
        route_override=args.route,
        source_url=args.url,
        title_override=args.title,
        source_override=args.source,
        manual_tags=manual_tags,
    )

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(json.dumps(result, ensure_ascii=False, indent=2))

    if result.get("status") == "needs_classification":
        print("\n⚠️ 路由无法判断，需要用户确认")
        sys.exit(2)


if __name__ == "__main__":
    main()
