'''
Author: 汪培良 rick_wang@yunquna.com
Date: 2025-11-30 19:32:44
LastEditors: 汪培良 rick_wang@yunquna.com
LastEditTime: 2025-12-01 10:07:32
FilePath: /RAG_service/demp.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
# import sys
import os
import json
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from chain.custom_prompt_template import CustomPromptTemplate, PersonInfo
from chain.advanced_prompt_template import AdvancedPersonInfoPromptTemplate

def demo_custom_template():
    template = CustomPromptTemplate(
        include_skills_analysis=True,
        include_career_advice=True,
        output_language='chinese'
    )
    person_data = {
        "name": "张三",
        "age": 30,
        "occupation": "软件工程师",
        "skills": ["JavaScript", "NestJs", "Python"],
        "experience_years": 8,
        "location": "上海"
    }

    prompt = template.format(person_info=person_data, analysis_type="comprehensive")

    return prompt

def demo_advanced_template():
    """演示高级模板功能"""
    advanced_template = AdvancedPersonInfoPromptTemplate(
        template_version="2.0.0",
        include_skills_analysis=True,
        include_career_advice=True,
        enable_cache=True
    )
    
    metadata = advanced_template.get_template_metadata()
    print("模板元数据:")
    print(json.dumps(metadata, ensure_ascii=False, indent=2))
    
    person_data = PersonInfo(
        name="李四",
        age=32,
        occupation="产品经理",
        skills=["产品设计", "数据分析", "项目管理"],
        experience_years=8,
        location="上海"
    )
    
    try:
        prompt = advanced_template.format_with_validation(
            person_info=person_data,
            analysis_type="comprehensive"
        )
        print("\n高级模板生成的提示:")
        print("="*30)
        print(prompt[:300] + "..." if len(prompt) > 300 else prompt)
    except ValueError as e:
        print(f"验证失败: {e}")

if __name__ == "__main__":
    prompt = demo_custom_template()
    print(prompt)

    demo_advanced_template()

