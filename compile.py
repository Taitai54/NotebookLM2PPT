# 读取toml中的版本号
# 执行编译命令
import toml
import os

# pyinstaller --clean -F -w -n notebooklm2ppt_{version} --optimize=2 --collect-all spire.presentation main.py 


with open("pyproject.toml", "r", encoding="utf-8") as f:
    pyproject_data = toml.load(f)


version = pyproject_data["project"]["version"]
output_name = f"notebooklm2ppt-{version}"
print(f"编译版本: {output_name}")

os.system(f'pyinstaller --clean -F -w -n {output_name} --optimize=2 --collect-all spire.presentation main.py ')