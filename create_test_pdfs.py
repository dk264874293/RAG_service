"""
创建测试PDF文件（使用pypdfium2）
将测试用例转换为PDF格式用于系统测试
"""

import pypdfium2
from generate_test_cases import test_cases


def create_test_pdf_files(test_cases):
    """创建所有测试用例的PDF文件"""

    print("\n" + "=" * 80)
    print("开始创建测试PDF文件")
    print("=" * 80)

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n[{i}/{len(test_cases)}] 创建: {test_case['file_name']}")

        try:
            pdf = pypdfium2.PdfDocument.New()
            page = pdf.new_page()

            page_width = 595  # A4宽度
            page_height = 842  # A4高度

            # 加载cmap支持中文
            cmap = pypdfium2.PdfEmbedFont("sans-serif")

            y_position = 50
            line_height = 20

            # 添加标题
            title = f"测试用例: {test_case['description']}"
            text_object = page.insert_textobject(
                page_width / 2 - len(title) * 3,  # 简单居中
                y_position,
                title,
                font=cmap,
                fontsize=14,
            )
            text_object.set_textcolor(0, 0, 0)
            y_position += line_height * 2

            # 添加内容（逐行处理）
            lines = test_case["content"].split("\n")
            for line in lines:
                if len(line) > 80:
                    words = line.split(" ")
                    current_line = ""
                    for word in words:
                        if len(current_line + " " + word) > 75:
                            page.insert_textobject(
                                10,
                                y_position,
                                current_line.strip(),
                                font=cmap,
                                fontsize=10,
                            )
                            page.insert_textobject(
                                10, y_position, text_object, font=cmap, fontsize=10
                            )
                            y_position += line_height
                            current_line = word + " "
                        else:
                            current_line += word + " "
                    if current_line.strip():
                        page.insert_textobject(
                            10, y_position, current_line.strip(), font=cmap, fontsize=10
                        )
                        page.insert_textobject(
                            10, y_position, text_object, font=cmap, fontsize=10
                        )
                        y_position += line_height
                else:
                    page.insert_textobject(10, y_position, line, font=cmap, fontsize=10)
                    page.insert_textobject(
                        10, y_position, text_object, font=cmap, fontsize=10
                    )
                    y_position += line_height

                # 超过一页时创建新页
                if y_position > page_height - 50:
                    page = pdf.new_page()
                    y_position = 50

            # 保存文件
            output_dir = "src/pdfs/test_cases"
            import os

            os.makedirs(output_dir, exist_ok=True)

            output_path = f"{output_dir}/{test_case['file_name']}"
            pdf.save(output_path)

            print(f"    ✓ 已保存: {output_path}")

        except Exception as e:
            print(f"    ✗ 创建失败: {e}")

    print("\n" + "=" * 80)
    print(f"完成！共创建 {len(test_cases)} 个测试PDF文件")
    print(f"文件保存位置: src/pdfs/test_cases/")
    print("=" * 80)


if __name__ == "__main__":
    create_test_pdf_files(test_cases)
