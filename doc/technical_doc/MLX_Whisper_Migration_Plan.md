# MLX Whisper迁移计划 + Speaker Diarization集成

## 概述

本文档详细制定从WhisperKit subprocess模式迁移到MLX Whisper Python API，同时集成Speaker Diarization功能的完整迁移计划。

**迁移目标**:
- 🎯 **性能提升**: 消除subprocess开销，预期转录速度提升30-50%
- 🎯 **功能增强**: 集成说话人分离，支持多人对话场景
- 🎯 **架构简化**: 纯Python实现，减少外部依赖和复杂度
- 🎯 **错误处理**: 原生异常处理，替代subprocess stderr解析

## 当前架构分析

### WhisperKit使用现状调研

经过代码调研，发现WhisperKit在以下核心模块中被使用：

#### 主要使用位置
1. **src/core/transcription.py** - 核心转录服务
   - `TranscriptionService` - 主要转录服务类
   - `WhisperKitClient` - subprocess封装客户端 (185-433行)

2. **src/core/audio_processor.py** - 音频处理编排器  
   - 依赖注入使用`TranscriptionService`
   - 在端到端处理流程中调用转录服务

3. **src/core/dependency_container.py** - 依赖容器
   - 管理`TranscriptionService`的创建和配置

#### 配置系统集成
- **config.template.yaml**: WhisperKit配置节点 (30-120行)
- 支持本地模型路径、多provider配置
- 模型自动发现机制

#### 测试覆盖
- **tests/unit/core/test_transcription.py**: 69个测试用例覆盖核心功能
- **tests/integration/**: 多个集成测试验证端到端流程

### 当前WhisperKit实现问题

#### 性能问题
- **subprocess开销**: 每次转录都要启动新进程
- **进程间通信**: 音频数据和结果通过文件系统传递
- **内存管理**: 无法精细控制模型加载和释放

#### 维护复杂性
- **错误处理**: 依赖stderr解析，诊断困难
- **超时管理**: 复杂的进度监控和超时逻辑
- **配置传递**: 命令行参数构建复杂

## MLX Whisper技术方案

### API特性分析

基于`doc/technical_doc/mlx_whisper.md`文档分析：

#### 核心API
```python
import mlx_whisper

# 基础转录
text = mlx_whisper.transcribe(speech_file)["text"]

# 指定模型
result = mlx_whisper.transcribe(speech_file, path_or_hf_repo="models/large")

# 词级时间戳 - MLX Whisper原生支持
output = mlx_whisper.transcribe(speech_file, word_timestamps=True)
print(output["segments"][0]["words"])
# 输出: [{"start": 0.0, "end": 0.8, "word": "Hello"}, ...]
```

#### 模型系统
- **预转换模型**: Hugging Face MLX Community提供
- **本地模型**: 支持本地MLX格式模型
- **自动下载**: 从HuggingFace自动下载模型
- **量化支持**: 4-bit量化模型，减少内存占用

#### Apple Silicon优化
- **MLX框架**: 充分利用Metal Performance Shaders
- **内存效率**: 统一内存架构，减少数据拷贝
- **并行处理**: 多核心和GPU并行加速

## Speaker Diarization技术选型

### 候选方案对比

#### 方案1: pyannote-audio (推荐)
**优点**:
- 工业级精度，广泛应用
- 实时处理能力强
- 丰富的配置选项
- 活跃的社区支持

**缺点**:
- 模型较大 (~100MB)
- 需要HuggingFace token
- GPU加速可选但不是必须

**使用示例**:
```python
from pyannote.audio import Pipeline

pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1")
diarization = pipeline("audio.wav")

for turn, _, speaker in diarization.itertracks(yield_label=True):
    print(f"start={turn.start:.1f}s stop={turn.end:.1f}s speaker_{speaker}")
```

#### 方案2: simple-diarizer (备选)
**优点**:
- 轻量级，易集成
- 无外部认证需求
- 纯Python实现

**缺点**:
- 精度有限
- 功能相对简单
- 社区较小

#### 推荐决策: pyannote-audio
选择pyannote-audio作为主要方案，simple-diarizer作为备选方案，通过配置开关控制。

## 详细迁移架构设计

### 新架构概览 - 解耦设计

```python
# 转录服务 - 独立职责
class MLXTranscriptionService:
    """基于MLX Whisper的转录服务 - 只负责转录"""
    
    def __init__(self, config):
        self.config = config
        self.whisper_model = None  # 延迟加载
        
    def transcribe(self, audio_path, **kwargs):
        """纯转录功能，返回带词级时间戳的结果"""
        # 1. 加载MLX Whisper模型
        # 2. 执行转录获取词级时间戳
        return transcription_result
        
# 说话人分离服务 - 独立职责  
class SpeakerDiarization:
    """说话人分离服务 - 可选启用"""
    
    def __init__(self, config):
        self.config = config
        self.pipeline = None
        
    def diarize_audio(self, audio_path, **kwargs):
        """执行说话人分离，返回时间戳片段"""
        if not self.config.get('enabled', False):
            return None  # 未启用时直接返回
        return speaker_segments
        
    def merge_with_transcription(self, transcription, speaker_segments):
        """合并转录和说话人信息 - 可选步骤"""
        if speaker_segments is None:
            return transcription  # 无diarization时返回原转录
        return enhanced_transcription_with_speakers
        
# 工作流编排器 - 基于content type
class AudioProcessor:
    def process_audio(self, audio_path, content_type=None, enable_diarization=None):
        """灵活的音频处理流程 - 基于content type配置"""
        # 1. 始终执行转录
        transcription = self.transcription_service.transcribe(audio_path)
        
        # 2. 根据content type和用户选择决定是否执行diarization
        should_diarize = self._should_enable_diarization(content_type, enable_diarization)
        
        if should_diarize:
            speaker_segments = self.diarization.diarize_audio(audio_path)
            result = self.diarization.merge_with_transcription(
                transcription, speaker_segments)
        else:
            result = transcription
            
        return result
        
    def _should_enable_diarization(self, content_type, user_override):
        """决定是否启用diarization的逻辑"""
        # 1. 用户明确覆盖设置优先
        if user_override is not None:
            return user_override
            
        # 2. 根据content type和subcategory的默认配置
        if content_type:
            # 如果有subcategory，优先使用subcategory配置
            if hasattr(content_type, 'subcategory') and content_type.subcategory:
                subcategory_config = self.config.diarization.content_type_defaults.get(
                    f"{content_type.main}_subcategories", {})
                return subcategory_config.get(content_type.subcategory, False)
            
            # 否则使用主分类配置
            return self.config.diarization.content_type_defaults.get(
                content_type, False)
        
        # 3. 全局默认为false
        return False
```

### 配置系统扩展

```yaml
# config.yaml 新增配置节点
mlx_whisper:
  enabled: true
  # 模型配置
  model_repo: "mlx-community/whisper-large-v3"  # 默认模型
  local_model_path: "./models/mlx_whisper"      # 统一models目录
  
  # 性能配置
  word_timestamps: true    # MLX Whisper原生支持，只需设置flag
  chunk_length: 30         # 音频分块长度(秒)
  memory_limit: 4096       # 内存限制(MB)
  
  # 备选模型列表
  models:
    - name: "large-v3"
      repo: "mlx-community/whisper-large-v3"
      description: "最高精度，速度较慢"
    - name: "medium"  
      repo: "mlx-community/whisper-medium"
      description: "平衡精度和速度"
    - name: "small"
      repo: "mlx-community/whisper-small" 
      description: "快速处理，精度适中"

diarization:
  provider: "pyannote"     # 主要使用pyannote-audio
  model_path: "./models/diarization"  # 统一models目录
  
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
  
  # pyannote配置
  pyannote:
    model: "pyannote/speaker-diarization-3.1"
    hf_token: "${HUGGINGFACE_TOKEN}"  # 从环境变量读取
    max_speakers: 6        # 最大说话人数
    min_segment_duration: 1.0  # 最小片段时长(秒)
    
  # 输出格式配置
  output:
    format: "enhanced"     # simple | enhanced | detailed
    timestamp_precision: 1 # 时间戳精度(小数位数)
    speaker_labels: ["Speaker 1", "Speaker 2", "Speaker 3"]

# 迁移配置
migration:
  # 迁移模式: 直接迁移到MLX Whisper
  mode: "direct"
  # 性能监控配置
  performance_monitoring: true
  # 详细错误日志
  detailed_logging: true
```

### 输出格式设计

#### Enhanced格式 (推荐)
```markdown
# 会议转录 - 多说话人版本

**处理时间**: 2025-08-31 14:30:25  
**音频时长**: 15分32秒  
**识别说话人**: 3人  
**转录引擎**: MLX Whisper Large-v3  
**说话人分离**: pyannote-audio v3.1  

---

## 转录内容

**Speaker 1** [00:00 - 00:15]: 欢迎大家参加今天的项目讨论会议。我是项目经理张三，首先让我来介绍一下今天的议程。

**Speaker 2** [00:16 - 00:32]: 谢谢张经理。我是技术负责人李四，我想先汇报一下上周的工作进展，主要完成了系统架构设计。

**Speaker 3** [00:33 - 00:48]: 作为UI设计师，我负责用户界面部分。目前原型设计已经基本完成，准备进入开发阶段。

**Speaker 1** [00:49 - 01:05]: 很好，那我们接下来讨论技术方案的具体实施细节...

---

## 会议统计

- **总发言时间**: 15分32秒
- **Speaker 1**: 7分12秒 (46.3%)
- **Speaker 2**: 5分8秒 (33.0%) 
- **Speaker 3**: 3分12秒 (20.7%)
- **说话人切换次数**: 23次
- **平均发言片段时长**: 40.5秒
```

#### JSON格式 (API/程序调用)
```json
{
  "metadata": {
    "audio_duration": 932.5,
    "processing_time": 45.2,
    "num_speakers": 3,
    "transcription_engine": "mlx-whisper-large-v3",
    "diarization_engine": "pyannote-audio-3.1",
    "timestamp": "2025-08-31T14:30:25Z"
  },
  "segments": [
    {
      "start": 0.0,
      "end": 15.2,
      "speaker": "Speaker 1",
      "text": "欢迎大家参加今天的项目讨论会议...",
      "words": [
        {"start": 0.0, "end": 0.8, "word": "欢迎"},
        {"start": 0.9, "end": 1.5, "word": "大家"}
      ]
    }
  ],
  "statistics": {
    "total_duration": 932.5,
    "speaker_stats": {
      "Speaker 1": {"duration": 432.1, "percentage": 46.3},
      "Speaker 2": {"duration": 308.2, "percentage": 33.0},
      "Speaker 3": {"duration": 192.2, "percentage": 20.7}
    },
    "turn_taking": {
      "total_turns": 23,
      "avg_turn_duration": 40.5
    }
  }
}
```

## 实施步骤详细规划

### Phase 1: MLX Whisper基础集成 (2-3天)

#### Day 1: 环境准备和基础架构
1. **依赖管理**:
   ```bash
   pip install mlx-whisper
   # 可选: 如果需要转换模型
   pip install torch transformers
   ```

2. **创建MLX Whisper服务类**:
   ```python
   # src/core/mlx_transcription.py
   class MLXWhisperService:
       def __init__(self, config):
           self.config = config
           self.model = None
           self.logger = logging.getLogger('project_bach.mlx_whisper')
           
       def load_model(self):
           """延迟加载模型"""
           if self.model is None:
               model_repo = self.config.get('model_repo')
               self.model = mlx_whisper.load_model(model_repo)
               
       def transcribe(self, audio_path, **kwargs):
           """转录音频文件"""
           self.load_model()
           result = mlx_whisper.transcribe(audio_path, **kwargs)
           return result
   ```

3. **兼容性接口设计**:
   - 保持与现有`TranscriptionService` API兼容
   - 添加feature flag控制新旧实现切换

#### Day 2: 核心转录功能实现
1. **实现转录核心逻辑**:
   - 音频预处理和格式转换
   - 模型加载和缓存管理
   - 错误处理和重试机制

2. **性能优化**:
   - 内存管理和模型释放
   - 批处理支持
   - 缓存策略

3. **单元测试开发**:
   - 基础转录功能测试
   - 错误处理测试  
   - 性能基准测试

#### Day 3: 集成和测试
1. **集成到现有架构**:
   - 修改`dependency_container.py`支持MLX Whisper
   - 更新`AudioProcessor`调用逻辑
   - 配置文件扩展

2. **性能监控框架**:
   - 实现转录速度和内存使用监控
   - 添加详细的性能对比日志
   - 完善的错误处理和诊断机制

### Phase 2: Speaker Diarization集成 (3-4天)

#### Day 1: Diarization服务架构
1. **创建Diarization模块**:
   ```python
   # src/core/diarization.py
   class SpeakerDiarization:
       def __init__(self, config):
           self.config = config
           self.pipeline = None
           
       def load_pipeline(self):
           """加载diarization模型"""
           from pyannote.audio import Pipeline
           model_name = self.config.get('model')
           self.pipeline = Pipeline.from_pretrained(model_name)
           
       def diarize_audio(self, audio_path):
           """执行说话人分离"""
           self.load_pipeline()
           diarization = self.pipeline(audio_path)
           return self._format_segments(diarization)
   ```

2. **环境配置**:
   ```bash
   pip install pyannote.audio
   # 设置HuggingFace token
   export HUGGINGFACE_TOKEN="your_token_here"
   ```

#### Day 2-3: 结果合并算法
1. **时间戳对齐算法**:
   - 将转录结果的词级时间戳与说话人片段对齐
   - 处理时间戳重叠和空白
   - 优化切换点检测精度

2. **输出格式生成**:
   - Enhanced Markdown格式
   - JSON结构化数据
   - 统计信息计算

#### Day 4: 集成测试和优化
1. **端到端测试**:
   - 多人对话音频测试
   - 边界情况处理
   - 性能压力测试

2. **用户体验优化**:
   - 进度显示优化
   - 错误提示改善
   - 配置验证

### Phase 3: 生产准备和部署 (1-2天)

#### Day 1: 完整性测试
1. **回归测试**:
   - 运行现有69个转录测试用例
   - 验证端到端处理流程
   - 确认Web界面兼容性

2. **性能基准测试**:
   - 对比新旧实现的性能指标
   - 内存使用监控
   - 错误率统计

#### Day 2: 文档和部署
1. **文档更新**:
   - API文档更新
   - 配置说明完善  
   - 使用示例补充

2. **部署配置**:
   - 生产配置文件调整
   - 环境变量设置
   - 监控和日志配置

## 风险评估与缓解策略

### 技术风险

#### 1. MLX Whisper模型兼容性
**风险**: MLX模型可能与现有WhisperKit模型精度不同  
**影响**: 用户可能发现转录结果质量变化  
**缓解措施**:
- 充分的性能基准测试和对比
- 详细的功能验证和测试覆盖
- 完整的迁移文档和使用指南

#### 2. Diarization精度问题  
**风险**: 复杂音频环境下说话人识别可能不准确  
**影响**: 多说话人标记错误，影响用户体验  
**缓解措施**:
- 提供置信度阈值配置
- 支持手动调整选项
- 详细的错误诊断和日志记录

#### 3. 内存和性能问题
**风险**: 新实现可能比WhisperKit消耗更多内存  
**影响**: 处理大文件时可能出现内存不足  
**缓解措施**:
- 实施内存监控和限制
- 支持音频分块处理
- 模型量化选项

### 业务风险

#### 1. 用户适应问题
**风险**: 输出格式变化可能影响用户工作流  
**影响**: 用户投诉和使用困扰  
**缓解措施**:
- 保持向后兼容性
- 渐进式推出
- 详细的迁移指南

#### 2. 功能回退风险
**风险**: 新实现可能缺少某些WhisperKit特性  
**影响**: 功能不完整影响用户体验  
**缓解措施**:
- 完整功能对比分析
- 缺失功能补齐计划
- 用户反馈收集机制

## 成功指标定义

### 性能指标
- **转录速度**: 比WhisperKit提升30%以上
- **内存使用**: 控制在合理范围内 (<2GB峰值)
- **错误率**: 保持与WhisperKit相同水平或更低

### 功能指标  
- **Diarization精度**: 多人对话场景识别准确率>85%
- **时间戳精度**: 秒级精度，误差<1秒
- **格式丰富性**: 支持3种输出格式(Enhanced MD, JSON, Simple)

### 用户体验指标
- **迁移成功率**: 95%以上用户成功切换到新后端
- **错误处理**: 0个crash，完善的异常处理和错误恢复
- **配置简化**: 配置项减少或保持不变

## 时间线和里程碑

### 总体时间线: 6-8天

```
Week 1:
├── Day 1-3: Phase 1 - MLX Whisper基础集成
├── Day 4-7: Phase 2 - Speaker Diarization集成  
└── Day 8: Phase 3 - 生产准备和部署

里程碑:
📍 M1 (Day 3): MLX Whisper基础功能可用
📍 M2 (Day 7): Diarization功能完整集成
📍 M3 (Day 8): 生产环境就绪
```

### 详细里程碑

#### M1: MLX Whisper基础可用 (Day 3)
- ✅ MLX Whisper转录功能实现
- ✅ 与现有架构集成完成
- ✅ 性能监控系统就绪
- ✅ 基础性能测试通过

#### M2: Diarization完整集成 (Day 7)  
- ✅ 说话人分离功能实现
- ✅ 时间戳对齐算法完成
- ✅ 输出格式完整支持
- ✅ 端到端测试通过

#### M3: 生产环境就绪 (Day 8)
- ✅ 所有测试用例通过
- ✅ 性能基准达到预期
- ✅ 文档和部署配置完成
- ✅ 用户迁移指南就绪

## 后续扩展计划

### 短期扩展 (1-2周后)
1. **实时转录支持**: 支持流式音频处理
2. **说话人识别**: 基于声纹的说话人身份识别
3. **多语言diarization**: 支持中英混合语音的说话人分离
4. **GPU加速**: 利用MLX的GPU加速能力

### 中期扩展 (1-3个月)
1. **自定义模型**: 支持领域特定的fine-tuned模型
2. **高级分析**: 情感分析、关键词提取等
3. **API服务**: 提供RESTful API接口
4. **可视化界面**: 音频波形和说话人时间线可视化

---

**文档版本**: v1.0  
**创建日期**: 2025-08-31  
**最后更新**: 2025-08-31  
**负责人**: Claude Code Assistant  
**审核状态**: 待审核