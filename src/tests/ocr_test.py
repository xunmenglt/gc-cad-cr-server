"""
# 参考文档
https://paddlepaddle.github.io/PaddleOCR/latest/paddlex/quick_start.html#python
"""
from paddlex import create_pipeline

pipeline = create_pipeline(pipeline="OCR")
output = pipeline.predict("../data/images/b.png")
for res in output:
    res.print()