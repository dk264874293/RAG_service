"""
HTML 到 Markdown 转换工具

使用 html2text 库提供更强大的 HTML 到 Markdown 转换功能
"""

import re
from typing import Optional

# 尝试导入 html2text
html2text_available = False
try:
    import html2text

    html2text_available = True
    # 配置 html2text
    html2text_config = html2text.HTML2Text()
    html2text_config.body_width = 0  # 禁用自动换行
    html2text_config.ignore_links = False  # 保留链接
    html2text_config.ignore_images = False  # 保留图片
    html2text_config.ignore_tables = False  # 转换表格
    html2text_config.pad_tables = True  # 填充表格，生成标准 Markdown 格式
except ImportError:
    # 如果没有安装 html2text，使用备用方案
    from bs4 import BeautifulSoup

    pass


def convert_html_table_to_markdown(markdown_content: str) -> str:
    """
    将 HTML 内容（包括 table、div 等所有标签）转换为 Markdown 格式

    Args:
        markdown_content: 包含 HTML 标签的内容

    Returns:
        转换后的纯 Markdown 内容
    """
    if not markdown_content:
        return markdown_content

    # 使用 html2text 进行转换
    if html2text_available:
        return html2text_config.handle(markdown_content)
    else:
        # 备用方案：使用原有的 BeautifulSoup 实现
        return _legacy_convert_html_table_to_markdown(markdown_content)


def _legacy_convert_html_table_to_markdown(markdown_content: str) -> str:
    """
    遗留的 HTML table 转换实现（当 html2text 不可用时）
    """
    try:
        soup = BeautifulSoup(markdown_content, "html.parser")
    except ImportError:
        return _simple_html_to_markdown(markdown_content)

    converted_content = markdown_content

    for table in soup.find_all("table"):
        markdown_table = _table_to_markdown(table)
        converted_content = converted_content.replace(str(table), markdown_table)

    return converted_content


def _table_to_markdown(table) -> str:
    """
    遗留的表格转换实现
    """
    markdown_lines = []

    rows = table.find_all("tr")
    for row in rows:
        cells = []
        for cell in row.find_all(["td", "th"]):
            cell_text = cell.get_text(strip=True)
            colspan = int(cell.get("colspan", 1))
            cells.append(cell_text * colspan)

        markdown_lines.append("| " + " | ".join(cells) + " |")

    if markdown_lines:
        separator = "|" + "---|" * (len(markdown_lines[0].split("|")) - 1)
        markdown_lines.insert(1, separator)

    return "\n".join(markdown_lines)


def _simple_html_to_markdown(html_content: str) -> str:
    """
    简单的 HTML 到 Markdown 转换（当 html2text 和 BeautifulSoup 都不可用时）
    """
    table_pattern = r"<table[^>]*>(.*?)</table>"

    def replace_table(match):
        table_html = match.group(1)
        row_pattern = r"<tr[^>]*>(.*?)</tr>"
        rows = re.findall(row_pattern, table_html, re.DOTALL)

        if not rows:
            return match.group(0)

        markdown_rows = []
        for row in rows:
            cell_pattern = r"<t[dh][^>]*>(.*?)</t[dh]>"
            cells = re.findall(cell_pattern, row, re.DOTALL)

            markdown_cells = []
            for cell in cells:
                cell_text = re.sub(r"<[^>]+>", "", cell).strip()
                colspan_match = re.search(r'colspan="(\d+)"', cell)
                if colspan_match:
                    repeat = int(colspan_match.group(1))
                    cell_text = cell_text * repeat
                markdown_cells.append(cell_text)

            if markdown_cells:
                markdown_rows.append("| " + " | ".join(markdown_cells) + " |")

        if markdown_rows:
            separator = "|" + "---|" * (len(markdown_rows[0].split("|")) - 1)
            markdown_rows.insert(1, separator)
            return "\n".join(markdown_rows)

        return match.group(0)

    return re.sub(table_pattern, replace_table, html_content, flags=re.DOTALL)


def get_conversion_engine() -> str:
    """
    获取当前使用的转换引擎

    Returns:
        转换引擎名称
    """
    if html2text_available:
        return f"html2text v{html2text.__version__}"
    else:
        return "legacy converter"


if __name__ == "__main__":
    print(f"使用转换引擎: {get_conversion_engine()}")
    print("=" * 60)

    # 测试用例
    test_cases = [
        {
            "name": "基本表格",
            "html": """
            <table>
                <tr>
                    <th>姓名</th>
                    <th>年龄</th>
                </tr>
                <tr>
                    <td>张三</td>
                    <td>25</td>
                </tr>
            </table>
            """,
        },
        {
            "name": "合并列表格",
            "html": """
            <table>
                <tr>
                    <th colspan="2">个人信息</th>
                </tr>
                <tr>
                    <td>姓名</td>
                    <td>李四</td>
                </tr>
            </table>
            """,
        },
        {
            "name": "复杂表格",
            "html": """
            <table border="1">
                <tr>
                    <th>产品</th>
                    <th>价格</th>
                    <th>库存</th>
                </tr>
                <tr>
                    <td>苹果</td>
                    <td>5元</td>
                    <td>100</td>
                </tr>
                <tr>
                    <td>香蕉</td>
                    <td>3元</td>
                    <td>50</td>
                </tr>
            </table>
            """,
        },
    ]

    for i, test in enumerate(test_cases, 1):
        print(f"\n=== 测试{i}: {test['name']} ===")
        print("转换前:")
        print(test["html"])
        print("转换后:")
        result = convert_html_table_to_markdown(test["html"])
        print(result)

    print("\n" + "=" * 60)
    print("测试完成！")
