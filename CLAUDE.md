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

### ✅ **代码清理与架构重构完成**

**已完成的清理工作**:
- ✅ **配置与密钥分离**: API keys完全迁移到环境变量，配置文件无敏感信息
- ✅ **冗余代码删除**: 移除~1500行重复/未使用代码
  - 删除重复的Web前端ProcessingService类 (419行)
  - 删除未使用的RSS handler和content_classifier (~978行)
  - 删除GitHub deployment monitor等冗余功能
- ✅ **环境变量架构**: 纯Python实现.env加载，零依赖
- ✅ **配置文件重构**: config.yaml已加入版本控制，移除config.template.yaml

**架构优化成果**:
- **配置管理简化**: config.yaml直接版本控制，环境变量独立管理
- **依赖减少**: 移除不必要的python-dotenv依赖
- **安全提升**: 敏感信息完全从配置文件分离

### 🔴 **当前开发任务 - Phase 7: 前端用户体验优化**

**Phase 7.1 已完成** ✅: API重构和代码优化 (重构/private/路由，统一API响应)
**Phase 7.2 部分完成** 🔄: Post-Processing选择器 + 智能Subcategory管理

**Phase 7.2 已完成功能** ✅:
- Post-Processing选择器UI (匿名化、摘要、思维导图、说话人分离)
- PreferencesManager核心架构 (差异化存储、继承机制)
- 创建新subcategory功能 (API + 前端UI)
- Diarization决策逻辑简化 (移除三层冗余逻辑)
- 配置系统重构 (默认值从代码迁移到user_preferences.json)

**Phase 7.2 待完成功能** 📋:
- **编辑已有subcategory功能**: 前端UI + 后端API支持修改已创建的subcategory配置
- **删除subcategory功能**: 前端UI + 后端API支持删除不需要的subcategory

### 📋 **后续开发重点**

#### **Phase 7.1: API重构和代码优化**

**需求背景**:
1. **代码质量**: app.py中/private/路由300+行代码过长，影响可维护性
2. **API一致性**: 缺少统一的响应格式，错误处理不一致
3. **重复代码**: 配置管理器获取代码重复，需要提取辅助函数

**核心功能要求**:

##### **A. /private/路由重构**:
1. **函数拆分**: 将300+行代码拆分为独立的辅助函数
2. **模块化**: 内容扫描、组织、渲染分离
3. **性能优化**: 减少重复的文件系统操作

##### **B. API响应统一化**:
1. **标准格式**: 统一JSON响应结构
2. **错误处理**: 一致的错误码和消息格式
3. **配置辅助**: 提取重复的配置获取逻辑

#### **Phase 7.2: Post-Processing选择器 + 智能Subcategory管理**

**需求背景**:
1. **成本控制**: 当前所有后处理步骤(NER匿名化、摘要生成、思维导图)都是hardcoded，用户无法根据需要选择性启用
2. **配置管理**: subcategory配置分散在config.yaml中，难以动态管理，用户无法灵活添加自定义类别

**核心功能要求**:

##### **A. Post-Processing选择器**:
1. **NER + 匿名化**: 可选的敏感信息识别和匿名化
2. **摘要生成**: 可选的AI内容摘要生成
3. **思维导图生成**: 可选的AI结构化思维导图
4. **说话人分离**: 可选的多人对话识别
5. **智能记忆**: 配置按content_type和subcategory自动保存和加载

##### **B. 智能Subcategory管理**:
1. **极简配置**: config.yaml只定义基础content_type (lecture, meeting)
2. **动态添加**: 用户可通过前端"Add new"直接创建subcategory
3. **差异化存储**: user_preferences.json只保存与默认值不同的配置
4. **继承机制**: 系统默认 → content_type默认 → subcategory覆盖
5. **显示名称**: 支持友好的subcategory显示名称

**Phase 7.1 技术实现方案**:

##### **A. /private/路由重构**
```python
# 原300+行函数拆分为：
def _scan_content_directory(directory_path, is_private=False):
    """扫描目录获取内容文件信息"""
    # 文件扫描逻辑

def _organize_content_by_type(content_list):
    """将内容按类型和课程组织为树形结构"""
    # 内容组织逻辑

def _render_private_index(all_content, organized_content):
    """渲染私有内容首页"""
    # 模板渲染逻辑

def _serve_private_file(filepath):
    """提供私有文件访问"""
    # 文件服务逻辑
```

##### **B. 统一API响应和配置助手**
```python
def get_config_value(app, key_path, default=None):
    """统一配置获取助手"""
    config_manager = app.config.get('CONFIG_MANAGER')
    if config_manager:
        return config_manager.get_nested_config(*key_path.split('.')) or default
    return default

def create_api_response(success=True, data=None, message=None, error=None):
    """标准API响应格式"""
    return {
        'success': success,
        'data': data,
        'message': message,
        'error': error,
        'timestamp': datetime.now().isoformat()
    }
```

**Phase 7.2 技术实现方案**:

##### **A. 极简config.yaml结构**
```yaml
# 只保留基础content_type定义
content_types:
  lecture: "🎓 Academic Lecture"
  meeting: "🏢 Meeting Recording"
```

##### **B. 智能用户偏好系统**
```json
// user_preferences.json - 差异化存储
{
  "lecture": {
    "_defaults": {
      "enable_anonymization": false,
      "enable_summary": true,
      "enable_mindmap": true,
      "diarization": false
    },
    "CS101": {
      "_display_name": "Computer Science 101",
      "enable_anonymization": true  // 仅存储与defaults不同的部分
    }
  }
}
```

##### **C. PreferencesManager核心类**
```python
class PreferencesManager:
    def get_effective_config(self, content_type, subcategory):
        """继承机制：系统默认 → content_type默认 → subcategory覆盖"""

    def save_config(self, content_type, subcategory, display_name, config):
        """差异化存储：只保存与有效默认值不同的配置"""
```

##### **D. 前端"Add new"UI**
```html
<select name="subcategory">
    <option value="CS101">Computer Science 101</option>
    <option value="__new__">➕ Add new...</option>
</select>

<div class="post-processing-options">
    <label><input type="checkbox" name="enable_anonymization">🕵️ Name Anonymization</label>
    <label><input type="checkbox" name="enable_summary">📝 AI Summary</label>
    <label><input type="checkbox" name="enable_mindmap">🧠 Mindmap</label>
    <label><input type="checkbox" name="diarization">👥 Speaker Diarization</label>
</div>
        </label>
    </div>
</div>
```

##### **B. 前端Transcript动态加载功能**
```javascript
// 增强dynamic-content-loader.js支持transcript显示
class DynamicContentLoader {
    async loadContent(url, title, type) {
        // 1. 加载HTML内容 (现有功能)
        const htmlContent = await this.fetchHTML(url);

        // 2. 同时加载JSON数据获取transcript
        const jsonUrl = url.replace('_result.html', '_result.json');
        const jsonData = await this.fetchJSON(jsonUrl);

        // 3. 在页面中添加transcript功能
        this.renderContentWithTranscript(htmlContent, jsonData, title, type);
    }

    renderContentWithTranscript(htmlContent, jsonData, title, type) {
        // 渲染主要内容
        this.renderLoadedContent(htmlContent, title, type);

        // 添加transcript section (如果存在且为public内容)
        if (jsonData.anonymized_transcript &&
            jsonData.metadata?.privacy_level === 'public') {
            this.addTranscriptSection(jsonData.anonymized_transcript);
        }
    }

    addTranscriptSection(transcript) {
        // 创建可交互的transcript显示区域
        // - 预览模式 (前500字符)
        // - 展开/收起功能
        // - 复制到剪贴板功能
        // - 搜索高亮功能
    }
}
```

##### **C. 实时进度API和AudioProcessor增强**
```python
# 增强的ProcessingService
class ProcessingService:
    def update_substage(self, processing_id: str, substage: str,
                       progress: int = None, eta_seconds: int = None):
        """更新子阶段进度和预计剩余时间"""
        pass

    def cancel_processing(self, processing_id: str):
        """取消处理任务"""
        pass

# 修改现有AudioProcessor支持post-processing选项
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

# 修改现有上传端点支持post-processing选项
@app.route('/upload/audio', methods=['POST'])
def upload_audio():
    # 获取post-processing选项
    enable_anonymization = request.form.get('enable_anonymization', 'on') == 'on'
    enable_summary = request.form.get('enable_summary', 'on') == 'on'
    enable_mindmap = request.form.get('enable_mindmap', 'on') == 'on'

    metadata = {
        'post_processing': {
            'enable_anonymization': enable_anonymization,
            'enable_summary': enable_summary,
            'enable_mindmap': enable_mindmap
        }
    }
```

**Phase 7完成标准**:

**Phase 7.1完成标准**:
- ✅ /private/路由重构为模块化函数
- ✅ 统一API响应格式和错误处理
- ✅ 提取配置管理重复代码
- ✅ 代码可读性和维护性提升

**Phase 7.2完成标准**:
- ✅ 前端UI支持三个post-processing选项开关
- ✅ AudioProcessor根据选项动态跳过步骤
- ✅ 实时进度API显示子步骤和预计时间
- ✅ 处理任务取消和重试功能
- ✅ 配置系统智能默认值支持
- ✅ 向后兼容现有API行为

#### **Phase 7.3: Post-Processing配置依赖检查和前端智能提示**

**需求背景**:
1. **配置依赖复杂**: 4个post-processing功能依赖不同的配置和API
2. **用户体验差**: 用户不知道哪些功能可用，选择后才发现失败
3. **错误处理滞后**: 处理开始后才发现配置缺失，浪费时间

**核心功能要求**:

##### **A. 配置依赖映射**:
1. **🕵️ Name Anonymization (NER)**: 依赖spaCy模型 `zh_core_web_sm`
2. **📝 AI Summary Generation**: 依赖OpenRouter API Key + API可用性
3. **🧠 Mindmap Generation**: 依赖OpenRouter API Key + API可用性
4. **🎙️ Speaker Diarization**: 依赖HuggingFace Token + pyannote.audio访问权限

##### **B. 后端API扩展**:
```python
@app.route('/api/config/dependencies')
def api_config_dependencies():
    """检查所有post-processing功能的配置依赖"""
    dependencies = {
        'ner': {
            'available': check_spacy_model(),
            'message': 'spaCy model zh_core_web_sm not installed' if not available else 'Ready'
        },
        'ai_summary': {
            'available': check_openrouter_api(),
            'message': 'OpenRouter API not configured or invalid' if not available else 'Ready'
        },
        'mindmap': {
            'available': check_openrouter_api(),
            'message': 'OpenRouter API not configured or invalid' if not available else 'Ready'
        },
        'diarization': {
            'available': check_huggingface_token(),
            'message': 'HuggingFace token not configured or invalid' if not available else 'Ready'
        }
    }
```

##### **C. 前端智能禁用逻辑**:
```javascript
async function checkPostProcessingDependencies() {
    // 1. 调用API获取依赖状态
    // 2. 对不可用功能：禁用checkbox + 透明度0.5 + tooltip提示
    // 3. 添加警告标签如"⚠️ OpenRouter API missing"
    // 4. 确保用户明确知道为什么某功能不可用
}
```

**Phase 7.3完成标准**:
- 📋 后端依赖检查API `/api/config/dependencies`
- 📋 各功能的配置验证函数（spaCy、OpenRouter、HuggingFace）
- 📋 前端页面加载时自动检查并禁用不可用选项
- 📋 清晰的英文tooltip提示具体配置要求
- 📋 优雅的视觉反馈（禁用状态、透明度、警告标签）

**用户价值**:
- **开发体验**: 代码更易维护，API更一致
- **用户体验**: 精确进度显示，可控处理选项，智能功能可用性提示
- **成本控制**: 选择性跳过AI生成步骤，避免配置错误浪费时间
- **处理效率**: 减少不需要步骤提升速度，预防配置缺失导致的处理失败
- **配置引导**: 通过tooltip明确告知用户需要配置什么来启用功能

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
```

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