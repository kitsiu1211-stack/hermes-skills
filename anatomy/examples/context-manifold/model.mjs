// 上下文汇流台 model — 纯数据，无几何。
// 真值来源：2026-10-13「豆包有约第 9 期」字幕 — 豆包工作对客的胜负手不是模型，
// 是客户业务数据能不能接进来；协同数据只占 10~20%，剩下 80% 在客户业务系统，全靠连接器。
export const PORTS = [
  { id: 0, kind: "synergy", x: -110, label: "协同" },
  { id: 1, kind: "business", x: -66, label: "业务系统 A" },
  { id: 2, kind: "business", x: -22, label: "业务系统 B" },
  { id: 3, kind: "business", x: 22, label: "业务系统 C" },
  { id: 4, kind: "business", x: 66, label: "业务系统 D" },
];

export const SHARE_PER_PORT = 100 / PORTS.length; // 20

export const shareOf = (index) => ((index + 1) * SHARE_PER_PORT) / 100;

export function readoutOf(index) {
  const ports = index + 1;
  const share = Math.round(ports * SHARE_PER_PORT);
  return `接通 ${ports}/${PORTS.length} 路 · 上下文 ${share}%`;
}

export const REACH = [PORTS[0].x, PORTS[PORTS.length - 1].x];
