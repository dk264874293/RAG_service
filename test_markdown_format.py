import sys
sys.path.insert(0, 'src')
from extractor.ocr_module.core.html_to_markdown import convert_html_table_to_markdown

# 测试简单的表格
html = """<table border=1>
<tr><th>姓名</th><th>年龄</th></tr>
<tr><td>张三</td><td>25</td></tr>
</table>"""

result = convert_html_table_to_markdown(html)

print("=== 输入 HTML ===")
print(html)
print("\n=== 输出 Markdown ===")
print(result)
print("\n=== repr 格式 ===")
print(repr(result))
print("\n=== 验证标准 Markdown 表格格式 ===")
# 标准格式：
# | 标题1 | 标题2 |
# |---|---|
# | 数据1 | 数据2 |

lines = result.split('\n')
print("行数:", len(lines))
for i, line in enumerate(lines):
    print(f"行 {i}: {repr(line)}")
