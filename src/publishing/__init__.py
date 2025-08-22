#!/usr/bin/env python3.11
"""
Project Bach 第五阶段 - GitHub自动发布模块
"""

from .github_publisher import GitHubPublisher, GitHubAPIRateLimiter
from .content_formatter import ContentFormatter
from .git_operations import GitOperations, GitWorkflowManager
from .template_engine import TemplateEngine
from .publishing_workflow import PublishingWorkflow
from .github_actions import GitHubActionsManager

__version__ = "1.0.0"
__author__ = "Project Bach"

__all__ = [
    'GitHubPublisher',
    'GitHubAPIRateLimiter',
    'ContentFormatter',
    'GitOperations',
    'GitWorkflowManager', 
    'TemplateEngine',
    'PublishingWorkflow',
    'GitHubActionsManager'
]