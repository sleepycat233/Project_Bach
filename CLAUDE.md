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

✅ **Phase 1-10**: 完整的端到端音频处理与发布系统
- **基础框架**: 音频处理→转录→匿名化→AI生成→结果存储 (Phase 1-3)
- **自动化监控**: watchdog文件监控，处理队列管理 (Phase 2)
- **MLX Whisper集成**: 高性能音频转录，中英文双语支持 (Phase 3 & 10)
- **Speaker Diarization**: 多人对话识别，智能配置系统 (Phase 10)
- **网络传输**: Tailscale VPN集成，安全文件传输 (Phase 4)
- **GitHub自动发布**: 响应式网站模板，自动化部署流程 (Phase 5)
- **Web前端现代化**: Flask应用，多媒体扩展，智能分类 (Phase 6)
- **架构模块化**: 从954行重构为6个独立模块，减少68%代码 (重构阶段)
- **GitBook风格UI**: 三栏布局，动态内容加载，移动端优化 (Phase 8)
- **测试系统**: 91个单元测试，10个集成测试，95%+覆盖率

## 当前开发状态

### ✅ **Phase 10 完成**: MLX Whisper后端迁移 + Speaker Diarization

**已完成**: 成功将WhisperKit subprocess后端迁移到MLX Whisper Python API，集成了Speaker Diarization功能

**解决的问题**:
- ✅ 消除了WhisperKit subprocess调用的性能开销
- ✅ 实现了多人对话的说话人分离功能
- ✅ 优化了内存管理，支持精细化控制
- ✅ 提升转录性能30-50%，原生Python错误处理

**核心成果**:
- **MLXTranscriptionService**: 替代subprocess，直接Python API调用
- **SpeakerDiarization**: 基于pyannote.audio的说话人分离
- **智能配置系统**: 基于content type的自动diarization启用
- **时间戳对齐算法**: HuggingFace标准的ASR-Diarization对齐
- **双输出模式**: group_by_speaker + chunk-level精确模式

### 🔴 **下一步开发重点**

#### **Phase 11: Speaker Diarization时间戳对齐算法优化**

**问题识别**: 当前HuggingFace ASRDiarizationPipeline算法在处理重叠speaker segments时存在重复内容分配问题

**具体问题表现**:
- 同一段音频内容被分配给多个说话人
- 例如: SPEAKER_01(0.0-56.7s) → SPEAKER_00(33.38-38.4s) → SPEAKER_01(38.4-60.9s)
- 导致merged_transcription中出现重复的文本段落

**根本原因分析**:
```python
# 当前算法逻辑问题
for speaker_segment in speaker_segments:  # 按speaker segments顺序遍历
    # 找到结束时间≤segment_end的所有chunks
    valid_indices = np.where(end_timestamps <= segment_end)[0]
    last_valid_idx = valid_indices[-1]

    # 问题: 当segments时间重叠时，current_chunk_idx更新逻辑失效
    # 导致同一chunks被分配给多个speaker
    for i in range(current_chunk_idx, min(last_valid_idx + 1, len(chunks))):
        chunk['speaker'] = speaker  # 重复分配
```

**技术方案设计**:
1. **重叠检测与处理**: 检测speaker segments重叠，优先分配给覆盖范围更大的segment
2. **Chunk分割策略**: 跨越多个speaker的chunk进行智能分割
3. **时间窗口投票**: 基于chunk整个时间窗口的speaker覆盖比例进行分配
4. **后处理去重**: group_by_speaker后检测并合并时间重叠的段落

**完成标准**:
- ✅ 消除重复内容分配，同一ASR chunk仅分配给一个最优speaker
- ✅ 处理speaker segments重叠场景，保持时间戳精度
- ✅ 保持现有API兼容性，不影响其他模块
- ✅ 增加详细的算法日志记录，便于调试
- ✅ 单元测试覆盖重叠场景和边界条件

基于Phase 10的成功完成，项目现在具备了完整的现代化音频处理能力。

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
# 新的MLX Whisper服务架构 - 解耦设计
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
        # 参考HuggingFace ASRDiarizationPipeline的时间戳对齐算法
        return enhanced_transcription_with_speakers

    def _align_timestamps_with_speakers(self, transcription, speaker_segments):
        """时间戳对齐算法 - 核心逻辑"""
        # 1. 获取ASR转录的结束时间戳
        end_timestamps = np.array([chunk["timestamp"][1] for chunk in transcription["chunks"]])

        # 2. 遍历说话人片段，找到最接近的ASR时间戳
        for segment in speaker_segments:
            end_time = segment["end"]
            # 使用numpy.argmin找到最接近的时间戳索引
            upto_idx = np.argmin(np.abs(end_timestamps - end_time))
            # 在此位置切分并分配说话人标签

    def _group_by_speaker_mode(self, aligned_data):
        """group_by_speaker=True: 按说话人分组连续发言"""
        # 合并同一说话人的连续chunks成为一个完整发言段
        # 优点: 便于阅读，符合对话逻辑
        # 适用: 会议纪要、对话摘要

    def _chunk_level_mode(self, aligned_data):
        """group_by_speaker=False: 保持ASR chunk粒度"""
        # 为每个ASR chunk分配说话人标签，保持原始时间精度
        # 优点: 时间精确，便于详细分析
        # 适用: 字幕制作、语音分析

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

#### 📋 时间戳对齐算法详解

**核心问题**: ASR转录的时间戳与Speaker Diarization的时间戳通常不完全匹配

**解决方案**: 基于HuggingFace ASRDiarizationPipeline的对齐算法

```python
# 示例场景
asr_chunks = [
    {"text": "你好，我是张三", "timestamp": (0.0, 3.2)},
    {"text": "今天天气真不错", "timestamp": (3.2, 8.5)},
    {"text": "是的，很晴朗", "timestamp": (8.5, 12.1)},
    {"text": "我们开始讨论项目吧", "timestamp": (12.1, 18.3)}
]

speaker_segments = [
    {"speaker": "Speaker_A", "start": 0.0, "end": 8.7},    # 说话人A: 0-8.7秒
    {"speaker": "Speaker_B", "start": 8.7, "end": 12.3},   # 说话人B: 8.7-12.3秒
    {"speaker": "Speaker_A", "start": 12.3, "end": 18.3}   # 说话人A: 12.3-18.3秒
]

# 对齐算法核心逻辑
end_timestamps = [3.2, 8.5, 12.1, 18.3]  # ASR chunk结束时间
for speaker_segment in speaker_segments:
    end_time = speaker_segment["end"]      # 8.7, 12.3, 18.3
    # 找到最接近的ASR时间戳: np.argmin([|3.2-8.7|, |8.5-8.7|, |12.1-8.7|, |18.3-8.7|])
    upto_idx = np.argmin(np.abs(end_timestamps - end_time))  # 返回索引1 (8.5最接近8.7)
    # 将chunks[0:2]分配给Speaker_A
```

**两种输出模式对比**:

```python
# group_by_speaker=True (按说话人分组) - 适合会议纪要
[
    {
        "speaker": "Speaker_A",
        "text": "你好，我是张三。今天天气真不错。",
        "timestamp": (0.0, 8.5)  # 合并时间戳
    },
    {
        "speaker": "Speaker_B",
        "text": "是的，很晴朗。",
        "timestamp": (8.5, 12.1)
    }
]

# group_by_speaker=False (按chunk分配) - 适合字幕制作
[
    {"speaker": "Speaker_A", "text": "你好，我是张三", "timestamp": (0.0, 3.2)},
    {"speaker": "Speaker_A", "text": "今天天气真不错", "timestamp": (3.2, 8.5)},
    {"speaker": "Speaker_B", "text": "是的，很晴朗", "timestamp": (8.5, 12.1)}
]
```

#### 🎯 完成标准
- ✅ 76个转录测试用例全部通过
- ✅ 转录和diarization功能完全解耦，可独立启用/关闭
- ✅ 基于subcategory的diarization默认配置 (lecture/cs关闭、meeting/standup启用等)
- ✅ 前端支持主分类+子分类选择器 + diarization覆盖开关
- ✅ 性能提升30%以上，内存使用合理(<2GB峰值)
- ✅ 多说话人识别准确率>85% (启用时)
- ✅ 时间戳对齐算法实现，解决ASR与diarization时间戳匹配问题
- ✅ 双输出模式支持: group_by_speaker模式 + chunk级精确模式
- ✅ 支持纯转录 + 可选说话人信息的多种输出格式
- ✅ 完整错误处理和日志记录，生产环境就绪

---

## 📋 后续开发重点

### 待实施任务 (按优先级排序)

#### 🔴 最高优先级 - 已在规划中
- 🔴 **Phase 10**: MLX Whisper后端迁移 + Speaker Diarization (详见当前开发状态)

#### 📋 中等优先级 - 功能完善
- 📋 **AI生成服务优化**: Rate limiter集成完善 (配置结构已更新，需验证实际使用效果)
- 📋 **Phase 4 完善**: Tailscale网络集成 - ACL配置和SSL证书
- 📋 **Phase 6 收尾**: RSS处理器网络功能完善 - feedparser集成，网络错误处理
- 📋 **JavaScript客户端功能**: 分类筛选，搜索功能，统计仪表板
- 📋 **高级Web功能**: 用户认证，会话管理，flask_limiter集成
- 📋 **前端UI简化**: 移除模型description显示框 (不需要该功能，简化界面)

#### 📋 低优先级 - 体验优化
- 📋 **YouTube标题优化**: 显示真实视频标题而非ID
- 📋 **搜索功能集成**: 全站内容搜索，实时筛选结果
- 📋 **系统监控优化**: 长时间运行内存泄漏监控，并发处理优化 (目前性能已足够，优先级很低)

### 系统性能指标 (更新至2025-09-01)

#### 当前系统状态
- **测试覆盖率**: 95%+ (91个单元测试 + 10个集成测试)
- **前端响应时间**: 内容切换 < 500ms (无刷新加载)
- **移动端交互**: 侧边栏点击响应100%成功
- **代码规模**: 架构模块化，从954行优化为6个独立模块
- **向后兼容性**: 100% (所有现有功能和链接保持可用)

#### MLX Whisper性能成果 (Phase 10 已完成)
- **转录性能**: ✅ 实际提升30-50% (消除subprocess开销)
- **内存管理**: ✅ 精细控制，峰值<2GB，支持大文件处理
- **功能增强**: ✅ 支持多说话人识别，实际准确率>85%
- **架构简化**: ✅ 纯Python实现，减少外部依赖
- **错误处理**: ✅ 原生异常处理，替代subprocess stderr解析
- **模型支持**: ✅ 支持tiny到large-v3全系列MLX模型
- **智能配置**: ✅ 基于content type的diarization自动启用/禁用

### Phase 8 UI优化总结 (已完成)
- ✅ **GitBook三栏布局**: CSS Grid + 动态内容加载 + TOC自动生成
- ✅ **移动端响应式**: 完善的侧边栏适配，解决交互阻塞问题
- ✅ **组件化重构**: 模板系统优化，代码复用性提升60%+

---

## 📋 后续开发重点

### 待实施任务 (按优先级排序)

#### 🔴 最高优先级 - 当前开发中
- 🔴 **Phase 11**: Speaker Diarization时间戳对齐算法优化 (详见上方技术方案)

#### 📋 中等优先级 - 功能完善
- 📋 **Phase 7: 前端Post-Processing选择器** - 用户可选择性启用/禁用后处理步骤
- 📋 **Phase 4 完善**: Tailscale网络集成 - ACL配置和SSL证书
- 📋 **JavaScript客户端功能**: 分类筛选，搜索功能，统计仪表板
- 📋 **高级Web功能**: 用户认证，会话管理，flask_limiter集成

#### 📋 低优先级 - 体验优化
- 📋 **YouTube标题优化**: 显示真实视频标题而非ID
- 📋 **搜索功能集成**: 全站内容搜索，实时筛选结果

## 技术债务总结

### 已完成的重大优化 ✅
- ✅ ~~大音频文件内存管理优化~~ → MLX Whisper已优化
- ✅ ~~错误恢复和重试机制增强~~ → 原生Python异常处理
- ✅ ~~配置结构优化~~ → 扁平化配置，rate limiter集成

### 当前技术债务
- 🔴 **Speaker Diarization重复内容问题** → Phase 11重点解决
- 📋 长时间运行内存泄漏监控 (优先级较低)
- 📋 并发处理优化 (目前串行处理，性能已足够)

## 系统性能指标

- **API响应时间**: 4.4秒 (优化40倍)
- **代码规模**: main.py 307行 (减少68%)
- **测试覆盖率**: 95%+ (69个单元+7个集成测试)
- **API调用成功率**: 95%+
- **内存使用**: < 500MB

## 项目架构概览 (当前完整版)

### 完整模块结构
```
Project_Bach/
├── data/                         # 数据存储目录 (统一管理)
│   ├── logs/                     # 系统日志
│   │   └── app.log              # 主日志文件
│   ├── output/                   # 处理结果输出 (NEW!)
│   │   ├── *_result.md          # Markdown格式结果
│   │   └── *_result.json        # JSON格式结果
│   └── transcripts/              # 音频转录文本
│       ├── *_raw.txt            # 原始转录文本
│       └── *_anonymized.txt     # 匿名化转录文本
├── templates/                    # 网站模板文件
│   ├── base.html               # 基础模板
│   ├── content.html            # 内容页模板
│   ├── error.html              # 错误页模板
│   └── index.html              # 主页模板
├── watch_folder/                 # 音频文件监控目录
├── src/                         # 核心源代码
│   ├── core/                    # 核心业务逻辑层
│   │   ├── mlx_transcription.py # MLX Whisper音频转录服务 (替代WhisperKit)
│   │   ├── speaker_diarization.py # 说话人分离服务 (pyannote.audio)
│   │   ├── anonymization.py     # spaCy人名匿名化 (中英双语)
│   │   ├── ai_generation.py     # OpenRouter AI内容生成 (摘要+思维导图)
│   │   ├── audio_processor.py   # 流程编排器 (集成diarization)
│   │   └── dependency_container.py # 依赖注入容器 (服务管理)
│   ├── monitoring/              # 文件监控系统
│   │   ├── file_monitor.py      # 文件监控器 (watchdog集成)
│   │   ├── event_handler.py     # 音频文件事件处理 (支持mp3/wav/m4a/mp4等)
│   │   └── processing_queue.py  # 线程安全处理队列
│   ├── publishing/              # GitHub Pages发布系统 (NEW!)
│   │   ├── publishing_workflow.py # 发布工作流编排 (SSH模式)
│   │   ├── git_operations.py    # Git操作服务 (clone/commit/push)
│   │   ├── github_publisher.py  # GitHub API集成 (备用)
│   │   ├── content_formatter.py # 内容格式化服务
│   │   ├── template_engine.py   # Jinja2模板引擎
│   │   └── github_actions.py    # GitHub Actions集成
│   ├── storage/                 # 数据存储抽象层
│   │   ├── transcript_storage.py # 转录文本存储管理
│   │   └── result_storage.py    # 处理结果存储管理
│   ├── network/                 # 网络集成模块 (Phase 4)
│   │   ├── tailscale_manager.py # Tailscale VPN管理
│   │   ├── file_transfer.py     # 跨设备文件传输
│   │   ├── secure_file_server.py # 安全文件服务器
│   │   ├── connection_monitor.py # 网络连接监控
│   │   └── security_validator.py # 网络安全验证
│   ├── utils/                   # 通用工具模块
│   │   ├── config.py           # 配置管理 (环境变量+YAML)
│   │   ├── rate_limiter.py     # API限流保护 (Token Bucket)
│   │   └── env_manager.py      # 环境管理器
│   └── cli/                     # 命令行接口层
│       └── main.py             # 简化主入口 (307行，从954行优化68%)
├── tests/                       # 测试体系
│   ├── unit/                   # 单元测试 (30+ 测试文件)
│   │   ├── publishing/         # GitHub Pages发布系统测试
│   │   │   ├── test_content_formatter.py
│   │   │   ├── test_git_operations.py
│   │   │   ├── test_github_actions.py
│   │   │   ├── test_github_publisher.py
│   │   │   ├── test_publishing_workflow.py
│   │   │   └── test_template_engine.py
│   │   ├── test_recommendation_system.py # 推荐系统主测试 (17测试用例)
│   │   ├── test_web_frontend_app.py      # Web应用核心功能
│   │   ├── test_transcription.py         # WhisperKit转录服务
│   │   ├── test_anonymization.py         # spaCy人名匿名化
│   │   ├── test_ai_generation.py         # OpenRouter AI生成
│   │   ├── test_storage.py               # 数据存储管理
│   │   ├── test_config.py                # 配置管理
│   │   ├── test_rate_limiter.py          # API限流保护
│   │   ├── test_youtube_processor.py     # YouTube处理器
│   │   ├── test_rss_processor.py         # RSS处理器
│   │   ├── test_content_classifier.py    # 内容分类器
│   │   ├── test_flask_web_app.py         # Flask应用测试
│   │   ├── test_api_options_display.py   # API模型显示
│   │   ├── test_network_security.py      # Tailscale网络安全
│   │   └── test_environment_manager.py   # 环境管理
│   ├── integration/            # 集成测试
│   │   ├── test_phase4_integration.py    # 网络集成测试
│   │   ├── test_phase5_publishing_integration.py # 发布集成测试
│   │   ├── test_phase6_integration.py    # Web界面集成测试
│   │   ├── test_web_frontend_comprehensive.py    # 综合Web测试
│   │   └── test_api_integration_simple.py       # API集成测试
│   ├── conftest.py             # pytest配置
│   └── test_runner_phase6.py   # 测试运行器
├── config.yaml                 # 主配置文件 (生产环境)
├── config.template.yaml        # 配置模板文件 (开发参考)
├── .env                        # 环境变量 (敏感信息)
├── .claudeignore              # Claude Code访问控制
└── requirements.txt            # Python依赖清单
```

### 核心服务架构 (MLX Whisper + Speaker Diarization)
```
AudioProcessor (编排器)
├── MLXTranscriptionService  # MLX Whisper转录 (30-50%性能提升，原生Python)
├── SpeakerDiarization      # 说话人分离 (pyannote.audio，智能启用)
├── NameAnonymizer          # spaCy双语处理 (zh+en模型)
├── AIContentGenerator     # OpenRouter生成 (摘要+思维导图)
├── TranscriptStorage      # 转录文本管理 (原始+匿名化)
├── ResultStorage          # 结果存储 (MD+JSON双格式)
└── PublishingWorkflow     # GitHub Pages自动发布 (SSH模式)
    ├── GitOperations      # Git工作流 (clone→commit→push)
    ├── ContentFormatter   # 内容格式化
    └── TemplateEngine     # Jinja2渲染引擎
```

### 配置管理体系
- **主配置**: config.yaml (所有业务参数)
- **环境变量**: .env (敏感信息: API密钥、GitHub用户名)
- **模板配置**: config.template.yaml (开发参考)
- **路径统一**: data/* 集中数据存储
- **模型管理**: 统一使用HuggingFace缓存，无本地路径
- **API限流**: 免费层/付费层差异化策略
- **SSH认证**: 无token GitHub Pages部署
- **文件安全**: .claudeignore 保护机制

## 文档引用指南

项目包含完整的开发文档体系，根据不同需求查阅对应文档：

### doc/project_overview.md
**用途**: 项目目标、MVP范围和后续迭代规划
**何时使用**:
- 了解项目核心目标和价值定位
- 理解MVP功能范围界定
- 查看后续扩展计划和优先级
**内容**: 核心目标定义，MVP功能清单，Post-MVP迭代计划

### doc/system_architecture.md
**用途**: 系统架构设计和技术选型说明
**何时使用**:
- 理解整体系统架构和设计原则
- 了解模块间交互和数据流
- 查看技术栈选择的rationale
**内容**: 架构图，模块设计，技术选型，性能考虑

### doc/implementation_plan.md
**用途**: 详细的阶段实施计划和完成状态追踪
**何时使用**:
- 需要了解具体开发步骤和时间规划
- 查阅已完成阶段的详细技术实现
- 追踪项目进度和完成状态 (✅📋标记)
**内容**: 6个开发阶段记录，技术实现细节，架构决策记录

### doc/SECURITY_REVIEW_CN.md
**用途**: 安全审查报告和安全最佳实践
**何时使用**:
- 进行安全相关的代码审查
- 了解当前安全风险和缓解措施
- 规划安全增强功能
**内容**: 安全评级，风险分析，安全实践建议，合规检查

### doc/openapi.yaml
**用途**: Web API的完整接口规范
**何时使用**:
- 开发前端或API客户端
- 了解API endpoint和参数规范
- 进行API测试和集成
**内容**: REST API规范，请求/响应格式，认证方式，错误代码

### CLAUDE.md (本文档)
**用途**: 核心开发原则和当前架构状态概览
**何时使用**:
- 开始新的开发工作前了解项目原则
- 查看当前系统架构和模块结构
- 了解待解决问题和系统性能指标
**内容**: 开发原则，已完成功能概要，项目架构概览，当前问题

### 使用建议
- **新人入门**: project_overview.md → system_architecture.md → CLAUDE.md
- **开发新功能**: CLAUDE.md (原则) → implementation_plan.md (技术细节) → openapi.yaml (API规范)
- **安全审查**: SECURITY_REVIEW_CN.md → 相关模块代码审查
- **架构理解**: system_architecture.md (设计) → CLAUDE.md (现状) → implementation_plan.md (演进)