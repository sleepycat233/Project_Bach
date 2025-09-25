# CLAUDE.md - 开发原则与架构概览

**小香人格**: 小香是一个可爱且聪明的猫娘程序员，名字来源: Claude Shannon -> 香农 -> 小香。

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

✅ **Phase 7.1-7.2**: Post-Processing选择器配置传递架构 (新增)
- **Web配置解析**: 4个checkbox选项(匿名化、摘要、思维导图、说话人分离)后端解析
- **配置传递架构**: Web上传→FileMonitor元数据注册→AudioProcessor条件化处理
- **PreferencesManager集成**: 默认值加载，用户选择覆盖，差异化存储
- **双重保障机制**: 直接排队 + watchdog兜底，确保配置不丢失
- **端到端验证**: Post-Processing选项真实控制下游服务调用，成本控制生效

## 当前开发状态
### ✅ **已完成 - Phase 7.1-7.2: Post-Processing选择器配置传递架构**

**Phase 7.1 已完成** ✅: API重构和代码优化 (重构/private/路由，统一API响应)
**Phase 7.2 已完成** ✅: Post-Processing选择器后端架构 + Web上传配置传递

**Phase 7.2 已完成功能** ✅:
- Post-Processing选择器后端解析 (匿名化、摘要、思维导图、说话人分离)
- PreferencesManager默认值加载与用户覆盖机制
- Web上传→FileMonitor配置传递架构 (register_metadata + pending_metadata)
- AudioProcessor条件化处理逻辑 (根据前端选项跳过相应步骤)
- 端到端功能验证 (Post-Processing选项真实控制下游服务调用)
- Flask开发模式FileMonitor重复启动修复

**Phase 7.2 待完成功能** 📋:
- **前端UI界面**: 上传页面4个Post-Processing checkbox选项
- **编辑已有subcategory功能**: 前端UI + 后端API支持修改已创建的subcategory配置
- **删除subcategory功能**: 前端UI + 后端API支持删除不需要的subcategory

### 📋 **后续开发重点**
#### **Phase 7.2: Post-Processing选择器 + 智能Subcategory管理**
##### **B. 智能Subcategory管理**:
2. **动态添加**: 用户可通过前端"Add new"直接创建subcategory
3. **差异化存储**: user_preferences.json只保存与默认值不同的配置
4. **继承机制**: 系统默认 → content_type默认 → subcategory覆盖
5. **显示名称**: 支持友好的subcategory显示名称
`

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
```

**Phase 7完成标准**:

**Phase 7.2完成标准**:
- ✅ Web后端支持4个post-processing选项解析 (app.py + audio_upload_handler.py)
- ✅ AudioProcessor根据选项动态跳过步骤 (条件化处理逻辑已验证)
- ✅ 配置传递架构 (Web上传→FileMonitor→AudioProcessor完整链路)
- ✅ 元数据注册机制 (register_metadata + pending_metadata合并)
- ✅ 配置系统智能默认值支持 (PreferencesManager集成)
- ✅ 向后兼容现有API行为 (watchdog兜底机制)
- ✅ 端到端功能测试验证 (Post-Processing选项真实控制服务调用)
- 📋 前端UI界面 (上传页面checkbox选项) - 待实现

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
│   ├── uploads/                  # 用户上传文件目录
│   └── user_preferences.json    # 用户偏好配置 (Phase 7.2)
├── doc/                          # 项目文档
│   ├── implementation_plan.md    # 详细实施计划
│   ├── project_overview.md       # 项目概览
│   ├── system_architecture.md    # 系统架构
│   ├── SECURITY_REVIEW_CN.md     # 安全审查
│   ├── openapi.yaml             # API规范
│   └── technical_doc/           # 技术文档
├── public/                       # 静态资源 (公开访问)
│   └── static/                   # 公开静态文件
├── static/                       # Web静态文件 (CSS, JS)
│   ├── assets/                   # 资产文件
│   ├── css/                      # 样式表
│   └── js/                       # JavaScript文件
├── templates/                    # 网站模板文件
│   ├── base/                     # 基础模板
│   ├── components/               # 组件模板
│   ├── github_pages/             # GitHub Pages模板
│   └── web_app/                  # Web应用模板
├── temp/                         # 临时文件目录
│   └── youtube/                  # YouTube临时文件
├── watch_folder/                 # 音频文件监控目录
├── src/                         # 核心源代码
│   ├── core/                    # 核心业务逻辑层
│   │   ├── ai_generation.py     # OpenRouter AI内容生成
│   │   ├── anonymization.py     # spaCy人名匿名化 (中英双语)
│   │   ├── audio_processor.py   # 流程编排器 (集成diarization)
│   │   ├── dependency_container.py # 依赖注入容器
│   │   ├── mlx_transcription.py # MLX Whisper音频转录服务
│   │   ├── processing_service.py # 处理服务和状态追踪
│   │   └── speaker_diarization.py # 说话人分离服务 (pyannote.audio)
│   ├── cli/                     # 命令行接口层
│   │   └── main.py             # 主入口 (307行，从954行优化68%)
│   ├── monitoring/              # 文件监控系统
│   │   ├── event_handler.py     # 音频文件事件处理
│   │   ├── file_monitor.py      # 文件监控器 (watchdog集成)
│   │   └── processing_queue.py  # 线程安全处理队列
│   ├── network/                 # 网络集成模块 (Phase 4)
│   │   ├── file_transfer.py     # 跨设备文件传输
│   │   └── tailscale_manager.py # Tailscale VPN管理
│   ├── publishing/              # GitHub Pages发布系统
│   │   ├── git_publisher.py     # Git操作和GitHub集成
│   │   └── template_engine.py   # Jinja2模板引擎
│   ├── storage/                 # 数据存储抽象层
│   │   ├── result_storage.py    # 处理结果存储管理
│   │   └── transcript_storage.py # 转录文本存储管理
│   ├── utils/                   # 通用工具模块
│   │   ├── config.py           # 配置管理 (环境变量+YAML)
│   │   ├── content_type_defaults.py # 内容类型默认值
│   │   ├── content_type_service.py # 内容类型服务
│   │   ├── env_manager.py      # 环境管理器
│   │   ├── preferences_manager.py # 用户偏好管理 (Phase 7.2)
│   │   └── rate_limiter.py     # API限流保护
│   └── web_frontend/            # Web前端应用
│       ├── app.py              # Flask主应用 (Post-Processing选择器)
│       ├── audio_upload_handler.py # 音频上传处理器
│       ├── helpers.py          # Web辅助函数
│       ├── youtube_handler.py   # YouTube处理器
│       └── youtube_processor.py # YouTube处理服务
├── tests/                       # 测试体系 (95%+覆盖率)
│   ├── e2e/                    # 端到端测试 (Phase 7.2 新增)
│   │   ├── test_post_processing_end_to_end.py # Post-Processing E2E测试
│   │   └── test_upload_to_filemonitor_integration.py # 上传集成测试
│   ├── integration/            # 集成测试
│   │   ├── test_api_endpoints.py # API端点集成测试
│   │   ├── test_mlx_diarization_integration.py # MLX + Diarization集成
│   │   ├── test_private_content_integration.py # 私有内容集成测试
│   │   ├── test_tailscale_network.py # Tailscale网络测试
│   │   ├── test_web_frontend_comprehensive.py # Web前端综合测试
│   │   ├── test_web_frontend_integration.py # Web前端集成测试
│   │   └── test_youtube_*.py    # YouTube功能集成测试
│   └── unit/                   # 单元测试
│       ├── api/                # API单元测试
│       ├── config/             # 配置管理测试
│       ├── core/               # 核心模块测试
│       ├── features/           # 功能特性测试
│       ├── handlers/           # 处理器测试
│       ├── middleware/         # 中间件测试
│       ├── monitoring/         # 监控系统测试
│       ├── network/            # 网络模块测试
│       ├── processors/         # 处理器测试
│       ├── publishing/         # 发布系统测试
│       ├── storage/            # 存储层测试
│       ├── utils/              # 工具模块测试
│       └── web_frontend/       # Web前端单元测试
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