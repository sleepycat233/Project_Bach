# CLAUDE.md - 开发原则与架构概览

这个文件记录了Project Bach的核心开发原则和当前架构状态，供Claude在开发中参考。

## 核心开发原则

### 1. 测试驱动开发 (TDD)
每个功能实现前必须先编写完整测试用例，覆盖正常流程、边界情况和异常处理。

### 2. 渐进式实现
每个阶段都要有可运行版本，按照implementation_plan.md逐步实现，优先保证核心流程可用。

### 3. 简洁优先
个人项目重点是简洁和易实施，能用就行，不过度优化，最小依赖原则。

### 4. 配置驱动
所有可变参数通过config.yaml管理：API密钥、文件路径、模型选择、处理参数。

### 5. Git提交规范
使用Conventional Commits规范，保持提交历史清晰。

**提交格式**: `<type>(<scope>): <description>`

**常用类型**:
- `feat:` - 新功能
- `fix:` - Bug修复
- `docs:` - 文档更新
- `style:` - 代码格式（不影响功能）
- `refactor:` - 重构代码
- `test:` - 测试相关
- `chore:` - 构建过程或辅助工具变动

## 已完成功能概要

✅ **Phase 1-11**: 完整的端到端音频处理与发布系统
- **基础框架**: 音频处理→转录→匿名化→AI生成→结果存储 (Phase 1-3)
- **自动化监控**: watchdog文件监控，处理队列管理 (Phase 2)
- **网络传输**: Tailscale VPN集成，安全文件传输 (Phase 4)
- **GitHub自动发布**: 响应式网站模板，自动化部署流程 (Phase 5)
- **Web前端现代化**: Flask应用，多媒体扩展，智能分类 (Phase 6)
- **架构模块化**: 从954行重构为6个独立模块，减少68%代码 (重构阶段)
- **GitBook风格UI**: 三栏布局，动态内容加载，移动端优化 (Phase 8)
- **MLX Whisper迁移**: 消除subprocess调用，提升转录性能30-50% (Phase 10)
- **Speaker Diarization**: 多人对话识别，IoU时间戳对齐算法 (Phase 10-11)
- **测试系统**: 91个单元测试，10个集成测试，95%+覆盖率

## 当前开发状态

### ✅ **Phase 10-11 完成**: MLX Whisper + Speaker Diarization + 算法分析

**已完成核心功能**:
- ✅ MLX Whisper后端迁移: 消除subprocess调用，提升转录性能30-50%
- ✅ Speaker Diarization集成: 基于pyannote.audio的多人对话识别
- ✅ 智能配置系统: 基于content type的自动diarization启用
- ✅ IoU时间戳对齐算法: 实现ASR转录与说话人信息的精确合并
- ✅ 双输出模式: group_by_speaker模式 + chunk级精确模式
- ✅ 深度算法分析: 识别跨说话人边界chunks的分配问题，设计了改进方案

**当前系统能力**:
- **多说话人识别**: 支持2-6人对话，准确率>85%
- **性能优化**: 转录速度提升，内存管理精细化(<2GB峰值)
- **灵活配置**: 基于subcategory的diarization默认配置
- **生产就绪**: 完整错误处理和日志记录

### 🔴 **下一步开发重点**

#### **Phase 7: 前端Post-Processing选择器 - 灵活化后处理流程**

**需求背景**: 当前所有后处理步骤(NER匿名化、摘要生成、思维导图)都是hardcoded，用户无法根据需要选择性启用

**核心后处理步骤**:
1. **NER + 匿名化**: 识别和匿名化人名等敏感信息
2. **摘要生成**: AI生成内容摘要  
3. **思维导图生成**: AI生成结构化思维导图

**技术实现方案**:

##### **前端UI设计**
```html
<!-- Post-Processing Options -->
<div class="form-group">
    <label class="form-label">🔧 Post-Processing Options</label>
    
    <div class="post-processing-options">
        <label class="checkbox-item">
            <input type="checkbox" name="enable_anonymization" checked>
            <span>🕵️ Name Anonymization (NER)</span>
            <small>Detect and anonymize personal names in transcription</small>
        </label>
        
        <label class="checkbox-item">
            <input type="checkbox" name="enable_summary" checked>
            <span>📝 AI Summary Generation</span>
            <small>Generate content summary using AI</small>
        </label>
        
        <label class="checkbox-item">
            <input type="checkbox" name="enable_mindmap" checked>  
            <span>🧠 Mindmap Generation</span>
            <small>Create structured mindmap from content</small>
        </label>
    </div>
</div>
```

##### **后端架构重构**
```python
# 扩展metadata结构
metadata = {
    # 现有字段...
    'post_processing': {
        'enable_anonymization': True,  # 用户选择
        'enable_summary': True,
        'enable_mindmap': True
    }
}

# AudioProcessor流程控制优化
class AudioProcessor:
    def process_audio_file(self, audio_path, metadata=None):
        # 1. 转录 (必需)
        transcript = self.transcribe_audio(...)
        
        # 2. 条件化后处理
        post_config = metadata.get('post_processing', {})
        
        if post_config.get('enable_anonymization', True):
            anonymized_text = self.anonymizer.anonymize(transcript)
        else:
            anonymized_text = transcript  # 跳过匿名化
            
        if post_config.get('enable_summary', True):
            summary = self.ai_generator.generate_summary(anonymized_text)
        else:
            summary = None  # 跳过摘要生成
            
        if post_config.get('enable_mindmap', True):
            mindmap = self.ai_generator.generate_mindmap(anonymized_text)
        else:
            mindmap = None  # 跳过思维导图
```

##### **配置系统扩展**
```yaml
# config.yaml
post_processing:
  defaults:
    enable_anonymization: true    # 默认启用匿名化
    enable_summary: true         # 默认启用摘要
    enable_mindmap: true         # 默认启用思维导图
  
  # 基于content type的智能默认值
  content_type_defaults:
    lecture:
      enable_anonymization: false  # 讲座通常无敏感信息
      enable_summary: true
      enable_mindmap: true
    meeting:
      enable_anonymization: true   # 会议可能包含人名
      enable_summary: true  
      enable_mindmap: false        # 会议不适合mindmap
```

**完成标准**:
- ✅ 前端UI支持三个post-processing选项的独立启用/禁用
- ✅ 后端AudioProcessor根据用户选择条件化执行各步骤
- ✅ 配置系统支持基于content type的智能默认值
- ✅ API性能优化：跳过不需要的AI调用可节省时间和费用
- ✅ 向后兼容：现有API调用保持默认行为
- ✅ 结果存储适配：支持部分后处理结果的存储格式

**用户价值**:
- **成本控制**: 可选择性跳过昂贵的AI生成步骤
- **处理速度**: 减少不需要的后处理可提升整体速度
- **使用灵活性**: 根据不同场景选择合适的后处理组合
- **隐私控制**: 可选择跳过匿名化用于个人使用场景

#### 📋 技术架构设计
```python
# MLX Whisper + Speaker Diarization架构
class MLXTranscriptionService:
    def __init__(self, config):
        self.whisper_model = None  # 延迟加载
        self.config = config

    def transcribe(self, audio_path, **kwargs):
        # 1. 加载MLX Whisper模型
        # 2. 执行转录获取词级时间戳
        return transcription_result

class SpeakerDiarization:
    def __init__(self, config):
        self.pipeline = None  # 延迟加载
        self.config = config

    def diarize_audio(self, audio_path, **kwargs):
        # 执行说话人分离，返回时间戳片段
        return speaker_segments

    def merge_with_transcription(self, transcription, speaker_segments, group_by_speaker=True):
        # 合并转录文本与说话人信息
        # 使用IoU时间戳对齐算法
        return enhanced_transcription_with_speakers

# 配置系统扩展 - 基于content type的解耦设计
mlx_whisper:
  available_models:
    - "mlx-community/whisper-tiny-mlx"
    - "mlx-community/whisper-large-v3-mlx"     # 统一使用HuggingFace缓存
  word_timestamps: true                         # 词级时间戳(原生支持)

diarization:
  provider: "pyannote"   # 使用pyannote-audio，从HuggingFace缓存加载
  max_speakers: 6
  min_segment_duration: 1.0

  # 基于content type和subcategory的diarization配置
  content_type_defaults:
    # 主分类默认设置
    lecture: false       # 讲座通常单人，默认不启用
    meeting: true        # 会议多人对话，默认启用

    # Lecture子分类配置 - 用户可自定义
    lecture_subcategories:
      cs: false          # CS课程，单人讲授
      math: false        # 数学课程，单人讲授
      physics: false     # 物理课程，单人讲授
      seminar: true      # 研讨会，可能有讨论环节
      workshop: true     # 工作坊，可能有互动

    # Meeting子分类配置 - 用户可自定义
    meeting_subcategories:
      standup: true      # 站会，多人参与
      review: true       # 评审会议，多人讨论
      planning: true     # 规划会议，多人参与
      interview: true    # 面试，双人对话
      oneonone: false    # 一对一会议，可选择不启用

  # 输出格式配置
  output_format:
    group_by_speaker: true          # 默认按说话人分组，便于阅读
    timestamp_precision: 1          # 时间戳精度(小数位数)
    include_confidence: false       # 是否包含置信度信息
```

---

## 📋 后续开发重点

### 待实施任务 (按优先级排序)

#### 📋 中等优先级 - 功能完善
- 📋 **Phase 4 完善**: Tailscale网络集成 - ACL配置和SSL证书
- 📋 **JavaScript客户端功能**: 分类筛选，搜索功能，统计仪表板
- 📋 **高级Web功能**: 用户认证，会话管理，flask_limiter集成

#### 📋 低优先级 - 体验优化
- 📋 **YouTube标题优化**: 显示真实视频标题而非ID
- 📋 **搜索功能集成**: 全站内容搜索，实时筛选结果

#### 📋 性能优化项目 - 需要数据集验证
- 📋 **Phase 11.2**: Speaker Diarization算法精度提升 (需要多场景测试数据集)

### 系统性能指标

#### 当前系统状态
- **测试覆盖率**: 95%+ (91个单元测试 + 10个集成测试)
- **前端响应时间**: 内容切换 < 500ms (无刷新加载)
- **代码规模**: 架构模块化，从954行优化为6个独立模块
- **API响应时间**: 4.4秒 (优化40倍)
- **内存使用**: < 2GB峰值，支持大文件处理

## 技术债务总结

### 已完成的重大优化 ✅
- ✅ ~~大音频文件内存管理优化~~ → MLX Whisper已优化
- ✅ ~~错误恢复和重试机制增强~~ → 原生Python异常处理
- ✅ ~~配置结构优化~~ → 扁平化配置，rate limiter集成

### 当前技术债务
- 📋 Speaker Diarization跨说话人边界chunks分配精度 (需要多场景数据集验证)
- 📋 长时间运行内存泄漏监控 (优先级较低)
- 📋 并发处理优化 (目前串行处理，性能已足够)

## 项目架构概览 (当前完整版)

### 完整模块结构
```
Project_Bach/
├── audio/                        # 音频文件存储 (测试音频)
├── data/                         # 数据存储目录 (统一管理)
│   ├── logs/                     # 系统日志
│   ├── output/                   # 处理结果输出
│   └── transcripts/              # 音频转录文本
├── doc/                          # 项目文档
│   ├── implementation_plan.md    # 详细实施计划
│   ├── project_overview.md       # 项目概览
│   ├── system_architecture.md    # 系统架构
│   ├── SECURITY_REVIEW_CN.md     # 安全审查
│   └── openapi.yaml             # API规范
├── public/                       # 静态资源 (公开访问)
├── static/                       # Web静态文件 (CSS, JS)
├── templates/                    # 网站模板文件
│   ├── base/                     # 基础模板
│   ├── components/               # 组件模板
│   ├── github_pages/             # GitHub Pages模板
│   └── web_app/                  # Web应用模板
├── uploads/                      # 用户上传文件目录
├── watch_folder/                 # 音频文件监控目录
├── src/                         # 核心源代码
│   ├── core/                    # 核心业务逻辑层
│   │   ├── ai_generation.py     # OpenRouter AI内容生成
│   │   ├── anonymization.py     # spaCy人名匿名化 (中英双语)
│   │   ├── audio_processor.py   # 流程编排器 (集成diarization)
│   │   ├── dependency_container.py # 依赖注入容器
│   │   ├── mlx_transcription.py # MLX Whisper音频转录服务
│   │   ├── processing_service.py # 处理服务
│   │   └── speaker_diarization.py # 说话人分离服务 (pyannote.audio)
│   ├── cli/                     # 命令行接口层
│   │   └── main.py             # 主入口 (307行，从954行优化68%)
│   ├── monitoring/              # 文件监控系统
│   │   ├── event_handler.py     # 音频文件事件处理
│   │   ├── file_monitor.py      # 文件监控器 (watchdog集成)
│   │   └── processing_queue.py  # 线程安全处理队列
│   ├── network/                 # 网络集成模块 (Phase 4)
│   │   ├── connection_monitor.py # 网络连接监控
│   │   ├── file_transfer.py     # 跨设备文件传输
│   │   ├── network_manager.py   # 网络管理器
│   │   ├── security_validator.py # 网络安全验证
│   │   └── tailscale_manager.py # Tailscale VPN管理
│   ├── publishing/              # GitHub Pages发布系统
│   │   ├── content_formatter.py # 内容格式化服务
│   │   ├── git_operations.py    # Git操作服务
│   │   ├── github_publisher.py  # GitHub API集成
│   │   └── template_engine.py   # Jinja2模板引擎
│   ├── storage/                 # 数据存储抽象层
│   │   ├── file_manager.py      # 文件管理器
│   │   ├── result_storage.py    # 处理结果存储管理
│   │   └── transcript_storage.py # 转录文本存储管理
│   ├── utils/                   # 通用工具模块
│   │   ├── config.py           # 配置管理 (环境变量+YAML)
│   │   ├── env_manager.py      # 环境管理器
│   │   ├── logging_setup.py    # 日志配置
│   │   └── rate_limiter.py     # API限流保护
│   └── web_frontend/            # Web前端应用
│       ├── app.py              # Flask主应用
│       ├── handlers/           # 路由处理器
│       ├── processors/         # 内容处理器
│       └── services/           # Web服务层
├── tests/                       # 测试体系 (95%+覆盖率)
│   ├── unit/                   # 单元测试
│   │   ├── core/               # 核心模块测试
│   │   ├── config/             # 配置管理测试
│   │   ├── features/           # 功能特性测试
│   │   ├── middleware/         # 中间件测试
│   │   ├── network/            # 网络模块测试
│   │   └── publishing/         # 发布系统测试
│   └── integration/            # 集成测试
├── run_frontend.py             # Web前端启动脚本
├── debug_speaker_diarization.py # Speaker Diarization调试脚本
├── test_timestamp_alignment_algorithm.py # 时间戳对齐算法测试
├── config.yaml                 # 主配置文件 (生产环境)
├── config.template.yaml        # 配置模板文件 (开发参考)
├── .env                        # 环境变量 (敏感信息)
├── .env.template               # 环境变量模板
├── .claudeignore              # Claude Code访问控制
├── requirements.txt            # Python依赖清单
├── CLAUDE.md                   # 开发原则与架构概览
└── README.md                   # 项目说明文档
```

### 核心服务架构
```
AudioProcessor (编排器)
├── MLXTranscriptionService  # MLX Whisper转录
├── SpeakerDiarization      # 说话人分离
├── NameAnonymizer          # spaCy双语处理
├── AIContentGenerator     # OpenRouter生成
├── TranscriptStorage      # 转录文本管理
├── ResultStorage          # 结果存储
└── PublishingWorkflow     # GitHub Pages自动发布
```

## 文档引用指南

项目包含完整的开发文档体系，根据不同需求查阅对应文档：

### 使用建议
- **新人入门**: project_overview.md → system_architecture.md → CLAUDE.md
- **开发新功能**: CLAUDE.md (原则) → implementation_plan.md (技术细节) → openapi.yaml (API规范)
- **安全审查**: SECURITY_REVIEW_CN.md → 相关模块代码审查
- **架构理解**: system_architecture.md (设计) → CLAUDE.md (现状) → implementation_plan.md (演进)