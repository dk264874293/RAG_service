"""
标准匹配技能
负责为分析项目匹配国标标准，支持多种匹配策略
"""

import logging
from typing import Dict, Any, Optional, Tuple
from pathlib import Path

from src.models.compliance import StandardRequirement
from src.vector.retrieval_service import RetrievalService

logger = logging.getLogger(__name__)


class StandardMatchingSkill:
    """
    标准匹配技能
    使用多种策略匹配国标标准
    """

    def __init__(self, retrieval_service: Optional[RetrievalService] = None):
        """
        初始化标准匹配技能

        Args:
            retrieval_service: 向量检索服务（可选，用于智能匹配）
        """
        self.retrieval_service = retrieval_service

        # 预定义的项目到标准映射
        self.project_to_standard_map = {
            "腐蚀性": {
                "standard_code": "GB 5085.1-2007",
                "standard_name": "危险废物鉴别标准 腐蚀性鉴别",
                "indicator": "pH",
                "limit_type": "范围",
                "limit_range": (2.0, 12.5),
                "unit": None,
                "description": "pH值≤2.0或≥12.5",
            },
            "急性毒性": {
                "standard_code": "GB 5085.2-2007",
                "standard_name": "危险废物鉴别标准 急性毒性初筛",
            },
            "浸出毒性": {
                "standard_code": "GB 5085.3-2007",
                "standard_name": "危险废物鉴别标准 浸出毒性鉴别",
            },
            "易燃性": {
                "standard_code": "GB 5085.4-2007",
                "standard_name": "危险废物鉴别标准 易燃性鉴别",
            },
            "反应性": {
                "standard_code": "GB 5085.5-2007",
                "standard_name": "危险废物鉴别标准 反应性鉴别",
            },
            "毒性物质含量": {
                "standard_code": "GB 5085.6-2017",
                "standard_name": "危险废物鉴别标准 毒性物质含量鉴别",
            },
        }

        # 浸出毒性限值
        self.leaching_limits = {
            "总汞": {"limit": 0.1, "unit": "mg/L"},
            "总镉": {"limit": 1.0, "unit": "mg/L"},
            "总铬": {"limit": 15.0, "unit": "mg/L"},
            "六价铬": {"limit": 5.0, "unit": "mg/L"},
            "总铜": {"limit": 100.0, "unit": "mg/L"},
            "总锌": {"limit": 100.0, "unit": "mg/L"},
            "总铍": {"limit": 0.1, "unit": "mg/L"},
            "总钡": {"limit": 100.0, "unit": "mg/L"},
            "总镍": {"limit": 5.0, "unit": "mg/L"},
            "总砷": {"limit": 5.0, "unit": "mg/L"},
            "无机氟化物": {"limit": 100.0, "unit": "mg/L"},
            "氰化物": {"limit": 5.0, "unit": "mg/L"},
        }

        # 水质标准（GB 3838-2002）
        self.water_quality_limits = {
            "化学需氧量": {"limit": 20.0, "unit": "mg/L"},
            "悬浮物": {"limit": 25.0, "unit": "mg/L"},
            "总磷": {"limit": 0.2, "unit": "mg/L"},
            "氨氮": {"limit": 1.0, "unit": "mg/L"},
            "总氮": {"limit": 1.0, "unit": "mg/L"},
        }

        # 毒性物质含量限值
        self.toxic_substance_limits = {
            "汞": {"limit": 0.1, "unit": "mg/kg"},
            "铅": {"limit": 5.0, "unit": "mg/kg"},
            "镉": {"limit": 1.0, "unit": "mg/kg"},
            "总铬": {"limit": 15.0, "unit": "mg/kg"},
            "六价铬": {"limit": 5.0, "unit": "mg/kg"},
            "铜": {"limit": 100.0, "unit": "mg/kg"},
            "锌": {"limit": 100.0, "unit": "mg/kg"},
            "镍": {"limit": 5.0, "unit": "mg/kg"},
            "砷": {"limit": 5.0, "unit": "mg/kg"},
        }

    def match_standard(
        self,
        project_name: str,
        method_basis: Optional[str] = None,
        use_vector_retrieval: bool = True,
    ) -> Optional[StandardRequirement]:
        """
        为分析项目匹配国标标准

        Args:
            project_name: 分析项目名称
            method_basis: 方法依据
            use_vector_retrieval: 是否使用向量检索

        Returns:
            匹配的标准要求，如果没有匹配则返回None
        """
        # 策略1: 直接映射
        if project_name in self.project_to_standard_map:
            standard_info = self.project_to_standard_map[project_name]
            return StandardRequirement(**standard_info)

        # 策略2: 从方法依据中提取标准编号
        if method_basis:
            standard_code = self._extract_standard_code(method_basis)
            if standard_code:
                standard_info = self._find_standard_by_code(standard_code)
                if standard_info:
                    return StandardRequirement(**standard_info)

        # 策略3: 检查浸出毒性
        for substance, limit_info in self.leaching_limits.items():
            if substance in project_name or project_name in substance:
                return StandardRequirement(
                    standard_code="GB 5085.3-2007",
                    standard_name="危险废物鉴别标准 浸出毒性鉴别",
                    indicator=substance,
                    limit_value=limit_info["limit"],
                    limit_type="≤",
                    unit=limit_info["unit"],
                    description=f"{substance}浸出浓度≤{limit_info['limit']}{limit_info['unit']}",
                )

        # 策略4: 检查毒性物质含量
        for substance, limit_info in self.toxic_substance_limits.items():
            if substance in project_name or project_name in substance:
                return StandardRequirement(
                    standard_code="GB 5085.6-2017",
                    standard_name="危险废物鉴别标准 毒性物质含量鉴别",
                    indicator=substance,
                    limit_value=limit_info["limit"],
                    limit_type="≤",
                    unit=limit_info["unit"],
                    description=f"{substance}含量≤{limit_info['limit']}{limit_info['unit']}",
                )

        # 策略5: 检查水质标准
        for substance, limit_info in self.water_quality_limits.items():
            if substance in project_name or project_name in substance:
                return StandardRequirement(
                    standard_code="GB 3838-2002",
                    standard_name="地表水环境质量标准",
                    indicator=substance,
                    limit_value=limit_info["limit"],
                    limit_type="≤",
                    unit=limit_info["unit"],
                    description=f"{substance}浓度≤{limit_info['limit']}{limit_info['unit']}",
                )

        # 策略6: 使用向量检索（如果可用）
        if use_vector_retrieval and self.retrieval_service:
            return self._match_by_vector_retrieval(project_name)

        logger.warning(f"未找到匹配的国标标准: {project_name}")
        return None

    def _extract_standard_code(self, method_basis: str) -> Optional[str]:
        """
        从方法依据中提取标准编号

        Args:
            method_basis: 方法依据文本

        Returns:
            标准编号，如果没有找到则返回None
        """
        import re

        patterns = [
            r"(GB\s*\d+\.\d+-\d{4})",
            r"(GB/T\s*\d+-\d{4})",
            r"(HJ\s*\d+-\d{4})",
            r"(GB\s*\d+-\d{4})",
        ]

        for pattern in patterns:
            match = re.search(pattern, method_basis)
            if match:
                return match.group(1)

        return None

    def _find_standard_by_code(self, standard_code: str) -> Optional[Dict[str, Any]]:
        """
        根据标准编号查找标准信息

        Args:
            standard_code: 标准编号

        Returns:
            标准信息字典，如果没有找到则返回None
        """
        # 这里可以扩展为从数据库或文件系统查找
        # 目前简化为返回空
        return None

    def _match_by_vector_retrieval(
        self, project_name: str
    ) -> Optional[StandardRequirement]:
        """
        使用向量检索匹配标准

        Args:
            project_name: 分析项目名称

        Returns:
            匹配的标准要求，如果没有匹配则返回None
        """
        if not self.retrieval_service:
            return None

        try:
            # 构造查询
            query = f"{project_name} 国标标准 限值 鉴别"

            # 检索相关标准
            results = self.retrieval_service.search(query, k=3)

            if results and len(results) > 0:
                best_match = results[0]

                # 从检索结果中提取标准信息
                return StandardRequirement(
                    standard_code=best_match.metadata.get("standard_code", "未知"),
                    standard_name=best_match.metadata.get("standard_name", "未知"),
                    indicator=project_name,
                    limit_value=best_match.metadata.get("limit_value"),
                    limit_type=best_match.metadata.get("limit_type"),
                    unit=best_match.metadata.get("unit"),
                    description=best_match.page_content[:200],
                    source_document=best_match.metadata.get("source"),
                )

        except Exception as e:
            logger.error(f"向量检索匹配失败: {e}")

        return None

    def check_compliance(
        self,
        measured_value: float,
        standard: StandardRequirement,
        unit: Optional[str] = None,
    ) -> Tuple[bool, Optional[str]]:
        """
        检查测量值是否符合标准

        Args:
            measured_value: 测量值
            standard: 标准要求
            unit: 测量值单位

        Returns:
            (是否合规, 违规原因)
        """
        # 单位一致性检查（简单实现）
        if unit and standard.unit and unit != standard.unit:
            logger.warning(f"单位不一致: 测量单位={unit}, 标准单位={standard.unit}")

        # 检查限值类型
        if standard.limit_type == "≤":
            if measured_value <= standard.limit_value:
                return True, None
            else:
                return (
                    False,
                    f"测量值{measured_value}{unit}超过限值{standard.limit_value}{standard.unit}",
                )

        elif standard.limit_type == "≥":
            if measured_value >= standard.limit_value:
                return True, None
            else:
                return (
                    False,
                    f"测量值{measured_value}{unit}低于限值{standard.limit_value}{standard.unit}",
                )

        elif standard.limit_type == "范围" and standard.limit_range:
            min_val, max_val = standard.limit_range
            if min_val <= measured_value <= max_val:
                return True, None
            else:
                return (
                    False,
                    f"测量值{measured_value}{unit}不在标准范围{min_val}-{max_val}内",
                )

        elif standard.limit_value is not None:
            if measured_value <= standard.limit_value:
                return True, None
            else:
                return (
                    False,
                    f"测量值{measured_value}{unit}超过限值{standard.limit_value}{standard.unit}",
                )

        # 无法确定合规性
        return None, f"无法确定合规性，缺少标准限值信息"
