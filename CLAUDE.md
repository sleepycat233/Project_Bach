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

✅ **Phase 1-6**: 完整的端到端音频处理与发布系统
- **基础框架**: 音频处理→转录→匿名化→AI生成→结果存储 
- **自动化监控**: watchdog文件监控，处理队列管理
- **WhisperKit集成**: 真实音频转录，中英文双语支持
- **架构模块化**: 从954行重构为6个独立模块，减少68%代码
- **GitHub自动发布**: 响应式网站模板，自动化部署流程
- **Web前端现代化**: Flask应用，模板分离，静态资源组织
- **文件组织系统**: 智能分类，子分类支持，文件夹自动创建
- **测试系统**: 69个单元测试，7个集成测试，95%+覆盖率

## 当前开发状态

### 正在进行：第六阶段多媒体扩展完善 (75%完成)

#### 已完成核心功能 ✅
- ✅ **配置系统扩展**: 支持content_types和分类配置
- ✅ **ContentClassifier**: 智能内容分类器 (18个测试通过)
- ✅ **YouTubeProcessor**: yt-dlp集成 (15个测试通过)  
- ✅ **AudioUploadProcessor**: 音频上传+分类选择 (23个测试通过)
- ✅ **前端架构现代化**: 模板系统重构，静态资源分离 (39个文件变更)
- ✅ **Web界面基础**: Flask应用框架，核心功能完整 (13/19测试通过)
- ✅ **GitHub Pages分类展示**: 左侧边栏导航，分类专用页面
- ✅ **文件组织系统**: 智能分类，子分类支持 (22个新增测试)
- ✅ **测试系统整合**: 17/17推荐系统测试通过

#### 支持的内容类型
```yaml
content_types:
  lecture:     # 🎓 学术讲座
    subcategories: [PHYS101, CS101, ML301]
    processor: AudioUploadProcessor
    
  youtube:     # 📺 YouTube视频  
    processor: YouTubeProcessor
    features: [yt-dlp音频提取, 元数据提取]
    
  rss:         # 📰 RSS文章
    processor: RSSProcessor (基础实现)
    status: 需要网络功能完善
    
  podcast:     # 🎙️ 播客内容
    processor: AudioUploadProcessor
    features: [访谈识别, 自动分类]
```

#### Web前端技术架构
```
Flask Web应用 (src/web_frontend/app.py)
├── handlers/              # 请求处理器
│   ├── AudioUploadHandler # 音频文件上传处理
│   ├── YouTubeHandler     # YouTube URL处理  
│   └── RSSHandler         # RSS订阅管理 (基础实现)
├── processors/            # 业务处理器
│   ├── ContentClassifier  # 智能内容分类
│   └── ProcessingService  # 状态管理
└── templates/             # 响应式模板 (已现代化)
    ├── base/             # 基础模板 (HTML/CSS/JS分离)
    ├── components/       # 可复用组件
    └── web_app/         # Web应用专用模板
```

#### 当前待完成功能 (25%)
- 📋 **RSS处理器网络功能完善**: feedparser集成，网络错误处理
- 📋 **Tailscale安全配置**: ACL访问控制规则，网络分段，SSL/TLS证书
- 📋 **JavaScript客户端功能**: 分类筛选，搜索功能，统计仪表板  
- 📋 **高级Web功能**: 用户认证，会话管理，flask_limiter集成

#### 完成标准
- ✅ 69个测试用例全部通过 (Unit: 62个, Integration: 7个)
- ✅ 支持4种内容类型的自动分类和处理
- ✅ GitHub Pages左侧边栏分类展示完善
- 📋 Tailscale私有Web界面安全配置 (基础框架完成)
- ✅ 端到端处理性能 (<5分钟/文件)


## 当前待解决问题

### 技术债务
- 大音频文件内存管理优化
- 长时间运行内存泄漏监控
- 并发处理优化 (目前串行处理)
- 错误恢复和重试机制增强

### 功能缺失
- RSS处理器网络功能完善
- Tailscale安全配置完整实施
- JavaScript客户端筛选和搜索功能
- 用户认证和会话管理

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
│   │   ├── transcription.py     # WhisperKit音频转录服务
│   │   ├── anonymization.py     # spaCy人名匿名化 (中英双语)
│   │   ├── ai_generation.py     # OpenRouter AI内容生成 (摘要+思维导图)
│   │   ├── audio_processor.py   # 流程编排器 (5步骤工作流)
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

### 核心服务架构
```
AudioProcessor (编排器)
├── TranscriptionService      # WhisperKit转录 (distil-large-v3: 18x实时)
├── NameAnonymizer           # spaCy双语处理 (zh+en模型)
├── AIContentGenerator      # OpenRouter生成 (摘要+思维导图)
├── TranscriptStorage       # 转录文本管理 (原始+匿名化)
├── ResultStorage           # 结果存储 (MD+JSON双格式)
└── PublishingWorkflow      # GitHub Pages自动发布 (SSH模式)
    ├── GitOperations       # Git工作流 (clone→commit→push)
    ├── ContentFormatter    # 内容格式化
    └── TemplateEngine      # Jinja2渲染引擎
```

### 配置管理体系
- **主配置**: config.yaml (所有业务参数)
- **环境变量**: .env (敏感信息: API密钥、GitHub用户名)
- **模板配置**: config.template.yaml (开发参考)
- **路径统一**: data/* 集中数据存储
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