#!/usr/bin/env python3
"""
测试 Markdown 表格渲染格式是否正确
"""
import sys
sys.path.insert(0, 'src')

from extractor.ocr_module.core.html_to_markdown import convert_html_table_to_markdown

# 测试数据
test_cases = [
    {
        "name": "简单表格",
        "html": """<table>
<tr><th>姓名</th><th>年龄</th></tr>
<tr><td>张三</td><td>25</td></tr>
</table>"""
    },
    {
        "name": "实际 OCR 数据",
        "html": """<table border=1 style='margin: auto;'>
<tr><td style='text-align: center;'>委托单位</td><td colspan="2">重庆市铜梁区</td></tr>
<tr><td>B-0111</td><td>地表水</td><td>五日生化需氧量</td></tr>
</table>"""
    }
]

print("="*70)
print("Markdown 表格渲染格式测试")
print("="*70)

for test in test_cases:
    print(f"\n【测试: {test['name']}】")
    print("-"*70)
    
    result = convert_html_table_to_markdown(test['html'])
    
    print("输出内容:")
    print(result)
    
    # 验证标准 Markdown 表格格式
    lines = result.strip().split('\n')
    
    # 检查是否有表格
    has_table = '|' in result and '---' in result
    
    # 检查格式是否标准
    # 标准: | 标题1 | 标题2 |
    #       |---|---|
    is_standard = False
    if len(lines) >= 2:
        first_line = lines[0].strip()
        second_line = lines[1].strip()
        
        # 第一行应该以 | 开头和结尾
        if first_line.startswith('|') and first_line.endswith('|'):
            # 第二行应该包含分隔符
            if '|' in second_line and ('---' in second_line or '-' * 3 in second_line):
                is_standard = True
    
    print(f"\n验证结果:")
    print(f"  - 包含表格: {has_table}")
    print(f"  - 标准格式: {is_standard}")
    
    if has_table and is_standard:
        print(f"  ✅ 可以被正确渲染")
    else:
        print(f"  ❌ 格式有问题")
    
    print()

print("="*70)
print("测试完成")
print("="*70)
print("\n说明:")
print("- 表格应该以 | 开头和结尾")
print("- 第二行应该包含分隔符 |---|---|")
print("- 符合标准 Markdown 表格格式的可以被渲染器正确显示")
