"""
国标标准匹配器
从国标PDF中提取标准，并与分析项目进行匹配
"""

import logging
import pypdfium2
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from ..models.compliance import StandardRequirement
from config import settings

logger = logging.getLogger(__name__)


class StandardMatcher:
    """国标标准匹配器"""

    def __init__(self, retrieval_service=None):
        """
        初始化匹配器

        Args:
            retrieval_service: 向量检索服务（可选，用于智能匹配）
        """
        self.retrieval_service = retrieval_service

        # 常见的分析项目与国标映射
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
            "固体废物": {
                "standard_code": "GB 34330-2017",
                "standard_name": "固体废物鉴别标准 通则",
            },
        }

        # 浸出毒性限值（部分常见物质）
        self.leaching_limits = {
            "总汞": {"limit": 0.1, "unit": "mg/L", "method": "GB 5085.3-2007"},
            "总镉": {"limit": 1.0, "unit": "mg/L", "method": "GB 5085.3-2007"},
            "总铬": {"limit": 15.0, "unit": "mg/L", "method": "GB 5085.3-2007"},
            "六价铬": {"limit": 5.0, "unit": "mg/L", "method": "GB 5085.3-2007"},
            "总铜": {"limit": 100.0, "unit": "mg/L", "method": "GB 5085.3-2007"},
            "总锌": {"limit": 100.0, "unit": "mg/L", "method": "GB 5085.3-2007"},
            "总铍": {"limit": 0.1, "unit": "mg/L", "method": "GB 5085.3-2007"},
            "总钡": {"limit": 100.0, "unit": "mg/L", "method": "GB 5085.3-2007"},
            "总镍": {"limit": 5.0, "unit": "mg/L", "method": "GB 5085.3-2007"},
            "总砷": {"limit": 5.0, "unit": "mg/L", "method": "GB 5085.3-2007"},
            "无机氟化物": {"limit": 100.0, "unit": "mg/L", "method": "GB 5085.3-2007"},
            "氰化物": {"limit": 5.0, "unit": "mg/L", "method": "GB 5085.3-2007"},
        }

        # 水质标准（GB 3838-2002）
        self.water_quality_limits = {
            "化学需氧量": {"limit": 20.0, "unit": "mg/L", "method": "GB 3838-2002"},
            "悬浮物": {"limit": 25.0, "unit": "mg/L", "method": "GB 3838-2002"},
            "总磷": {"limit": 0.2, "unit": "mg/L", "method": "GB 3838-2002"},
            "氨氮": {"limit": 1.0, "unit": "mg/L", "method": "GB 3838-2002"},
            "总氮": {"limit": 1.0, "unit": "mg/L", "method": "GB 3838-2002"},
        }

        # 毒性物质含量限值
        self.toxic_substance_limits = {
            "汞": {"limit": 0.1, "unit": "mg/kg", "method": "GB 5085.6-2017"},
            "铅": {"limit": 5.0, "unit": "mg/kg", "method": "GB 5085.6-2017"},
            "镉": {"limit": 1.0, "unit": "mg/kg", "method": "GB 5085.6-2017"},
            "总铬": {"limit": 15.0, "unit": "mg/kg", "method": "GB 5085.6-2017"},
            "六价铬": {"limit": 5.0, "unit": "mg/kg", "method": "GB 5085.6-2017"},
            "铜": {"limit": 100.0, "unit": "mg/kg", "method": "GB 5085.6-2017"},
            "锌": {"limit": 100.0, "unit": "mg/kg", "method": "GB 5085.6-2017"},
            "镍": {"limit": 5.0, "unit": "mg/kg", "method": "GB 5085.6-2017"},
            "砷": {"limit": 5.0, "unit": "mg/kg", "method": "GB 5085.6-2017"},
        }

    async def match_standard(
        self,
        project_name: str,
        method_basis: Optional[str] = None,
        gb_directory: str = "src/pdfs/GB",
    ) -> Optional[StandardRequirement]:
        """
        为分析项目匹配国标标准

        Args:
            project_name: 分析项目名称
            method_basis: 方法依据
            gb_directory: 国标目录路径

        Returns:
            匹配的标准要求，如果没有匹配则返回None
        """
        # 1. 尝试直接映射
        if project_name in self.project_to_standard_map:
            standard_info = self.project_to_standard_map[project_name]
            return StandardRequirement(**standard_info)

        # 2. 尝试从方法依据中提取标准编号
        if method_basis:
            standard_code = self._extract_standard_code(method_basis)
            if standard_code:
                standard_info = self._find_standard_by_code(standard_code, gb_directory)
                if standard_info:
                    return standard_info

        # 3. 检查浸出毒性
        for substance, limit_info in self.leaching_limits.items():
            if substance in project_name or project_name in substance:
                return StandardRequirement(
                    standard_code=limit_info["method"],
                    standard_name="危险废物鉴别标准 浸出毒性鉴别",
                    indicator=substance,
                    limit_value=limit_info["limit"],
                    limit_type="≤",
                    unit=limit_info["unit"],
                    description=f"{substance}浸出浓度≤{limit_info['limit']}{limit_info['unit']}",
                )

        # 4. 检查毒性物质含量
        for substance, limit_info in self.toxic_substance_limits.items():
            if substance in project_name or project_name in substance:
                return StandardRequirement(
                    standard_code=limit_info["method"],
                    standard_name="危险废物鉴别标准 毒性物质含量鉴别",
                    indicator=substance,
                    limit_value=limit_info["limit"],
                    limit_type="≤",
                    unit=limit_info["unit"],
                    description=f"{substance}含量≤{limit_info['limit']}{limit_info['unit']}",
                )

        # 5. 检查水质标准（常规检测）
        for substance, limit_info in self.water_quality_limits.items():
            if substance in project_name or project_name in substance:
                return StandardRequirement(
                    standard_code=limit_info["method"],
                    standard_name="地表水环境质量标准",
                    indicator=substance,
                    limit_value=limit_info["limit"],
                    limit_type="≤",
                    unit=limit_info["unit"],
                    description=f"{substance}浓度≤{limit_info['limit']}{limit_info['unit']}",
                )

        # 4. 检查毒性物质含量
        for substance, limit_info in self.toxic_substance_limits.items():
            if substance in project_name or project_name in substance:
                return StandardRequirement(
                    standard_code=limit_info["method"],
                    standard_name="危险废物鉴别标准 毒性物质含量鉴别",
                    indicator=substance,
                    limit_value=limit_info["limit"],
                    limit_type="≤",
                    unit=limit_info["unit"],
                    description=f"{substance}含量≤{limit_info['limit']}{limit_info['unit']}",
                )

        # 5. 使用向量检索（如果可用）
        if self.retrieval_service:
            return await self._match_by_vector_retrieval(project_name)

        logger.warning(f"未找到匹配的国标标准: {project_name}")
        return None

    def _extract_standard_code(self, method_basis: str) -> Optional[str]:
        """从方法依据中提取标准编号"""
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

    def _find_standard_by_code(
        self, standard_code: str, gb_directory: str
    ) -> Optional[Dict]:
        """根据标准编号在国标目录中查找"""
        gb_dir = Path(gb_directory)
        if not gb_dir.exists():
            logger.warning(f"国标目录不存在: {gb_directory}")
            return None

        # 在文件名中搜索
        for pdf_file in gb_dir.glob("*.pdf"):
            if standard_code.replace(" ", "").replace("T", "") in pdf_file.stem.replace(
                " ", ""
            ):
                # 解析PDF提取标准内容
                standard_info = self._extract_standard_from_pdf(pdf_file)
                if standard_info:
                    return standard_info

        return None

    def _extract_standard_from_pdf(self, pdf_path: str) -> Optional[Dict]:
        """从PDF文件中提取标准信息"""
        try:
            pdf = pypdfium2.PdfDocument(pdf_path)
            text = ""
            for page in pdf:
                textpage = page.get_textpage()
                text += textpage.get_text_range()
            pdf.close()

            # 提取标准编号和名称
            import re

            standard_code_match = re.search(r"(GB\s*[\d.T]+\-*\d{4})", text)
            standard_name_match = re.search(r"(危险废物鉴别标准\s*[^0-9]+)", text)

            # 查找鉴别标准或限值
            limit_match = re.search(r"鉴别标准[：:：]?\s*([^\n]+)", text)

            standard_info = {
                "standard_code": standard_code_match.group(1)
                if standard_code_match
                else pdf_path.stem,
                "standard_name": standard_name_match.group(1)
                if standard_name_match
                else pdf_path.stem,
                "indicator": "待定",
                "description": limit_match.group(1) if limit_match else None,
                "source_document": pdf_path,
            }

            return standard_info

        except Exception as e:
            logger.error(f"解析国标PDF失败: {pdf_path}, error={e}")
            return None

    def _match_by_vector_retrieval(
        self, project_name: str
    ) -> Optional[StandardRequirement]:
        """使用向量检索匹配标准"""
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

    def batch_load_standards(
        self, gb_directory: str = "src/pdfs/GB"
    ) -> List[StandardRequirement]:
        """
        批量加载国标目录中的所有标准

        Args:
            gb_directory: 国标目录路径

        Returns:
            标准要求列表
        """
        standards = []
        gb_dir = Path(gb_directory)

        if not gb_dir.exists():
            logger.warning(f"国标目录不存在: {gb_directory}")
            return standards

        for pdf_file in gb_dir.glob("*.pdf"):
            standard_info = self._extract_standard_from_pdf(str(pdf_file))
            if standard_info:
                standards.append(StandardRequirement(**standard_info))
                logger.info(f"加载标准: {standard_info['standard_code']}")

        return standards
