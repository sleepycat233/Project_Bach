# Project Bach - 系统架构设计

## 1. 设计原则 (重构后)

**个人项目，简洁至上，架构清晰**
- **模块化设计**: 清晰的职责分离，易于维护和测试  
- **简单实用**: 能跑就行，不追求完美
- **串行处理**: 一个音频文件处理完再处理下一个
- **最小依赖**: 只用必需的库，避免过度工程化
- **配置驱动**: 统一配置管理，易于调整

## 2. 简化架构图

```
┌─────────────────────────────────────────────────────────┐
│                 外部设备 (手机)                          │
│  ┌──────────────┐    Tailscale    ┌─────────────────┐   │
│  │ 音频文件     │ ───────────────→ │ Mac mini 共享    │   │
│  │ (录音)       │                 │ 文件夹          │   │
│  └──────────────┘                 └─────────────────┘   │
└─────────────────────────────────────────────────────────┘
                                           │
                                           ▼
┌─────────────────────────────────────────────────────────┐
│               单个 Python 脚本处理                       │
│                                                         │
│  文件监控 → WhisperKit → spaCy → OpenRouter → Git Push  │
│                                                         │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐        │
│  │ 检测新   │ │ 音频转录 │ │ 人名替换 │ │ 内容发布 │        │
│  │ 音频文件 │ │         │ │         │ │         │        │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘        │
└─────────────────────────────────────────────────────────┘
```

## 3. 核心文件结构 (重构后)

```
Project_Bach/
├── src/                    # 模块化源代码
│   ├── core/              # 核心业务逻辑
│   │   ├── transcription.py     # 音频转录服务
│   │   ├── anonymization.py     # 人名匿名化服务  
│   │   ├── ai_generation.py     # AI内容生成服务
│   │   ├── audio_processor.py   # 音频处理编排器
│   │   └── dependency_container.py # 依赖注入容器
│   ├── monitoring/        # 文件监控系统
│   │   ├── file_monitor.py      # 文件监控器
│   │   ├── event_handler.py     # 文件事件处理器
│   │   └── processing_queue.py  # 处理队列管理
│   ├── utils/             # 工具模块
│   │   ├── config.py           # 配置管理
│   │   └── rate_limiter.py     # API限流保护
│   ├── storage/           # 存储模块
│   │   ├── transcript_storage.py # 转录文本存储
│   │   └── result_storage.py     # 结果文件存储
│   └── cli/               # 命令行接口
│       └── main.py             # 简化主入口 (307行)
├── tests/                  # 测试目录
│   ├── unit/              # 单元测试
│   └── integration/       # 集成测试
├── config.yaml            # 统一配置文件
├── requirements.txt       # 依赖清单
├── data/                  # 数据目录
│   ├── audio/            # 音频文件存储
│   ├── transcripts/      # 转录文本存储
│   └── logs/             # 简单日志
└── watch_folder/         # 监控文件夹 (Tailscale共享)
```

## 4. 技术栈 (最小化)

| 功能 | 技术选择 | 理由 |
|------|----------|------|
| 文件监控 | watchdog | 简单易用 |
| 音频转录 | WhisperKit | 本地运行 |
| 人名识别 | spaCy | 现成方案 |
| HTTP请求 | requests | 最基础库 |
| Git操作 | GitPython | 简单自动化 |
| 配置管理 | yaml | 人类可读 |

## 5. 主要代码结构

```python
# main.py - 完整处理流程
import time
import yaml
import spacy
import requests
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class AudioProcessor:
    def __init__(self):
        self.config = yaml.safe_load(open('config.yaml'))
        self.nlp = spacy.load("zh_core_web_sm")
        
    def process_audio_file(self, file_path):
        """串行处理单个音频文件"""
        print(f"开始处理: {file_path}")
        
        # 1. 音频转录
        transcript = self.transcribe_audio(file_path)
        
        # 2. 人名匿名化  
        anonymized_text = self.anonymize_names(transcript)
        
        # 3. AI处理
        summary, mindmap = self.generate_content(anonymized_text)
        
        # 4. 发布到GitHub
        self.publish_content(summary, mindmap)
        
        print(f"处理完成: {file_path}")
    
    def transcribe_audio(self, file_path):
        # WhisperKit调用
        pass
    
    def anonymize_names(self, text):
        # spaCy人名识别和替换
        doc = self.nlp(text)
        result = text
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                result = result.replace(ent.text, "某人")
        return result
    
    def generate_content(self, text):
        # 简单的API调用
        summary = requests.post("https://api.openrouter.ai/...", json={
            "model": "deepseek/deepseek-chat",
            "messages": [{"role": "user", "content": f"总结这段文字: {text}"}]
        })
        
        mindmap = requests.post("https://api.openrouter.ai/...", json={
            "model": "kimi/kimi-k2",  
            "messages": [{"role": "user", "content": f"做思维导图: {text}"}]
        })
        
        return summary.json(), mindmap.json()
    
    def publish_content(self, summary, mindmap):
        # 简单的git操作
        pass

class FileHandler(FileSystemEventHandler):
    def __init__(self, processor):
        self.processor = processor
        
    def on_created(self, event):
        if event.is_file and event.src_path.endswith(('.mp3', '.wav', '.m4a')):
            # 等待文件传输完成
            time.sleep(2)
            self.processor.process_audio_file(event.src_path)

def main():
    processor = AudioProcessor()
    handler = FileHandler(processor)
    observer = Observer()
    observer.schedule(handler, "watch_folder", recursive=False)
    observer.start()
    
    print("开始监控文件夹...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    main()
```

## 6. 配置文件

```yaml
# config.yaml
api:
  openrouter_key: "your-api-key"
  
github:
  repo_url: "https://github.com/username/repo.git"
  token: "your-github-token"
  
paths:
  watch_folder: "./watch_folder"
  data_folder: "./data"
  
spacy:
  model: "zh_core_web_sm"
```

## 7. 安装和运行

```bash
# 1. 安装依赖
pip3.11 install -r requirements.txt
python3.11 -m spacy download zh_core_web_sm

# 2. 配置文件
cp config.yaml.example config.yaml
# 编辑config.yaml填入API密钥

# 3. 运行
python3.11 main.py
```

## 8. 部署方式

**最简单的方式 - 直接运行**
```bash
# 在Mac mini上
cd ~/project_bach
python3.11 main.py &

# 或者用screen保持后台运行
screen -S project_bach
python3.11 main.py
# Ctrl+A, D 离开screen
```

**稍微正式一点 - launchd服务**
```xml
<!-- ~/Library/LaunchAgents/com.projectbach.plist -->
<?xml version="1.0" encoding="UTF-8"?>
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.projectbach</string>
    <key>ProgramArguments</key>
    <array>
        <string>/opt/homebrew/bin/python3.11</string>
        <string>/Users/admin/project_bach/main.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/admin/project_bach</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/Users/admin/project_bach/logs/output.log</string>
</dict>
</plist>
```

## 9. 错误处理 (保持简单)

```python
def safe_process(func, *args, **kwargs):
    """简单的错误处理装饰器"""
    try:
        return func(*args, **kwargs)
    except Exception as e:
        print(f"错误: {e}")
        # 写入简单日志
        with open("logs/error.log", "a") as f:
            f.write(f"{time.now()}: {e}\n")
        return None
```

## 10. 数据管理

**简单的文件组织**
```
data/
├── audio/
│   ├── 2024-01-15_meeting.mp3
│   └── 2024-01-16_lecture.wav
├── transcripts/
│   ├── 2024-01-15_meeting_raw.txt
│   ├── 2024-01-15_meeting_anonymized.txt
│   └── 2024-01-16_lecture_raw.txt
└── logs/
    ├── processing.log
    └── error.log
```

**定期清理脚本** (可选)
```python
# cleanup.py - 每月运行一次
import os
import time

def cleanup_old_files():
    # 删除30天前的音频文件
    # 保留转录文本
    pass
```

## 总结

这个简化版本的特点：

1. **单文件主逻辑** - 所有处理都在main.py里
2. **串行处理** - 不需要考虑并发、锁、队列
3. **最小依赖** - 只用必需的库
4. **简单配置** - 一个yaml文件搞定
5. **直接运行** - python main.py就能工作
6. **易于调试** - 所有逻辑都能直接print调试

**重点是先让它跑起来，后续需要什么功能再慢慢加！**