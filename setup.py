import setuptools

from pip._internal.req import parse_requirements

# 若Discription.md中有中文 須加上 encoding="utf-8"
with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()


# 載入 requirements.txt 中的相依性
install_requires = [str(req.requirement) for req in parse_requirements('requirements.txt', session='hack')]

setuptools.setup(
    name="video-streaming-api",
    version="0.2.0",
    author="MarcoWu",
    author_email="marcowu1999@gmail.com",
    description="process video streaming",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/marcovwu/video-streaming-api",
    project_urls={
        "Source Code": "https://github.com/marcovwu/video-streaming-api",
        "Issue Tracker": "https://github.com/marcovwu/video-streaming-api/issues",
    },
    packages=setuptools.find_packages(),
    install_requires=install_requires,
    classifiers=[
        "Development Status :: 3 - Alpha",         # 開發狀態（Alpha、Beta、Production/Stable）
        "Intended Audience :: Developers",         # 目標受眾
        "Topic :: Multimedia :: Video",            # 主題分類
        "License :: OSI Approved :: MIT License",  # 軟體授權
        "Programming Language :: Python :: 3",     # 使用的編程語言版本
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Operating System :: OS Independent",      # 支援的作業系統
    ],
    python_requires='>=3.7'
)
print("Found packages:", setuptools.find_packages())
