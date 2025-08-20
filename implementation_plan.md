# Project Bach - 实施计划

## 阶段规划 (渐进式实现)

### 第一阶段: 基础框架 ✅ 先跑起来再说

**目标**: 建立最简单的端到端流程

**功能范围**:
- 手动放音频文件到指定文件夹
- 基础音频转录 (WhisperKit)
- 基础人名匿名化 (spaCy)
- 简单的AI内容生成 (OpenRouter)
- 手动查看结果

**技术要求**:
- 单个Python脚本
- 手动触发处理
- 最小依赖配置
- 基础错误处理

**完成标准**:
- 能够成功处理一个音频文件
- 生成可读的转录文本
- 人名被正确替换
- AI生成摘要和思维导图
- 结果保存到本地文件

---

### 第二阶段: 自动化监控 🔄 让它自己跑

**目标**: 添加文件监控，实现自动处理

**新增功能**:
- watchdog文件监控
- 自动检测新音频文件
- 处理队列管理
- 基础日志记录

**改进内容**:
- 异常处理增强
- 配置文件管理
- 处理状态跟踪

**完成标准**:
- 拖放音频文件自动开始处理
- 处理过程有日志输出
- 支持多种音频格式
- 基本的错误恢复

---

### 第三阶段: 网络集成 🌐 远程文件传输

**目标**: 集成Tailscale，支持远程文件传输

**新增功能**:
- Tailscale网络配置
- 远程文件夹访问
- 手机端文件传输测试
- 网络连接状态监控

**改进内容**:
- 文件传输完整性检查
- 网络异常处理
- 远程访问权限管理

**完成标准**:
- 手机可以安全传输音频文件到Mac mini
- 支持大文件传输
- 网络中断后自动恢复
- 传输过程有进度反馈

---

### 第四阶段: 内容发布 📝 自动化部署

**目标**: 自动发布内容到GitHub Pages

**新增功能**:
- GitHub仓库自动化
- 内容格式化和模板
- Git提交和推送
- GitHub Actions触发

**改进内容**:
- 内容质量检查
- 发布失败重试
- 版本管理优化

**完成标准**:
- 处理完成后自动发布到网站
- 内容格式美观易读
- 支持历史内容浏览
- 发布状态可追踪

---

### 第五阶段: 优化增强 ⚡ 体验优化

**目标**: 提升系统稳定性和用户体验

**优化内容**:
- 处理速度优化
- AI输出质量调优
- 错误处理完善
- 监控和告警

**新增功能**:
- Web简单管理界面 (可选)
- 处理历史查看
- 系统健康检查
- 配置热更新

---

## 第一阶段详细实施步骤

### Step 1: 环境准备

```bash
# 1. 创建项目目录结构
mkdir -p ~/project_bach/{data/{audio,transcripts,logs},watch_folder,output}
cd ~/project_bach

# 2. 安装Python依赖
pip3.11 install watchdog spacy requests gitpython pyyaml

# 3. 下载spaCy模型
python3.11 -m spacy download zh_core_web_sm
python3.11 -m spacy download en_core_web_sm

# 4. 验证WhisperKit (假设已安装)
# TODO: 确认WhisperKit安装方法
```

### Step 2: 创建核心文件

**config.yaml** - 基础配置
```yaml
api:
  openrouter:
    key: "YOUR_API_KEY"
    base_url: "https://openrouter.ai/api/v1"
    models:
      summary: "deepseek/deepseek-chat"
      mindmap: "openai/gpt-4o-mini"  # 先用便宜的测试

paths:
  watch_folder: "./watch_folder"
  data_folder: "./data"
  output_folder: "./output"

spacy:
  model: "zh_core_web_sm"
  
logging:
  level: "INFO"
  file: "./data/logs/app.log"
```

**main.py** - 主处理脚本
```python
#!/usr/bin/env python3.11
"""
Project Bach - 第一阶段实现
简单的音频处理脚本，手动触发处理
"""

import os
import time
import yaml
import spacy
import requests
import logging
from pathlib import Path
from datetime import datetime

class AudioProcessor:
    def __init__(self, config_path="config.yaml"):
        self.config = self.load_config(config_path)
        self.setup_logging()
        self.setup_spacy()
        
    def load_config(self, path):
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def setup_logging(self):
        logging.basicConfig(
            level=getattr(logging, self.config['logging']['level']),
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.config['logging']['file']),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def setup_spacy(self):
        model_name = self.config['spacy']['model']
        self.logger.info(f"加载spaCy模型: {model_name}")
        self.nlp = spacy.load(model_name)
    
    def process_audio_file(self, audio_path):
        """处理单个音频文件的完整流程"""
        start_time = time.time()
        audio_path = Path(audio_path)
        
        self.logger.info(f"开始处理音频文件: {audio_path.name}")
        
        try:
            # 1. 音频转录
            transcript = self.transcribe_audio(audio_path)
            if not transcript:
                raise Exception("转录失败")
            
            # 2. 保存原始转录
            self.save_transcript(audio_path.stem, transcript, "raw")
            
            # 3. 人名匿名化
            anonymized_text = self.anonymize_names(transcript)
            self.save_transcript(audio_path.stem, anonymized_text, "anonymized")
            
            # 4. AI内容生成
            summary = self.generate_summary(anonymized_text)
            mindmap = self.generate_mindmap(anonymized_text)
            
            # 5. 保存结果
            self.save_results(audio_path.stem, {
                'summary': summary,
                'mindmap': mindmap,
                'original_file': str(audio_path),
                'processed_time': datetime.now().isoformat()
            })
            
            elapsed = time.time() - start_time
            self.logger.info(f"处理完成: {audio_path.name} (耗时: {elapsed:.2f}秒)")
            
        except Exception as e:
            self.logger.error(f"处理失败: {audio_path.name} - {str(e)}")
            raise
    
    def transcribe_audio(self, audio_path):
        """音频转录 - 第一阶段先用模拟数据"""
        self.logger.info(f"转录音频: {audio_path.name}")
        
        # TODO: 集成真实的WhisperKit
        # 现在返回模拟数据用于测试
        return f"""
这是一个模拟的转录结果，来自文件 {audio_path.name}。
在实际实现中，这里会调用WhisperKit进行音频转录。
会议内容：张三和李四讨论了项目进展，王五提出了新的建议。
时间大约持续了30分钟，主要涉及技术架构和实施计划。
        """.strip()
    
    def anonymize_names(self, text):
        """使用spaCy进行人名匿名化"""
        self.logger.info("开始人名匿名化处理")
        
        doc = self.nlp(text)
        result = text
        name_count = 0
        
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                name_count += 1
                placeholder = f"人员{name_count}"
                result = result.replace(ent.text, placeholder)
                self.logger.debug(f"替换人名: {ent.text} -> {placeholder}")
        
        self.logger.info(f"匿名化完成，替换了 {name_count} 个人名")
        return result
    
    def generate_summary(self, text):
        """调用AI生成摘要"""
        self.logger.info("生成内容摘要")
        
        try:
            response = requests.post(
                f"{self.config['api']['openrouter']['base_url']}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.config['api']['openrouter']['key']}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.config['api']['openrouter']['models']['summary'],
                    "messages": [
                        {
                            "role": "user", 
                            "content": f"请为以下内容生成一个简洁的摘要（300字以内）：\n\n{text}"
                        }
                    ],
                    "max_tokens": 500,
                    "temperature": 0.7
                },
                timeout=30
            )
            
            if response.status_code == 200:
                content = response.json()['choices'][0]['message']['content']
                self.logger.info("摘要生成成功")
                return content
            else:
                raise Exception(f"API调用失败: {response.status_code}")
                
        except Exception as e:
            self.logger.error(f"摘要生成失败: {str(e)}")
            return f"摘要生成失败: {str(e)}"
    
    def generate_mindmap(self, text):
        """调用AI生成思维导图"""
        self.logger.info("生成思维导图")
        
        try:
            response = requests.post(
                f"{self.config['api']['openrouter']['base_url']}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.config['api']['openrouter']['key']}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.config['api']['openrouter']['models']['mindmap'],
                    "messages": [
                        {
                            "role": "user", 
                            "content": f"请将以下内容整理成Markdown格式的思维导图结构：\n\n{text}"
                        }
                    ],
                    "max_tokens": 800,
                    "temperature": 0.5
                },
                timeout=30
            )
            
            if response.status_code == 200:
                content = response.json()['choices'][0]['message']['content']
                self.logger.info("思维导图生成成功")
                return content
            else:
                raise Exception(f"API调用失败: {response.status_code}")
                
        except Exception as e:
            self.logger.error(f"思维导图生成失败: {str(e)}")
            return f"思维导图生成失败: {str(e)}"
    
    def save_transcript(self, filename, content, suffix):
        """保存转录文本"""
        transcript_dir = Path(self.config['paths']['data_folder']) / 'transcripts'
        transcript_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = transcript_dir / f"{filename}_{suffix}.txt"
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        self.logger.debug(f"保存转录文件: {file_path}")
    
    def save_results(self, filename, results):
        """保存最终结果"""
        output_dir = Path(self.config['paths']['output_folder'])
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成markdown格式的结果文件
        markdown_content = f"""# {filename} - 处理结果

**处理时间**: {results['processed_time']}
**原始文件**: {results['original_file']}

## 内容摘要

{results['summary']}

## 思维导图

{results['mindmap']}

---
*由 Project Bach 自动生成*
"""
        
        result_file = output_dir / f"{filename}_result.md"
        with open(result_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        self.logger.info(f"结果已保存: {result_file}")

def main():
    """主函数 - 第一阶段手动处理"""
    print("=== Project Bach - 第一阶段测试 ===")
    
    # 检查配置文件
    if not os.path.exists("config.yaml"):
        print("错误: 找不到 config.yaml 配置文件")
        print("请先创建配置文件并填入API密钥")
        return
    
    processor = AudioProcessor()
    
    # 检查音频文件夹
    watch_folder = Path(processor.config['paths']['watch_folder'])
    audio_files = list(watch_folder.glob("*.mp3")) + \
                 list(watch_folder.glob("*.wav")) + \
                 list(watch_folder.glob("*.m4a"))
    
    if not audio_files:
        print(f"在 {watch_folder} 中没有找到音频文件")
        print("请将音频文件放入该文件夹后重新运行")
        return
    
    # 处理找到的音频文件
    for audio_file in audio_files:
        try:
            print(f"\n正在处理: {audio_file.name}")
            processor.process_audio_file(audio_file)
            print(f"✅ 处理完成: {audio_file.name}")
        except Exception as e:
            print(f"❌ 处理失败: {audio_file.name} - {str(e)}")
    
    print(f"\n处理完成! 结果保存在: {processor.config['paths']['output_folder']}")

if __name__ == "__main__":
    main()
```

### Step 3: 测试验证

**test_run.py** - 简单测试脚本
```python
#!/usr/bin/env python3.11
"""测试脚本 - 验证基础功能"""

import os
import shutil
from pathlib import Path

def setup_test_environment():
    """设置测试环境"""
    print("设置测试环境...")
    
    # 创建测试音频文件 (空文件用于测试)
    test_audio = Path("watch_folder/test_meeting.mp3")
    test_audio.parent.mkdir(exist_ok=True)
    test_audio.touch()
    
    print(f"创建测试文件: {test_audio}")

def check_dependencies():
    """检查依赖是否正确安装"""
    print("检查依赖...")
    
    try:
        import spacy
        nlp = spacy.load("zh_core_web_sm")
        print("✅ spaCy中文模型已安装")
    except:
        print("❌ spaCy中文模型未安装")
        return False
    
    try:
        import yaml, requests
        print("✅ 基础依赖已安装")
    except:
        print("❌ 基础依赖缺失")
        return False
    
    return True

def main():
    if not check_dependencies():
        print("请先安装必要依赖")
        return
    
    setup_test_environment()
    print("测试环境准备完成，请运行: python3.11 main.py")

if __name__ == "__main__":
    main()
```

### Step 4: 第一阶段验收标准

**功能验收**:
- [ ] 成功加载spaCy中文模型
- [ ] 正确读取配置文件
- [ ] 模拟转录功能正常 (为真实WhisperKit做准备)
- [ ] 人名匿名化功能正常
- [ ] OpenRouter API调用成功
- [ ] 生成格式正确的摘要和思维导图
- [ ] 结果文件正确保存到指定位置

**文件输出验收**:
```
project_bach/
├── data/
│   ├── transcripts/
│   │   ├── test_meeting_raw.txt
│   │   └── test_meeting_anonymized.txt
│   └── logs/
│       └── app.log
├── output/
│   └── test_meeting_result.md
└── watch_folder/
    └── test_meeting.mp3
```

**性能指标**:
- 处理一个5分钟音频文件(模拟) < 30秒
- API调用成功率 > 95%
- 人名识别准确率 > 80%

---

## 后续阶段预览

### 第二阶段关键任务
1. 实现watchdog自动监控
2. 集成真实WhisperKit API
3. 完善错误处理和重试机制
4. 添加处理状态跟踪

### 第三阶段关键任务
1. 配置Tailscale网络
2. 测试跨设备文件传输
3. 优化大文件处理
4. 添加传输安全验证

### 第四阶段关键任务
1. 集成GitHub API
2. 设计网站模板
3. 实现自动部署流程
4. 添加内容版本管理

### 第五阶段关键任务
1. 性能监控和优化
2. 用户体验改进
3. 系统稳定性测试
4. 可选功能开发

---

## 风险控制

**技术风险**:
- WhisperKit集成复杂度: 预留足够测试时间
- API限流问题: 实现请求频率控制
- 网络连接稳定性: 添加重试和降级策略

**进度风险**:
- 每个阶段设置明确的完成标准
- 优先保证核心功能可用
- 允许功能范围灵活调整

**质量风险**:
- 每个阶段都要有可用的版本
- 充分测试再进入下一阶段
- 保持代码简洁，避免过度优化

---

*第一阶段的重点是验证整体流程的可行性，为后续开发奠定基础。*