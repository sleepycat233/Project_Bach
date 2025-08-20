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
from typing import Dict, Tuple, Optional


class AudioProcessor:
    def __init__(self, config_path="config.yaml"):
        """初始化音频处理器"""
        self.config = self.load_config(config_path)
        self.setup_logging()
        self.setup_directories()
        self.setup_spacy()
        self.name_mapping: Dict[str, str] = {}
        self.name_counter = 0
        
    def load_config(self, path: str) -> dict:
        """加载配置文件"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # 验证必要的配置项
            required_keys = ['api', 'paths', 'spacy', 'logging']
            for key in required_keys:
                if key not in config:
                    raise ValueError(f"配置文件缺少必要项: {key}")
            
            return config
        except FileNotFoundError:
            raise FileNotFoundError(f"配置文件未找到: {path}")
        except yaml.YAMLError as e:
            raise ValueError(f"配置文件格式错误: {e}")
    
    def setup_logging(self):
        """设置日志系统"""
        log_file = Path(self.config['logging']['file'])
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            level=getattr(logging, self.config['logging']['level']),
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info("日志系统初始化完成")
    
    def setup_directories(self):
        """创建必要的目录结构"""
        directories = [
            self.config['paths']['watch_folder'],
            self.config['paths']['data_folder'],
            self.config['paths']['output_folder'],
            os.path.join(self.config['paths']['data_folder'], 'transcripts'),
            os.path.join(self.config['paths']['data_folder'], 'logs')
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
        
        self.logger.info("目录结构创建完成")
    
    def setup_spacy(self):
        """设置spaCy模型"""
        model_name = self.config['spacy']['model']
        try:
            self.logger.info(f"加载spaCy模型: {model_name}")
            self.nlp = spacy.load(model_name)
            self.logger.info("spaCy模型加载成功")
        except OSError:
            self.logger.error(f"spaCy模型加载失败: {model_name}")
            self.logger.error("请运行: python -m spacy download zh_core_web_sm")
            raise
    
    def process_audio_file(self, audio_path: str) -> bool:
        """处理单个音频文件的完整流程"""
        start_time = time.time()
        audio_path = Path(audio_path)
        
        self.logger.info(f"开始处理音频文件: {audio_path.name}")
        
        try:
            # 1. 音频转录
            self.logger.info("步骤1: 开始音频转录")
            transcript = self.transcribe_audio(audio_path)
            if not transcript:
                raise Exception("转录失败或结果为空")
            
            # 2. 保存原始转录
            self.save_transcript(audio_path.stem, transcript, "raw")
            
            # 3. 人名匿名化
            self.logger.info("步骤2: 开始人名匿名化")
            anonymized_text, mapping = self.anonymize_names(transcript)
            self.save_transcript(audio_path.stem, anonymized_text, "anonymized")
            
            # 记录匿名化映射
            if mapping:
                self.logger.info(f"人名匿名化映射: {mapping}")
            
            # 4. AI内容生成
            self.logger.info("步骤3: 开始AI内容生成")
            summary = self.generate_summary(anonymized_text)
            mindmap = self.generate_mindmap(anonymized_text)
            
            # 5. 保存结果
            self.logger.info("步骤4: 保存处理结果")
            self.save_results(audio_path.stem, {
                'summary': summary,
                'mindmap': mindmap,
                'original_file': str(audio_path),
                'processed_time': datetime.now().isoformat(),
                'anonymization_mapping': mapping
            })
            
            elapsed = time.time() - start_time
            self.logger.info(f"处理完成: {audio_path.name} (耗时: {elapsed:.2f}秒)")
            return True
            
        except Exception as e:
            self.logger.error(f"处理失败: {audio_path.name} - {str(e)}")
            return False
    
    def transcribe_audio(self, audio_path: Path) -> str:
        """音频转录 - 第一阶段使用模拟数据"""
        self.logger.info(f"转录音频: {audio_path.name}")
        
        # TODO: 集成真实的WhisperKit
        # 现在返回模拟数据用于测试第一阶段其他功能
        
        # 模拟不同的转录内容基于文件名
        if "meeting" in audio_path.name.lower():
            transcript = f"""
这是一个关于项目进展的会议转录，来自文件 {audio_path.name}。
张三首先汇报了上周的工作进展，主要完成了系统架构设计。
李四提到了在实施过程中遇到的技术难题，需要进一步研究。
王五建议采用新的技术方案来解决性能问题。
赵六负责协调各部门之间的配合工作。
会议持续了大约45分钟，最终确定了下一阶段的工作计划。
主要决策包括：技术架构优化、人员分工调整、时间节点确认。
            """.strip()
        elif "lecture" in audio_path.name.lower():
            transcript = f"""
这是一堂技术讲座的转录内容，来自文件 {audio_path.name}。
教授陈明详细介绍了人工智能在现代软件开发中的应用。
学生刘华提问关于机器学习算法的选择问题。
助教孙丽回答了关于数据预处理的具体方法。
讲座涵盖了理论基础、实践案例和未来发展趋势。
课程时长约60分钟，包含15分钟的问答环节。
            """.strip()
        else:
            transcript = f"""
这是音频文件 {audio_path.name} 的转录结果。
在实际实现中，这里会调用WhisperKit进行真实的音频转录。
内容包含了多位发言人的讨论，涉及技术和业务层面的话题。
发言人包括：马云、马化腾、李彦宏等业界知名人士。
讨论持续了约30分钟，涵盖了当前技术发展的重要议题。
            """.strip()
        
        self.logger.info(f"转录完成，文本长度: {len(transcript)} 字符")
        return transcript
    
    def anonymize_names(self, text: str) -> Tuple[str, Dict[str, str]]:
        """使用spaCy进行人名匿名化"""
        self.logger.info("开始人名匿名化处理")
        
        try:
            doc = self.nlp(text)
            result = text
            current_mapping = {}
            
            # 识别人名实体
            person_entities = [ent for ent in doc.ents if ent.label_ == "PERSON"]
            
            if not person_entities:
                self.logger.info("未检测到人名实体")
                return result, current_mapping
            
            # 处理每个人名
            for ent in person_entities:
                original_name = ent.text.strip()
                
                # 跳过空字符串或过短的实体
                if len(original_name) < 2:
                    continue
                
                # 为新人名分配占位符
                if original_name not in self.name_mapping:
                    self.name_counter += 1
                    # 根据文本语言选择合适的占位符
                    if self._is_chinese_text(text):
                        placeholder = f"人员{self.name_counter}"
                    else:
                        placeholder = f"Person{self.name_counter}"
                    
                    self.name_mapping[original_name] = placeholder
                    self.logger.debug(f"新增人名映射: {original_name} -> {placeholder}")
                
                current_mapping[original_name] = self.name_mapping[original_name]
                
                # 执行替换
                result = result.replace(original_name, self.name_mapping[original_name])
            
            self.logger.info(f"匿名化完成，替换了 {len(current_mapping)} 个人名")
            return result, current_mapping
            
        except Exception as e:
            self.logger.error(f"人名匿名化失败: {str(e)}")
            return text, {}
    
    def _is_chinese_text(self, text: str) -> bool:
        """检测文本是否主要为中文"""
        chinese_chars = sum(1 for char in text if '\u4e00' <= char <= '\u9fff')
        return chinese_chars > len(text) * 0.3  # 如果30%以上是中文字符
    
    def generate_summary(self, text: str) -> str:
        """调用AI生成摘要"""
        self.logger.info("生成内容摘要")
        
        try:
            api_config = self.config['api']['openrouter']
            
            response = requests.post(
                f"{api_config['base_url']}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_config['key']}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": api_config['models']['summary'],
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
                return content.strip()
            else:
                error_msg = f"API调用失败，状态码: {response.status_code}"
                if response.text:
                    error_msg += f"，响应: {response.text[:200]}"
                raise Exception(error_msg)
                
        except requests.exceptions.Timeout:
            error_msg = "API调用超时"
            self.logger.error(error_msg)
            return f"摘要生成失败: {error_msg}"
        except requests.exceptions.RequestException as e:
            error_msg = f"网络请求失败: {str(e)}"
            self.logger.error(error_msg)
            return f"摘要生成失败: {error_msg}"
        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"摘要生成失败: {error_msg}")
            return f"摘要生成失败: {error_msg}"
    
    def generate_mindmap(self, text: str) -> str:
        """调用AI生成思维导图"""
        self.logger.info("生成思维导图")
        
        try:
            api_config = self.config['api']['openrouter']
            
            response = requests.post(
                f"{api_config['base_url']}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_config['key']}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": api_config['models']['mindmap'],
                    "messages": [
                        {
                            "role": "user", 
                            "content": f"请将以下内容整理成Markdown格式的思维导图结构，使用#、##、###等标题层级和-列表项：\n\n{text}"
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
                return content.strip()
            else:
                error_msg = f"API调用失败，状态码: {response.status_code}"
                if response.text:
                    error_msg += f"，响应: {response.text[:200]}"
                raise Exception(error_msg)
                
        except requests.exceptions.Timeout:
            error_msg = "API调用超时"
            self.logger.error(error_msg)
            return f"思维导图生成失败: {error_msg}"
        except requests.exceptions.RequestException as e:
            error_msg = f"网络请求失败: {str(e)}"
            self.logger.error(error_msg)
            return f"思维导图生成失败: {error_msg}"
        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"思维导图生成失败: {error_msg}")
            return f"思维导图生成失败: {error_msg}"
    
    def save_transcript(self, filename: str, content: str, suffix: str):
        """保存转录文本"""
        transcript_dir = Path(self.config['paths']['data_folder']) / 'transcripts'
        transcript_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = transcript_dir / f"{filename}_{suffix}.txt"
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self.logger.debug(f"保存转录文件: {file_path}")
        except Exception as e:
            self.logger.error(f"保存转录文件失败: {str(e)}")
    
    def save_results(self, filename: str, results: dict):
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

## 处理信息

**匿名化映射**: {results.get('anonymization_mapping', '无')}

---
*由 Project Bach 自动生成*
"""
        
        result_file = output_dir / f"{filename}_result.md"
        try:
            with open(result_file, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            self.logger.info(f"结果已保存: {result_file}")
        except Exception as e:
            self.logger.error(f"保存结果文件失败: {str(e)}")


def check_dependencies():
    """检查依赖是否正确安装"""
    print("检查系统依赖...")
    
    issues = []
    
    # 检查spaCy模型
    try:
        import spacy
        nlp = spacy.load("zh_core_web_sm")
        print("✅ spaCy中文模型已安装")
    except ImportError:
        issues.append("❌ spaCy未安装，请运行: pip install spacy")
    except OSError:
        issues.append("❌ spaCy中文模型未安装，请运行: python -m spacy download zh_core_web_sm")
    
    # 检查其他必要依赖
    required_packages = ['yaml', 'requests']
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package} 已安装")
        except ImportError:
            issues.append(f"❌ {package} 未安装，请运行: pip install {package}")
    
    return issues


def setup_test_environment():
    """设置测试环境"""
    print("设置测试环境...")
    
    # 创建测试音频文件
    test_files = [
        "watch_folder/test_meeting.mp3",
        "watch_folder/tech_lecture.wav", 
        "watch_folder/discussion.m4a"
    ]
    
    for test_file in test_files:
        test_path = Path(test_file)
        test_path.parent.mkdir(exist_ok=True)
        if not test_path.exists():
            test_path.write_bytes(b'fake audio data for testing')
            print(f"创建测试文件: {test_file}")


def main():
    """主函数 - 第一阶段手动处理"""
    print("=== Project Bach - 第一阶段测试 ===")
    print("简洁的音频处理管道 - 基础功能验证")
    print()
    
    # 检查依赖
    issues = check_dependencies()
    if issues:
        print("依赖检查失败:")
        for issue in issues:
            print(f"  {issue}")
        print("\n请解决上述问题后重新运行")
        return False
    
    # 检查配置文件
    config_path = "config.yaml"
    if not os.path.exists(config_path):
        print(f"❌ 错误: 找不到 {config_path} 配置文件")
        print("请先创建配置文件并填入API密钥")
        return False
    
    # 检查API密钥配置
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    api_key = config.get('api', {}).get('openrouter', {}).get('key', '')
    if api_key == 'YOUR_API_KEY_HERE' or not api_key:
        print("❌ 警告: 请在 config.yaml 中配置真实的 OpenRouter API 密钥")
        print("当前将使用模拟模式运行...")
    
    try:
        # 初始化处理器
        processor = AudioProcessor(config_path)
        print("✅ 音频处理器初始化成功")
        
        # 检查音频文件夹
        watch_folder = Path(processor.config['paths']['watch_folder'])
        if not watch_folder.exists():
            print(f"创建监控文件夹: {watch_folder}")
            watch_folder.mkdir(parents=True, exist_ok=True)
        
        # 查找音频文件
        audio_extensions = ['*.mp3', '*.wav', '*.m4a', '*.flac']
        audio_files = []
        for ext in audio_extensions:
            audio_files.extend(watch_folder.glob(ext))
        
        if not audio_files:
            print(f"在 {watch_folder} 中没有找到音频文件")
            setup_test_environment()
            print("已创建测试文件，请重新运行程序")
            return True
        
        # 处理找到的音频文件
        success_count = 0
        total_count = len(audio_files)
        
        print(f"找到 {total_count} 个音频文件，开始处理...")
        print()
        
        for i, audio_file in enumerate(audio_files, 1):
            print(f"[{i}/{total_count}] 正在处理: {audio_file.name}")
            
            if processor.process_audio_file(audio_file):
                print(f"✅ 处理完成: {audio_file.name}")
                success_count += 1
            else:
                print(f"❌ 处理失败: {audio_file.name}")
            print()
        
        # 输出处理摘要
        print("=== 处理摘要 ===")
        print(f"总文件数: {total_count}")
        print(f"成功处理: {success_count}")
        print(f"失败数量: {total_count - success_count}")
        print(f"成功率: {success_count/total_count*100:.1f}%")
        print()
        print(f"结果保存在: {processor.config['paths']['output_folder']}")
        print(f"日志文件: {processor.config['logging']['file']}")
        
        return success_count == total_count
        
    except Exception as e:
        print(f"❌ 程序运行失败: {str(e)}")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)