from loader.work_loader import WorkExtractor

if __name__ == '__main__':
    print("程序成功运行！")
    # WorkExtractor类需要DOCX格式的文件或URL
    print("注意：WorkExtractor类需要DOCX格式的文件或URL")
    print("请提供DOCX文件路径或URL进行测试")
    work_extractor = WorkExtractor(
        "https://bagejj.oss-cn-heyuan.aliyuncs.com/templates/%E5%8E%9F%E5%A7%8B%E8%AE%B0%E5%BD%952_%E7%8E%AF%E5%A2%83%E7%A9%BA%E6%B0%94%E9%87%87%E6%A0%B7%E5%8E%9F%E5%A7%8B%E8%AE%B0%E5%BD%95_CQGH_YS_02_2__8b92ecb3360139d33e9b6442f37d3a4d_1.docx",
        "tenant_id","user_id")
    work_extractor.extract()