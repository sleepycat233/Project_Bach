# Project Bach Implementation Plan

详细的渐进式实施计划，记录各阶段开发过程、技术方案和重要架构决策。

## 阶段状态总览

- ✅ **Phase 1**: 基础框架 (2025-01-20)
- ✅ **Phase 2**: 自动化监控 (2025-08-21)
- ✅ **Phase 3**: WhisperKit集成 (2025-08-21)
- ✅ **Phase 4**: Tailscale网络集成 (2025-08-21)
- ✅ **Phase 5**: GitHub Pages自动发布 (2025-08-22)
- ✅ **Phase 6**: Web前端现代化 (2025-08-24)
- ✅ **重构阶段**: 架构模块化 (2025-08-21)
- ✅ **Phase 8**: UI体验增强与命名优化 (2025-08-29)
- ✅ **Phase 10**: MLX Whisper后端迁移 + Speaker Diarization (2025-09-01)
- 🔴 **Phase 11**: Speaker Diarization时间戳对齐算法优化 - **分析完成，待数据集验证**
- 📋 **Phase 7**: 前端Post-Processing选择器 - **中等优先级**
- 📋 **其他功能完善**: JavaScript客户端、高级Web功能等

---

## 已完成阶段详细记录

### ✅ Phase 1: 基础框架 (2025-01-20)

**目标**: 建立最简单的端到端音频处理流程

**核心功能**:
- ✅ 音频文件处理 (手动放置 → 自动处理)
- ✅ WhisperKit音频转录 (模拟实现 → 后续真实集成)
- ✅ spaCy人名匿名化 (中英文双语)
- ✅ OpenRouter AI内容生成 (摘要功能)
- ✅ 结果存储 (Markdown格式)

**技术实现**:
- Python 3.11 + spaCy + OpenRouter集成
- 配置驱动 (config.yaml)
- 测试驱动开发 (22/22测试用例通过)

### ✅ Phase 2: 自动化监控 (2025-08-21)

**目标**: 添加文件监控，实现自动化处理

**核心功能**:
- ✅ watchdog文件监控系统 (FileMonitor类)
- ✅ 处理队列管理 (线程安全 + 状态跟踪)
- ✅ 双模式支持 (batch/monitor模式)
- ✅ 优雅启停机制

**技术特性**:
- 支持8种音频格式 (mp3/wav/m4a/flac/aac/ogg等)
- 文件稳定性检查 (避免处理传输中文件)
- 完整日志记录和异常处理

---

### ✅ Phase 3: WhisperKit集成 (2025-08-21)

**目标**: 集成真实音频转录，替换模拟实现

**核心功能**:
- ✅ WhisperKit CLI集成 (subprocess调用)
- ✅ 真实音频转录 (替换模拟数据)
- ✅ 中英文双语支持 (智能语言检测)
- ✅ 配置驱动模型选择 (tiny/small/base/medium/large-v3)

**性能优化**:
- API响应时间优化: 3分钟 → 4.4秒 (40倍提升)
- 双spaCy模型支持 (zh_core_web_sm + en_core_web_sm)
- Google Gemma 3N模型集成

### ✅ Phase 4: Tailscale网络集成 (2025-08-21)

**目标**: 实现跨设备安全文件传输

**核心功能**:
- ✅ Tailscale VPN集成 (TailscaleManager)
- ✅ 安全文件传输 (加密 + 完整性检查)
- ✅ 网络连接监控 (实时状态跟踪)
- ✅ 环境变量安全管理

**安全特性**:
- MD5/SHA256文件完整性验证
- IP白名单和访问控制
- 分块传输和断点续传
- 60+单元测试，100%传输完整性验证

### ✅ Phase 5: GitHub Pages自动发布 (2025-08-22)

**目标**: 实现处理结果自动发布到网站

**核心服务**:
- ✅ GitHubPublisher - 仓库管理和Pages配置
- ✅ ContentFormatter - Markdown/HTML内容格式化
- ✅ TemplateEngine - Jinja2响应式模板系统
- ✅ GitOperations - Git工作流自动化
- ✅ PublishingWorkflow - 端到端发布流程

**技术实现**:
- 6个服务模块，模块化设计
- 响应式模板 (支持暗色模式)
- 31个单元测试，TDD开发方式

---

### ✅ 重构阶段: 架构模块化 (2025-08-21)

**目标**: 解决main.py过度臃肿问题 (954行 → 307行)

**核心成果**:
- ✅ 6个独立功能模块 (core/monitoring/utils/storage/cli)
- ✅ 依赖注入容器管理服务依赖
- ✅ API限流保护机制 (Token bucket算法)
- ✅ 单元测试+集成测试双重保障

**质量提升**:
- 代码规模减少68% (954行 → 307行)
- 可维护性、可测试性、可扩展性大幅改善
- 保持向后兼容，所有原有功能正常

### ✅ Phase 8: UI体验增强与命名优化 (2025-08-29)

**目标**: 实现GitBook风格三栏文档布局，优化YouTube内容命名显示

**核心功能**:
- ✅ GitBook风格三栏布局实现 (CSS Grid + 动态内容加载)
- ✅ 模板系统重构 (组件化导航，删除过期模板)
- ✅ TOC自动生成与滚动高亮
- ✅ 无刷新内容切换和移动端响应式设计

**技术实现**:
- CSS Grid三栏布局 (左导航+主内容+右TOC)
- 新增837行功能代码，删除421行过期代码
- JavaScript动态内容加载系统
- 模板继承优化和组件模块化

### ✅ Phase 10: MLX Whisper后端迁移 + Speaker Diarization (2025-09-01)

**目标**: 将WhisperKit subprocess后端迁移到MLX Whisper Python API，集成Speaker Diarization

**核心功能**:
- ✅ MLX Whisper Python API集成 (替代subprocess调用)
- ✅ Speaker Diarization功能 (pyannote.audio)
- ✅ 智能配置系统 (基于content type自动启用diarization)
- ✅ 双输出模式支持 (group_by_speaker + chunk级精确模式)

**性能提升**:
- 转录性能提升30-50% (消除subprocess开销)
- 说话人识别准确率>85%
- 支持MP4到WAV转换，MPS GPU加速
- HuggingFace标准时间戳对齐算法

### ✅ Phase 11: Speaker Diarization算法分析优化 (2025-09-06)

**目标**: 深度分析时间戳对齐算法，识别并设计跨说话人边界chunks分配问题的解决方案

**核心成果**:
- ✅ **问题精确定位**: 通过详细调试脚本识别IoU算法在跨说话人边界处的分配逻辑问题
- ✅ **具体案例分析**: SEC音频145.52s-148.60s chunk分配问题的完整分析
- ✅ **技术方案设计**: 设计了3种改进算法方案（开始时间优先法、IoU权重调整法、改进版混合法）
- ✅ **调试工具开发**: 完整的`debug_speaker_diarization.py`脚本，输出详细对齐过程

**技术发现**:
- IoU算法数学正确但语言学不够准确：chunk开始时间更能反映实际说话人
- 跨说话人边界的chunks需要启发式规则：chunk开始时间优先 + IoU回退
- 需要多场景数据集验证：当前仅基于SEC 3人对话单一case

**后续优化路径**:
- **Phase 11.1** (短期): 基于现有数据实施改进版开始时间优先算法
- **Phase 11.2** (长期): 收集多样化测试数据集，建立自动化算法评估框架

### 🔄 Phase 6: 多媒体扩展与Web前端 (进行中 75%完成)

**目标**: 构建支持多种内容源的统一处理与分类展示系统

**核心完成状态**:
- ✅ ContentClassifier智能分类器 (18个测试)
- ✅ YouTubeProcessor处理器 (15个测试)
- ✅ AudioUploadProcessor处理器 (23个测试)
- ✅ Flask Web应用框架 (13/19测试通过)
- ✅ 前端架构现代化 (39个文件变更)
- ✅ 文件组织系统增强 (22个新增测试)
- ✅ 测试系统整合完成 (17/17通过)
- 📋 YouTube处理器输出格式统一 (待修复)
- 📋 前端AI处理配置界面 (Phase 7预备功能)
- 📋 部署模式选择功能 (Phase 4预备功能)
- 📋 Tailscale安全配置 (待实施)
- 📋 JavaScript客户端功能 (待开发)

---

## 未来规划

### 📋 Phase 4: Tailscale网络集成与部署模式选择 (待实施)

**目标**: 完善跨设备安全访问和文件传输，支持灵活的部署模式

#### 4.1 部署模式选择功能
- 📋 **本地模式 (Local Mode)**: 本地同时部署前端和后端服务
  - 前端和后端在同一台机器上运行
  - 无需Tailscale连接，直接localhost访问
  - 适合单机使用场景
- 📋 **远程模式 (Remote Mode)**: 通过Tailscale连接远程后端
  - 前端本地运行，后端在远程服务器
  - 通过Tailscale安全网络通信
  - 适合多设备协作场景
- 📋 **配置开关**: 启动时选择部署模式
  ```yaml
  # config.yaml示例
  deployment:
    mode: "local"  # 或 "remote"
    local:
      frontend_port: 8080
      backend_port: 8081
    remote:
      tailscale_enabled: true
      backend_host: "100.x.x.x"  # Tailscale IP
  ```

#### 4.2 网络集成功能
- 📋 网络安全配置完善
- 📋 Web界面Tailscale集成
- 📋 跨设备文件同步机制

#### 4.3 技术实现要点
- 📋 **启动脚本增强**: 根据配置模式启动相应服务
- 📋 **环境检测**: 自动检测Tailscale可用性
- 📋 **配置验证**: 确保选择的模式配置完整
- 📋 **向后兼容**: 默认保持现有行为不变

### 📋 Phase 7: 前端AI处理配置系统 (规划中)

**目标**: 实现用户可定制的AI处理流程配置界面

#### 7.1 前端配置面板
- 📋 **AI服务选择器**: 用户可勾选启用/禁用的处理服务
  - Summary生成 (可选开启/关闭)
  - Mindmap生成 (可选开启/关闭)
  - 未来扩展服务 (关键词提取、情感分析等)
- 📋 **模型选择下拉框**: 动态显示可用的AI模型
  - OpenRouter模型列表 (Gemma, GPT-4, Claude等)
  - 模型性能和成本信息显示
  - 用户偏好设置保存

#### 7.2 后端架构增强
- 📋 **动态服务调度**: 根据用户选择执行相应的AI服务
- 📋 **Prompt模板系统**: 将现有硬编码的prompt转为可配置模板
  ```python
  # 当前: 固定的summary和mindmap生成
  # 目标: 基于用户配置动态选择服务
  selected_services = user_config.get('ai_services', ['summary', 'mindmap'])
  selected_model = user_config.get('ai_model', 'google/gemma-3n-e2b-it:free')
  ```
- 📋 **配置持久化**: 用户设置的存储和恢复机制

#### 7.3 技术实现要点
- 📋 **前端组件**: 新增AI配置面板组件 (AIConfigPanel.js)
- 📋 **API扩展**: 增加用户配置的保存/读取接口
- 📋 **配置管理**: 扩展config.yaml支持用户自定义AI流程
- 📋 **向后兼容**: 保持现有默认配置不变，新功能为增强选项

---

### ✅ Phase 8: UI体验增强与命名优化 (2025-08-29)

**目标**: 实现GitBook风格三栏文档布局，优化YouTube内容命名显示

**核心功能**:
- ✅ 技术方案评估 (Jinja2 vs Jekyll)
- ✅ 架构决策记录 (继续使用Jinja2模板系统)
- ✅ GitBook风格三栏布局实现 (CSS Grid + 动态内容加载)
- ✅ 模板系统重构 (组件化导航，删除过期模板)
- ✅ TOC自动生成与滚动高亮
- 📋 YouTube标题优化显示 (基础实现完成)
- 📋 响应式设计完善 (移动端优化)
- 📋 搜索功能集成

**技术特性**:
- CSS Grid三栏布局 (左导航+主内容+右TOC)
- YouTube文件名语义化 (显示真实标题而非ID)
- 移动端响应式设计 (抽屉式导航)
- 实时搜索和内容筛选功能

**架构决策**: 基于成熟Jinja2系统扩展，避免Jekyll迁移风险

**实施清单**:
- [x] 三栏布局模板重构 (HTML/CSS/JS) - CSS Grid布局完成
- [x] 导航系统组件化 - 拆分为独立可复用组件
- [x] 动态内容加载系统 - 支持Markdown和HTML内容无缝切换
- [x] TOC组件实现 - 自动生成目录与滚动高亮
- [x] 过期模板清理 - 删除content.html, lectures.html等5个文件
- [ ] YouTube标题优化显示 - 基础框架已完成
- [ ] 响应式设计完善 - 移动端抽屉式导航
- [ ] 搜索功能集成 - 实时筛选和内容发现
- [x] 向后兼容性保证 - 现有文件链接和发布流程保持兼容

### 8.1 当前实现状态 (2025-08-29完成)

#### ✅ 核心架构重构
- **三栏布局**: 使用CSS Grid实现左侧导航(18rem) + 主内容(1fr) + 右侧TOC(16rem)
- **模板继承优化**: github_base.html → private_base.html，统一条件逻辑
- **组件模块化**: 导航拆分为4个独立组件(_nav_content_tree.html等)

#### ✅ 动态内容系统
- **无刷新切换**: JavaScript动态加载Markdown/HTML内容到主区域
- **Markdown渲染**: 内置简单Markdown解析器，支持标题、列表、代码等
- **智能回退**: Markdown不存在时自动回退到HTML加载

#### ✅ TOC功能实现
- **自动生成**: 解析h1-h6标签，生成结构化目录树
- **滚动高亮**: 简化版IntersectionObserver实现当前章节高亮
- **点击导航**: 支持TOC链接点击跳转到对应章节

#### 🔧 技术架构
- **文件结构**: 7个新文件，5个过期文件删除，16个文件修改
- **代码规模**: 新增837行功能代码，删除421行过期代码
- **样式系统**: 新增toc.css，扩展github-pages.css和navigation.css
- **JavaScript**: 新增dynamic-content-loader.js，增强github-pages.js

### 8.5 优化后的技术优势

#### 基于现有架构的优势
1. **零重构风险**: 基于1,383行成熟Jinja2代码，无需大规模改动
2. **渐进式实施**: 扩展现有18个模板和6个CSS文件，而非重写
3. **Python生态无缝**: 与AI处理流程深度集成，保持技术栈一致性

#### 实现效果对比
- **原计划**: 8-11天实现 (含Jekyll学习和迁移成本)
- **优化方案**: 5-6天完成 (减少40%工作量)
- **风险等级**: 从高风险重构降为低风险扩展

### 8.6 预期成果

#### 用户体验提升
- **GitBook风格导航**: 现代三栏布局，媲美专业文档平台
- **YouTube标题优化**: 显示真实视频标题，提升内容识别度
- **响应式设计**: 移动端友好的抽屉式导航
- **搜索功能**: 实时搜索和内容筛选

#### 技术架构强化
- **企业级模板系统**: 基于成熟Jinja2架构的进一步优化
- **组件化前端**: 扩展现有组件库，保持代码复用性
- **向后兼容**: 现有文件链接和发布流程完全不受影响

---

### 📋 Phase 9: 智能内容溯源与交互功能 (规划中)

**目标**: 基于word-level timestamp实现AI生成内容的可溯源交互，提升内容可信度

**核心功能**: 让用户能够点击AI生成的笔记内容，自动跳转到对应的transcript原始位置

#### 9.1 Word-Level Timestamp数据增强
- 📋 **转录数据扩展**: 扩展WhisperKit输出，保留word-level时间戳信息
  ```python
  # 当前: 只保存纯文本转录
  transcript = "今天我们讨论机器学习的基本概念..."

  # 目标: 保存带时间戳的结构化数据
  transcript_with_timestamps = [
      {"word": "今天", "start": 0.5, "end": 1.2},
      {"word": "我们", "start": 1.3, "end": 1.8},
      {"word": "讨论", "start": 1.9, "end": 2.4},
      # ...
  ]
  ```

#### 9.2 内容映射与关联系统
- 📋 **AI生成内容标记**: 在summary和mindmap生成时建立与原文的映射关系
- 📋 **语义匹配算法**: 将AI生成的概念/句子映射回transcript中的具体位置
- 📋 **引用追踪系统**: 为每个生成的概念建立可追溯的源引用
  ```python
  # 示例: AI生成的summary中的每个段落都有源引用
  summary_section = {
      "content": "讲师强调了监督学习的重要性",
      "source_refs": [
          {"start_time": 125.3, "end_time": 142.8, "confidence": 0.89},
          {"start_time": 298.1, "end_time": 315.4, "confidence": 0.76}
      ]
  }
  ```

#### 9.3 前端交互界面实现
- 📋 **可点击内容标记**: 在AI生成的笔记中标识可溯源的内容片段
  - 鼠标悬停显示来源时间范围
  - 点击触发跳转到transcript对应位置
- 📋 **Transcript时间轴视图**: 实现带时间轴的transcript显示界面
  - 支持时间点精确跳转 (如: 跳转到02:15位置)
  - 高亮显示当前查看的文本段落
  - 提供播放控制 (如果有音频文件)
- 📋 **双向导航**: 支持从transcript也能跳转到相关的AI生成内容

#### 9.4 技术实现架构
- 📋 **后端数据结构**:
  ```python
  class TimestampedTranscript:
      words: List[WordTimestamp]
      summary_mappings: Dict[str, List[TimeRange]]
      mindmap_mappings: Dict[str, List[TimeRange]]

  class ContentReference:
      source_file: str
      time_range: TimeRange
      confidence_score: float
      matched_text: str
  ```

- 📋 **前端交互组件**:
  - `SourceTraceableContent.js`: 可溯源内容显示组件
  - `TranscriptViewer.js`: 时间轴transcript查看器
  - `NavigationBridge.js`: 双向跳转逻辑控制

#### 9.5 用户体验设计
- 📋 **视觉标识系统**:
  - 可溯源内容使用下划线或特殊颜色标识
  - 不同置信度使用不同的视觉强度表示
  - 多源引用内容显示多重标记
- 📋 **交互反馈**:
  - 点击后平滑滚动到目标位置
  - 目标内容高亮显示3秒
  - 提供"返回笔记"快捷按钮

#### 9.6 实施优先级
- 🔴 **高优先级**: Word-level timestamp数据保存 (基础数据层)
- 🟡 **中优先级**: 内容映射算法开发 (核心功能层)
- 🟢 **低优先级**: 高级交互功能 (体验优化层)

**预期价值**:
- **提升可信度**: 用户可验证AI生成内容的原始来源
- **增强学习体验**: 快速定位关键信息在原始材料中的位置
- **支持深度分析**: 便于研究者和学习者进行细致的内容分析

---

**最后更新**: 2025-09-06 (Phase 10-11 完成总结)
**文档维护**: 记录重要架构决策、开发进度和当前开发重点，指导未来开发方向
