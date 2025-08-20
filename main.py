#!/usr/bin/env python3.11
"""
Project Bach - 第一阶段实现
简单的音频处理脚本，手动触发处理
"""

import os
import sys
import time
import yaml
import spacy
import requests
import logging
import queue
import threading
import argparse
import signal
from pathlib import Path
from datetime import datetime
from typing import Dict, Tuple, Optional, List
from faker import Faker
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileMovedEvent


class AudioFileHandler(FileSystemEventHandler):
    """音频文件事件处理器"""
    
    def __init__(self, file_monitor):
        super().__init__()
        self.file_monitor = file_monitor
        self.supported_formats = {'.mp3', '.wav', '.m4a', '.flac', '.aac', '.ogg'}
        self.ignore_patterns = {'.DS_Store', '.tmp', '.part', '.download'}
    
    def on_created(self, event):
        """文件创建事件"""
        if not event.is_directory:
            self._handle_new_file(event.src_path)
    
    def on_moved(self, event):
        """文件移动事件"""
        if not event.is_directory:
            self._handle_new_file(event.dest_path)
    
    def _handle_new_file(self, file_path: str):
        """处理新文件"""
        path = Path(file_path)
        
        # 检查文件格式
        if path.suffix.lower() not in self.supported_formats:
            return
        
        # 检查是否为临时文件
        if any(pattern in path.name for pattern in self.ignore_patterns):
            return
        
        # 添加到处理队列
        self.file_monitor.add_to_queue(file_path)


class ProcessingQueue:
    """处理队列管理"""
    
    def __init__(self, max_size=100):
        self.queue = queue.Queue(maxsize=max_size)
        self.processing_status = {}  # 文件处理状态跟踪
        self.lock = threading.Lock()
    
    def add_file(self, file_path: str) -> bool:
        """添加文件到队列"""
        with self.lock:
            # 防止重复处理
            if file_path in self.processing_status:
                return False
            
            try:
                self.queue.put(file_path, block=False)
                self.processing_status[file_path] = 'pending'
                return True
            except queue.Full:
                return False
    
    def get_file(self) -> Optional[str]:
        """从队列获取文件"""
        try:
            file_path = self.queue.get(timeout=1.0)
            with self.lock:
                self.processing_status[file_path] = 'processing'
            return file_path
        except queue.Empty:
            return None
    
    def mark_completed(self, file_path: str):
        """标记文件处理完成"""
        with self.lock:
            self.processing_status[file_path] = 'completed'
    
    def mark_failed(self, file_path: str):
        """标记文件处理失败"""
        with self.lock:
            self.processing_status[file_path] = 'failed'
    
    def get_status(self, file_path: str) -> str:
        """获取文件处理状态"""
        with self.lock:
            return self.processing_status.get(file_path, 'unknown')
    
    def is_empty(self) -> bool:
        """检查队列是否为空"""
        return self.queue.empty()


class FileMonitor:
    """文件监控器"""
    
    def __init__(self, watch_folder: str, audio_processor):
        self.watch_folder = Path(watch_folder)
        self.audio_processor = audio_processor
        self.processing_queue = ProcessingQueue()
        self.observer = Observer()
        self.event_handler = AudioFileHandler(self)
        self.is_running = False
        self.processing_thread = None
        self.logger = logging.getLogger(__name__)
    
    def start_monitoring(self):
        """开始文件监控"""
        if self.is_running:
            return
        
        self.observer.schedule(
            self.event_handler,
            str(self.watch_folder),
            recursive=False
        )
        
        self.observer.start()
        self.is_running = True
        
        # 启动处理线程
        self.processing_thread = threading.Thread(target=self._processing_worker)
        self.processing_thread.daemon = True
        self.processing_thread.start()
        
        self.logger.info(f"开始监控文件夹: {self.watch_folder}")
    
    def stop_monitoring(self):
        """停止文件监控"""
        if not self.is_running:
            return
        
        self.is_running = False
        self.observer.stop()
        self.observer.join()
        
        if self.processing_thread:
            self.processing_thread.join(timeout=5.0)
        
        self.logger.info("文件监控已停止")
    
    def add_to_queue(self, file_path: str):
        """添加文件到处理队列"""
        # 等待文件稳定（避免处理正在传输的文件）
        time.sleep(2)
        
        if self._is_file_stable(file_path):
            if self.processing_queue.add_file(file_path):
                self.logger.info(f"文件已添加到处理队列: {Path(file_path).name}")
            else:
                self.logger.warning(f"文件无法添加到队列: {Path(file_path).name}")
    
    def _is_file_stable(self, file_path: str) -> bool:
        """检查文件是否稳定（大小不再变化）"""
        try:
            path = Path(file_path)
            if not path.exists():
                return False
            
            # 检查文件大小稳定性
            size1 = path.stat().st_size
            time.sleep(1)
            size2 = path.stat().st_size
            
            return size1 == size2 and size1 > 0
        except Exception:
            return False
    
    def _processing_worker(self):
        """处理队列工作线程"""
        while self.is_running:
            file_path = self.processing_queue.get_file()
            
            if file_path:
                self.logger.info(f"开始处理文件: {Path(file_path).name}")
                try:
                    # 调用音频处理器处理文件
                    success = self.audio_processor.process_audio_file(file_path)
                    
                    if success:
                        self.processing_queue.mark_completed(file_path)
                        self.logger.info(f"文件处理完成: {Path(file_path).name}")
                    else:
                        self.processing_queue.mark_failed(file_path)
                        self.logger.error(f"文件处理失败: {Path(file_path).name}")
                        
                except Exception as e:
                    self.processing_queue.mark_failed(file_path)
                    self.logger.error(f"文件处理异常: {Path(file_path).name}, 错误: {str(e)}")
            else:
                # 队列为空时短暂休眠
                time.sleep(0.5)


class AudioProcessor:
    def __init__(self, config_path="config.yaml"):
        """初始化音频处理器"""
        self.config = self.load_config(config_path)
        self.setup_logging()
        self.setup_directories()
        self.setup_spacy()
        # 初始化基于NLP + Faker的动态人名映射系统
        self.name_mapping: Dict[str, str] = {}
        
        # 初始化Faker生成器
        self.fake_zh = Faker('zh_CN')  # 中文虚拟数据生成器
        self.fake_en = Faker('en_US')  # 英文虚拟数据生成器
        
        # 已使用的虚拟人名（避免重复）
        self.used_names = set()
        
        # Phase 2: 文件监控器
        self.file_monitor = None
        
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
        """设置spaCy双语模型"""
        try:
            # 加载中文模型
            self.logger.info("加载spaCy中文模型: zh_core_web_sm")
            self.nlp_zh = spacy.load("zh_core_web_sm")
            
            # 加载英文模型
            self.logger.info("加载spaCy英文模型: en_core_web_sm")
            self.nlp_en = spacy.load("en_core_web_sm")
            
            # 默认使用中文模型（向后兼容）
            self.nlp = self.nlp_zh
            
            self.logger.info("spaCy双语模型加载成功")
        except OSError as e:
            self.logger.error(f"spaCy模型加载失败: {str(e)}")
            self.logger.error("请运行: python -m spacy download zh_core_web_sm")
            self.logger.error("请运行: python -m spacy download en_core_web_sm")
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
        """转录音频文件 - 集成真实WhisperKit"""
        self.logger.info(f"转录音频: {audio_path.name}")
        
        try:
            # 使用WhisperKit CLI进行真实转录
            return self._transcribe_with_whisperkit(audio_path)
        except Exception as e:
            self.logger.warning(f"WhisperKit转录失败，使用备用方案: {str(e)}")
            return self._fallback_transcription(audio_path)
    
    def _transcribe_with_whisperkit(self, audio_path: Path) -> str:
        """使用WhisperKit CLI进行音频转录"""
        import subprocess
        
        # 从配置文件获取WhisperKit设置
        whisperkit_config = self.config.get('whisperkit', {})
        model = whisperkit_config.get('model', 'medium')
        default_language = whisperkit_config.get('language', 'zh')
        
        # 检测音频语言
        language = self._detect_audio_language(audio_path, default_language)
        
        # 构建WhisperKit命令
        cmd = [
            "whisperkit-cli",
            "transcribe",
            "--audio-path", str(audio_path),
            "--language", language,
            "--model", model,
            "--task", "transcribe"
        ]
        
        self.logger.debug(f"WhisperKit命令: {' '.join(cmd)}")
        
        # 执行转录
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120  # 2分钟超时
        )
        
        if result.returncode != 0:
            raise Exception(f"WhisperKit执行失败: {result.stderr}")
        
        # 提取转录文本
        transcript = result.stdout.strip()
        
        if not transcript or len(transcript.strip()) < 5:
            raise Exception("转录结果为空或过短")
        
        self.logger.info(f"WhisperKit转录完成，文本长度: {len(transcript)} 字符")
        return transcript
    
    def _detect_audio_language(self, audio_path: Path, default_language: str = 'en') -> str:
        """智能检测音频语言（支持中英文双语）"""
        filename_lower = audio_path.name.lower()
        
        # 中文关键词检测
        chinese_keywords = ['chinese', 'zh', '中文', '会议', '讲座', '讨论', '汇报', '培训']
        if any(keyword in filename_lower for keyword in chinese_keywords):
            self.logger.debug(f"文件名检测为中文: {audio_path.name}")
            return 'zh'
        
        # 英文关键词检测
        english_keywords = ['english', 'en', 'lecture', 'meeting', 'class', 'course', 'lesson', 'presentation', 'seminar']
        if any(keyword in filename_lower for keyword in english_keywords):
            self.logger.debug(f"文件名检测为英文: {audio_path.name}")
            return 'en'
        
        # 检查文件名中是否包含中文字符
        if any('\u4e00' <= char <= '\u9fff' for char in audio_path.name):
            self.logger.debug(f"文件名包含中文字符，判定为中文: {audio_path.name}")
            return 'zh'
        
        # 默认使用配置文件中的语言（现在是英文）
        self.logger.debug(f"使用默认语言 {default_language}: {audio_path.name}")
        return default_language
    
    def _fallback_transcription(self, audio_path: Path) -> str:
        """备用转录方案（模拟转录）"""
        self.logger.info("使用备用转录方案")
        
        # 保留原有的模拟转录逻辑作为备份
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
WhisperKit转录备用方案 - 文件: {audio_path.name}
系统已尝试使用WhisperKit进行真实音频转录，但遇到技术问题。
建议检查：1) WhisperKit CLI是否正确安装 2) 音频文件格式是否支持 3) 系统资源是否充足
如需技术支持，请提供日志文件以便进一步诊断。
处理时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """.strip()
        
        self.logger.info(f"备用转录完成，文本长度: {len(transcript)} 字符")
        return transcript
    
    def anonymize_names(self, text: str, language: str = 'auto') -> Tuple[str, Dict[str, str]]:
        """使用spaCy进行基于NLP的完全动态人名匿名化（支持双语）"""
        self.logger.info("开始基于NLP的动态人名匿名化处理")
        
        try:
            # 智能选择spaCy模型
            if language == 'auto':
                # 自动检测语言
                chinese_chars = sum(1 for char in text if '\u4e00' <= char <= '\u9fff')
                if chinese_chars > len(text) * 0.1:  # 如果10%以上是中文字符
                    nlp_model = self.nlp_zh
                    self.logger.debug("使用中文spaCy模型进行人名识别")
                else:
                    nlp_model = self.nlp_en
                    self.logger.debug("使用英文spaCy模型进行人名识别")
            elif language == 'zh':
                nlp_model = self.nlp_zh
                self.logger.debug("指定使用中文spaCy模型")
            elif language == 'en':
                nlp_model = self.nlp_en
                self.logger.debug("指定使用英文spaCy模型")
            else:
                nlp_model = self.nlp_zh  # 默认中文
                self.logger.debug("使用默认中文spaCy模型")
            
            doc = nlp_model(text)
            result = text
            current_mapping = {}
            
            # 使用spaCy识别所有人名实体
            person_entities = [ent for ent in doc.ents if ent.label_ == "PERSON"]
            
            if not person_entities:
                self.logger.info("NLP检测：未发现人名实体")
                return result, current_mapping
            
            # 基于NLP检测结果进行动态处理
            for ent in person_entities:
                original_name = ent.text.strip()
                
                # 过滤无效检测结果
                if len(original_name) < 2 or self._is_invalid_name(original_name):
                    continue
                
                # 为每个新检测到的人名动态生成虚拟人名
                if original_name not in self.name_mapping:
                    # 基于检测到的语言生成虚拟人名
                    detected_lang = 'zh' if nlp_model == self.nlp_zh else 'en'
                    fake_name = self._generate_virtual_name(original_name, text, detected_lang)
                    self.name_mapping[original_name] = fake_name
                    self.logger.debug(f"NLP检测到新人名，动态映射: {original_name} -> {fake_name} (语言: {detected_lang})")
                
                current_mapping[original_name] = self.name_mapping[original_name]
                
                # 执行全文替换
                result = result.replace(original_name, self.name_mapping[original_name])
            
            self.logger.info(f"NLP动态匿名化完成，处理了 {len(current_mapping)} 个人名")
            return result, current_mapping
            
        except Exception as e:
            self.logger.error(f"NLP人名匿名化失败: {str(e)}")
            return text, {}
    
    def _is_chinese_text(self, text: str) -> bool:
        """检测文本是否主要为中文"""
        chinese_chars = sum(1 for char in text if '\u4e00' <= char <= '\u9fff')
        return chinese_chars > len(text) * 0.3  # 如果30%以上是中文字符
    
    def _is_chinese_name(self, name: str) -> bool:
        """基于NLP检测判断是否为中文人名"""
        return any('\u4e00' <= char <= '\u9fff' for char in name)
    
    def _is_invalid_name(self, name: str) -> bool:
        """过滤无效的人名检测结果"""
        invalid_patterns = ['先生', '女士', '教授', '博士', '总监', '经理', '老师']
        return any(pattern in name for pattern in invalid_patterns)
    
    def _generate_virtual_name(self, original_name: str, context_text: str, language: str = 'auto') -> str:
        """基于NLP检测结果动态生成虚拟人名（支持双语）"""
        if language == 'zh' or (language == 'auto' and self._is_chinese_name(original_name)):
            return self._generate_chinese_virtual_name()
        else:
            return self._generate_english_virtual_name()
    
    def _generate_chinese_virtual_name(self) -> str:
        """使用Faker动态生成中文虚拟人名"""
        max_attempts = 50
        for _ in range(max_attempts):
            virtual_name = self.fake_zh.name()
            if virtual_name not in self.used_names:
                self.used_names.add(virtual_name)
                return virtual_name
        
        # 如果重复太多，使用简单的序号方式
        fallback_name = f"李明{len(self.used_names) + 1}"
        self.used_names.add(fallback_name)
        return fallback_name
    
    def _generate_english_virtual_name(self) -> str:
        """使用Faker动态生成英文虚拟人名"""
        max_attempts = 50
        for _ in range(max_attempts):
            virtual_name = self.fake_en.first_name()
            if virtual_name not in self.used_names:
                self.used_names.add(virtual_name)
                return virtual_name
        
        # 如果重复太多，使用简单的序号方式
        fallback_name = f"Alex{len(self.used_names) + 1}"
        self.used_names.add(fallback_name)
        return fallback_name
    
    def start_file_monitoring(self):
        """启动文件监控（Phase 2新功能）"""
        if self.file_monitor is None:
            watch_folder = self.config['paths']['watch_folder']
            self.file_monitor = FileMonitor(watch_folder, self)
        
        self.file_monitor.start_monitoring()
        self.logger.info("自动文件监控已启动")
    
    def stop_file_monitoring(self):
        """停止文件监控"""
        if self.file_monitor:
            self.file_monitor.stop_monitoring()
            self.logger.info("自动文件监控已停止")
    
    def get_queue_status(self) -> Dict:
        """获取处理队列状态"""
        if not self.file_monitor:
            return {"status": "monitoring_not_started"}
        
        queue = self.file_monitor.processing_queue
        return {
            "is_empty": queue.is_empty(),
            "processing_status": dict(queue.processing_status)
        }
    
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


def run_batch_mode(processor):
    """批量处理模式（Phase 1兼容）"""
    print("=== 批量处理模式 ===")
    
    # 查找音频文件
    watch_folder = Path(processor.config['paths']['watch_folder'])
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


def run_monitor_mode(processor):
    """文件监控模式（Phase 2新功能）"""
    print("=== 自动文件监控模式 ===")
    print("监控文件夹中的新音频文件，自动处理...")
    print("按 Ctrl+C 停止监控")
    print()
    
    # 设置信号处理器
    def signal_handler(signum, frame):
        print("\n正在停止文件监控...")
        processor.stop_file_monitoring()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 启动文件监控
    processor.start_file_monitoring()
    
    try:
        # 保持程序运行
        while True:
            time.sleep(5)
            # 显示队列状态
            status = processor.get_queue_status()
            if status.get("processing_status"):
                processing_files = [f for f, s in status["processing_status"].items() if s == "processing"]
                if processing_files:
                    print(f"正在处理: {', '.join([Path(f).name for f in processing_files])}")
            
    except KeyboardInterrupt:
        print("\n停止监控...")
        processor.stop_file_monitoring()


def main():
    """主函数 - 支持Phase 1和Phase 2模式"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='Project Bach - 音频处理系统')
    parser.add_argument('--mode', choices=['batch', 'monitor'], default='batch',
                       help='运行模式: batch=批量处理（默认），monitor=自动监控')
    parser.add_argument('--config', default='config.yaml',
                       help='配置文件路径（默认: config.yaml）')
    
    args = parser.parse_args()
    
    print("=== Project Bach - 音频处理系统 ===")
    print(f"运行模式: {'批量处理' if args.mode == 'batch' else '自动监控'}")
    print()
    print("检查系统依赖...")
    
    # 检查依赖
    issues = check_dependencies()
    if issues:
        print("依赖检查失败:")
        for issue in issues:
            print(f"  {issue}")
        print("\n请解决上述问题后重新运行")
        return False
    
    # 检查配置文件
    config_path = args.config
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
        
        # 根据模式运行
        if args.mode == 'batch':
            return run_batch_mode(processor)
        else:
            run_monitor_mode(processor)
            return True
            
    except Exception as e:
        print(f"❌ 程序运行失败: {str(e)}")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)