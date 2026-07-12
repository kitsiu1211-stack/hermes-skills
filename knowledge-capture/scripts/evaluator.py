#!/usr/bin/env python3
"""
Knowledge Capture - Evaluator
独立质检脚本 — 强制执行三维度内容质量检查
Generator 生成 → Evaluator 把关，两者物理分离是关键保障
"""

import argparse
import json
import sys
from typing import Dict, Any, List


class KnowledgeCaptureEvaluator:
    """知识捕获独立质检器 — 三维度评分"""

    def __init__(self):
        self.errors: List[Dict] = []
        self.warnings: List[str] = []
        self.max_score = 100

    def evaluate(self, data: Dict) -> Dict[str, Any]:
        """执行三维度质检"""
        if data.get("status") == "needs_classification":
            return {
                "total_score": 0,
                "dimension_scores": {"accuracy": 0, "completeness": 0, "usability": 0},
                "errors": [{"severity": "critical", "message": "路由未判断，需要用户确认", "action": "clarify 询问用户"}],
                "warnings": [],
                "conclusion": "❌ 打回（禁止写入）",
                "action": "需要用户确认路由后再生成",
            }

        scores = {
            "accuracy": self._check_accuracy(data),
            "completeness": self._check_completeness(data),
            "usability": self._check_usability(data),
        }

        total_score = sum(scores.values())

        return {
            "total_score": total_score,
            "dimension_scores": scores,
            "errors": self.errors,
            "warnings": self.warnings,
            "conclusion": self._get_conclusion(total_score),
            "action": self._get_action(total_score),
        }

    def _check_accuracy(self, data: Dict) -> int:
        """准确性检查（权重 25%）"""
        score = 25
        route = data.get("route", {})
        target = route.get("target", "")
        extracted = data.get("extracted", {})

        # 路由必须有效
        if target not in ("growth_graph", "knowledge_graph"):
            self.errors.append({
                "severity": "critical",
                "message": f"无效路由目标: {target}",
                "action": "重新执行路由判断",
            })
            return 0

        # 成长图谱必须有关键字段
        if target == "growth_graph":
            # 检查 compiled_truth
            if not extracted.get("compiled_truth") or len(extracted["compiled_truth"]) < 10:
                self.errors.append({
                    "severity": "critical",
                    "message": "成长图谱缺少 compiled_truth 或内容过短",
                    "action": "补充核心洞察内容后重新生成",
                })
                score -= 15

        # 知识图谱需要检查来源
        if target == "knowledge_graph":
            formatted = data.get("formatted_output", "")
            if "**来源**" not in formatted:
                self.errors.append({
                    "severity": "warning",
                    "message": "知识图谱缺少来源标注",
                    "action": "补充来源信息",
                })
                score -= 5

        return max(0, score)

    def _check_completeness(self, data: Dict) -> int:
        """完整性检查（权重 50%）"""
        score = 50
        formatted = data.get("formatted_output", "")
        target = data.get("route", {}).get("target", "")
        extracted = data.get("extracted", {})

        if target == "growth_graph":
            # 必须包含所有标准章节
            required_sections = [
                ("## 20", "日期标题"),
                ("主题：", "主题行"),
                ("### 一句话引入", "一句话引入"),
                ("### 体系篇", "体系篇"),
                ("### 功能篇", "功能篇"),
                ("### 一句话总结", "一句话总结"),
            ]
            for pattern, name in required_sections:
                if pattern not in formatted:
                    self.errors.append({
                        "severity": "critical",
                        "message": f"成长图谱格式错误：缺少 '{name}'",
                        "action": "必须包含所有标准结构",
                    })
                    score -= 8

            # 检查空章节
            for section in ["体系篇", "功能篇"]:
                # 找到 ### {section} 后面的内容
                section_start = formatted.find(f"### {section}")
                if section_start >= 0:
                    after_section = formatted[section_start:]
                    next_section = after_section.find("###", len(f"### {section}"))
                    if next_section > 0:
                        section_content = after_section[len(f"### {section}"):next_section].strip()
                    else:
                        section_content = after_section[len(f"### {section}"):].strip()
                    if len(section_content) < 5:
                        self.warnings.append(f"{section}内容为空或过短")
                        score -= 5

        elif target == "knowledge_graph":
            # 知识图谱必须包含的结构
            required_elements = [
                ("##### 20", "日期标题"),
                ("**来源**", "来源行"),
                ("**Compiled Truth**", "Compiled Truth"),
                ("**关键要点**", "关键要点"),
            ]
            for pattern, name in required_elements:
                if pattern not in formatted:
                    self.errors.append({
                        "severity": "critical",
                        "message": f"知识图谱格式错误：缺少 '{name}'",
                        "action": "补充缺失的章节",
                    })
                    score -= 10

            # 标签检查
            tags = extracted.get("tags", [])
            if not tags:
                self.warnings.append("未生成任何标签")
                score -= 5

        return max(0, score)

    def _check_usability(self, data: Dict) -> int:
        """可用性检查（权重 25%）"""
        score = 25
        formatted = data.get("formatted_output", "")

        content_length = len(formatted)

        if content_length < 100:
            self.warnings.append(f"内容过短（{content_length} 字符），可能信息不完整")
            score -= 10
        elif content_length > 3000:
            self.warnings.append(f"内容过长（{content_length} 字符），建议精简到 2000 以内")
            score -= 5

        # 检查是否包含纯占位文本（一处也不行，必须填充真实内容）
        placeholder_patterns = [
            "（待补充）", "（未提取到", "无标签", "（需要补充",
            "暂无", "（无内容）", "（空）"
        ]
        for p in placeholder_patterns:
            if p in formatted:
                self.errors.append({
                    "severity": "warning",
                    "message": f"存在占位文本: '{p}'，内容不完整",
                    "action": "替换为实际内容",
                })
                score -= 5

        # 检查 compiled_truth 是否就是原始输入（未提炼）
        extracted = data.get("extracted", {})
        compiled = extracted.get("compiled_truth", "")
        if compiled and len(compiled) > 100:
            self.warnings.append(
                f"compiled_truth 过长（{len(compiled)} 字符），应提炼为 50-200 字的精炼洞察"
            )
            score -= 3

        # 检查 action_items 是否有实际内容（而非只有节标题占位）
        action_section_headers = ["可行动项", "行动项", "action item", "TODO", "待办"]
        for item in extracted.get("action_items", []):
            if any(item.strip("：:").strip() == m for m in action_section_headers):
                self.errors.append({
                    "severity": "warning",
                    "message": f"可行动项 '{item}' 是节标题而非实际内容",
                    "action": "补充实际可行动项或删除空标题",
                })
                score -= 5

        return max(0, score)

    def _get_conclusion(self, total_score: int) -> str:
        if total_score >= 85:
            return "✅ 通过"
        elif total_score >= 70:
            return "⚠️ 警告"
        else:
            return "❌ 打回（禁止写入）"

    def _get_action(self, total_score: int) -> str:
        if total_score >= 85:
            return "执行双轨写入"
        elif total_score >= 70:
            return "根据警告优化 → 再次质检 → 通过后写入"
        else:
            return "严重问题需修正，禁止直接写入"


def main():
    parser = argparse.ArgumentParser(description="Knowledge Capture Evaluator")
    parser.add_argument("--input", required=True, help="Generator output JSON file")
    parser.add_argument("--output", default="", help="Output report file (optional)")
    args = parser.parse_args()

    # 读取 generator 输出
    try:
        with open(args.input, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"❌ 文件不存在: {args.input}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ JSON 解析失败: {e}")
        sys.exit(1)

    # 执行质检
    evaluator = KnowledgeCaptureEvaluator()
    result = evaluator.evaluate(data)

    # 打印报告
    print("=" * 60)
    print("Knowledge Capture Evaluator 质检报告")
    print("=" * 60)
    print(f"总分：{result['total_score']}/{evaluator.max_score}")
    print(f"\n维度得分：")
    print(f"  • 准确性 ({result['dimension_scores']['accuracy']}/25): 路由正确、来源标注")
    print(f"  • 完整性 ({result['dimension_scores']['completeness']}/50): 核心洞察、格式规范、标签")
    print(f"  • 可用性 ({result['dimension_scores']['usability']}/25): 内容长度、空章节")

    if result["errors"]:
        print(f"\n❌ 严重错误：")
        for error in result["errors"]:
            print(f"  [{error['severity']}] {error['message']}")
            print(f"    → {error['action']}")

    if result["warnings"]:
        print(f"\n⚠️ 警告：")
        for warning in result["warnings"]:
            print(f"  • {warning}")

    print(f"\n结论：{result['conclusion']}")
    print(f"处理动作：{result['action']}")
    print("=" * 60)

    # 保存报告
    output_file = args.output or "evaluation_report.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n详细报告已保存: {output_file}")

    # 评分 <70 时以非零退出码退出
    if result["total_score"] < 70:
        sys.exit(1)


if __name__ == "__main__":
    main()
