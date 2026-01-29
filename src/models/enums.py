'''
Author: 汪培良 rick_wang@yunquna.com
Date: 2026-01-04 20:46:39
LastEditors: 汪培良 rick_wang@yunquna.com
LastEditTime: 2026-01-06 13:05:13
FilePath: /RAG_agent/src/models/enums.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
from enum import StrEnum

# from core.workflow.enums import NodeType


class CreatorUserRole(StrEnum):
    ACCOUNT = "account"
    END_USER = "end_user"


class UserFrom(StrEnum):
    ACCOUNT = "account"
    END_USER = "end-user"


class WorkflowRunTriggeredFrom(StrEnum):
    DEBUGGING = "debugging"
    APP_RUN = "app-run"  # webapp / service api
    RAG_PIPELINE_RUN = "rag-pipeline-run"
    RAG_PIPELINE_DEBUGGING = "rag-pipeline-debugging"
    WEBHOOK = "webhook"
    SCHEDULE = "schedule"
    PLUGIN = "plugin"


class DraftVariableType(StrEnum):
    # node means that the correspond variable
    NODE = "node"
    SYS = "sys"
    CONVERSATION = "conversation"


class MessageStatus(StrEnum):
    """
    Message Status Enum
    """

    NORMAL = "normal"
    ERROR = "error"


class ExecutionOffLoadType(StrEnum):
    INPUTS = "inputs"
    PROCESS_DATA = "process_data"
    OUTPUTS = "outputs"


class WorkflowTriggerStatus(StrEnum):
    """Workflow Trigger Execution Status"""

    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    PAUSED = "paused"
    FAILED = "failed"
    RATE_LIMITED = "rate_limited"
    RETRYING = "retrying"


class AppTriggerStatus(StrEnum):
    """App Trigger Status Enum"""

    ENABLED = "enabled"
    DISABLED = "disabled"
    UNAUTHORIZED = "unauthorized"
    RATE_LIMITED = "rate_limited"



