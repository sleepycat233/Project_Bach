# Project Bach - 系统架构设计文档

## 1. 架构概述

Project Bach是一个隐私优先的自动化音频处理管道，运行在本地Mac mini上。系统采用事件驱动的微服务架构，确保数据处理的安全性、自动化和可扩展性。

### 1.1 核心设计原则

- **隐私优先**: 敏感数据本地处理，匿名化后才发送到云端
- **自动化**: 最小人工干预，端到端自动处理
- **安全性**: 基于Tailscale的安全网络传输
- **可扩展性**: 模块化设计，支持后续功能扩展
- **可观测性**: 完整的日志和监控体系

## 2. 系统架构图

```
┌─────────────────── 外部设备 (手机/笔记本) ──────────────────┐
│                                                        │
│  ┌──────────────┐    Tailscale Network    ┌─────────────┐   │
│  │ Audio Files  │ ──────────────────────→ │ Mac mini    │   │
│  └──────────────┘                         └─────────────┘   │
└────────────────────────────────────────────────────────────┘
                                                 │
                                                 ▼
┌─────────────────── Mac Mini 本地处理层 ──────────────────┐
│                                                        │
│  ┌──────────────┐    ┌──────────────┐    ┌─────────────┐   │
│  │ File Monitor │    │ Audio        │    │ Privacy     │   │
│  │ Service      │ ──→│ Transcription│ ──→│ Anonymizer  │   │
│  │              │    │ (WhisperKit) │    │             │   │
│  └──────────────┘    └──────────────┘    └─────────────┘   │
│                                                 │          │
└─────────────────────────────────────────────────│──────────┘
                                                 │
                                                 ▼
┌─────────────────── 云端AI处理层 ──────────────────────┐
│                                                        │
│  ┌──────────────┐    ┌──────────────┐    ┌─────────────┐   │
│  │ OpenRouter   │    │ DeepSeek     │    │ KimiK2      │   │
│  │ API Gateway  │ ──→│ Summary      │ ──→│ Mind Map    │   │
│  │              │    │ Generation   │    │ Generation  │   │
│  └──────────────┘    └──────────────┘    └─────────────┘   │
│                                                 │          │
└─────────────────────────────────────────────────│──────────┘
                                                 │
                                                 ▼
┌─────────────────── 自动化部署层 ──────────────────────┐
│                                                        │
│  ┌──────────────┐    ┌──────────────┐    ┌─────────────┐   │
│  │ GitHub       │    │ GitHub       │    │ GitHub      │   │
│  │ Repository   │ ──→│ Actions      │ ──→│ Pages       │   │
│  │              │    │ CI/CD        │    │ Website     │   │
│  └──────────────┘    └──────────────┘    └─────────────┘   │
└────────────────────────────────────────────────────────────┘
```

## 3. 核心组件设计

### 3.1 网络接入层

**组件**: Tailscale网络服务
- **功能**: 提供安全的点对点网络连接
- **技术**: Tailscale VPN服务
- **特点**: 零配置、端到端加密、NAT穿透

### 3.2 文件监控服务 (File Monitor Service)

**职责**: 监控指定文件夹，检测新音频文件并触发处理流程

**核心功能**:
- 实时文件系统监控
- 音频文件格式验证
- 处理队列管理
- 错误处理和重试机制

**技术实现**:
```python
# 伪代码示例
class FileMonitorService:
    def __init__(self, watch_directory: str):
        self.watch_directory = watch_directory
        self.processing_queue = Queue()
    
    def on_file_created(self, event):
        if self.is_audio_file(event.src_path):
            self.add_to_queue(event.src_path)
    
    def process_file(self, file_path: str):
        # 触发音频转录流程
        pass
```

### 3.3 音频转录服务 (Audio Transcription Service)

**职责**: 使用WhisperKit进行本地音频转录

**核心功能**:
- 音频预处理 (格式转换、降噪)
- WhisperKit API调用
- 转录结果后处理
- 性能优化 (批处理、并行处理)

**技术实现**:
```python
class AudioTranscriptionService:
    def __init__(self):
        self.whisper_model = WhisperKit.load_model()
    
    def transcribe(self, audio_file: str) -> str:
        # 音频预处理
        processed_audio = self.preprocess_audio(audio_file)
        
        # 调用WhisperKit进行转录
        transcription = self.whisper_model.transcribe(processed_audio)
        
        # 后处理
        return self.postprocess_transcription(transcription)
```

### 3.4 隐私匿名化服务 (Privacy Anonymizer Service)

**职责**: 使用spaCy识别并替换文本中的人名

**核心功能**:
- 基于spaCy的人名实体识别
- 人名替换策略 (使用通用占位符)
- 匿名化映射记录 (便于调试)
- 批量文本处理优化

**技术实现**:
```python
import spacy
from typing import Dict, Tuple

class PrivacyAnonymizerService:
    def __init__(self):
        # 加载中文和英文模型
        self.nlp_zh = spacy.load("zh_core_web_sm")
        self.nlp_en = spacy.load("en_core_web_sm")
        self.name_mapping: Dict[str, str] = {}
        self.name_counter = 0
    
    def anonymize(self, text: str) -> Tuple[str, Dict[str, str]]:
        # 检测语言并选择合适的模型
        nlp = self._detect_language_model(text)
        doc = nlp(text)
        
        anonymized_text = text
        current_mapping = {}
        
        # 识别人名实体 (PERSON类型)
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                original_name = ent.text
                if original_name not in self.name_mapping:
                    self.name_counter += 1
                    placeholder = f"人员{self.name_counter}" if self._is_chinese(text) else f"Person{self.name_counter}"
                    self.name_mapping[original_name] = placeholder
                
                current_mapping[original_name] = self.name_mapping[original_name]
                anonymized_text = anonymized_text.replace(original_name, self.name_mapping[original_name])
        
        return anonymized_text, current_mapping
    
    def _detect_language_model(self, text: str):
        # 简单的语言检测
        return self.nlp_zh if self._is_chinese(text) else self.nlp_en
    
    def _is_chinese(self, text: str) -> bool:
        return any('\u4e00' <= char <= '\u9fff' for char in text)
```

### 3.5 AI服务协调器 (AI Service Orchestrator)

**职责**: 协调云端AI服务调用

**核心功能**:
- OpenRouter API管理
- 多模型调用协调
- 错误处理和重试
- 速率限制管理

**技术实现**:
```python
class AIServiceOrchestrator:
    def __init__(self):
        self.openrouter_client = OpenRouterClient()
        self.rate_limiter = RateLimiter()
    
    async def process_content(self, anonymized_text: str) -> dict:
        # 并行调用不同AI服务
        summary_task = self.generate_summary(anonymized_text)
        mindmap_task = self.generate_mindmap(anonymized_text)
        
        summary, mindmap = await asyncio.gather(summary_task, mindmap_task)
        
        return {
            'summary': summary,
            'mindmap': mindmap
        }
```

### 3.6 部署服务 (Deployment Service)

**职责**: 自动化内容部署到GitHub Pages

**核心功能**:
- Git仓库管理
- 内容格式化和组织
- 自动提交和推送
- 部署状态监控

## 4. 数据流设计

### 4.1 主要数据流

```
音频文件 → 文件监控 → 转录 → 匿名化 → AI处理 → 部署
    ↓        ↓        ↓       ↓       ↓       ↓
  原始音频   事件触发   文本    匿名文本  结构化内容 网站更新
```

### 4.2 数据存储策略

**本地存储** (早期阶段完整保留数据):
- 原始音频文件: 永久保留，便于回溯和质量分析
- 转录文本: 永久保留，用于模型优化和调试
- 匿名化文本: 保留副本，便于匿名化算法改进
- 处理日志: 长期保留，包含详细的处理链路信息

**存储目录结构**:
```
~/project_bach_data/
├── audio/
│   ├── 2024-01-15/
│   │   ├── meeting_001.mp3
│   │   └── lecture_002.wav
├── transcripts/
│   ├── 2024-01-15/
│   │   ├── meeting_001_raw.txt
│   │   └── meeting_001_anonymized.txt
└── logs/
    └── processing_2024-01-15.log
```

**远程存储**:
- GitHub Repository: 最终内容存储
- 云端API: 无状态调用，不存储数据

### 4.3 消息传递

使用事件驱动架构，组件间通过消息队列通信:

```python
# 事件定义
@dataclass
class AudioFileDetectedEvent:
    file_path: str
    timestamp: datetime
    file_size: int

@dataclass
class TranscriptionCompletedEvent:
    audio_file: str
    transcription: str
    processing_time: float

@dataclass
class ContentPublishedEvent:
    github_url: str
    content_type: str
    publish_time: datetime
```

## 5. 技术栈选择

### 5.1 核心技术栈

| 组件层 | 技术选择 | 理由 |
|--------|----------|------|
| 运行时 | Python 3.11+ | 丰富的AI/ML生态系统 |
| 音频处理 | WhisperKit | Apple优化，本地高性能 |
| 文件监控 | watchdog | 跨平台文件系统监控 |
| 异步处理 | asyncio + aiohttp | 高并发API调用 |
| NLP处理 | spaCy | 成熟的人名实体识别 |
| AI服务 | OpenRouter API | 统一多模型接口 |
| 版本控制 | GitPython | Git操作自动化 |
| 配置管理 | pydantic + YAML | 类型安全配置 |
| 日志系统 | structlog | 结构化日志记录 |

### 5.2 依赖管理

```toml
# pyproject.toml
[tool.poetry.dependencies]
python = "^3.11"
whisperkit = "^1.0.0"
watchdog = "^3.0.0"
aiohttp = "^3.9.0"
gitpython = "^3.1.0"
pydantic = "^2.0.0"
structlog = "^23.1.0"
spacy = "^3.7.0"  # 人名实体识别
openai = "^1.0.0"  # OpenRouter兼容客户端

# spaCy语言模型 (需要单独下载)
# python -m spacy download zh_core_web_sm  # 中文模型
# python -m spacy download en_core_web_sm  # 英文模型
```

## 6. 安全架构

### 6.1 网络安全

- **Tailscale VPN**: 端到端加密的私有网络
- **零信任架构**: 默认拒绝，显式授权
- **API密钥管理**: 环境变量 + Keychain存储

### 6.2 数据安全

- **本地优先**: 敏感数据不离开本地设备
- **匿名化处理**: 云端处理前移除个人信息
- **临时存储**: 处理完成后清理本地文件
- **传输加密**: HTTPS + TLS 1.3

### 6.3 访问控制

```python
# 安全配置示例
class SecurityConfig:
    # API访问控制
    OPENROUTER_API_KEY: str = Field(..., env="OPENROUTER_API_KEY")
    GITHUB_TOKEN: str = Field(..., env="GITHUB_TOKEN")
    
    # 文件访问控制
    ALLOWED_AUDIO_FORMATS: list = [".mp3", ".wav", ".m4a", ".flac"]
    MAX_FILE_SIZE: int = 100 * 1024 * 1024  # 100MB
    
    # 网络访问控制
    ALLOWED_DOMAINS: list = ["api.openrouter.ai", "api.github.com"]
```

## 7. 可观测性设计

### 7.1 日志系统

**分层日志结构**:
- **应用层**: 业务逻辑日志
- **服务层**: 组件交互日志
- **基础设施层**: 系统资源日志

```python
# 结构化日志示例
import structlog

logger = structlog.get_logger()

# 在处理流程中记录关键事件
logger.info(
    "audio_transcription_started",
    file_path=audio_file,
    file_size=file_size,
    expected_duration=estimated_duration
)
```

### 7.2 监控指标

**性能指标**:
- 音频转录耗时
- API调用延迟
- 文件处理吞吐量
- 系统资源使用率

**业务指标**:
- 每日处理音频数量
- 转录准确率
- 部署成功率
- 错误发生频率

### 7.3 告警系统

```python
# 告警规则定义
class AlertingRules:
    # 性能告警
    TRANSCRIPTION_TIMEOUT = 300  # 5分钟
    API_ERROR_THRESHOLD = 5      # 连续5次失败
    
    # 资源告警  
    DISK_USAGE_THRESHOLD = 0.9   # 90%磁盘使用率
    MEMORY_USAGE_THRESHOLD = 0.8 # 80%内存使用率
```

## 8. 部署架构

### 8.1 本地部署

**Mac mini环境**:
- macOS Sonoma 14.0+
- Python 3.11+ (通过Homebrew)
- 充足存储空间 (建议1TB+)
- 稳定网络连接

**spaCy环境配置**:
```bash
# 安装spaCy语言模型
python3.11 -m pip install spacy

# 下载中文模型 (支持人名识别)
python3.11 -m spacy download zh_core_web_sm

# 下载英文模型 (备用)
python3.11 -m spacy download en_core_web_sm

# 验证模型安装
python3.11 -c "import spacy; nlp = spacy.load('zh_core_web_sm'); print('中文模型加载成功')"
```

**服务部署方式**:
```bash
# 系统服务配置 (launchd)
# ~/Library/LaunchAgents/com.projectbach.processor.plist
<?xml version="1.0" encoding="UTF-8"?>
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.projectbach.processor</string>
    <key>ProgramArguments</key>
    <array>
        <string>/opt/homebrew/bin/python3.11</string>
        <string>/Users/admin/project_bach/main.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
```

### 8.2 云端部署

**GitHub Actions工作流**:
```yaml
# .github/workflows/deploy.yml
name: Deploy Content
on:
  push:
    paths: ['content/**']
    
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      - name: Build and Deploy
        run: |
          npm install
          npm run build
          npm run deploy
```

## 9. 扩展性设计

### 9.1 水平扩展

**多实例支持**:
- 任务队列分片
- 负载均衡
- 状态同步

**分布式处理**:
```python
# 集群配置
class ClusterConfig:
    nodes: List[str] = ["mac-mini-1", "mac-mini-2"]
    load_balancer: str = "round_robin"
    shared_storage: str = "/shared/project_bach"
```

### 9.2 功能扩展

**插件系统设计**:
```python
class ProcessorPlugin:
    def process(self, content: str) -> str:
        raise NotImplementedError

class YouTubePlugin(ProcessorPlugin):
    def process(self, youtube_url: str) -> str:
        # YouTube视频处理逻辑
        pass

class PodcastPlugin(ProcessorPlugin):
    def process(self, rss_url: str) -> str:
        # 播客RSS处理逻辑
        pass
```

### 9.3 配置管理

**多环境配置**:
```yaml
# config/production.yml
database:
  url: "sqlite:///prod.db"
  
logging:
  level: "INFO"
  
api:
  openrouter:
    base_url: "https://api.openrouter.ai"
    timeout: 30

# config/development.yml  
database:
  url: "sqlite:///dev.db"
  
logging:
  level: "DEBUG"
```

## 10. 容错与恢复

### 10.1 错误处理策略

**分级错误处理**:
- **可恢复错误**: 自动重试 (网络超时、API限流)
- **部分失败**: 降级处理 (单个AI服务失败)
- **致命错误**: 人工干预 (配置错误、权限问题)

**重试机制**:
```python
from tenacity import retry, stop_after_attempt, wait_exponential

class APIService:
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def call_api(self, request: dict) -> dict:
        # API调用逻辑
        pass
```

### 10.2 数据备份

**备份策略**:
- 配置文件: Git版本控制
- 处理日志: 定期归档
- 生成内容: GitHub自动备份

### 10.3 灾难恢复

**恢复程序**:
1. 系统状态检查
2. 配置恢复
3. 服务重启
4. 数据一致性验证

```python
class DisasterRecovery:
    def recover_system(self):
        self.check_system_health()
        self.restore_configuration()
        self.restart_services()
        self.verify_data_integrity()
```

## 11. 性能优化

### 11.1 处理性能

**并行处理**:
- 音频转录: 多文件并行
- AI调用: 异步并发
- 文件I/O: 异步操作

**缓存策略**:
```python
class CacheManager:
    def __init__(self):
        self.transcription_cache = TTLCache(maxsize=100, ttl=3600)
        self.anonymization_cache = TTLCache(maxsize=200, ttl=1800)
    
    def get_cached_transcription(self, audio_hash: str) -> Optional[str]:
        return self.transcription_cache.get(audio_hash)
```

### 11.2 资源优化

**内存管理**:
- 流式处理大文件
- 及时释放临时对象
- 内存使用监控

**存储优化**:
- 压缩临时文件
- 定期清理过期数据
- 存储使用量监控

## 12. 总结

Project Bach的系统架构设计充分考虑了隐私保护、自动化处理、系统可靠性和未来扩展性。通过模块化的微服务架构，系统具备了以下关键特性:

1. **隐私优先**: 敏感数据本地处理，匿名化后再进行云端AI处理
2. **高度自动化**: 从文件接收到内容发布的全流程自动化
3. **安全可靠**: 基于Tailscale的安全网络，完善的错误处理和恢复机制
4. **易于扩展**: 插件化设计，支持多种输入源和处理方式
5. **可观测性**: 完整的日志、监控和告警体系

该架构为Project Bach提供了坚实的技术基础，能够支撑MVP功能的快速实现，同时为后续功能迭代预留了充分的扩展空间。