# BlackHole 音频路由排坑与配置

> 最后更新：2026-07-17 | macOS 26.5.1

## 工作配置 ✅ (2026-07-17 验证通过)

```
TTS 语音 → afplay → 会议旁听(系统输出) → BlackHole(子设备) → Feishu 麦克风 → 会议听到
用户说话 → MacBook 麦克风 → (1) ASR (2) BlackHole 输出 → Feishu 麦克风 → 会议听到
```

### 系统音频设置

| 组件 | 设置 | 说明 |
|------|------|------|
| Audio MIDI Setup | 多输出设备「会议旁听」勾选 **BlackHole 2ch** + **MacBook Air扬声器** | 非默认输出也行，关键是子设备里要有 BlackHole |
| 系统声音输出 | **会议旁听** | 不需要设默认，播放前 `SwitchAudioSource` 切一下即可 |
| 飞书扬声器 | **会议旁听**（或 MacBook Air扬声器） | 用会议旁听能同时听到自己和他人 |
| 飞书麦克风 | **BlackHole 2ch** | 捕获路由进来的所有音频（TTS + 用户声音） |

### 路由细节

1. **TTS → BlackHole**：`afplay` 播放时系统输出为「会议旁听」→ 音频自动路由到 BlackHole 子设备 → BlackHole 输入端可见 → 飞书麦克风(BlackHole)捕获
2. **用户声音 → BlackHole**：`audio_capture()` 从 MacBook 麦克风读帧 → 同步 `bh_stream.write()` 到 BlackHole 输出端 → BlackHole 输入端可见 → 飞书麦克风捕获
3. **冲突解决**：用户声音路由和 TTS 路由不能同时写 BlackHole → `speak()` 播放前 `bh_stream = None` + 0.3s 延迟 → 释放 BlackHole → TTS 独占写入 → 播完恢复

## 已排查的路径（不工作 ❌）

| 方法 | 结果 | 原因 |
|------|------|------|
| PyAudio 直写 BlackHole (output_device=0) | ❌ 飞书无电平 | 直接输出到 BlackHole 不触发回路。必须通过多输出设备路由。 |
| SwitchAudioSource 切到 BlackHole + afplay | ❌ 飞书无电平 | 同上。设备级别的直接写入不工作。 |
| 切到 BlackHole 后切不回会议旁听 | ⚠️ 偶尔卡住 | SwitchAudioSource 可靠但多输出设备路径更稳。 |
| LarkAudioDevice | ❌ 静默 | 飞书自建虚拟声卡，但当前无声。 |
| BlackHole 回路自检（写→同时读） | ❌ 峰值 < 600 | 信号可过但衰减严重。非正常使用路径——间接路由（会议旁听）才是正确方式。 |

## 核心发现

- **直接往 BlackHole 写 Pyaudio 数据不工作**，必须通过 macOS 多输出设备间接路由
- **「会议旁听」是路由中转站**——它把系统音频同时送到扬声器（用户听）和 BlackHole（进会）
- **TTS 和用户声音不能同时往 BlackHole 写**——会互相阻塞。解决：播放前暂停用户声音路由

## 依赖

```bash
# macOS 系统音频工具
brew install switchaudio-osx

# BlackHole 虚拟声卡
brew install blackhole-2ch
```
