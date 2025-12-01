'''
Author: 汪培良 rick_wang@yunquna.com
Date: 2025-11-30 19:05:47
LastEditors: 汪培良 rick_wang@yunquna.com
LastEditTime: 2025-12-01 10:10:11
FilePath: /RAG_service/chain/ext_template.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
from chain.custom_prompt_template import CustomPromptTemplate, PersonInfo
from optparse import Values
from pydantic import BaseModel, Field, field_validator
from typing import Dict, List, Any, Optional
import json
from datetime import datetime


class AdvancedPersonInfoPromptTemplate(CustomPromptTemplate):
    """
    高级人员信息提示模板类
    支持更多工程化功能
    """

    template_version:str = Field(default="1.0.0", description="模版版本号")
    supported_languages: List[str] = Field(default=["chinese", "english"], description="支持的语言列表")
    enable_cache: bool = Field(default=True, description="是否启用缓存")
    cache_ttl: int = Field(default=3600, description="缓存过期时间（秒）")

    def format_with_validation(self, **kwargs:Any) -> str:
        """带验证的格式化方法"""
        self._validate_inputs(**kwargs)
        return super().format(**kwargs)

    def _validate_inputs(self, **kwargs:Any):
        """验证输入参数"""
        person_info = kwargs.get("person_info")
        analysis_type = kwargs.get("analysis_type")

        if not person_info:
            raise ValueError("person_info 参数不能为空")
        
        valid_analysis_types = ["basic", "career", "skills", "comprehensive"]
        if analysis_type not in valid_analysis_types:
            raise ValueError(f"analysis_type 参数无效，有效值包括：{valid_analysis_types}")

        if self.output_language not in self.supported_languages:
            raise ValueError(f"output_language 参数无效，有效值包括：{self.supported_languages}")

    def get_template_metadata(self) -> Dict[str,Any]:
        """获取模版元数据"""
        return {
            "version": self.template_version,
            "type": self.template_type,
            "supported_languages": self.supported_languages,
            "features":{
                "skills_analysis": self.include_skills_analysis,
                "career_advice": self.include_career_advice,
                "caching": self.enable_cache
            },
            "input_variables": self.input_variables
        }