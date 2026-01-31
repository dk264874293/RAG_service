# 环境监测数据合规性检查系统 - 最终使用指南

## 快速开始

### 1. 启动服务
```bash
python3 main.py
```
服务将在 http://localhost:8000 上运行

---

## 2. 准备测试文件

### 测试文件位置
- 测试PDF: `src/pdfs/test/25CF0065分析.pdf`
- 国标目录: `src/pdfs/GB/` (52个标准文件)

---

## 3. 使用API进行合规性检查

### 方式1: 文件路径检查

```bash
curl -X POST "http://localhost:8000/api/compliance/check-by-path" \
  -H "Content-Type: application/json" \
  -d '{
    "test_pdf_path": "src/pdfs/test/25CF0065分析.pdf",
    "enable_formula_calculation": true,
    "enable_vector_retrieval": true
  }'
```

### 方式2: 上传文件检查

```bash
curl -X POST "http://localhost:8000/api/compliance/check" \
  -F "file=@src/pdfs/test/25CF0065分析.pdf" \
  -F "enable_formula_calculation=true" \
  -F "enable_vector_retrieval=true"
```

---

## 4. 查看API文档

访问 Swagger UI: http://localhost:8000/docs

---

## 功能说明

### 支持的检测项目

#### 危险废物鉴别 (✅ 完全支持)
- **腐蚀性**: GB 5085.1-2007 (pH≤2.0或≥12.5)
- **浸出毒性**: GB 5085.3-2007 (汞、镉、铬、铜、锌、镍、砷等11种物质）
- **毒性物质含量**: GB 5085.6-2017

#### 水质常规监测 (✅ 部分支持)
- **化学需氧量(COD)**: GB 3838-2002 (≤20.0 mg/L)
- **悬浮物**: GB 3838-2002 (≤25.0 mg/L)
- **总磷**: GB 3838-2002 (≤0.2 mg/L)
- **氨氮**: GB 3838-2002 (≤1.0 mg/L)
- **总氮**: GB 3838-2002 (≤1.0 mg/L)

### 核心功能

#### 1. 数据提取 ✅
- 自动识别分析项目
- 提取方法依据 (GB/T、HJ标准编号）
- 提取计算公式 (支持中文符号)
- 提取测量值和单位

#### 2. 标准匹配 ✅
- 规则匹配：预定义项目-标准映射
- 向量检索：使用FAISS+DashScope智能匹配
- 支持多种限值类型 (≤、≥、范围)

#### 3. 公式计算 ✅
- 公式标准化 (×→*、÷→/、10^6→10**6)
- 参数解析 (从表格中提取数值)
- 安全计算 (白名单机制)
- 结果验证 (对比计算值和测量值)

#### 4. 合规性判断 ✅
- 支持多种限值类型
- 单位一致性检查
- 详细的违规原因说明

### API响应示例

```json
{
  "request_id": "uuid",
  "test_file": "src/pdfs/test/25CF0065分析.pdf",
  "total_items": 15,
  "compliant_count": 10,
  "non_compliant_count": 3,
  "unknown_count": 2,
  "check_results": [
    {
      "analysis_item": {
        "project_name": "总汞",
        "method_basis": "GB/T 15555.1-1995",
        "measured_value": 0.08
        "unit": "mg/L"
      },
      "matched_standard": {
        "standard_code": "GB 5085.3-2007",
        "standard_name": "危险废物鉴别标准 浸出毒性鉴别",
        "limit_value": 0.1,
        "limit_type": "≤",
        "unit": "mg/L"
      },
      "is_compliant": true,
      "violation_reason": null,
      "match_confidence": 0.9
    }
  ],
  "summary": "合规10项, 不合规3项, 无法确定2项"
}
```

---

## 故障排查

### 常见问题

#### 问题：检查结果全为"未知状态"
**原因**:
1. 未匹配到标准：项目名称或方法依据不在标准库中
2. 测量值未提取：表格格式不标准或参数识别失败
3. 公式计算失败：公式包含非法字符或格式错误

**解决方法**:
1. 查看检查详情，确认是哪个环节失败
2. 查看对应的标准是否存在于国标目录
3. 修改标准库添加缺失的标准

#### 问题：向量检索失败
**现象**: `RuntimeWarning: coroutine 'RetrievalService.search' was never awaited`

**解决方法**: 已在v1.1版本中修复

---

## 性能优化建议

### 提高检查速度
1. 使用`enable_vector_retrieval=False` 只使用规则匹配（更快）
2. 使用`enable_formula_calculation=False` 禁用公式计算（如果不需要）

### 提高匹配准确率
1. 确保项目名称使用标准术语
2. 检查方法依据的标准编号是否准确

### 批量处理建议
1. 一次提交多个PDF文件进行检查
2. 使用异步API并发调用（需要前端支持）

---

## 系统架构

```
用户上传PDF
    ↓
FastAPI路由 (src/api/routes/compliance.py)
    ↓
合规性检查服务 (src/service/compliance_service.py)
    ↓
数据提取器 (src/extractor/analysis_data_extractor.py)
    ↓
标准匹配器 (src/compliance/standard_matcher.py)
    ↓
公式计算器 (src/compliance/formula_calculator.py)
    ↓
合规性检查响应 (src/models/compliance.py)
    ↓
返回详细报告
```

---

## 文档索引

| 文档 | 说明 |
|-----|------|
| COMPLIANCE_README.md | 详细使用说明、API文档、支持的标准 |
| IMPLEMENTATION_SUMMARY.md | 实现总结、文件清单、系统特点 |
| EVALUATION_REPORT.md | 评估报告、问题分析、优化建议 |
| FIX_REPORT.md | 修复报告、验证结果、最终指南 |
| QUICKSTART.md | 快速开始指南（本文档） |

---

## 技术支持

- 查看 `/docs` 端点文档：http://localhost:8000/docs
- 查看源代码注释：所有核心模块都有详细的docstring
- 运行测试脚本：`test_compliance.py`、`test_compliance_api.py`

---

**版本**: 1.1.0
**更新日期**: 2026-01-29
